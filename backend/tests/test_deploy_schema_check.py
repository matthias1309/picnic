"""
Ordering guard: the schema drift check must run, unguarded, before the
service restart in scripts/deploy.sh (TEST-025).

Traces: ARCH-025
Verifies: REQ-025 (AC-025-04)

Structural/text assertions on deploy.sh itself, mirroring
test_pipeline_wiring.py's approach to ci-cd.yml: no subprocess, no SSH, no
real deploy — just confirming the script is wired the way ARCH-025
requires, so set -e is what aborts the deploy on drift.
"""

from pathlib import Path

DEPLOY_SH = Path(__file__).resolve().parents[2] / "scripts" / "deploy.sh"


def _lines() -> list[str]:
    return DEPLOY_SH.read_text().splitlines()


# TC-025-04
# Given the text of scripts/deploy.sh
# Then "set -e" appears near the top of the file, unconditionally
# And the schema-check invocation ("backend.schema_check") appears earlier
#   in the file than "supervisorctl restart"
# And the schema-check invocation is not wrapped in "set +e", "|| true", or
#   any construct that discards its exit status
def test_schema_check_runs_unguarded_before_restart():
    # Arrange
    lines = _lines()

    set_e_lines = [i for i, line in enumerate(lines) if line.strip().startswith("set -e")]
    schema_check_lines = [i for i, line in enumerate(lines) if "backend.schema_check" in line]
    restart_lines = [i for i, line in enumerate(lines) if "supervisorctl restart" in line]

    # Act / Assert
    assert set_e_lines, "deploy.sh must set -e unconditionally near the top"
    assert set_e_lines[0] < 20, "set -e must not be gated behind any setup step"

    assert schema_check_lines, "deploy.sh must invoke backend.schema_check"
    assert restart_lines, "deploy.sh must still restart the service on success"
    assert schema_check_lines[0] < restart_lines[0], (
        "the schema check must run before supervisorctl restart, so a drift "
        "failure (via set -e) happens before the old workers are touched"
    )

    for offset in (-1, 0, 1):
        neighbor = lines[schema_check_lines[0] + offset]
        assert "set +e" not in neighbor
        assert "|| true" not in neighbor
