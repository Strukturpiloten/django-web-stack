"""Exercise the generated artifacts and the template update contract."""

import ast
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml
from build import ProjectBuilder
from copier import run_copy, run_update


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
    )
    return result.stdout.strip()


def initialize_git(repository: Path) -> None:
    git(repository, "init", "--initial-branch=main")
    git(repository, "config", "user.name", "Template tests")
    git(repository, "config", "user.email", "tests@example.invalid")
    git(repository, "config", "commit.gpgsign", "false")


def commit_all(repository: Path, message: str) -> None:
    git(repository, "add", ".")
    git(repository, "commit", "-m", message)


@pytest.mark.parametrize(
    ("project_name", "slug", "package", "description"),
    [
        ("Field Service", "field-service", "field_service", "Field service application"),
        ("Übersicht", "customer-portal", "customer_portal", 'Quotes " and \\ paths\nÜbersicht'),
    ],
)
def test_render_build_and_import(
    template_source: Path,
    tmp_path: Path,
    project_name: str,
    slug: str,
    package: str,
    description: str,
) -> None:
    destination = tmp_path / "application"
    run_copy(
        str(template_source),
        destination,
        data={
            "project_name": project_name,
            "project_slug": slug,
            "python_package": package,
            "project_description": description,
        },
        defaults=True,
        quiet=True,
    )

    metadata = tomllib.loads((destination / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == slug
    assert metadata["project"]["description"] == description
    assert metadata["project"]["requires-python"] == ">=3.14,<3.15"
    answers = yaml.safe_load((destination / ".copier-answers.yml").read_text())
    assert answers["_src_path"] == str(template_source)
    assert answers["python_package"] == package

    for path in destination.rglob("*"):
        assert "{{" not in str(path)
        assert not path.name.endswith(".jinja")
    for path in destination.rglob("*.py"):
        ast.parse(path.read_text(), filename=str(path))

    # Validate the actual installed layout: the wheel must be importable without
    # the working tree on sys.path, and must carry its license.
    wheel = ProjectBuilder(destination).build("wheel", tmp_path / "wheels")
    with ZipFile(wheel) as archive:
        assert f"{package}/__init__.py" in archive.namelist()
        license_path = next(name for name in archive.namelist() if name.endswith("/LICENSE"))
        assert archive.read(license_path) == (template_source / "template/LICENSE").read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import importlib, sys; sys.path.insert(0, sys.argv[1]); "
            "print(importlib.import_module(sys.argv[2]).__file__)",
            wheel,
            package,
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(wheel) in result.stdout

    for arguments in (["check", "."], ["format", "--check", "."]):
        subprocess.run([sys.executable, "-m", "ruff", *arguments], cwd=destination, check=True)


@pytest.mark.parametrize(
    ("question", "value"),
    [
        ("project_name", ""),
        ("project_name", "Multiple\nlines"),
        ("project_slug", "../escape"),
        ("project_slug", "invalid/name"),
        ("project_slug", "app--name"),
        ("project_slug", "app\n"),
        ("python_package", "../escape"),
        ("python_package", "class"),
        ("python_package", "django"),
        ("python_package", "9invalid"),
        ("python_package", "has-hyphen"),
        ("python_package", "app\n"),
    ],
)
def test_reject_invalid_identifiers(
    template_source: Path, tmp_path: Path, question: str, value: str
) -> None:
    destination = tmp_path / "application"
    with pytest.raises(ValueError, match=question):
        run_copy(
            str(template_source),
            destination,
            data={question: value},
            defaults=True,
            quiet=True,
        )
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize("mode", ["full", "web-only", "api-only", "backend-only"])
def test_generation_modes(template_source: Path, tmp_path: Path, mode: str) -> None:
    destination = tmp_path / "application"
    run_copy(str(template_source), destination, data={"default_mode": mode}, defaults=True)
    has_ui = mode in {"full", "web-only"}
    for name in (
        "package.json",
        "package-lock.json",
        "scripts/build-assets.mjs",
        "tests/test_browser.py",
    ):
        assert (destination / name).exists() == has_ui
    assert (destination / "src/my_application/templates/demo/index.html").exists() == has_ui
    for file in ("Containerfile", ".devcontainer/Dockerfile"):
        assert ("library/node:" in (destination / file).read_text()) == has_ui
    workflow = (destination / ".github/workflows/checks.yml").read_text()
    assert ("actions/setup-node@" in workflow) == has_ui
    assert ("npm ci" in (destination / ".devcontainer/verify-tools.sh").read_text()) == has_ui
    assert f"DJANGO_MODE={mode}\n" in (destination / ".env.example").read_text()
    for path in (".vscode/tasks.json", ".devcontainer/devcontainer.json", "renovate.json"):
        json.loads((destination / path).read_text())
    assert yaml.safe_load(workflow)["jobs"]["check"]
    assert yaml.safe_load((destination / "compose.yaml").read_text())["services"]["web"]
    subprocess.run(["uv", "lock", "--check"], cwd=destination, check=True)


@pytest.mark.parametrize("mode", ["full", "api-only"])
def test_update_keeps_project_owned_files(template_source: Path, tmp_path: Path, mode: str) -> None:
    initialize_git(template_source)
    commit_all(template_source, "Initial template")
    git(template_source, "tag", "v0.1.0")
    destination = tmp_path / "application"
    run_copy(
        str(template_source), destination, data={"default_mode": mode}, defaults=True, quiet=True
    )
    initialize_git(destination)
    commit_all(destination, "Generate application")

    business_module = destination / "src/my_application/business.py"
    business_module.write_text('"""Project-owned business rules."""\n')
    readme = destination / "README.md"
    readme.write_text(readme.read_text() + "\nProject-specific development notes.\n")
    commit_all(destination, "Add application-owned code and documentation")

    template_readme = template_source / "template/README.md.jinja"
    template_readme.write_text(
        template_readme.read_text().replace(
            "## Status", "Template update compatibility check.\n\n## Status"
        )
    )
    commit_all(template_source, "Update template guidance")
    git(template_source, "tag", "v0.2.0")

    run_update(destination, defaults=True, overwrite=True, quiet=True)
    assert "Template update compatibility check." in readme.read_text()
    assert "Project-specific development notes." in readme.read_text()
    assert business_module.read_text() == '"""Project-owned business rules."""\n'
    answers = yaml.safe_load((destination / ".copier-answers.yml").read_text())
    assert answers["_commit"] == "v0.2.0"
    assert answers["default_mode"] == mode
    assert (destination / ".env.example").is_file()
    assert (destination / "package.json").is_file() == (mode == "full")
    assert not list(destination.rglob("*.rej"))
