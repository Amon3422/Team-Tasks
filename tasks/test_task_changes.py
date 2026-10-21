from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Membership, Task, Team


class TaskChangeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.alice = User.objects.create_user(username="alice")
        cls.bob = User.objects.create_user(username="bob")
        cls.charlie = User.objects.create_user(username="charlie")

        cls.team_a = Team.objects.create(name="Team A")
        cls.team_b = Team.objects.create(name="Team B")

        memberships = [
            (cls.alice, cls.team_a, Membership.Role.EDITOR),
            (cls.alice, cls.team_b, Membership.Role.VIEWER),
            (cls.bob, cls.team_a, Membership.Role.EDITOR),
            (cls.bob, cls.team_b, Membership.Role.EDITOR),
            (cls.charlie, cls.team_a, Membership.Role.VIEWER),
        ]

        for user, team, role in memberships:
            Membership.objects.create(
                user=user,
                team=team,
                role=role,
            )

        cls.task_a = Task.objects.create(
            team=cls.team_a,
            created_by=cls.bob,
            title="Original Team A task",
            description="Original description",
        )

        cls.task_b = Task.objects.create(
            team=cls.team_b,
            created_by=cls.bob,
            title="Original Team B task",
        )

    def setUp(self):
        self.client.force_login(self.alice)

    def task_snapshot(self):
        return list(
            Task.objects.order_by("pk").values(
                "id",
                "title",
                "description",
                "status",
                "team_id",
                "created_by_id",
            )
        )

    def valid_payload(self, **overrides):
        payload = {
            "title": "Updated title",
            "description": "Updated description",
            "status": Task.Status.DONE,
        }
        payload.update(overrides)
        return payload

    def test_editor_can_edit_another_members_task(self):
        before = self.task_snapshot()
        url = reverse("tasks:edit", args=[self.task_a.pk])
        payload = self.valid_payload()

        response = self.client.post(url, payload)

        self.assertRedirects(
            response,
            reverse("tasks:detail", args=[self.task_a.pk]),
        )

        expected = [
            {**row, **payload} if row["id"] == self.task_a.pk else row
            for row in before
        ]

        # Verifies the target's changes, unchanged ownership,
        # unchanged row count, and preservation of other tasks.
        self.assertEqual(self.task_snapshot(), expected)

    def test_viewer_cannot_edit_even_if_editor_elsewhere(self):
        before = self.task_snapshot()
        url = reverse("tasks:edit", args=[self.task_b.pk])

        response = self.client.post(url, self.valid_payload())

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.task_snapshot(), before)

    def test_editor_gets_edit_page(self):
        before = self.task_snapshot()
        url = reverse("tasks:edit", args=[self.task_a.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tasks/task_form.html")

        form = response.context["form"]

        self.assertFalse(form.is_bound)
        self.assertEqual(form.instance.pk, self.task_a.pk)
        self.assertEqual(form["title"].value(), self.task_a.title)
        self.assertEqual(
            form["description"].value(),
            self.task_a.description,
        )
        self.assertEqual(form["status"].value(), self.task_a.status)
        self.assertEqual(self.task_snapshot(), before)

    def test_invalid_edit(self):
        url = reverse("tasks:edit", args=[self.task_a.pk])
        before = self.task_snapshot()

        cases = [
            ("title", ""),
            ("title", "    "),
            ("title", "a" * 201),
            ("status", "unknown"),
        ]

        for field, value in cases:
            with self.subTest(field=field, value=repr(value)):
                payload = self.valid_payload()
                payload[field] = value

                response = self.client.post(url, payload)

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response,
                    "tasks/task_form.html",
                )

                form = response.context["form"]

                self.assertTrue(form.is_bound)
                self.assertIn(field, form.errors)
                self.assertEqual(self.task_snapshot(), before)

    def test_forged_edit_fields(self):
        before = self.task_snapshot()
        url = reverse("tasks:edit", args=[self.task_a.pk])

        allowed_changes = self.valid_payload(
            title="Forged edit fields",
            description="Forged edit fields description",
        )
        payload = {
            **allowed_changes,
            "team": self.team_b.pk,
            "created_by": self.alice.pk,
        }

        response = self.client.post(url, payload)

        self.assertRedirects(
            response,
            reverse("tasks:detail", args=[self.task_a.pk]),
        )

        # Only allowlisted changes belong in the expected state.
        expected = [
            {**row, **allowed_changes}
            if row["id"] == self.task_a.pk
            else row
            for row in before
        ]

        self.assertEqual(self.task_snapshot(), expected)

    def test_non_member_cannot_edit(self):
        self.client.force_login(self.charlie)

        before = self.task_snapshot()
        url = reverse("tasks:edit", args=[self.task_b.pk])

        response = self.client.post(url, self.valid_payload())

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.task_snapshot(), before)

    def test_editor_gets_delete_page(self):
        before = self.task_snapshot()
        url = reverse("tasks:delete", args=[self.task_a.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "tasks/task_confirm_delete.html",
        )
        self.assertEqual(
            response.context["task"].pk,
            self.task_a.pk,
        )
        self.assertContains(response, self.task_a.title)
        self.assertEqual(self.task_snapshot(), before)

    def test_editor_posts_delete(self):
        before = self.task_snapshot()
        task_id = self.task_a.pk
        url = reverse("tasks:delete", args=[task_id])

        response = self.client.post(url)

        self.assertRedirects(response, reverse("tasks:list"))

        expected = [
            row for row in before
            if row["id"] != task_id
        ]

        self.assertEqual(self.task_snapshot(), expected)

    def test_viewer_or_non_member_cannot_delete(self):
        before = self.task_snapshot()
        url = reverse("tasks:delete", args=[self.task_b.pk])

        for user in (self.alice, self.charlie):
            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.post(url)

                self.assertEqual(response.status_code, 404)
                self.assertEqual(self.task_snapshot(), before)

    def test_unauthorized_gets_do_not_expose_task(self):
        before = self.task_snapshot()

        for user in (self.alice, self.charlie):
            for route in ("tasks:edit", "tasks:delete"):
                with self.subTest(user=user.username, route=route):
                    self.client.force_login(user)
                    url = reverse(route, args=[self.task_b.pk])

                    response = self.client.get(url)

                    self.assertEqual(response.status_code, 404)
                    self.assertNotContains(
                        response,
                        self.task_b.title,
                        status_code=404,
                    )
                    self.assertEqual(self.task_snapshot(), before)

    def test_anonymous_requests_redirect_to_login(self):
        self.client.logout()
        before = self.task_snapshot()

        for route in ("tasks:edit", "tasks:delete"):
            for method in ("GET", "POST"):
                with self.subTest(route=route, method=method):
                    # This endpoint expects a Task ID, not a Team ID.
                    url = reverse(route, args=[self.task_b.pk])

                    if method == "GET":
                        response = self.client.get(url)
                    else:
                        response = self.client.post(
                            url,
                            self.valid_payload(),
                        )

                    expected_url = (
                        f"{reverse('tasks:login')}?"
                        f"{urlencode({'next': url})}"
                    )

                    self.assertRedirects(
                        response,
                        expected_url,
                        fetch_redirect_response=False,
                    )
                    self.assertEqual(self.task_snapshot(), before)

    def test_missing_task_id_returns_404(self):
        missing_id = max(self.task_a.pk, self.task_b.pk) + 1
        before = self.task_snapshot()

        self.assertFalse(
            Task.objects.filter(pk=missing_id).exists()
        )

        for route in ("tasks:edit", "tasks:delete"):
            for method in ("GET", "POST"):
                with self.subTest(route=route, method=method):
                    url = reverse(route, args=[missing_id])

                    if method == "GET":
                        response = self.client.get(url)
                    else:
                        response = self.client.post(
                            url,
                            self.valid_payload(),
                        )

                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(self.task_snapshot(), before)

    def test_unsupported_method_returns_405(self):
        before = self.task_snapshot()

        for route in ("tasks:edit", "tasks:delete"):
            with self.subTest(route=route):
                url = reverse(route, args=[self.task_a.pk])

                response = self.client.put(url)

                self.assertEqual(response.status_code, 405)
                self.assertEqual(self.task_snapshot(), before)

    def test_edit_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)

        url = reverse("tasks:edit", args=[self.task_a.pk])
        before = self.task_snapshot()
        payload = self.valid_payload(
            title="Updated through a CSRF-protected request",
        )

        rejected = client.post(url, payload)

        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(self.task_snapshot(), before)

        page = client.get(url)

        self.assertEqual(page.status_code, 200)
        self.assertEqual(self.task_snapshot(), before)

        token = client.cookies["csrftoken"].value

        accepted = client.post(
            url,
            {**payload, "csrfmiddlewaretoken": token},
        )

        self.assertRedirects(
            accepted,
            reverse("tasks:detail", args=[self.task_a.pk]),
            fetch_redirect_response=False,
        )

        expected = [
            {**row, **payload} if row["id"] == self.task_a.pk else row
            for row in before
        ]

        self.assertEqual(self.task_snapshot(), expected)

    def test_delete_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)

        task_id = self.task_a.pk
        url = reverse("tasks:delete", args=[task_id])
        before = self.task_snapshot()

        rejected = client.post(url)

        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(self.task_snapshot(), before)

        page = client.get(url)

        self.assertEqual(page.status_code, 200)
        self.assertEqual(self.task_snapshot(), before)

        token = client.cookies["csrftoken"].value

        accepted = client.post(
            url,
            {"csrfmiddlewaretoken": token},
        )

        self.assertRedirects(
            accepted,
            reverse("tasks:list"),
            fetch_redirect_response=False,
        )

        expected = [
            row for row in before
            if row["id"] != task_id
        ]

        self.assertEqual(self.task_snapshot(), expected)

    def _assert_permission_rechecked_before_post(self, route, payload):
        before = self.task_snapshot()
        url = reverse(route, args=[self.task_a.pk])

        # Alice initially has permission to open the page.
        page = self.client.get(url)

        self.assertEqual(page.status_code, 200)
        self.assertEqual(self.task_snapshot(), before)

        # Revoke editor privileges after the GET but before the POST.
        membership = Membership.objects.get(
            user=self.alice,
            team=self.team_a,
        )
        membership.role = Membership.Role.VIEWER
        membership.save(update_fields=["role"])

        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.task_snapshot(), before)

    def test_edit_rechecks_permission_after_get(self):
        self._assert_permission_rechecked_before_post(
            "tasks:edit",
            self.valid_payload(),
        )

    def test_delete_rechecks_permission_after_get(self):
        self._assert_permission_rechecked_before_post(
            "tasks:delete",
            {},
        )