#!/usr/bin/env bash
set -euo pipefail

for tool in python uv node npm git jq shellcheck shfmt; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
        printf 'Missing development tool: %s\n' "${tool}" >&2
        exit 1
    fi
done

# Separate the image interpreter and cache from host virtualenvs.
for directory in .venv "${UV_CACHE_DIR}"; do
    if [[ ! -w "${directory}" ]]; then
        sudo chown "$(id -u):$(id -g)" "${directory}"
    fi
done

python --version
uv --version
node --version
npm --version
uv sync --locked
uv run --locked copier --version
uv run --locked ruff --version
printf 'Template development tools are ready.\n'
