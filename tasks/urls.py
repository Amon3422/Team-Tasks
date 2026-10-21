from django.urls import path
from django.contrib.auth.views import LoginView
from . import views

app_name = "tasks"

urlpatterns = [
    path(
        "accounts/login/",
        LoginView.as_view(
            template_name="tasks/login.html",
            next_page="tasks:list",
        ),
        name="login",
        ),
    path(
        "team/<int:team_id>/tasks/new/",
        views.task_create,
        name="create",
    ),
    path(
        "tasks/<int:task_id>/edit/",
        views.task_edit,
        name="edit"
    ),
    path(
        "task/<int:task_id>/delete/",
        views.task_delete,
        name="delete",
    ),
    path("health/", views.health, name="health"),
    path("tasks/", views.task_list, name="list"),
    path("tasks/<int:task_id>/", views.task_detail, name="detail"),
    path("http-form/", views.http_form, name="http_form"),
    path("http-lab/", views.http_lab, name="http_lab"),
]

