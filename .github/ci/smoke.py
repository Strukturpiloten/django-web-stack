"""Run in the rendered web container with Django initialized by django shell."""

import time

from django.core.cache import cache
from my_application.models import User
from my_application.services import create_hello_job

cache.set("ci-health", "ready", 60)
assert cache.get("ci-health") == "ready"
job = create_hello_job(User.objects.create_user(username="ci-worker"))
for _ in range(60):
    job.refresh_from_db()
    if job.status == job.Status.SUCCEEDED:
        break
    time.sleep(1)
assert job.result == "Hello world", (job.status, job.result)
