import shutil
import tempfile
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from posts.models import Post, Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_create_post(self):
        """Создание записи посредством валидной формы"""
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
        form_data = {
            'group': self.group.id,
            'text': 'Тестовый текст',
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:profile', kwargs={
            'username': 'testuser'}))
        self.assertEqual(Post.objects.count(), 1)
        self.assertTrue(Post.objects.filter(group=self.group).exists())
        self.assertTrue(Post.objects.filter(author=self.user).exists())
        self.assertTrue(Post.objects.filter(text='Тестовый текст').exists())
        self.assertTrue(
            Post.objects.filter(
                image__isnull=False,
            ).exists()
        )

    def test_edit_post(self):
        """Проверка редактирования записи через форму"""
        self.post = Post.objects.create(
            author=self.user,
            text='Отдельная запись',
            group=self.group
        )
        form_data = {
            'group': self.group.id,
            'text': 'Тестовый текст после правки',
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.post.id}))
        self.assertTrue(
            Post.objects.filter(
                group=self.group,
                author=self.user,
                text='Тестовый текст после правки'
            ).exists()
        )

    def test_guest_cant_create_post(self):
        """Гость не может создать пост"""
        self.guest_client = Client()
        form_data = {
            'group': self.group.id,
            'text': 'Тестовый текст',
        }
        url_create_post = reverse('posts:post_create')
        response_guest = self.guest_client.post(
            url_create_post,
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), 0)
        self.assertRedirects(
            response_guest,
            f'/auth/login/?next={url_create_post}'
        )

    def test_guest_cant_edit_post(self):
        """Гость не может редактировать пост"""
        self.guest_client = Client()
        self.post = Post.objects.create(
            author=self.user,
            text='Отдельная запись',
            group=self.group
        )
        form_data = {
            'group': self.group.id,
            'text': 'Тестовый текст после правки',
        }
        response_guest = self.guest_client.post(
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
#1 добавить проверку поста в базе
        self.assertRedirects(
            response_guest, f'/auth/login/?next=/posts/{self.post.id}/edit/')
