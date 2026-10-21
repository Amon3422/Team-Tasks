from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.db.models.deletion import ProtectedError

from .models import Task, Team

class TaskModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alice = User.objects.create_user(username="alice")
        cls.team_a = Team.objects.create(name="Team A")
        cls.team_b = Team.objects.create(name="Team B")

    def test_valid_task_is_saved_with_default_values(self):
        task = Task(
            team=self.team_a,
            created_by=self.alice,
            title="Write authorization tests",
        )

        task.full_clean() #Call our clean() function to make sure no empty or only-whitespace title
        task.save() #If pass our clean() check, insert validated object

        saved = Task.objects.get(pk=task.pk)
        
        self.assertEqual(saved.title, "Write authorization tests")
        self.assertEqual(saved.team_id, self.team_a.pk)
        self.assertEqual(saved.created_by_id, self.alice.pk)
        self.assertEqual(saved.status, Task.Status.OPEN)
        self.assertEqual(saved.description, "")

    def test_blank_title_is_rejected_by_model_validation(self):
        for title in ("", "   "):
            with self.subTest(title=title):
                task = Task(
                    team=self.team_a,
                    created_by=self.alice,
                    title=title,
                )

                with self.assertRaises(ValidationError) as caught:
                    task.full_clean()

                self.assertIn("title", caught.exception.message_dict)


    def test_invalid_status(self):
        task = Task(
            team=self.team_a,
            created_by=self.alice,
            title="Test Invalid Status",
            status="unknown"
        )

        with self.assertRaises(ValidationError) as caught:
            task.full_clean()

        self.assertIn("status", caught.exception.message_dict)

    def test_creator_deletion_is_protected(self):
        task = Task(
            team=self.team_a,
            created_by=self.alice,
            title="Test Creator Deletion Is Protected"
        )

        task.full_clean()
        task.save()

        task_id = task.pk
        user_id = self.alice.pk
        
        with self.assertRaises(ProtectedError):
            self.alice.delete()

        User = get_user_model()

        self.assertTrue(User.objects.filter(pk=user_id).exists())

        self.assertTrue(Task.objects.filter(pk=task_id).exists())

    def test_team_deletion_removes_only_its_tasks(self):
        task1 = Task(
            team=self.team_a,
            created_by=self.alice,
            title="Test Team Deletion Is Protected",
        )

        task2 = Task(
            team=self.team_b,
            created_by=self.alice,
            title="Test Team Deletion Is Protected 2",
        )

        task1.full_clean()
        task2.full_clean()
        task1.save()
        task2.save()

        User = get_user_model()

        task1_id = task1.pk
        task2_id = task2.pk
        alice_id = self.alice.pk
        team_a_id = self.team_a.pk


        self.team_a.delete()

        self.assertFalse(Team.objects.filter(pk=team_a_id).exists())
        self.assertFalse(Task.objects.filter(pk=task1_id).exists())
        self.assertTrue(Task.objects.filter(pk=task2_id).exists())
        self.assertTrue(User.objects.filter(pk=alice_id).exists())