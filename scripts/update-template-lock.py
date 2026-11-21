"""Resolve the generated project's Python dependencies and retain its Copier package name."""

import subprocess
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory

from copier import run_copy

ROOT = Path(__file__).resolve().parents[1]
LOCK_PROJECT = "django-stack-lock-project"


def main() -> None:
    with TemporaryDirectory() as scratch:
        source = Path(scratch) / "source"
        project = Path(scratch) / "project"
        (source / "template").mkdir(parents=True)
        copy2(ROOT / "copier.yml", source)
        copy2(ROOT / "template/pyproject.toml.jinja", source / "template")
        run_copy(str(source), project, data={"project_slug": LOCK_PROJECT}, defaults=True)
        subprocess.run(["uv", "lock", "--upgrade"], cwd=project, check=True)
        lock = (project / "uv.lock").read_text()
        name = f'name = "{LOCK_PROJECT}"'
        if lock.count(name) != 1:
            raise ValueError("Expected a single entry for the generated project in uv.lock")
        (ROOT / "template/uv.lock.jinja").write_text(
            lock.replace(name, "name = {{ project_slug | tojson }}")
        )


if __name__ == "__main__":
    main()
