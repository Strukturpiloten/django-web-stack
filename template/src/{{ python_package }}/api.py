from uuid import UUID

from allauth.headless.contrib.ninja.security import XSessionTokenAuth
from django.conf import settings
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema, Status
from ninja.security import SessionAuth

from .models import HelloJob
from .services import create_hello_job, greeting


class AppSessionAuth(XSessionTokenAuth):
    openapi_in = "header"
    openapi_name = "X-Session-Token"


class GreetingOut(Schema):
    message: str


class JobOut(Schema):
    id: UUID
    status: str
    message: str
    result: str


def build_api() -> NinjaAPI:
    api = NinjaAPI(
        title="Hello demo API",
        version="1.0.0",
        urls_namespace="api-v1",
        docs_url="/docs" if settings.ENABLE_API_DOCS else None,
        openapi_url="/openapi.json" if settings.ENABLE_API_SCHEMA else None,
    )

    job_auth = [AppSessionAuth(), SessionAuth()]

    @api.get("/hello", response=GreetingOut, url_name="hello")
    def hello(request):
        return {"message": greeting()}

    @api.post("/jobs", response={202: JobOut}, auth=job_auth, url_name="job-create")
    def job_create(request):
        return Status(202, create_hello_job(request.user))

    @api.get("/jobs/{job_id}", response=JobOut, auth=job_auth, url_name="job-status")
    def job_status(request, job_id: UUID):
        return get_object_or_404(HelloJob, pk=job_id, owner=request.user)

    return api
