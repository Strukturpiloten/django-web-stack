"""Policy regressions that would skip integration checks or admit an unaged dependency."""

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

CI = Path(__file__).resolve().parents[1] / ".github/ci"


def module(name):
    spec = importlib.util.spec_from_file_location(name, CI / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


plan = module("plan")
policy = module("lock-policy")


def test_planner_handles_mixed_changes_and_unknowns():
    assert plan.select(["README.md"]) == ["docs"]
    lanes = plan.select(["README.md", "template/assets/styles.css", "template/README.md.jinja"])
    assert {"docs", "rendered-docs", "frontend", "image-full", "template"} <= set(lanes)
    assert "dev-root" not in lanes
    assert set(plan.select(["anything-new", "README.md"])) == plan.ALL
    assert set(plan.select([])) == plan.ALL
    assert {"backend", "frontend"} <= set(plan.select(["template/src/pkg/urls.py"]))
    assert {"image-full", "image-api-only"} <= set(plan.select(["template/compose.yaml.jinja"]))


NOW = datetime(2026, 11, 21, tzinfo=UTC)


@pytest.mark.parametrize(
    ("age", "old", "new", "old_alerts", "new_alerts", "reviewed", "allowed"),
    [
        (3, "2.4.7", "2.4.8", set(), set(), False, True),
        (2, "2.4.7", "2.4.8", set(), set(), True, False),
        (2, "2.4.7", "2.4.8", {"high"}, {"high"}, True, False),
        (0, "2.4.7", "3.0.0", {"high"}, set(), False, False),
        (0, "2.4.7", "3.0.0", {"high"}, set(), True, True),
        (29, "2.4.7", "2.5.0", set(), set(), True, False),
        (30, "2.4.7", "2.5.0", set(), set(), True, True),
        (3, "2.4.7", "2.5.1", set(), set(), False, False),
        (3, "2.4.7", "2.5.1", set(), set(), True, True),
    ],
)
def test_lock_policy(monkeypatch, age, old, new, old_alerts, new_alerts, reviewed, allowed):
    monkeypatch.setattr(policy, "published", lambda *_: NOW - timedelta(days=age))
    monkeypatch.setattr(
        policy, "advisories", lambda _, __, v: old_alerts if v == old else new_alerts
    )
    problems = policy.check({("pip", "django", old, new)}, reviewed, NOW)
    assert (not problems) == allowed
