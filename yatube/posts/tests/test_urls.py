from http import HTTPStatus as status

from django.test import Client, TestCase

from ..models import Group, Post, User


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_homepage(self):
        response = self.guest_client.get("/")
        self.assertEqual(response.status_code, status.OK)


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user("WithNoName")
        cls.fiend_user = User.objects.create_user("AnotherOne")
        cls.post = Post.objects.create(
            text="test_text",
            author=cls.user,
        )
        cls.group = Group.objects.create(
            title="test_group",
            description="test_group_description",
            slug="test_slug",
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.fiend_authorized_client = Client()
        self.fiend_authorized_client.force_login(self.fiend_user)

    def test_urls_uses_correct_template(self):
        templates_url_names = (
            ("posts/index.html", "/"),
            ("posts/post_create.html", "/create/"),
            ("posts/post_create.html", f"/posts/{self.post.id}/edit/"),
            ("posts/post_detail.html", f"/posts/{self.post.id}/"),
            ("posts/profile.html", f"/profile/{self.user}/"),
            ("posts/group_list.html", f"/group/{self.group.slug}/"),
        )

        for template, address in templates_url_names:
            with self.subTest(adress=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_404_for_unexisted(self):
        unexisted_id = 15
        unexisted_user = "Superman"
        unexisted_slug = "SupermanFans"
        fake_urls = (
            f"/posts/{unexisted_id}/",
            f"/profile/{unexisted_user}/",
            f"/group/{unexisted_slug}/",
            "/unexisted/",
        )
        for adress in fake_urls:
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, status.NOT_FOUND)

    def test_editing_not_author(self):
        response = self.fiend_authorized_client.get(
            f"/posts/{self.post.id}/edit/"
        )
        self.assertRedirects(response, f"/posts/{self.post.id}/")

    def test_access_to_login_required_urls(self):
        login_required_urls = (
            f"/posts/{self.post.id}/edit/",
            "/create/",
        )

        for address in login_required_urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertRedirects(response, f"/auth/login/?next={address}")
