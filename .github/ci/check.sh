#!/usr/bin/env bash
set -euo pipefail

render() {
    uv run --locked copier copy --quiet --defaults --vcs-ref HEAD -d "default_mode=$1" . "temp/$1"
}

devcontainer() {
    local project=$1
    docker build -f "$project/.devcontainer/Dockerfile" -t dev-tools:ci "$project"
    # Copy a clean checkout, then provision it with the image's actual non-root user and mounts.
    docker run --rm --user root -v "$PWD/$project:/source:ro" --tmpfs /work:exec \
        -e UV_CACHE_DIR=/tmp/uv-cache dev-tools:ci bash -ec '
        cd /work
        tar -C /source --exclude=.git --exclude=.venv --exclude=temp -cf - . | tar -xf -
        mkdir -p .venv "$UV_CACHE_DIR"
        chown -R vscode:vscode /work "$UV_CACHE_DIR"
        exec sudo -Hu vscode --preserve-env=UV_CACHE_DIR,UV_PYTHON_DOWNLOADS,UV_LINK_MODE bash .devcontainer/verify-tools.sh'
}

case "$LANE" in
    docs) ;;
    rendered-docs) render full; render api-only ;;
    template)
        uv run --locked ruff check .
        uv run --locked ruff format --check .
        uv run --locked pytest
        ;;
    renovate)
        # renovate: datasource=npm depName=renovate
        renovate_version=44.258.1
        npm exec --yes --package="renovate@$renovate_version" -- renovate-config-validator --no-global --strict renovate.json
        npm exec --yes --package="renovate@$renovate_version" -- \
            sh -c 'node .github/ci/test-renovate.mjs "$(command -v renovate)"'
        LOG_LEVEL=debug LOG_FORMAT=json GITHUB_COM_TOKEN="$GH_TOKEN" \
            npm exec --yes --package="renovate@$renovate_version" -- renovate --platform=local --dry-run=extract \
            > "$RUNNER_TEMP/renovate-extract.jsonl"
        python .github/ci/check-extraction.py "$RUNNER_TEMP/renovate-extract.jsonl"
        if [[ "$PR_AUTHOR" == 'renovate[bot]' && -n "$BASE" ]]; then
            trusted="$RUNNER_TEMP/dependency-policy"
            mkdir -p "$trusted"
            for file in pyproject.toml uv.lock .github/ci/lock-policy.py; do
                git show "$BASE:$file" > "$trusted/${file##*/}"
            done
            uv sync --locked --project "$trusted"
            "$trusted/.venv/bin/python" -I "$trusted/lock-policy.py" "$BASE"
        fi
        ;;
    workflows)
        render full
        render api-only
        # Run in each project root so actionlint also resolves local files and reusable workflows.
        for project in . temp/full temp/api-only; do
            (cd "$project" && docker run --rm -v "$PWD:/repo:ro" -w /repo \
                docker.io/rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667 \
                -color .github/workflows/*.yml)
        done
        ;;
    backend|frontend)
        mode=api-only
        [[ "$LANE" != frontend ]] || mode=full
        render "$mode"
        cd "temp/$mode"
        docker compose up -d --wait db rabbitmq
        uv run --locked --env-file .env.example python manage.py makemigrations --check --dry-run
        if [[ "$mode" == full ]]; then
            npm ci --ignore-scripts
            npm run build
            uv run --locked --group browser playwright install --with-deps chromium
            RUN_BROWSER_TESTS=1 uv run --locked --all-extras --group browser --env-file .env.example pytest
        else
            test ! -e package.json && test ! -d assets
            uv run --locked --all-extras --env-file .env.example pytest
        fi
        ;;
    image-*)
        mode=${LANE#image-}
        render "$mode"
        cd "temp/$mode"
        export CONTAINER_VALKEY_URL=redis://valkey:6379/0
        trap 'docker compose logs --tail=80' ERR
        docker compose build web
        docker compose --profile valkey up --no-build -d --wait --wait-timeout 240 web worker valkey
        curl --fail http://127.0.0.1:8000/health/ready
        docker compose exec -T web python -m django shell < ../../.github/ci/smoke.py
        ;;
    dev-root) devcontainer . ;;
    dev-full|dev-api-only)
        mode=${LANE#dev-}
        render "$mode"
        devcontainer "temp/$mode"
        ;;
    *) echo "Unknown lane: $LANE" >&2; exit 1 ;;
esac
