import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Page
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post, User


class PostPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user("WithNoName")
        cls.group = Group.objects.create(
            title="test_group",
            slug="test_slug",
        )
        cls.post = Post.objects.create(
            text="test_text", author=cls.user, group=cls.group
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_posts_uses_correct_template(self):
        templates_posts_names = (
            ("posts/index.html", reverse("posts:index")),
            ("posts/post_create.html", reverse("posts:post_create")),
            (
                "posts/post_create.html",
                reverse("posts:post_edit", args=[self.post.id]),
            ),
            (
                "posts/post_detail.html",
                reverse("posts:post_detail", args=[self.post.id]),
            ),
            ("posts/profile.html", reverse("posts:profile", args=[self.user])),
            (
                "posts/group_list.html",
                reverse("posts:group_list", args=[self.group.slug]),
            ),
            (
                "posts/post_delete.html",
                reverse("posts:post_delete", args=[self.post.id]),
            ),
        )
        for template, url in templates_posts_names:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_new_post_appears_in_list_view_context(self):
        list_view_pages = (
            reverse("posts:index"),
            reverse("posts:group_list", args=[self.group.slug]),
            reverse("posts:profile", args=[self.user]),
        )
        for url in list_view_pages:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                page_obj = response.context.get("page_obj")
                self.assertIsInstance(page_obj, Page)
                self.assertEqual(len(page_obj), 1)
                self.assertEqual(page_obj[0].pk, self.post.pk)
                self.assertEqual(page_obj[0].text, self.post.text)
                self.assertEqual(page_obj[0].group, self.post.group)

    def test_context_is_correct(self):
        urls_with_context = {
            reverse("posts:index"): {},
            reverse("posts:post_create"): {},
            reverse("posts:post_edit", args=[self.post.id]): {"is_edit": True},
            reverse("posts:post_detail", args=[self.post.id]): {
                "post": self.post,
                "author": self.user,
                "posts_count": 1,
            },
            reverse("posts:profile", args=[self.user]): {"author": self.user},
            reverse("posts:group_list", args=[self.group.slug]): {
                "group": self.group
            },
        }
        for url, expected_context in urls_with_context.items():
            response = self.authorized_client.get(url)
            context = response.context
            for expected_key, expected_value in expected_context.items():
                with self.subTest(
                    view_name=response.resolver_match.view_name,
                    key=expected_key,
                    value=expected_value,
                ):
                    self.assertEqual(context.get(expected_key), expected_value)

    def test_create_edit_form(self):
        list_urls = (
            reverse("posts:post_create"),
            reverse("posts:post_edit", args=[self.post.id]),
        )
        for url in list_urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                form = response.context.get("form")
                self.assertIsInstance(form, forms.ModelForm)
                self.assertIsInstance(
                    form.fields.get("text"), forms.fields.CharField
                )
                self.assertIsInstance(
                    form.fields.get("group"), forms.fields.ChoiceField
                )

    def test_comment_appears_on_post_detail_when_created(self):
        comment_data = {
            "author": self.user,
            "post": self.post,
            "text": "comment_text",
        }
        comment = self.post.comments.create(**comment_data)
        response = self.authorized_client.get(
            reverse("posts:post_detail", args=(self.post.id,))
        )
        response_post = response.context.get("post")
        self.assertEqual(
            response_post.comments.latest("id").text, comment.text
        )

    def test_index_is_cached(self):
        post = Post.objects.create(text="anytext", author=self.user)
        response = self.authorized_client.get(reverse("posts:index"))
        post.delete()
        expected_cached_response = self.authorized_client.get(
            reverse("posts:index")
        )
        self.assertEqual(response.content, expected_cached_response.content)
        cache.clear()
        uncached_response = self.authorized_client.get(reverse("posts:index"))
        self.assertNotEqual(
            expected_cached_response.content, uncached_response.content
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user("WithNoName")
        cls.group = Group.objects.create(
            title="test_group",
            slug="test_slug",
        )
        cls.POSTS_COUNT = 15
        cls.POSTS_PER_PAGE = 10
        for _ in range(cls.POSTS_COUNT):
            Post.objects.create(
                text="test_text",
                author=cls.user,
                group=cls.group,
            )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator_pages_contains_correct_number_of_records(self):
        list_view_pages = (
            reverse("posts:index"),
            reverse("posts:group_list", args=[self.group.slug]),
            reverse("posts:profile", args=[self.user]),
        )
        second_page_expected_count = self.POSTS_COUNT - self.POSTS_PER_PAGE
        for url in list_view_pages:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                page_obj = response.context.get("page_obj")
                self.assertEqual(len(page_obj), self.POSTS_PER_PAGE)

                response = self.authorized_client.get(url + "?page=2")
                page_obj = response.context.get("page_obj")
                self.assertEqual(len(page_obj), second_page_expected_count)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ImageContextTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user("WithNoName")
        cls.group = Group.objects.create(
            title="test_group",
            slug="test_slug",
        )
        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        uploaded = SimpleUploadedFile(
            name="small.gif",
            content=small_gif,
        )
        cls.post = Post.objects.create(
            text="test_text",
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(
            TEMP_MEDIA_ROOT,
            ignore_errors=True,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator_pages_context_contains_image(self):
        list_view_pages = (
            reverse("posts:index"),
            reverse(
                "posts:group_list",
                args=[self.group.slug],
            ),
            reverse(
                "posts:profile",
                args=[self.user],
            ),
        )
        for url in list_view_pages:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(
                    response.context.get("page_obj")[0].image,
                    self.post.image,
                )

    def test_post_detail_context_contains_image(self):
        response = self.authorized_client.get(
            reverse("posts:post_detail", args=[self.post.id])
        )
        self.assertEqual(
            response.context.get("post").image,
            self.post.image,
        )


class SubscriptionViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user("WithNoName")
        cls.user = User.objects.create_user("Subscriber")
        cls.not_subscriber = User.objects.create_user("NotSubscriber")

    def setUp(self):
        self.subscriber_client = Client()
        self.subscriber_client.force_login(self.user)
        self.not_subscriber_client = Client()
        self.not_subscriber_client.force_login(self.not_subscriber)

    def test_user_can_manage_subscriptions(self):
        self.subscriber_client.get(
            reverse("posts:profile_follow", args=[self.author])
        )
        self.assertTrue(self.user.follower.filter(author=self.author).exists())
        self.subscriber_client.get(
            reverse("posts:profile_unfollow", args=[self.author])
        )
        self.assertFalse(
            self.user.follower.filter(author=self.author).exists()
        )

    def test_post_arrives_at_follow_index_only_for_subscribers(self):
        Follow.objects.create(
            author=self.author,
            user=self.user,
        )
        Post.objects.create(
            text="anytext",
            author=self.author,
        )
        users = (
            (self.subscriber_client, 1),
            (self.not_subscriber_client, 0),
        )

        for user, expected_result in users:
            with self.subTest():
                response = user.get(reverse("posts:follow_index"))
                page_obj = response.context.get("page_obj")
                self.assertEqual(len(page_obj), expected_result)
