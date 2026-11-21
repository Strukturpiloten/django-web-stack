# Contributing

Edit `template/` for generated files and `copier.yml` for prompts. Keep Python 3.15 and Node 24 compatible across CI, containers, and manifests.

## Refresh dependencies

Use uv 0.13.9 (the version pinned in CI and the images). The repository and its generated projects have separate Python locks.

```sh
uv lock --upgrade
uv run --locked python scripts/update-template-lock.py
npm --prefix template outdated
```

For a frontend update, change the exact versions in `template/package.json` and run `npm --prefix template install --package-lock-only --ignore-scripts`. Include both manifests and their updated locks in the review. The generated Python lock retains a placeholder for the downstream package name.

## Check and merge

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

Open a PR against protected `main` and describe any consumer migration steps. `Required CI` aggregates the template suite and generated full and API-only checks. After merging, the successful push run on the exact `main` SHA makes it eligible for downstream update PRs. The template uses this SHA for distribution. Generated applications manage their own package versions.
