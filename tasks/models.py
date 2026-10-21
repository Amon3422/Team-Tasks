from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=100)

    def __str__ (self):
        return self.name

class Membership(models.Model):
    class Role(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        EDITOR = "editor", "Editor"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "team"],
                name="unique_user_team_membership",
            ),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.team_id} ({self.role})"

class Task(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DONE = "done", "Done"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tasks",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    def clean(self):
        super().clean()

        if isinstance(self.title, str) and not self.title.strip(): 
            raise ValidationError(
                {"title": "Title must contain non-whitespace character."}
            )

    def __str__ (self):
        return self.title