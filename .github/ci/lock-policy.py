"""Apply release holds to resolved versions, including incidental transitive upgrades."""

import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

LOCKS = ("uv.lock", "application-dependencies/uv.lock", "template/package-lock.json")
HOLD = timedelta(days=3)
DEV_MINOR = {"ruff", "pytest", "pytest-django", "build", "hatchling"}


def versions(path, content):
    if path.endswith(".lock"):
        return {
            p["name"]: p["version"]
            for p in tomllib.loads(content)["package"]
            if p["source"].get("registry")
        }
    return {
        location: package["version"]
        for location, package in json.loads(content)["packages"].items()
        if location and "version" in package
    }


def fetch(url, github=False):
    headers = {"User-Agent": "django-web-stack-dependency-check"}
    if github and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def published(ecosystem, name, version):
    package = quote(name, safe="")
    if ecosystem == "pip":
        release = fetch(f"https://pypi.org/pypi/{package}/{quote(version, safe='')}/json")
        timestamp = min(file["upload_time_iso_8601"] for file in release["urls"])
    else:
        timestamp = fetch(f"https://registry.npmjs.org/{package}")["time"][version]
    return datetime.fromisoformat(timestamp)


def advisories(ecosystem, name, version):
    found = set()
    for page in range(1, 101):
        query = urlencode(
            {
                "ecosystem": ecosystem,
                "affects": f"{name}@{version}",
                "type": "reviewed",
                "per_page": 100,
                "page": page,
            }
        )
        batch = fetch(f"https://api.github.com/advisories?{query}", github=True)
        found.update(
            item["ghsa_id"]
            for item in batch
            if not item["withdrawn_at"] and item["severity"] in {"high", "critical"}
        )
        if len(batch) < 100:
            return found
    raise ValueError("Advisory pagination limit reached")


def parts(version):
    match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?", version or "")
    return tuple(int(value or 0) for value in match.groups()) if match else ()


def check(updates, reviewed, now):
    problems = []
    for ecosystem, name, old, new in sorted(updates, key=str):
        age = now - published(ecosystem, name, new)
        before, after = parts(old), parts(new)
        new_line = bool(before and after and before[:2] != after[:2])
        first_release = new_line and after[2] == 0
        fixed = set()
        if old and (age < HOLD or first_release):
            fixed = advisories(ecosystem, name, old) - advisories(ecosystem, name, new)
        if fixed:
            print(f"{name} {old} → {new} fixes {', '.join(sorted(fixed))}")
        if age < HOLD and not fixed:
            problems.append(f"{name} {new} is under 72 hours old.")
        if first_release and not fixed and age < timedelta(days=30):
            problems.append(f"{name} {new} starts a new line. Wait for a patch or day 30.")
        needs_review = (
            fixed
            or first_release
            or not old
            or not before
            or not after
            or name.startswith("opentelemetry-")
            or (new_line and (before[0] != after[0] or name not in DEV_MINOR))
        )
        if needs_review and not reviewed:
            problems.append(f"{name} {old or '(new)'} → {new} needs the dependency-reviewed label.")
    return problems


def main(base):
    updates = set()
    for path in LOCKS:
        source = subprocess.check_output(["git", "show", f"{base}:{path}"], text=True)
        old = versions(path, source)
        for key, version in versions(path, Path(path).read_text()).items():
            if version != old.get(key):
                ecosystem = "npm" if path.endswith(".json") else "pip"
                name = key.split("node_modules/")[-1]
                updates.add((ecosystem, name, old.get(key), version))
    reviewed = "dependency-reviewed" in json.loads(os.environ.get("PR_LABELS", "[]"))
    problems = check(updates, reviewed, datetime.now(UTC))
    if problems:
        raise SystemExit("\n".join(problems))


if __name__ == "__main__":
    main(sys.argv[1])
