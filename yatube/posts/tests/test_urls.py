from http import HTTPStatus
from django.core.cache import cache
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from posts.models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
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
            text='Тестовый текст, который не должен быть слишком коротким',
            group=cls.group
        )
        post_id = 1
        cls.guest_user_urls = (
            ('/', 'posts/index.html'),
            ('/group/test_slug/', 'posts/group_list.html'),
            ('/profile/testuser/', 'posts/profile.html'),
            (f'/posts/{post_id}/', 'posts/post_detail.html'),
        )
        cls.registered_user_urls = (
            ('/create/', 'posts/create_post.html'),
            (f'/posts/{post_id}/edit/', 'posts/create_post.html'),
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_public_urls_work(self):
        for url, _ in self.guest_user_urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page_url_exists_at_desired_location(self):
        """Несуществующая страница - код 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

# Серия тестов для авторизованного пользователя
    def test_post_edit_url_exists_at_desired_location(self):
        """Страница /posts/<post_id>/edit доступна только автору."""
        post_id = 1
        url_edit = f'/posts/{post_id}/edit/'
        url_login = f'/auth/login/?next={url_edit}'
        response = self.guest_client.get(url_edit, follow=True)
        self.assertRedirects(response, url_login)

    def test_post_create_url_exists_at_desired_location(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_home_url_uses_correct_template(self):
        """Страница по адресу / использует шаблон posts/index.html."""
        response = self.authorized_client.get('/')
        self.assertTemplateUsed(response, 'posts/index.html')

# проверка шаблонов по адресам
    def test_urls_guest_user_template(self):
        """проверка шаблонов для гостя."""
        for url, template in self.guest_user_urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_urls_registered_user_template(self):
        """проверка шаблонов для авторизованного пользователя."""
        for url, template in self.registered_user_urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
