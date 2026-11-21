"""Select PR checks. Unknown files and changes to the selector itself run every lane."""

import argparse
import json
import os
import subprocess
from pathlib import PurePosixPath

ALL = {
    "docs",
    "rendered-docs",
    "template",
    "backend",
    "frontend",
    "image-full",
    "image-api-only",
    "dev-root",
    "dev-full",
    "dev-api-only",
    "workflows",
    "renovate",
}


def lanes_for(path: str) -> set[str]:
    if (
        path == "renovate.json"
        or path.startswith(".github/ci/")
        or path.startswith(".github/workflows/")
    ):
        return ALL
    if path.startswith("template/") and path.endswith((".md", ".md.jinja")):
        return {"rendered-docs"}
    if path.endswith(".md") or path == ".markdownlint.json":
        return {"docs", "rendered-docs"} if path == ".markdownlint.json" else {"docs"}
    if path.startswith(".devcontainer/"):
        return {"dev-root", "renovate"}
    if path.startswith("template/.devcontainer/"):
        return {"dev-full", "dev-api-only", "template", "renovate"}
    if path.startswith("template/.github/"):
        return {"template", "workflows", "renovate"}
    if path in {
        "template/Containerfile.jinja",
        "template/compose.yaml.jinja",
        "template/scripts/container-entrypoint.sh",
        "template/.dockerignore",
    }:
        return {"template", "image-full", "image-api-only", "dev-full", "dev-api-only", "renovate"}
    if (
        path.startswith(("template/assets/", "template/scripts/build-assets", "template/package"))
        or "/templates/" in path
    ):
        return {"template", "frontend", "image-full", "renovate"}
    if path.startswith(("application-dependencies/", "template/pyproject.", "template/uv.lock")):
        return ALL
    if path.startswith("tests/") and PurePosixPath(path).suffix == ".py":
        return {"template"}
    if path.startswith(("template/src/", "template/tests/")) and path.endswith(
        (".py", ".py.jinja")
    ):
        return {"template", "frontend", "backend"}
    return ALL


def select(paths: list[str]) -> list[str]:
    selected = set().union(*(lanes_for(path) for path in paths)) if paths else ALL
    return sorted(selected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diff", nargs=2, metavar=("BASE", "HEAD"))
    args = parser.parse_args()
    paths = []
    if args.diff:
        base, head = args.diff
        # --no-renames emits both names. A removed file matters as much as an added file.
        diff = subprocess.check_output(
            ["git", "diff", "--no-renames", "--name-only", "-z", f"{base}...{head}", "--"]
        )
        paths = [os.fsdecode(path) for path in diff.split(b"\0") if path]
    print(json.dumps(select(paths)))
