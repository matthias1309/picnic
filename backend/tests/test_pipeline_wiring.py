"""Structural guard for the staged-deployment pipeline (TEST-015).

These tests parse .github/workflows/ci-cd.yml and assert the dev → acceptance →
prod gate cannot be silently removed. They make no network calls and run in the
normal unit job.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci-cd.yml"


@pytest.fixture(scope="module")
def jobs() -> dict:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
    return workflow["jobs"]


def _environment_name(job: dict) -> str:
    environment = job.get("environment")
    if isinstance(environment, dict):
        return environment.get("name", "")
    return environment or ""


def _needs(job: dict) -> list[str]:
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else list(needs)


# TC-015-01
def test_deploy_dev_is_bound_to_develop_and_development_environment(jobs):
    deploy_dev = jobs["deploy-dev"]

    assert _environment_name(deploy_dev) == "development"
    assert "refs/heads/develop" in deploy_dev["if"]
    assert {"backend-test", "frontend-test"} <= set(_needs(deploy_dev))


# TC-015-02
def test_acceptance_runs_after_dev_deploy_against_dev_url(jobs):
    acceptance = jobs["acceptance"]
    job_text = yaml.safe_dump(acceptance)

    assert "deploy-dev" in _needs(acceptance)
    assert acceptance["env"]["BASE_URL"] == "https://mattdev.uber.space/picnic"
    assert "-m acceptance" in job_text  # the pytest marker is exercised


# TC-015-03
def test_prod_deploy_depends_on_acceptance(jobs):
    assert "acceptance" in _needs(jobs["deploy-prod"])


# TC-015-04
def test_prod_deploy_is_bound_to_main_and_production_environment(jobs):
    deploy_prod = jobs["deploy-prod"]

    assert _environment_name(deploy_prod) == "production"
    assert "refs/heads/main" in deploy_prod["if"]
