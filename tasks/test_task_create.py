from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from http import HTTPStatus
from urllib.parse import urlencode
from django.test import Client


from .models import Task, Team, Membership

class TaskCreateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alice = User.objects.create_user(username="alice")
        cls.bob = User.objects.create_user(username="bob")

        cls.team_a = Team.objects.create(name="Team A")
        cls.team_b = Team.objects.create(name="Team B")

        Membership.objects.create(
            user=cls.alice,
            team=cls.team_a,
            role=Membership.Role.EDITOR,
        )

        Membership.objects.create(
            user=cls.alice,
            team=cls.team_b,
            role=Membership.Role.VIEWER,
        )

        Membership.objects.create(
            user=cls.bob,
            team=cls.team_b,
            role=Membership.Role.EDITOR,
        )

    def setUp(self):
        self.url = reverse("tasks:create", args=[self.team_a.pk])

        self.client.force_login(self.alice)

    def test_get_displays_form_without_creating_task(self):
        before = Task.objects.count()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Task.objects.count(), before)
        self.assertTemplateUsed(response, "tasks/task_form.html")
        self.assertFalse(response.context["form"].is_bound)

        self.assertContains(
            response,
            "<h1>Create task</h1>",
            html=True,
        )
        self.assertContains(
            response,
            '<button type="submit">Create task</button>',
            html=True,
        )
        
    def test_editor_can_create_task(self):
        response = self.client.post(
            self.url,
            {
                "title": "Write creation tests",
                "description": "Check validation and permission.",
                "status": Task.Status.OPEN,
            },
        )
    
        self.assertEqual(Task.objects.count(), 1)

        task = Task.objects.get()

        self.assertEqual(task.title, "Write creation tests")
        self.assertEqual(task.team_id, self.team_a.pk)
        self.assertEqual(task.created_by_id, self.alice.pk)
        self.assertEqual(task.status, Task.Status.OPEN)

        self.assertRedirects(
            response,
            reverse("tasks:detail", args=[task.pk]),
        )


    def test_title_validation(self):
        for title in ["", "   ", "a" * 201]:
            with self.subTest(title=repr(title)):
                before = Task.objects.count()

                response = self.client.post(
                    self.url,
                    {
                        "title": title,
                        "description": "Check title validation",
                        "status": Task.Status.OPEN,
                    },
                )

                self.assertEqual(response.status_code, HTTPStatus.OK)

                form = response.context["form"]
                self.assertIn("title", form.errors)

                self.assertEqual(Task.objects.count(), before)

    def test_status_validation(self):
        before = Task.objects.count()

        response = self.client.post(
            self.url,
            {
                "title": "Test unknown status",
                "description": "",
                "status": "unknown",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tasks/task_form.html")

        form = response.context["form"]
        self.assertIn("status", form.errors)

        self.assertEqual(Task.objects.count(), before)

        self.assertContains(
            response,
            "<h1>Create task</h1>",
            html=True,
        )
        self.assertContains(
            response,
            '<button type="submit">Create task</button>',
            html=True,
        )

    def test_user_with_only_viewer_permission_create_task(self):
        before = Task.objects.count()
        url = reverse("tasks:create", args=[self.team_b.pk])

        response = self.client.post(
            url,
            {
                "title": "Test user with only viewer permission create task",
                "description": "",
                "status": Task.Status.OPEN,
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.assertEqual(Task.objects.count(), before)

    def test_user_with_no_permission_create_task(self):
        before = Task.objects.count()

        self.client.force_login(self.bob)

        response = self.client.post(
            self.url,
            {
                "title": "Test user with no permission create task",
                "description": "",
                "status": Task.Status.OPEN
            }
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        self.assertEqual(Task.objects.count(), before)

    def test_anonymous_get_or_post(self):
        before = Task.objects.count()
        
        self.client.logout()

        get_response = self.client.get(self.url)
        post_response = self.client.post(
            self.url,
            {
                "title": "Test anonymous Post",
                "description": "",
                "status": Task.Status.OPEN,
            },
        )

        expected_url = (
            f"{reverse('tasks:login')}?"
            f"{urlencode({'next': self.url})}"
        )

        self.assertRedirects(
            get_response,
            expected_url,
            fetch_redirect_response=False,
        )

        self.assertRedirects(
            post_response,
            expected_url,
            fetch_redirect_response=False,
        )

        self.assertEqual(Task.objects.count(), before)

    def test_authenticated_put(self):
        before = Task.objects.count()

        response = self.client.put(
            self.url,
            {
                "title": "Test authenticated Put",
                "description": "",
                "status": Task.Status.OPEN
            }
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

        self.assertEqual(Task.objects.count(), before)

    def test_forged_fields(self):
        before = Task.objects.count()

        response = self.client.post(
            self.url,
            {
                "title": "Attempt to forge ownership",
                "description": "",
                "status": Task.Status.OPEN,
                "created_by": self.bob.pk,
                "team": self.team_b.pk,
            }
        )

        task = Task.objects.get(title="Attempt to forge ownership")

        self.assertEqual(Task.objects.count(), before + 1)
        self.assertEqual(task.created_by_id, self.alice.pk)
        self.assertEqual(task.team_id, self.team_a.pk)
        self.assertRedirects(
            response,
            reverse("tasks:detail", args=[task.pk])
        )

    def test_creation_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)

        payload = {
            "title": "Check CSRF",
            "description": "",
            "status": Task.Status.OPEN, 
        }
        before = Task.objects.count()

        rejected = client.post(self.url, payload)

        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(Task.objects.count(), before)

        page = client.get(self.url)
        self.assertEqual(page.status_code, 200)

        token = client.cookies["csrftoken"].value
        accepted = client.post(
            self.url,
            {**payload, "csrfmiddlewaretoken": token},
        )

        self.assertEqual(accepted.status_code, 302)
        self.assertEqual(Task.objects.count(), before + 1)