"""Tests use the PostgreSQL configured by the same environment as the application."""

import os

import pytest
from django.conf import settings as django_settings
from django.test import override_settings

os.environ.setdefault("DJANGO_DEBUG", "true")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")


if os.environ.get("RUN_BROWSER_TESTS") != "1" or not django_settings.UI_ENABLED:
    collect_ignore = ["test_browser.py"]


@pytest.fixture(scope="session", autouse=True)
def source_static_assets():
    # Tests serve built source assets; the runtime image checks collected manifests.
    storages = {
        **django_settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    with override_settings(STORAGES=storages, WHITENOISE_USE_FINDERS=True, STATIC_ROOT=None):
        yield


@pytest.fixture(autouse=True)
def postgres_only(settings):
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
