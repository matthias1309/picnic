"""
Per-host .env value resolution for scripts/deploy.sh (TEST-019).

Traces: ARCH-019
Verifies: REQ-019 (AC-019-05, AC-019-06)

Mirrors test_deploy_ref.py's approach: source deploy_lib.sh in a subprocess
and invoke the function directly, so this stays SSH-free and fast.
"""

import subprocess
from pathlib import Path

DEPLOY_LIB = Path(__file__).resolve().parents[2] / "scripts" / "deploy_lib.sh"


def _read_env_default(key: str, default_value: str, env_file: Path) -> str:
    result = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{DEPLOY_LIB}"; read_env_default "$1" "$2" "$3"',
            "_",
            key,
            default_value,
            str(env_file),
        ],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
        check=True,
    )
    return result.stdout.strip()


# TC-019-05
# Given a temp .env file containing the line "URL_PREFIX="
# When read_env_default URL_PREFIX /picnic <that file> is invoked
# Then it echoes "" (the explicit empty override, not the /picnic default)
def test_read_env_default_honors_explicit_empty_url_prefix(tmp_path):
    # Arrange
    env_file = tmp_path / ".env"
    env_file.write_text("URL_PREFIX=\n")

    # Act
    result = _read_env_default("URL_PREFIX", "/picnic", env_file)

    # Assert
    assert result == ""


# TC-019-05
# Given a temp .env file with no URL_PREFIX line at all
# When read_env_default URL_PREFIX /picnic <that file> is invoked
# Then it echoes "/picnic" (the default)
def test_read_env_default_falls_back_when_url_prefix_absent(tmp_path):
    # Arrange
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=sqlite:///./picnic.db\n")

    # Act
    result = _read_env_default("URL_PREFIX", "/picnic", env_file)

    # Assert
    assert result == "/picnic"


# TC-019-06
# Given a temp .env file containing
#   "FRONTEND_PUBLISH_DIR=/var/www/virtual/mattmaxx/picnic.matt-maxx.de"
# When read_env_default FRONTEND_PUBLISH_DIR $HOME/html/picnic-frontend
#   <that file> is invoked
# Then it echoes "/var/www/virtual/mattmaxx/picnic.matt-maxx.de"
def test_read_env_default_honors_explicit_frontend_publish_dir(tmp_path):
    # Arrange
    env_file = tmp_path / ".env"
    env_file.write_text("FRONTEND_PUBLISH_DIR=/var/www/virtual/mattmaxx/picnic.matt-maxx.de\n")

    # Act
    result = _read_env_default(
        "FRONTEND_PUBLISH_DIR", "/home/mattdev/html/picnic-frontend", env_file
    )

    # Assert
    assert result == "/var/www/virtual/mattmaxx/picnic.matt-maxx.de"


# TC-019-06
# Given a temp .env file with no FRONTEND_PUBLISH_DIR line at all
# When read_env_default FRONTEND_PUBLISH_DIR $HOME/html/picnic-frontend
#   <that file> is invoked
# Then it echoes "$HOME/html/picnic-frontend" (today's hardcoded default)
def test_read_env_default_falls_back_when_frontend_publish_dir_absent(tmp_path):
    # Arrange
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=sqlite:///./picnic.db\n")

    # Act
    result = _read_env_default(
        "FRONTEND_PUBLISH_DIR", "/home/mattdev/html/picnic-frontend", env_file
    )

    # Assert
    assert result == "/home/mattdev/html/picnic-frontend"
