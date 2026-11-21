from django.db import transaction

from .models import HelloJob, User
from .tasks import run_hello_job


def greeting() -> str:
    """One demo service shared by the API, HTML views, and worker."""
    return "Hello world"


def create_hello_job(owner: User) -> HelloJob:
    with transaction.atomic():
        job = HelloJob.objects.create(owner=owner, message=greeting())
        run_hello_job.delay_on_commit(str(job.id))
    return job
