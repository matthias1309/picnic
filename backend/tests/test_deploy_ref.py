"""Deploy-ref resolution (TEST-015 / TC-015-05).

The deploy script must target origin/<DEPLOY_REF>, defaulting to main when the
variable is unset, so the same script deploys develop to dev and main to prod.
"""

import subprocess
from pathlib import Path

DEPLOY_LIB = Path(__file__).resolve().parents[2] / "scripts" / "deploy_lib.sh"


def _resolve(deploy_ref: str | None) -> str:
    env = {"PATH": "/usr/bin:/bin"}
    if deploy_ref is not None:
        env["DEPLOY_REF"] = deploy_ref
    result = subprocess.run(
        ["bash", "-c", f'source "{DEPLOY_LIB}"; resolve_deploy_ref'],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return result.stdout.strip()


# TC-015-05
def test_explicit_deploy_ref_is_used():
    assert _resolve("develop") == "develop"


# TC-015-05
def test_unset_deploy_ref_defaults_to_main():
    assert _resolve(None) == "main"
