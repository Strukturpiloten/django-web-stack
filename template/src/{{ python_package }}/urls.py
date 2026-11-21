from django.conf import settings
from django.urls import include, path

from . import views

urlpatterns = [
    path("health/live", views.live, name="health-live"),
    path("health/ready", views.ready, name="health-ready"),
    path("accounts/", include("allauth.urls")),
]

if settings.UI_ENABLED:
    urlpatterns += [
        path("", views.index, name="index"),
        path("hello/", views.hello, name="hello"),
        path("jobs/", views.job_create, name="job-create"),
        path("jobs/<uuid:job_id>/", views.job_status, name="job-status"),
    ]

if settings.API_ENABLED:
    from .api import build_api

    urlpatterns += [
        path("api/v1/", build_api().urls),
        path("_allauth/", include("allauth.headless.urls")),
    ]

if settings.ENABLE_ADMIN:
    from django.contrib import admin

    urlpatterns.append(path("admin/", admin.site.urls))
