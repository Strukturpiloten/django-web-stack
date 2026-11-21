"""Apply release holds to resolved versions, including incidental transitive upgrades."""

import json
import os
import re
import subprocess
import sys
import tomllib
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from cvss import CVSS3, CVSS4

LOCKS = ("uv.lock", "application-dependencies/uv.lock", "template/package-lock.json")
HOLD = timedelta(days=3)
DEV_MINOR = {"ruff", "pytest", "pytest-django", "build", "hatchling"}


def versions(path, content):
    if path.endswith(".lock"):
        resolved = defaultdict(set)
        for package in tomllib.loads(content)["package"]:
            if package["source"].get("registry"):
                resolved[package["name"]].add(package["version"])
        return resolved
    return {
        location: {package["version"]}
        for location, package in json.loads(content)["packages"].items()
        if location and "version" in package
    }


def fetch(url, github=False, payload=None):
    headers = {"User-Agent": "django-web-stack-dependency-check"}
    if github and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    with urlopen(Request(url, headers=headers, data=data), timeout=30) as response:
        return json.load(response)


def published(ecosystem, name, version):
    package = quote(name, safe="")
    if ecosystem == "pip":
        release = fetch(f"https://pypi.org/pypi/{package}/{quote(version, safe='')}/json")
        timestamp = min(file["upload_time_iso_8601"] for file in release["urls"])
    else:
        timestamp = fetch(f"https://registry.npmjs.org/{package}")["time"][version]
    return datetime.fromisoformat(timestamp)


def high_osv_severity(record):
    # Prefer the current CVSS standard when the publisher supplies multiple vectors.
    for kind, calculator in (("CVSS_V4", CVSS4), ("CVSS_V3", CVSS3)):
        for rating in record.get("severity", []):
            if rating["type"] == kind:
                return calculator(rating["score"]).scores()[0] >= 7
    return record.get("database_specific", {}).get("severity", "").upper() in {"HIGH", "CRITICAL"}


def osv_advisories(ecosystem, name, version):
    package = {"ecosystem": "PyPI" if ecosystem == "pip" else "npm", "name": name}
    query = {"package": package, "version": version}
    found = set()
    for _ in range(100):
        batch = fetch("https://api.osv.dev/v1/query", payload=query)
        found.update(
            item["id"]
            for item in batch.get("vulns", [])
            if not item.get("withdrawn") and high_osv_severity(item)
        )
        if not batch.get("next_page_token"):
            return found
        query["page_token"] = batch["next_page_token"]
    raise ValueError("OSV pagination limit reached")


def advisories(ecosystem, name, version):
    found = osv_advisories(ecosystem, name, version)
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
        for key, candidates in versions(path, Path(path).read_text()).items():
            previous = old.get(key, set())
            removed = previous - candidates
            # A package may have different Python versions for different environment markers.
            # An ambiguous replacement is reviewed as a newly introduced dependency.
            prior = next(iter(removed)) if len(removed) == 1 else None
            for version in candidates - previous:
                ecosystem = "npm" if path.endswith(".json") else "pip"
                name = key.split("node_modules/")[-1]
                updates.add((ecosystem, name, prior, version))
    reviewed = "dependency-reviewed" in json.loads(os.environ.get("PR_LABELS", "[]"))
    problems = check(updates, reviewed, datetime.now(UTC))
    if problems:
        raise SystemExit("\n".join(problems))


if __name__ == "__main__":
    main(sys.argv[1])
