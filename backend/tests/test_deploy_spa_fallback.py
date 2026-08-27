"""
SPA deep-link fallback generation for scripts/deploy.sh (TEST-021).

Traces: ARCH-021
Verifies: REQ-021 (AC-021-01, AC-021-02, AC-021-03, AC-021-04)

Mirrors test_deploy_env.py's approach: source deploy_lib.sh in a subprocess
and invoke the function directly, so this stays SSH-free and fast.
"""

import subprocess
from pathlib import Path

DEPLOY_LIB = Path(__file__).resolve().parents[2] / "scripts" / "deploy_lib.sh"


def _write_spa_fallback(publish_dir: Path, base_path: str) -> str:
    subprocess.run(
        [
            "bash",
            "-c",
            f'source "{DEPLOY_LIB}"; write_spa_fallback "$1" "$2"',
            "_",
            str(publish_dir),
            base_path,
        ],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
        check=True,
    )
    return (publish_dir / ".htaccess").read_text()


# TC-021-01
# Given an empty temp directory standing in for FRONTEND_PUBLISH_DIR
# When write_spa_fallback <dir> / is invoked
# Then <dir>/.htaccess exists
# And it enables the rewrite engine and rewrites unmatched paths to index.html
def test_write_spa_fallback_creates_htaccess_pointing_at_index(tmp_path):
    # Arrange
    publish_dir = tmp_path / "picnic.matt-maxx.de"
    publish_dir.mkdir()

    # Act
    content = _write_spa_fallback(publish_dir, "/")

    # Assert
    assert (publish_dir / ".htaccess").is_file()
    assert "RewriteEngine On" in content
    assert "RewriteRule . index.html [L]" in content


# TC-021-02
# Given write_spa_fallback has written the fallback configuration
# When the generated rules are inspected
# Then the rewrite is guarded by "not an existing file" and "not an existing
#   directory" conditions
def test_write_spa_fallback_excludes_existing_files_and_directories(tmp_path):
    # Arrange
    publish_dir = tmp_path / "picnic.matt-maxx.de"
    publish_dir.mkdir()

    # Act
    content = _write_spa_fallback(publish_dir, "/")

    # Assert
    assert "RewriteCond %{REQUEST_FILENAME} !-f" in content
    assert "RewriteCond %{REQUEST_FILENAME} !-d" in content


# TC-021-03
# Given the two base paths the project deploys with
# When write_spa_fallback is invoked with "/" and with "/picnic-frontend/"
# Then the generated configuration bases the rewrite at exactly that path
def test_write_spa_fallback_bases_rewrite_on_the_hosts_base_path(tmp_path):
    # Arrange
    prod_dir = tmp_path / "prod"
    dev_dir = tmp_path / "dev"
    prod_dir.mkdir()
    dev_dir.mkdir()

    # Act
    prod_content = _write_spa_fallback(prod_dir, "/")
    dev_content = _write_spa_fallback(dev_dir, "/picnic-frontend/")

    # Assert
    assert "RewriteBase /\n" in prod_content
    assert "RewriteBase /picnic-frontend/\n" in dev_content


# TC-021-04
# Given a publish directory that already contains an .htaccess without a
#   fallback rule (the hand-written "RewriteBase /" from the REQ-019 cutover)
# When write_spa_fallback is invoked for that directory
# Then the file is overwritten with the generated configuration
def test_write_spa_fallback_replaces_a_stale_htaccess(tmp_path):
    # Arrange
    publish_dir = tmp_path / "picnic.matt-maxx.de"
    publish_dir.mkdir()
    (publish_dir / ".htaccess").write_text("RewriteBase /\n")

    # Act
    content = _write_spa_fallback(publish_dir, "/")

    # Assert
    assert "RewriteRule . index.html [L]" in content
