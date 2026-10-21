from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from urllib.parse import urlencode

from .models import Membership, Task, Team


class TaskReadAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alice = User.objects.create_user(username="alice")
        cls.bob = User.objects.create_user(username="bob")
        cls.charlie = User.objects.create_user(username="charlie")

        cls.team_a = Team.objects.create(name="Team A")
        cls.team_b = Team.objects.create(name="Team B")
        cls.team_c = Team.objects.create(name="Team C")

        memberships = [
            (cls.alice, cls.team_a, Membership.Role.EDITOR),
            (cls.alice, cls.team_b, Membership.Role.VIEWER),
            (cls.bob, cls.team_a, Membership.Role.EDITOR),
            (cls.bob, cls.team_b, Membership.Role.EDITOR),
            (cls.bob, cls.team_c, Membership.Role.EDITOR),
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
            title="Planning Team A",
        )
        cls.task_b = Task.objects.create(
            team=cls.team_b,
            created_by=cls.bob,
            title="Planning Team B",
        )
        cls.task_c = Task.objects.create(
            team=cls.team_c,
            created_by=cls.charlie,
            title="Planning Team C PRIVATE-73",
            description="CONFIDENTIAL-DESCRIPTION-C",
        )

    def setUp(self):
        self.client.force_login(self.alice)

    def test_list_contains_only_accessible_tasks(self):
        response = self.client.get(reverse("tasks:list"))

        self.assertEqual(response.status_code, 200)

        returned_ids = [
            task.pk for task in response.context["tasks"]
        ]
        self.assertEqual(
            returned_ids,
            [self.task_a.pk, self.task_b.pk],
        )
        self.assertEqual(response.context["task_count"], 2)
        self.assertNotContains(response, self.task_c.title)

    def test_other_team_detail_is_not_accessible(self):
        url = reverse("tasks:detail", args=[self.task_c.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(
            response,
            self.task_c.title,
            status_code=404,
        )
        self.assertNotContains(
            response,
            self.task_c.description,
            status_code=404,
        )

    def test_editor_read_team_A_tasks(self):
        url = reverse("tasks:detail", args=[self.task_a.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        task = response.context["task"]
        self.assertEqual(task.pk, self.task_a.pk)

        self.assertContains(response, self.task_a.title)
        self.assertContains(response, self.task_a.description)

    def test_viewer_read_team_B_task(self):
        url = reverse("tasks:detail", args=[self.task_b.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        task = response.context["task"]
        self.assertEqual(task.pk, self.task_b.pk)

        self.assertContains(response, self.task_b.title)
        self.assertContains(response, self.task_b.description)

    def test_search_for_planning(self):
        url = reverse("tasks:list")

        response = self.client.get(
            url,
            query_params={"q": "Planning"}
        )

        self.assertEqual(response.status_code, 200)

        returned_ids = [task.pk for task in response.context["tasks"]]
        self.assertEqual(returned_ids, [self.task_a.pk, self.task_b.pk])

        self.assertEqual(response.context["task_count"], 2)        
        self.assertNotContains(response, self.task_c.title)

    def test_search_for_private_73(self):
        url = reverse("tasks:list")

        response = self.client.get(
            url,
            query_params={"q": "PRIVATE-73"}
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(response.context["tasks"])

        self.assertEqual(response.context["task_count"], 0)    
        self.assertNotContains(response, self.task_c.title)

    def test_charlie_has_no_memberships(self):
        url = reverse("tasks:list")
        self.client.force_login(self.charlie)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertFalse(response.context["tasks"])

        self.assertEqual(response.context["task_count"], 0)    

    def test_charlie_requests_the_task_he_created(self):
        url = reverse("tasks:detail", args=[self.task_c.pk])
        self.client.force_login(self.charlie)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_anonymous_list_or_detail_request(self):
        self.client.logout()

        for route in ["tasks:list", "tasks:detail"]:
            with self.subTest(route=route):
                if route == "tasks:list":
                    url = reverse("tasks:list")
                else:
                    url = reverse("tasks:detail", args=[self.task_a.pk])

                expected_url = (
                    f"{reverse('tasks:login')}?"
                    f"{urlencode({'next': url})}"
                )

                response = self.client.get(url)

                self.assertRedirects(
                    response,
                    expected_url,
                    fetch_redirect_response=False,    
                )

                for task in [self.task_a, self.task_b, self.task_c]:
                    self.assertNotContains(
                        response,
                        task.title,
                        status_code=302,
                    )

        

    def test_membership_is_removed_between_requests(self):
        list_url = reverse("tasks:list")
        detail_url = reverse("tasks:detail", args=[self.task_b.pk])

        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.task_b.pk, [task.pk for task in response.context["tasks"]])

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["task"].pk, self.task_b.pk)

        Membership.objects.filter(
            user=self.alice,
            team=self.task_b.team,
        ).delete()

        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([task.pk for task in response.context["tasks"]], [self.task_a.pk])
        self.assertEqual(response.context["task_count"], 1)
        self.assertNotContains(response, self.task_b.title)


        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(
            response,
            self.task_b.title,
            status_code=404,
        )

        self.assertTrue(Task.objects.filter(pk=self.task_b.pk).exists())
        

    def test_client_team_id_does_not_grant_access(self):
        response = self.client.get(
            reverse("tasks:list"),
            query_params={"team_id": self.task_c.team_id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [task.pk for task in response.context["tasks"]],
            [self.task_a.pk, self.task_b.pk],
        )
        self.assertEqual(response.context["task_count"], 2)
        self.assertNotContains(response, self.task_c.title)