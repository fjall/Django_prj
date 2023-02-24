import shutil
import tempfile
from http import HTTPStatus as status

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class FormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user("WithNoName")
        cls.fiend_user = User.objects.create_user("AnotherOne")
        cls.group = Group.objects.create(
            title="test_group",
            description="test_group_description",
            slug="test_slug",
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
        self.fiend_authorized_client = Client()
        self.fiend_authorized_client.force_login(self.fiend_user)
        self.guest_client = Client()

    def test_create_form_saving_post(self):
        post_data = {
            "text": "sometesttext",
            "group": self.group.id,
        }
        response = self.authorized_client.post(
            reverse("posts:post_create"), post_data
        )
        self.assertRedirects(
            response, reverse("posts:profile", args=(self.user,))
        )
        post = Post.objects.latest("id")
        self.assertEqual(post.text, post_data["text"])
        self.assertEqual(post.group_id, post_data["group"])

    def test_edit_form_saving_changes(self):
        existing_post = Post.objects.create(
            text="someoldtext", author=self.user
        )
        post_data = {
            "text": "somenewtext",
            "group": self.group.id,
        }
        response = self.authorized_client.post(
            reverse("posts:post_edit", args=(existing_post.id,)), post_data
        )
        self.assertRedirects(
            response, reverse("posts:post_detail", args=(existing_post.id,))
        )
        post = Post.objects.get(pk=existing_post.id)
        self.assertEqual(post.text, post_data["text"])
        self.assertEqual(post.group_id, post_data["group"])

    def test_unautorized_cant_create(self):
        post_data = {"text": "test text", "author": self.user}
        self.guest_client.post(reverse("posts:post_create"), post_data)
        self.assertEqual(Post.objects.count(), 0)

    def test_only_author_can_edit(self):
        fiends = (
            (self.guest_client, "unauthorized user"),
            (self.fiend_authorized_client, "user not author"),
        )
        post_data = {"text": "reference text", "author": self.user}
        edit_data = {"text": "different text"}
        for fiend, description in fiends:
            with self.subTest(user_type=description):
                post = Post.objects.create(**post_data)
                fiend.post(
                    reverse("posts:post_edit", args=(post.id,)), edit_data
                )
                post.refresh_from_db()
                self.assertEqual(post.text, post_data["text"])

    def test_form_with_image_creates_new_record_in_db(self):
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
        form_data = {
            "text": "text",
            "image": uploaded,
        }
        response = self.authorized_client.post(
            reverse("posts:post_create"),
            data=form_data,
        )
        self.assertEqual(response.status_code, status.FOUND)
        post = Post.objects.latest("id")
        self.assertEqual(post.text, form_data["text"])
        self.assertEqual(post.image, "posts/small.gif")

    # def test_authorized_can_comment(self):
    #     post_data = {"text": "reference text", "author": self.user}
    #     post = Post.objects.create(**post_data)
    #     post.refresh_from_db()
    #     comment_data = {"text": "text"}
    #     response = self.authorized_client.post(
    #         reverse("posts:add_comment", args=(post.id,)),
    #         comment_data,
    #     )
    #     comment = Comment.objects.latest("id")
    #     self.assertRedirects(
    #         response, reverse("posts:post_detail", args=(post.id,))
    #     )
    #     self.assertEqual(comment.text, comment_data["text"])

    # def test_unauthorized_cant_comment(self):
    #     post_data = {"text": "reference text", "author": self.user}
    #     post = Post.objects.create(**post_data)
    #     post.refresh_from_db()
    #     comment_data = {"text": "text"}
    #     response = self.guest_client.post(
    #         reverse("posts:add_comment", args=(post.id,)),
    #         comment_data,
    #     )
    #     self.assertRedirects(
    #         response,
    #         (
    #             f'{reverse("users:login")}?next='
    #             f'{reverse("posts:add_comment", args=(post.id,))}'
    #         ),
    #     )
    #     self.assertEqual(post.comments.count(), 0)

    def test_only_authorized_can_comment(self):
        post_data = {"text": "reference text", "author": self.user}
        post = Post.objects.create(**post_data)
        post.refresh_from_db()
        comment_data = {"text": "text"}
        users_with_assert_info = (
            (
                self.guest_client,
                f'{reverse("users:login")}?next='
                f'{reverse("posts:add_comment", args=(post.id,))}',
                0,
            ),
            (
                self.authorized_client,
                reverse("posts:post_detail", args=(post.id,)),
                1,
            ),
        )
        for (
            user,
            expected_url,
            expected_comments_count,
        ) in users_with_assert_info:
            with self.subTest():
                response = user.post(
                    reverse("posts:add_comment", args=(post.id,)),
                    comment_data,
                )
                self.assertRedirects(response, expected_url)
                self.assertEqual(
                    post.comments.count(), expected_comments_count
                )
                if expected_comments_count == 1:
                    comment = Comment.objects.latest("id")
                    self.assertEqual(comment.text, comment_data["text"])

    # def test_authorized_can_delete(self):
    #     post = Post.objects.create(
    #         text="anytext",
    #         author=self.user,
    #     )
    #     self.authorized_client.post(
    #         reverse("posts:post_delete", args=(post.id,))
    #     )
    #     self.assertEqual(Post.objects.count(), 0)

    def test_only_author_can_delete_post(self):
        post = Post.objects.create(
            text="anytext",
            author=self.user,
        )
        users_with_assert_info = (
            (self.guest_client, "unauthorized user", 1),
            (self.fiend_authorized_client, "fiend user", 1),
            (self.authorized_client, "author", 0),
        )
        for (
            user,
            description,
            expected_post_count_after_del,
        ) in users_with_assert_info:
            with self.subTest(user_type=description):
                response = user.post(
                    reverse("posts:post_delete", args=(post.id,))
                )
                self.assertEqual(
                    Post.objects.count(), expected_post_count_after_del
                )
                self.assertEqual(response.status_code, status.FOUND)
