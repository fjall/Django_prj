from django.test import Client, TestCase


class CustomErrorsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        self.guest_client = Client(enforce_csrf_checks=True)

    def test_urls_uses_correct_template(self):
        templates_url_names = (
            ("core/404.html", "get", "/unexisting/"),
            ("core/403csrf.html", "post", "/create/"),
        )

        for template, method, address in templates_url_names:
            with self.subTest(method=method):
                response = getattr(self.guest_client, method)(address)
                self.assertTemplateUsed(response, template)
