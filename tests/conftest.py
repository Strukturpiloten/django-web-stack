"""Test templates from a temporary source so uncommitted edits are included."""

from pathlib import Path
from shutil import copy2, copytree, ignore_patterns

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def template_source(tmp_path: Path) -> Path:
    source = tmp_path / "template-source"
    source.mkdir()
    copy2(REPOSITORY_ROOT / "copier.yml", source / "copier.yml")
    copytree(REPOSITORY_ROOT / "application-dependencies", source / "application-dependencies")
    copytree(
        REPOSITORY_ROOT / "template",
        source / "template",
        ignore=ignore_patterns(
            "node_modules", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"
        ),
    )
    return source
