from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Membership, Team

class MembershipTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alice = User.objects.create_user(username="alice")
        cls.bob = User.objects.create_user(username="bob")
        cls.team_a = Team.objects.create(name="Team A")
        cls.team_b = Team.objects.create(name="Team B")

    def test_duplicate_membership_is_rejected(self):
        Membership.objects.create(
            user=self.alice,
            team=self.team_a,
            role=Membership.Role.VIEWER
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(
                    user=self.alice,
                    team=self.team_a,
                    role=Membership.Role.EDITOR
                )

        memberships = Membership.objects.filter(
            user=self.alice,
            team=self.team_a
        )

        self.assertEqual(memberships.count(), 1)
        self.assertEqual(
            memberships.get().role,
            Membership.Role.VIEWER,
        )

    def test_same_user_in_different_teams(self):
        Membership.objects.create(
            user=self.alice,
            team=self.team_a,
            role=Membership.Role.EDITOR,
        )

        Membership.objects.create(
            user=self.alice,
            team=self.team_b,
            role=Membership.Role.VIEWER,
        )
        memberships = Membership.objects.filter(
            user=self.alice
        )
        self.assertEqual(memberships.count(), 2)

        team_a_membership = memberships.get(team=self.team_a)
        team_b_membership = memberships.get(team=self.team_b)

        self.assertEqual(
            team_a_membership.role,
            Membership.Role.EDITOR
        )

        self.assertEqual(
            team_b_membership.role,
            Membership.Role.VIEWER,
        )

    def test_different_users_same_team(self):
        Membership.objects.create(
            user=self.alice,
            team=self.team_a,
            role=Membership.Role.VIEWER
        )

        Membership.objects.create(
            user=self.bob,
            team=self.team_a,
            role=Membership.Role.VIEWER
        )        

        memberships = Membership.objects.filter(team=self.team_a)

        self.assertEqual(memberships.count(), 2)

        self.assertEqual(
            set(memberships.values_list("user_id", flat=True)),
            {self.alice.pk, self.bob.pk}
        )

    def test_default_role_is_viewer(self):
        membership = Membership.objects.create(
            user=self.alice,
            team=self.team_a
        )

        membership.refresh_from_db()

        self.assertEqual(
            membership.role,
            Membership.Role.VIEWER
        )

        