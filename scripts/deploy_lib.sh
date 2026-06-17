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
