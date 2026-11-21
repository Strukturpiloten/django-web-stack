# django-web-stack

A [Copier](https://copier.readthedocs.io/) template for independent Django repositories. Each project owns its source code, database, images, and release schedule. Use the template when starting a project, then pick up shared changes through reviewed updates.

## Choose the interfaces

| Copier `default_mode` | Django pages | HTTP API and app login | Frontend build |
| --- | --- | --- | --- |
| `full` (default) | Yes | Yes | Node |
| `web-only` | Yes | No | Node |
| `api-only` | No | Yes | None |
| `backend-only` | No | No | None |

Choose `web-only` when the API should start disabled. Set `DJANGO_MODE=full` later to expose it. A frontend-free project can switch between `api-only` and `backend-only` with the same image. To add Django pages to that repository later, run a Copier update and change its generation mode. Admin, OpenAPI schema, and interactive docs have separate switches. Health endpoints are available in every mode.

## Start a repository

To try a local checkout, run the following from its parent directory. Use the canonical remote for shared projects so every contributor can retrieve the same commit.

```sh
uvx --from 'copier>=9.19,<10' copier copy --vcs-ref HEAD -d default_mode=api-only "$PWD/django-web-stack" ./orders
```

For a shared project, select a full commit SHA from a successful `main` push to the [template checks](https://github.com/Strukturpiloten/django-web-stack/actions/workflows/checks.yml?query=branch%3Amain+event%3Apush). With the GitHub CLI, the commands below select the latest successful run and pin that exact revision. Python 3.15 is the default throughout the generated stack.

```sh
uv tool install 'copier>=9.19,<10'
upstream=Strukturpiloten/django-web-stack
template_sha=$(gh run list --repo "$upstream" --workflow checks.yml --branch main \
  --event push --status success --limit 1 --json headSha --jq '.[0].headSha // empty')
copier copy --vcs-ref "${template_sha:?No successful main run found}" -d default_mode=api-only \
  "https://github.com/$upstream.git" orders
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

The template uses full Git commit SHAs. Maintainers merge checked PRs into protected `main` and include breaking changes and migration instructions in the PR description. Each application commits its generated `.copier-answers.yml`, which records the exact template commit, URL, and generation choices.

The generated **Update Django template** workflow runs weekly and on demand. For GitHub HTTPS template sources it selects the latest successful `checks.yml` push on upstream `main`, applies forward updates with Copier, and opens or refreshes one PR with an upstream comparison link. Application CI checks the proposed changes before the consumer merges them. Dependabot continues to update the application's packages and actions.

To update manually, select a successful commit as in the generation example, then run these commands from a clean consumer checkout.

```sh
git switch -c chore/update-django-web-stack
copier update --defaults --vcs-ref "${template_sha:?Select a successful upstream SHA}"
git status
git diff HEAD
```

Copier reapplies local changes over the selected commit. Resolve conflicts locally, include new files and the updated answers, and run the consumer's checks before merging. Keep application business logic in project-owned Django apps to reduce conflicts. For changes shared at runtime, consider a separately packaged Django app.

## Develop the template

```sh
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

Tests exercise rendering, package builds, and upgrades to customized consumers. CI also builds and starts full and API-only applications. Keep local experiments under the ignored `temp/` directory. Dependency maintenance and merge instructions are in [CONTRIBUTING.md](CONTRIBUTING.md). The template and generated starter are MIT licensed.
