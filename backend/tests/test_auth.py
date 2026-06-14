"""
Integration tests for login, logout, and session-based authentication.

Traces: ARCH-006
Verifies: REQ-006 (AC-006-01, AC-006-02, AC-006-03, AC-006-04, AC-006-05, AC-006-06)
"""

from datetime import datetime, timedelta

from backend.auth.security import generate_token, hash_token
from backend.models import User, UserSession

BASE = "/picnic/api"


# TC-006-01: Successful login returns the user and sets a session cookie
def test_login_success_sets_session_cookie(unauthenticated_client, test_user):
    """
    Given a registered user "alice" with password "correct-password"
    When the client POSTs /picnic/api/auth/login with
         {"username": "alice", "password": "correct-password"}
    Then a 200 response is returned with {"id": ..., "username": "alice"}
    And the response sets an httponly "picnic_session" cookie
    """
    # Act
    response = unauthenticated_client.post(
        f"{BASE}/auth/login", json={"username": "alice", "password": "correct-password"}
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"id": test_user.id, "username": "alice"}
    assert "picnic_session" in response.cookies
    assert "HttpOnly" in response.headers["set-cookie"]


# TC-006-02: Login with the wrong password is rejected
def test_login_wrong_password_rejected(unauthenticated_client, test_user):
    """
    Given a registered user "alice" with password "correct-password"
    When the client POSTs /picnic/api/auth/login with
         {"username": "alice", "password": "wrong-password"}
    Then a 401 response is returned with {"detail": "Invalid username or password"}
    And no "picnic_session" cookie is set
    """
    # Act
    response = unauthenticated_client.post(
        f"{BASE}/auth/login", json={"username": "alice", "password": "wrong-password"}
    )

    # Assert
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}
    assert "picnic_session" not in response.cookies


# TC-006-03: Login with an unknown username is rejected
def test_login_unknown_username_rejected(unauthenticated_client, db_session):
    """
    Given no user "ghost" exists
    When the client POSTs /picnic/api/auth/login with
         {"username": "ghost", "password": "anything"}
    Then a 401 response is returned with {"detail": "Invalid username or password"}
    """
    # Act
    response = unauthenticated_client.post(
        f"{BASE}/auth/login", json={"username": "ghost", "password": "anything"}
    )

    # Assert
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


# TC-006-04: GET /auth/me without a session returns 401
def test_me_without_session_returns_401(unauthenticated_client):
    """
    Given no "picnic_session" cookie is sent
    When the client requests GET /picnic/api/auth/me
    Then a 401 response is returned with {"detail": "Not authenticated"}
    """
    # Act
    response = unauthenticated_client.get(f"{BASE}/auth/me")

    # Assert
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


# TC-006-05: GET /auth/me with a valid session returns the current user
def test_me_with_valid_session_returns_current_user(unauthenticated_client, test_user):
    """
    Given a registered user "alice" has logged in via POST /auth/login
    When the client requests GET /picnic/api/auth/me using the returned session cookie
    Then a 200 response is returned with {"id": ..., "username": "alice"}
    """
    # Arrange
    unauthenticated_client.post(
        f"{BASE}/auth/login", json={"username": "alice", "password": "correct-password"}
    )

    # Act
    response = unauthenticated_client.get(f"{BASE}/auth/me")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"id": test_user.id, "username": "alice"}


# TC-006-06: A protected data endpoint rejects requests without a session
def test_protected_endpoint_rejects_without_session(unauthenticated_client):
    """
    Given no "picnic_session" cookie is sent
    When the client requests GET /picnic/api/receipts
    Then a 401 response is returned with {"detail": "Not authenticated"}
    """
    # Act
    response = unauthenticated_client.get(f"{BASE}/receipts")

    # Assert
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


# TC-006-07: An expired session is rejected
def test_expired_session_is_rejected(unauthenticated_client, db_session, test_user):
    """
    Given a registered user "alice" has a session whose expires_at is in the past
    When the client requests GET /picnic/api/auth/me using that session's cookie
    Then a 401 response is returned with {"detail": "Not authenticated"}
    """
    # Arrange
    token = generate_token()
    db_session.add(
        UserSession(
            token_hash=hash_token(token),
            user_id=test_user.id,
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
    )
    db_session.commit()
    unauthenticated_client.cookies.set("picnic_session", token)

    # Act
    response = unauthenticated_client.get(f"{BASE}/auth/me")

    # Assert
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


# TC-006-08: Logout invalidates the session
def test_logout_invalidates_session(unauthenticated_client, test_user):
    """
    Given a registered user "alice" has logged in via POST /auth/login
    When the client POSTs /picnic/api/auth/logout using the session cookie
    Then a 200 response is returned and the "picnic_session" cookie is cleared
    And a subsequent GET /picnic/api/auth/me using the same (old) cookie value
        returns 401
    """
    # Arrange
    unauthenticated_client.post(
        f"{BASE}/auth/login", json={"username": "alice", "password": "correct-password"}
    )

    # Act
    logout_response = unauthenticated_client.post(f"{BASE}/auth/logout")
    me_response = unauthenticated_client.get(f"{BASE}/auth/me")

    # Assert
    assert logout_response.status_code == 200
    assert me_response.status_code == 401
    assert me_response.json() == {"detail": "Not authenticated"}


# Sanity check: User and UserSession models round-trip via the ORM
def test_user_and_session_models_persist(db_session):
    """
    Given a User with a hashed password
    When a UserSession referencing it is created
    Then both rows are persisted and linked via the relationship
    """
    # Arrange
    from backend.auth.security import hash_password as _hash

    user = User(username="bob", password_hash=_hash("hunter2"))
    db_session.add(user)
    db_session.commit()

    session = UserSession(
        token_hash=hash_token(generate_token()),
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(session)
    db_session.commit()

    # Assert
    assert session.user.username == "bob"
    assert user.sessions == [session]
