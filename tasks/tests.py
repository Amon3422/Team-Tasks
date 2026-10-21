from http import HTTPStatus

from django.utils.html import escape
from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse
from django.contrib.auth import get_user_model

from . import views
from .models import Team, Task, Membership

class HealthEndpointTests(SimpleTestCase):
    def test_health_url_can_be_reversed(self):
        url = reverse("tasks:health")

        self.assertEqual(url, "/health/")

    def test_health_url_can_resolve_to_health_view(self):
        match = resolve("/health/")

        self.assertEqual(match.func, views.health)

    def test_health_returns_expected_json(self):
        url = reverse("tasks:health")

        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(response.headers["Content-Type"], "application/json")

        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_rejects_post(self):
        url = reverse("tasks:health")

        response = self.client.post(url)

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

        self.assertEqual(response.headers["Allow"], "GET")


class TaskListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        alice = User.objects.create_user(username="alice")
        cls.alice = alice

        team_a = Team.objects.create(name="Team A")
        team_b = Team.objects.create(name="Team B")

        Membership.objects.create(
            user=alice,
            team=team_a,
            role=Membership.Role.EDITOR,
        )

        Membership.objects.create(
            user=alice,
            team=team_b,
            role=Membership.Role.VIEWER,
        )

        cls.read_task = Task.objects.create(
            team=team_a,
            created_by=alice,
            title="Read HTTP basics",
            description="Learn request and response structure.",
        )

        cls.done_task = Task.objects.create(
            team=team_a,
            created_by=alice,
            title="Inspect browser headers",
            status=Task.Status.DONE,
        )

        cls.other_team_task = Task.objects.create(
            team=team_b,
            created_by=alice,
            title="Write authorization tests",
        )

        cls.xss_task = Task.objects.create(
            team=team_b,
            created_by=alice,
            title='<script>alert("lab")</script>',
        )


    def setUp(self):
        self.url = reverse("tasks:list")
        self.client.force_login(self.alice)

    def test_list_without_query_displays_all_accessible_tasks(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "tasks/task_list.html")
        self.assertEqual(response.context["task_count"], 4)
        self.assertEqual(len(response.context["tasks"]), 4)
        self.assertContains(response, "Found 4 tasks.")

    def test_search_is_case_insensitive(self):
        response = self.client.get(
            self.url,
            query_params={"q": "HTTP"},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["task_count"], 1)
        self.assertContains(response, "Read HTTP basics")
        self.assertNotContains(response, "Inspect browser headers")

    def test_search_with_no_match_returns_empty_result(self):
        response = self.client.get(
            self.url,
            query_params={"q": "does-not-exist"},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["task_count"], 0)
        self.assertContains(
            response,
            "No tasks matched your search.",
        )

    def test_duplicate_query_parameter_is_rejected(self):
        response = self.client.get(
            f"{self.url}?q=first&q=second"
        )

        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
        )

    def test_query_longer_than_100_characters_is_rejected(self):
        response = self.client.get(
            self.url,
            query_params={"q": "a" * 101},
        )

        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
        )

    def test_search_query_is_html_escaped(self):
        payload = '<img src=x onerror=alert("xss")>'

        response = self.client.get(
            self.url,
            query_params={"q": payload},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, escape(payload))
        self.assertNotContains(response, payload)

    def test_list_rejects_post(self):
        response = self.client.post(self.url)

        self.assertEqual(
            response.status_code,
            HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_empty_database(self):
        Task.objects.all().delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["task_count"], 0)
        self.assertContains(response, "No tasks matched your search.")


class TaskDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        alice = User.objects.create_user(username="alice")
        cls.alice = alice

        team_a = Team.objects.create(name="Team A")
        team_b = Team.objects.create(name="Team B")

        Membership.objects.create(
            user=alice,
            team=team_a,
            role=Membership.Role.EDITOR,
        )

        Membership.objects.create(
            user=alice,
            team=team_b,
            role=Membership.Role.VIEWER,
        )


        cls.read_task = Task.objects.create(
            team=team_a,
            created_by=alice,
            title="Read HTTP basics",
            description="Learn request and response structure.",
        )

        cls.done_task = Task.objects.create(
            team=team_a,
            created_by=alice,
            title="Inspect browser headers",
            status=Task.Status.DONE,
        )

        cls.other_team_task = Task.objects.create(
            team=team_b,
            created_by=alice,
            title="Write authorization tests",
        )

        cls.xss_task = Task.objects.create(
            team=team_b,
            created_by=alice,
            title='<script>alert("lab")</script>',
        )

    def setUp(self):
        self.client.force_login(self.alice)

    def test_existing_task_returns_detail_page(self):
        url = reverse("tasks:detail", args=[self.read_task.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(
            response,
            "tasks/task_detail.html",
        )
        self.assertEqual(response.context["task"].pk, self.read_task.pk)
        self.assertContains(response, "Read HTTP basics")

    def test_missing_task_returns_404(self):
        missing_id = max(
            self.read_task.pk,
            self.done_task.pk,
            self.other_team_task.pk,
            self.xss_task.pk
        ) + 1
        url = reverse("tasks:detail", args=[missing_id])

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND,
        )

    def test_non_integer_task_id_returns_404(self):
        response = self.client.get("/tasks/not-an-integer/")

        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND,
        )

    def test_task_title_is_html_escaped(self):
        payload = '<script>alert("lab")</script>'
        url = reverse("tasks:detail", args=[self.xss_task.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, escape(payload))
        self.assertNotContains(response, payload)

    def test_detail_rejects_post(self):
        url = reverse("tasks:detail", args=[self.read_task.pk])

        response = self.client.post(url)

        self.assertEqual(
            response.status_code,
            HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_saved_change(self):
        url = reverse("tasks:detail", args=[self.read_task.pk])
        old_title = self.read_task.title
        self.read_task.title = "Changed Title for Test"
        self.read_task.save()

        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Changed Title for Test")
        self.assertNotContains(response, old_title)


    def test_completed_status(self):
        url = reverse("tasks:detail", args=[self.done_task.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Done")


class HttpLabTests(SimpleTestCase):
    def setUp(self):
        self.url = reverse("tasks:http_lab")

    def test_team_id_is_optional(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(response.json()["team_id"])

    def test_valid_team_id_is_converted_to_integer(self):
        response = self.client.get(
            self.url,
            query_params={"team_id": "10"},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["team_id"], 10)
        self.assertIsInstance(response.json()["team_id"], int)

    def test_non_numeric_team_id_is_rejected(self):
        response = self.client.get(
            self.url,
            query_params={"team_id": "abc"},
        )

        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
        )

    def test_zero_team_id_is_rejected(self):
        response = self.client.get(
            self.url,
            query_params={"team_id": "0"},
        )

        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
        )

    def test_duplicate_team_id_is_rejected(self):
        response = self.client.get(
            f"{self.url}?team_id=10&team_id=20"
        )

        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
        )

    