"""
Settings tolerates shell-only .env keys (REQ-019 incident follow-up).

Traces: ARCH-019

scripts/deploy.sh's VITE_BASE_PATH, VITE_API_BASE, and FRONTEND_PUBLISH_DIR
are meant to live in the same per-host .env as the Settings fields below,
but are consumed by deploy.sh directly (shell), not by Settings. Pydantic
rejects unrecognized keys read from a .env file by default, which crashed
prod startup (ValidationError: extra_forbidden) the first time those keys
were added to .env — this guards against that regressing.
"""

from pathlib import Path

from backend.config import Settings


def test_settings_ignores_unknown_env_file_keys(tmp_path: Path):
    # Arrange: an .env file with deploy.sh's shell-only vars alongside a
    # real Settings field, exactly as it looks on the production host.
    env_file = tmp_path / ".env"
    env_file.write_text(
        "URL_PREFIX=\n"
        "VITE_BASE_PATH=/\n"
        "VITE_API_BASE=/api\n"
        "FRONTEND_PUBLISH_DIR=/var/www/virtual/mattmaxx/picnic.matt-maxx.de\n"
    )

    # Act
    settings = Settings(_env_file=str(env_file))

    # Assert
    assert settings.url_prefix == ""
