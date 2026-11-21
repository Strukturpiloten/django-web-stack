from celery import shared_task
from django.db import OperationalError, transaction

from .models import HelloJob


@shared_task(autoretry_for=(OperationalError,), retry_backoff=True, max_retries=3)
def run_hello_job(job_id: str) -> str | None:
    # Keep the lock until completion: retries and duplicate deliveries cannot race.
    from .services import greeting

    with transaction.atomic():
        job = HelloJob.objects.select_for_update().filter(pk=job_id).first()
        if job is None:
            return None
        if job.status == HelloJob.Status.SUCCEEDED:
            return job.result
        job.status = HelloJob.Status.RUNNING
        job.save(update_fields=["status", "updated_at"])
        job.result = greeting()
        job.status = HelloJob.Status.SUCCEEDED
        job.save(update_fields=["result", "status", "updated_at"])
        return job.result
