import shutil
import tempfile
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from posts.forms import PostForm
from posts.models import Post, Group, Comment, Follow

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
        cls.uploaded = SimpleUploadedFile(
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
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def check_post_context(self, response, expected):
        first_object = response.context['page_obj'][0]

        template = (
            (first_object.text, expected.text),
            (first_object.group.title, expected.group.title),
            (first_object.author, expected.author),
            (first_object.image, expected.image),
        )
        for value, expected_data in template:
            self.assertEqual(value, expected_data)

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
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template, in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

# проверяем контекст
    def test_index_page_show_correct_context(self):
        """Шаблон главной страницы с правильным контекстом"""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_post_context(response, self.post)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""

        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}))
        self.check_post_context(response, self.post)

    def test_profile_page_show_correct_context(self):
        """Страница профиля с правильным контекстом"""

        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'testuser'}))
        self.check_post_context(response, self.post)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""

        response = (self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': 1})))
        object = response.context['post_detail']
        self.assertEqual(object.text, self.post.text)
        self.assertEqual(object.image, 'posts/small.gif')

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""

        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': 1}))
        # Словарь ожидаемых типов полей формы:
        form_fields = (
            ('text', forms.fields.CharField),
            ('group', forms.fields.ChoiceField),
            ('image', forms.fields.ImageField),
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
        form_fields = (
            ('text', forms.fields.CharField),
            ('group', forms.fields.ChoiceField),
        )
        for value, expected in form_fields:
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
            group=self.group2,
            image=self.uploaded,
        )
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_post_context(response, self.post2)

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
            group=self.group2,
            image=self.uploaded,
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test_slug2'}))
        self.check_post_context(response, self.post2)

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
            group=self.group2,
            image=self.uploaded,
        )
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'testuser'}))
        self.check_post_context(response, self.post2)

    # тестирование комментариев
    def test_registered_user_add_comment(self):
        """Комментировать пост может только зарегистрированный пользователь"""
        comment_text = {'text': 'Комментарий от auth-user'}
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            comment_text,
            follow=True
        )
        self.assertEqual(
            Comment.objects.get(post=self.post).text,
            comment_text['text']
        )

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
        self.assertIn(form_data['text'], response.content.decode())


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

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """ тестируем работу Paginator. Проверка вывода 10 записей"""

        num_posts_on_first_page = 10
        for reverse_name in self.list_template_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']),
                    num_posts_on_first_page
                )

    def test_second_page_contains_three_records(self):
        """ тестируем работу Paginator. Проверка вывода оставшихся 3 записей"""

        num_posts_on_second_page = 3

        for reverse_name in self.list_template_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name + '?page=2')
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
        response_one_post = self.authorized_client.get(reverse('posts:index'))
        Post.objects.create(
            author=self.user,
            text='Запись №2',
            group=self.group,
        )
        response_cached = self.authorized_client.get(reverse('posts:index'))
        # страница не изменилась
        self.assertEqual(response_one_post.content, response_cached.content)
        cache.clear()
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(response_one_post.content, response.content)


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
        Post.objects.bulk_create(
            [Post(
                text=f'Новая запись от {cls.user} № {i}',
                author=cls.user,
                group=cls.group,
            ) for i in range(4)])
        Post.objects.bulk_create(
            [Post(
                text=f'Новая запись от {cls.user2} № {i}',
                author=cls.user2,
                group=cls.group,
            ) for i in range(4)])

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_auth_user_can_follow_author(self):
        """
        Проверка возможности подписки авторизованного пользователя
        на другого автора"""
        url_follow = reverse(
            'posts:profile_follow',
            kwargs={'username': self.user2}
        )
        self.authorized_client.get(url_follow)
        self.assertEqual(Follow.objects.count(), 1)

    def test_auth_user_can_unfollow_author(self):
        """
        Проверка возможности отписки авторизованного пользователя
        от автора"""
        url_follow = reverse(
            'posts:profile_follow',
            kwargs={'username': self.user2}
        )
        url_unfollow = reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user2}
        )
        self.authorized_client.get(url_follow)
        self.assertEqual(Follow.objects.count(), 1)
        self.authorized_client.get(url_follow)
        self.authorized_client.get(url_unfollow)
        self.assertEqual(Follow.objects.count(), 0)

    def test_guest_user_cant_follow_author(self):
        """Гость не может подписаться на автора"""
        self.guest_client = Client()
        url_follow = reverse(
            'posts:profile_follow',
            kwargs={'username': self.user2}
        )
        url_login = f'{reverse("users:login")}?next={url_follow}'
        response = self.guest_client.get(url_follow)
        self.assertEqual(Follow.objects.count(), 0)
        # редирект на логин
        response = self.guest_client.get(url_follow, follow=True)
        self.assertRedirects(response, url_login)

    def test_after_follow_auth_user_see_new_posts_from_author(self):
        """
        После подписки на автора в ленте подписавшегося должна
        появиться запись"""
        url_follow = reverse(
            'posts:profile_follow',
            kwargs={'username': self.user2}
        )
        new_post = 'Отдельная запись от testuser2'
        self.authorized_client.get(url_follow)
        Post.objects.create(
            author=self.user2,
            text=new_post,
            group=self.group,
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        obj = response.context['page_obj']
        self.assertEqual(obj.paginator.object_list[0].text, new_post)

    def test_no_follow_auth_user_not_see_new_posts_from_author(self):
        """Тот, кто не подписался, не увидит новых записей от автора"""
        new_post = 'Отдельная запись от testuser2'
        Post.objects.create(
            author=self.user2,
            text=new_post,
            group=self.group,
        )
        self.user3 = User.objects.create_user(username='testuser3')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user3)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        # список должен быть пуст, т.к. подписок у нас нет
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_auth_user_cant_follow_himself(self):
        """Нельзя подписаться на самого себя"""
        url_follow = reverse(
            'posts:profile_follow',
            kwargs={'username': self.user}
        )
        self.authorized_client.get(url_follow)
        self.assertEqual(Follow.objects.count(), 0)
