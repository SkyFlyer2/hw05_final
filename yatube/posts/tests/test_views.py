import shutil
import tempfile
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from posts.forms import PostForm
from posts.models import Post, Group, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class GroupPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Отдельная запись',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

# Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""

        self.templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': 'test_slug'}): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': 'testuser'}): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                'post_id': 1}): 'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={
                'post_id': 1}): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }

        for reverse_name, template, in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
#
# проверяем контекст
    def test_index_page_show_correct_context(self):
        """Шаблон главной страницы с правильным контекстом"""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Отдельная запись')
        self.assertTrue(first_object.image, 'posts/small.gif')
#
    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""

        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.group.title, self.group.title)
        self.assertEqual(first_object.text, 'Отдельная запись')
        self.assertTrue(first_object.image, 'posts/small.gif')
#
    def test_profile_page_show_correct_context(self):
        """Страница профиля с правильным контекстом"""

        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'testuser'}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author, self.user)
        self.assertTrue(first_object.image, 'posts/small.gif')
#
    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""

        response = (self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': 1})))
        object = response.context['post_detail']
        self.assertEqual(object.text, 'Отдельная запись')
        self.assertTrue(object.image, 'posts/small.gif')
#        print(response.content.decode())


    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""

        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': 1}))
        # Словарь ожидаемых типов полей формы:
        form_fields = (
            ('text', forms.fields.CharField),
            ('group', forms.fields.ChoiceField),
        )
        for value, expected in form_fields:
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertIsInstance(response.context.get('form'), PostForm)
        self.assertIsInstance(response.context.get('is_edit'), bool)
        self.assertTrue(response.context.get('is_edit'))

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""

        response = self.authorized_client.get(
            reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertIsInstance(response.context.get('form'), PostForm)

# дополнительная проверка при создании поста
    def test_post_on_main_page(self):
        """Проверяем что новая запись группы появилась на главной странице"""

        self.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug2',
            description='Тестовое описание'
        )
        self.post2 = Post.objects.create(
            author=self.user,
            text='Отдельная запись',
            group=self.group2
        )
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Отдельная запись')
        self.assertEqual(first_object.group, self.group2)

    def test_post_second_group_list_page(self):
        """Проверяем что новая запись группы появилась на странице группы"""

        self.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug2',
            description='Тестовое описание'
        )
        self.post2 = Post.objects.create(
            author=self.user,
            text='Отдельная запись',
            group=self.group2
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test_slug2'}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.group.title, self.group2.title)
        self.assertEqual(first_object.text, 'Отдельная запись')

    def test_post_profile_page(self):
        """Проверяем что новая запись группы появилась в профиле
           пользователя"""

        self.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug2',
            description='Тестовое описание'
        )
        self.post2 = Post.objects.create(
            author=self.user,
            text='Отдельная запись',
            group=self.group2
        )
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'testuser'}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post2.text)
        self.assertEqual(first_object.author, self.user)
        self.assertEqual(first_object.group, self.group2)

# тестирование комментариев
    def test_registered_user_add_comment(self):
        """Комментировать пост может только зарегистрированный пользователь"""
        comment_text = {'text': 'Комментарий от auth-user'}
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            comment_text,
            follow=True
        )
        self.assertTrue(response.context.get('comments'))
        self.assertEqual(
            Comment.objects.get(post=self.post).text,
            comment_text['text']
        )

#        print(Comment.objects.get(post=self.post).text)
#        print(response.context.get('comments')[0].text)
#        post = Post.objects.last()

    def test_guest_can_not_add_comment(self):
        """Гость не может добавлять комментарии"""
        self.guest_client = Client()
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data={'text': 'Комментарий от guest-user'},
            follow=True
        )
        self.assertFalse(response.context.get('comments'))

    def test_comment_appears_page_post(self):
        """Комментарий появляется на странице поста"""
        form_data = {
            'text': 'Комментарий для поста 1',
            'author': self.user,
        }
        self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': 1}
            ),
            data=form_data,
        )
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': 1}
            ),
        )
        self.assertEqual(response.context.get('comments')[0].text, form_data['text'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )

    # создаём 13 тестовых записей.
        list_posts = [Post(
            text=f'Текст для проверки {i}',
            author=cls.user,
            group=cls.group,
        ) for i in range(13)]
        Post.objects.bulk_create(list_posts)

    # список шаблонов для проверки работы paginator
        cls.list_template_names = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}),
            reverse('posts:profile', kwargs={'username': 'testuser'}),
        }

    def test_first_page_contains_ten_records(self):
        """ тестируем работу Paginator. Проверка вывода 10 записей"""

        num_posts_on_first_page = 10
        for reverse_name in self.list_template_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']),
                    num_posts_on_first_page
                )

    def test_second_page_contains_three_records(self):
        """ тестируем работу Paginator. Проверка вывода оставшихся 3 записей"""

        num_posts_on_second_page = 3

        for reverse_name in self.list_template_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    num_posts_on_second_page
                )


class IndexPageCacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Отдельная запись',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_index_page_cache(self):
        """Проверка кеширования главной страницы"""
        key = make_template_fragment_key('index_page')
        response_one_post = self.authorized_client.get(reverse('posts:index'))
        Post.objects.create(
            author=self.user,
            text='Запись №2',
            group=self.group,
        )
        response_cached = self.authorized_client.get(reverse('posts:index'))
        # страница не изменилась
        self.assertEqual(response_one_post.content, response_cached.content)
#        cache.delete(key)
        cache.clear()
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(response_one_post.content, response.content)
#        print(response.content.decode())


class FollowServiceTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.user2 = User.objects.create_user(username='testuser2')
        cls.group = Group.objects.create(
            title='Тестовая группа1',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Отдельная запись от testuser',
            group=cls.group,
        )
        cls.post2 = Post.objects.create(
            author=cls.user2,
            text='Отдельная запись от testuser2',
            group=cls.group,
        )
        list_posts = [Post(
            text=f'Новая запись от {cls.user} № {i}',
            author=cls.user,
            group=cls.group,
        ) for i in range(4)]
        Post.objects.bulk_create(list_posts)

        list_posts = [Post(
            text=f'Новая запись от {cls.user2} № {i}',
            author=cls.user2,
            group=cls.group,
        ) for i in range(4)]
        Post.objects.bulk_create(list_posts)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        cache.clear()

    def test_auth_user_can_follow_second_user(self):
        """
        Проверка возможности подписки авторизованного пользователя
        на другого автора"""

        #response = self.authorized_client.get(reverse('posts:follow_index', kwargs={'username': 'testuser'}))
        print(reverse('posts:follow_index', kwargs={'username': 'testuser'}))
        #print(response)
        first_object = response.context['page_obj'][0]
#        print(response.content.decode())
