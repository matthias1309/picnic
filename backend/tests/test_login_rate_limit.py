"""
Integration tests for login rate limiting / lockout.

Traces: ARCH-007
Verifies: REQ-007 (AC-007-01, AC-007-02, AC-007-03, AC-007-04)
"""

from datetime import datetime, timedelta

from backend.models import LoginAttempt, User

BASE = "/picnic/api"


def _login(client, username: str, password: str):
    return client.post(f"{BASE}/auth/login", json={"username": username, "password": password})


# TC-007-01: Lockout after 5 failed attempts rejects the next attempt with 429
def test_lockout_after_five_failed_attempts(unauthenticated_client, test_user):
    """
    Given a registered user "alice" with password "correct-password"
    When the client POSTs /picnic/api/auth/login with the wrong password 5 times
    And then POSTs /picnic/api/auth/login with the correct password
    Then the 6th response is 429 Too Many Requests
    And no "picnic_session" cookie is set
    """
    # Act
    for _ in range(5):
        _login(unauthenticated_client, "alice", "wrong-password")
    response = _login(unauthenticated_client, "alice", "correct-password")

    # Assert
    assert response.status_code == 429
    assert "picnic_session" not in response.cookies


# TC-007-02: Successful login resets the failed-attempt counter
def test_successful_login_resets_failed_attempts(unauthenticated_client, test_user):
    """
    Given a registered user "alice" with password "correct-password"
    When the client POSTs /picnic/api/auth/login with the wrong password 3 times
    And then POSTs /picnic/api/auth/login with the correct password
    Then that response is 200 with a "picnic_session" cookie
    When the client then POSTs /picnic/api/auth/login with the wrong password once more
    Then that response is 401 (not 429) — the earlier failures were cleared
    """
    # Act
    for _ in range(3):
        _login(unauthenticated_client, "alice", "wrong-password")
    success_response = _login(unauthenticated_client, "alice", "correct-password")
    next_response = _login(unauthenticated_client, "alice", "wrong-password")

    # Assert
    assert success_response.status_code == 200
    assert "picnic_session" in success_response.cookies
    assert next_response.status_code == 401


# TC-007-03: Lockout applies equally to unknown usernames
def test_lockout_applies_to_unknown_username(unauthenticated_client, db_session):
    """
    Given no user "ghost" exists
    When the client POSTs /picnic/api/auth/login with username "ghost" 5 times
         (any password)
    And then POSTs /picnic/api/auth/login with username "ghost" again
    Then the 6th response is 429 Too Many Requests, the same as for a locked-out
         real account
    """
    # Act
    for _ in range(5):
        _login(unauthenticated_client, "ghost", "anything")
    response = _login(unauthenticated_client, "ghost", "anything")

    # Assert
    assert response.status_code == 429


# TC-007-04: An expired lockout no longer blocks login
def test_expired_lockout_does_not_block_login(unauthenticated_client, db_session, test_user: User):
    """
    Given a registered user "alice" with password "correct-password"
    And a LoginAttempt row for "alice" with locked_until in the past
    When the client POSTs /picnic/api/auth/login with the correct password
    Then the response is 200 with a "picnic_session" cookie
    """
    # Arrange
    db_session.add(
        LoginAttempt(
            username="alice",
            failed_count=5,
            first_failed_at=datetime.utcnow() - timedelta(minutes=30),
            locked_until=datetime.utcnow() - timedelta(minutes=1),
        )
    )
    db_session.commit()

    # Act
    response = _login(unauthenticated_client, "alice", "correct-password")

    # Assert
    assert response.status_code == 200
    assert "picnic_session" in response.cookies


# TC-007-05: A single failed attempt does not trigger a lockout
def test_single_failed_attempt_does_not_lock_out(unauthenticated_client, test_user):
    """
    Given a registered user "alice" with password "correct-password"
    When the client POSTs /picnic/api/auth/login with the wrong password once
    Then the response is 401 (not 429)
    """
    # Act
    response = _login(unauthenticated_client, "alice", "wrong-password")

    # Assert
    assert response.status_code == 401
