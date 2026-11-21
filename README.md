# django-web-stack

A versioned [Copier](https://copier.readthedocs.io/) template for independent Django repositories. Each project owns its source code, database, images, and release schedule. Use the template when starting a project, then pick up shared changes through reviewed updates.

## Choose the interfaces

| Copier `default_mode` | Django pages | HTTP API and app login | Frontend build |
| --- | --- | --- | --- |
| `full` (default) | Yes | Yes | Node |
| `web-only` | Yes | No | Node |
| `api-only` | No | Yes | None |
| `backend-only` | No | No | None |

Choose `web-only` when the API should start disabled. Set `DJANGO_MODE=full` later to expose it. A frontend-free project can switch between `api-only` and `backend-only` with the same image. To add Django pages to that repository later, run a Copier update and change its generation mode. Admin, OpenAPI schema, and interactive docs have separate switches. Health endpoints are available in every mode.

## Start a repository

To try a committed local checkout before the first release, run the following from the parent directory. Use the canonical remote for long-lived projects so every contributor can retrieve the template.

```sh
uvx --from 'copier>=9.19,<10' copier copy --vcs-ref HEAD -d default_mode=api-only "$PWD/django-web-stack" ./orders
```

Once the template has a published release, copy from its canonical Git URL. Copier selects the latest stable tag. Pin a particular published tag with `--vcs-ref` when multiple projects should start from the same revision.

```sh
uv tool install 'copier>=9.19,<10'
copier copy -d default_mode=api-only https://github.com/Strukturpiloten/django-web-stack.git orders
cd orders
git init -b main
git add .
git commit -m "Generate orders from django-web-stack"
cp .env.example .env
podman compose up --build -d
curl --fail http://localhost:8000/api/v1/hello
```

The example returns `{"message":"Hello world"}`. Use `docker compose` for Docker. The generated README covers configuration, tests, and authenticated requests.

For an existing application, generate into a sibling directory and compare its settings, URLs, migrations, and deployment files to your own. To adopt the whole template, use the generated baseline on an integration branch and port the application's changes onto it, preserving its migration history and app labels. Projects that only need to call another service can consume its versioned HTTP API directly.

## Container design

Django renders HTML and HTMX fragments and serves the versioned Ninja API. In UI projects a Node build stage compiles Tailwind CSS, daisyUI, and local HTMX assets. WhiteNoise serves collected files from the Python image. Frontend-free generation omits the Node stage, npm manifests, product templates, and browser tests. An independently released SPA can live in its own repository and deployment.

Compose runs Uvicorn, the Celery worker, and the one-shot migration command as separate services from one non-root application image. PostgreSQL holds application data and sessions. RabbitMQ delivers tasks. Valkey caching and OpenTelemetry export are optional. The included Compose configuration binds ports to localhost for development. Each consumer configures its own secrets, HTTPS ingress, and data backups for deployment.

## Inherit upstream changes

1. **Template maintainers** commit the tested scaffold and publish immutable version tags such as `v0.1.0`. Describe breaking changes and any manual migration steps in the release notes.
2. **Application maintainers** commit `.copier-answers.yml`. It records the source, release, and answers. Keep domain-specific code in project-owned Django apps to reduce overlap with the scaffold.
3. From a clean consumer checkout, run the following commands and review the result in a pull request.

```sh
copier check-update
git switch -c chore/update-django-web-stack
copier update --defaults
git status
git diff HEAD
```

Copier reapplies local changes over the new template. Resolve conflicts, include new files and the updated answers, and run the application checks before merging. For a specific release, pass `--vcs-ref <published-tag>` to `copier update`. Business logic that several projects must execute identically is a candidate for a separately versioned Django package with ordinary dependency updates.

Generated repositories include a Renovate configuration limited to Copier. Enable Renovate for the repository to receive template upgrade PRs. Dependabot covers the generated application's dependencies. [Copier update guide](https://copier.readthedocs.io/en/stable/updating/) · [Renovate Copier manager](https://docs.renovatebot.com/modules/manager/copier/)

## Develop the template

```sh
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

Tests exercise rendering, package builds, and upgrades to customized consumers. CI also builds and starts full and API-only applications. Keep local experiments under the ignored `temp/` directory. Dependency maintenance and release instructions are in [CONTRIBUTING.md](CONTRIBUTING.md). The template and generated starter are MIT licensed.
