from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, connections
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import HelloJob
from .services import create_hello_job, greeting


@require_GET
@ensure_csrf_cookie
def index(request: HttpRequest) -> HttpResponse:
    return render(request, "demo/index.html")


@require_GET
def hello(request: HttpRequest) -> HttpResponse:
    return render(request, "demo/_hello.html", {"message": greeting()})


@login_required
@require_POST
def job_create(request: HttpRequest) -> HttpResponse:
    job = create_hello_job(request.user)
    return render(request, "demo/_job.html", {"job": job}, status=202)


@login_required
@require_GET
def job_status(request: HttpRequest, job_id: UUID) -> HttpResponse:
    job = get_object_or_404(HelloJob, pk=job_id, owner=request.user)
    return render(request, "demo/_job.html", {"job": job})


@require_GET
def live(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_GET
def ready(request: HttpRequest) -> JsonResponse:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
