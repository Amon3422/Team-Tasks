from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods, require_GET

from .models import Task, Membership, Team
from .forms import TaskForm

@login_required(login_url="tasks:login")
@require_GET
def task_list(request):
    query_values = request.GET.getlist("q")

    if len(query_values) > 1:
        return HttpResponseBadRequest("Accept query at most once")

    query = query_values[0].strip() if query_values else ""

    if len(query) > 100:
        return HttpResponseBadRequest("Query should not exceed 100 characters")

    visible_tasks = _tasks_visible_to(request.user)

    if query:
        visible_tasks = visible_tasks.filter(title__icontains=query)

    context = {
        "tasks": visible_tasks,
        "query": query,
        "task_count": len(visible_tasks),
    }

    
    return render(request, "tasks/task_list.html" ,context)

@login_required(login_url="tasks:login")
@require_GET
def task_detail(request, task_id):
    task = get_object_or_404(_tasks_visible_to(request.user), pk=task_id)

    return render(
        request,
        "tasks/task_detail.html",
        {"task": task},
    )



@require_http_methods(["GET", "POST"])
def http_form(request):
    if request.method == "GET":
        return render(request, "tasks/http_form.html")

    title = request.POST.get("title", "").strip()
    team_id = request.POST.get("team_id", "")
    errors = {}

    if not title:
        errors["title"] = "Title is required"

    if not team_id.isdecimal() or int(team_id) <= 0:
        errors["team_id"] = "team_id should be a positive integer"

    if errors:
        return JsonResponse(
            {"errors": errors},
            status=400
        )

    return JsonResponse(
        {
            "Message": "POST form successfully",
            "title": title,
            "team_id": int(team_id)
        },
        status=201
    )


@require_GET
def http_lab(request):
    team_id_values = request.GET.getlist("team_id")

    if len(team_id_values) > 1:
        return JsonResponse(
            {"error": "team_id must be provided at most once"},
            status=400,
        )

    if not team_id_values:
        team_id = None
    else:
        team_id_text = team_id_values[0].strip()

        if not team_id_text.isdecimal() or int(team_id_text) <= 0:
            return JsonResponse(
                {"error": "team_id must be a positive integer"},
                status=400,
            )

        team_id = int(team_id_text)

    return JsonResponse(
        {
            "method": request.method,
            "path": request.path,
            "team_id": team_id,
            "status": request.GET.get("status"),
            "all_team_ids": team_id_values,
            "request_content_type": request.content_type,
        }
    )

@require_GET
def health(request):
    return JsonResponse(
        {"status": "ok"}
    )

@login_required(login_url="tasks:login")
@require_http_methods(["GET", "POST"])
def task_create(request, team_id):
    team = get_object_or_404(
        Team,
        pk=team_id,
        memberships__user=request.user,
        memberships__role=Membership.Role.EDITOR,
    )

    if request.method == "POST":
        form = TaskForm(request.POST)

        if form.is_valid():
            task = form.save(commit=False)
            task.team = team
            task.created_by = request.user
            task.save()

            return redirect("tasks:detail", task_id = task.pk)

    else:
        form = TaskForm()

    return render(
        request,
        "tasks/task_form.html",
        {"form": form, "team": team, "page_title": "Create task", "submit_label": "Create task"},
    )


@login_required(login_url="tasks:login")
@require_http_methods(["GET", "POST"])
def task_edit(request, task_id):
    task = get_object_or_404(
        Task,
        pk=task_id,
        team__memberships__user=request.user,
        team__memberships__role=Membership.Role.EDITOR,
    )

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)

        if form.is_valid():
            form.save()
            return redirect("tasks:detail", task_id=task.pk)
    else:
        form = TaskForm(instance=task)

    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "team": task.team,
            "page_title": "Edit task",
            "submit_label": "Save changes"
        }
    )

@login_required(login_url="tasks:login")
@require_http_methods(["GET", "POST"])
def task_delete(request, task_id):
    task = get_object_or_404(
        Task,
        pk=task_id,
        team__memberships__user=request.user,
        team__memberships__role=Membership.Role.EDITOR,
    )

    if request.method == "POST":
        task.delete()
        return redirect("tasks:list")

    return render(
        request,
        "tasks/task_confirm_delete.html",
        {"task": task},
    )

def _tasks_visible_to(user):
    return Task.objects.filter(
        team__memberships__user=user,
        team__memberships__role__in=[
            Membership.Role.VIEWER,
            Membership.Role.EDITOR,
        ],
    ).order_by("pk")

