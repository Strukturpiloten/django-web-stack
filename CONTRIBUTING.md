# Contributing

Edit `template/` for generated files and `copier.yml` for prompts. Keep Python 3.14 and Node 24 compatible across CI, containers, and manifests.

## Refresh dependencies

Use uv 0.13.9 (the version pinned in CI and the images). The repository and its generated projects have separate Python locks.

```sh
uv lock --upgrade
uv run --locked python scripts/update-template-lock.py
npm --prefix template outdated
```

For a frontend update, change the exact versions in `template/package.json` and run `npm --prefix template install --package-lock-only --ignore-scripts`. Include both manifests and their updated locks in the review. The generated Python lock retains a placeholder for the downstream package name.

## Check and release

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

On a release commit, confirm that the tracked files include `template/.env.example.jinja`, both template locks, and the answers-file template. Let the generated-image CI jobs pass. Tag that commit with an immutable version such as `v0.1.0` and publish the tag and release notes. Call out changes to configuration, database migrations and build requirements. Consumers using Renovate receive a template update PR after their next scan.
