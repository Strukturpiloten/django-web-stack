"""Fail when Renovate silently stops discovering a dependency in a generated file."""

import json
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

found = defaultdict(set)
for line in Path(sys.argv[1]).read_text().splitlines():
    if not line.startswith("{"):
        continue
    files = json.loads(line).get("packageFiles")
    if isinstance(files, dict):
        for group in files.values():
            for manifest in group:
                for dep in manifest.get("deps", []):
                    if not dep.get("skipReason"):
                        found[manifest["packageFile"]].add(dep["depName"].lower())

expected = defaultdict(set)
for path in [Path("pyproject.toml"), Path("application-dependencies/pyproject.toml")]:
    manifest = tomllib.loads(path.read_text())
    groups = [
        manifest["project"]["dependencies"],
        *manifest["project"].get("optional-dependencies", {}).values(),
        *manifest["dependency-groups"].values(),
        manifest.get("build-system", {}).get("requires", []),
    ]
    expected[str(path)] = {
        re.match(r"[\w.-]+", req).group().lower() for group in groups for req in group
    }
npm = "template/package.json"
expected[npm] = set(json.loads(Path(npm).read_text())["devDependencies"])
for path in [
    *Path(".github/workflows").glob("*.yml"),
    *Path("template/.github/workflows").glob("*"),
    Path(".devcontainer/Dockerfile"),
    Path("template/.devcontainer/Dockerfile.jinja"),
    Path("template/Containerfile.jinja"),
    Path("template/compose.yaml.jinja"),
    Path(".github/ci/check.sh"),
]:
    source = path.read_text()
    expected[str(path)].update(re.findall(r"uses: ([\w.-]+/[\w.-]+)@[a-f\d]{40}", source.lower()))
    expected[str(path)].update(re.findall(r"(?:docker\.io|ghcr\.io)/[\w-]+/[\w.-]+(?=:)", source))
    if "setup-uv@" in source:
        expected[str(path)].add("uv")
expected[".github/ci/check.sh"].add("renovate")
for path, names in expected.items():
    missing = names - found[path]
    if missing:
        raise SystemExit(f"Renovate did not extract {', '.join(sorted(missing))} from {path}")
print(f"Verified dependency extraction for {len(expected)} manifests and templates.")
