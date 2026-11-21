# Contributing

Edit `template/` for generated files and `copier.yml` for prompts. The repository's `pyproject.toml` and `uv.lock` describe the maintainer environment. The corresponding files in `application-dependencies/` are the source for every generated Django application. Copier substitutes the chosen project metadata when rendering them.

## Dependency updates

Renovate monitors this repository, including generated Python and npm dependencies, CI actions and container images. Each consumer keeps its own Dependabot configuration and its existing Copier update workflow. A consumer chooses when to accept a new template SHA.

| Update | Earliest eligibility | Merge |
| --- | --- | --- |
| Stable patch on the current line | 72 hours after publication | Automatic after required CI |
| Minor for Ruff, pytest, pytest-django, build or hatchling | First nonzero patch on that line, aged 72 hours | Automatic after required CI |
| Other minor or any major | First nonzero patch on that line, aged 72 hours | Maintainer |
| A new line that still has only a `.0` release | After 30 days | Maintainer decision through the Dependency Dashboard |
| Image digest rebuild, prerelease or OpenTelemetry update | Normal hold | Maintainer |
| Fix for a high or critical advisory | Immediately on detection, including a fixed `.0` | Maintainer after required CI |

High and critical are the advisory provider’s severity ratings (typically CVSS 7.0 or higher). Renovate uses GitHub alerts where available and queries OSV for supported ecosystems. It opens a separate security PR targeting the lowest fixed version. An update that fixes a low, medium or unscored advisory keeps the ordinary hold. Missing release dates keep routine updates pending. Detection depends on the advisory feed and the next Renovate run.

The lockfile check also inspects incidental Python and npm upgrades. For a release younger than 72 hours it queries reviewed GitHub advisories for the **old and new resolved versions**. A maintainer applies the `dependency-reviewed` label after reviewing a security exception, a new package, a prerelease, or a locked runtime minor or major. Adding the label reruns CI. It cannot waive the age hold. If a registry or advisory lookup fails, rerun the failed job when the data is available. For an advisory that only exists in another feed, verify the affected and fixed versions and submit a reviewed maintainer PR. For PostgreSQL, `18.7` is a maintenance release on the 18 line. A new PostgreSQL major also requires a database upgrade and rollback plan.

Use the uv release pinned in CI. To refresh a particular Python package, run `uv lock --upgrade-package NAME` in the corresponding directory. For frontend dependencies, edit `template/package.json` and run `npm --prefix template install --package-lock-only --ignore-scripts`. Review all changed locks, especially newly introduced dependencies.

## Check and merge

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

Open a PR against protected `main` and describe any consumer migration steps. `Required CI` checks the results of every selected lane. Documentation changes run Markdown and offline link checks. Template, backend, browser, image and devcontainer changes run their relevant integration tests. Shared CI, unrecognized files, merge queues, manual runs and pushes to `main` run the full suite. External links are checked weekly. A successful push run on the exact `main` SHA makes it eligible for downstream update PRs.
