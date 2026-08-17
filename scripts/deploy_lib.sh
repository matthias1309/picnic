#!/bin/bash
#
# Shared deploy helpers for the Picnic staged-deployment pipeline (REQ-015).
# Sourced by scripts/deploy.sh; kept separate so the ref-resolution logic is
# unit-testable without SSH (see backend/tests/test_deploy_ref.py).
#

# Echo the git ref to deploy: the DEPLOY_REF env var when set, else "main".
# The default keeps a bare `deploy.sh` invocation production-safe.
resolve_deploy_ref() {
    echo "${DEPLOY_REF:-main}"
}

# Echo the value of KEY from a dotenv-style file, or DEFAULT_VALUE if KEY is
# not present as a line in the file at all (REQ-019). A line present with an
# empty value (KEY=) is honored as an explicit override rather than falling
# back to DEFAULT_VALUE — plain bash `${VAR:-default}` can't make that
# distinction, which is what lets prod's .env set URL_PREFIX= to mean "no
# prefix" while a dev .env with no URL_PREFIX line at all keeps defaulting
# to /picnic.
read_env_default() {
    local key="$1" default_value="$2" env_file="$3"
    if [ -f "$env_file" ] && grep -qE "^${key}=" "$env_file"; then
        grep -E "^${key}=" "$env_file" | tail -1 | cut -d= -f2-
    else
        echo "$default_value"
    fi
}
