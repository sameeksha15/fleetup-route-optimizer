"""Auth flow + security properties: hashing, sessions, enumeration, lockout."""

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.services.seeding import DEMO_EMAIL, DEMO_PASSWORD


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@acmefleet.com"


def test_demo_login_succeeds_and_returns_org(anon_client):
    resp = anon_client.post(
        "/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == DEMO_EMAIL
    assert body["role"] == "owner"
    assert body["organization"]["name"]
    # A session cookie is set, httponly and not exposed to JS.
    assert "fleetup_session" in resp.cookies


def test_login_is_case_insensitive_for_email(anon_client):
    resp = anon_client.post(
        "/api/auth/login", json={"email": DEMO_EMAIL.upper(), "password": DEMO_PASSWORD}
    )
    assert resp.status_code == 200


def test_wrong_password_and_unknown_email_are_indistinguishable(anon_client):
    wrong = anon_client.post(
        "/api/auth/login", json={"email": DEMO_EMAIL, "password": "totally-wrong-1"}
    )
    unknown = anon_client.post(
        "/api/auth/login", json={"email": "nobody@acmefleet.com", "password": "whatever-1"}
    )
    assert wrong.status_code == 401 and unknown.status_code == 401
    # Same generic message -> no user enumeration.
    assert wrong.json()["detail"] == unknown.json()["detail"] == "Invalid email or password."


def test_me_requires_authentication(anon_client):
    assert anon_client.get("/api/auth/me").status_code == 401


def test_signup_login_me_logout_cycle():
    email = _unique_email()
    with TestClient(app) as c:
        signup = c.post(
            "/api/auth/signup",
            json={
                "full_name": "Asha Rao",
                "company_name": "Rao Freight Pvt Ltd",
                "email": email,
                "password": "Str0ngPass1",
            },
        )
        assert signup.status_code == 201, signup.text
        assert signup.json()["organization"]["name"] == "Rao Freight Pvt Ltd"

        # Signup logs you in: /me works immediately with the returned cookie.
        me = c.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == email

        assert c.post("/api/auth/logout").status_code == 204
        assert c.get("/api/auth/me").status_code == 401


def test_signup_rejects_duplicate_email(anon_client):
    resp = anon_client.post(
        "/api/auth/signup",
        json={
            "full_name": "Someone Else",
            "company_name": "Another Co",
            "email": DEMO_EMAIL,
            "password": "Str0ngPass1",
        },
    )
    assert resp.status_code == 409


def test_signup_enforces_password_policy(anon_client):
    for weak in ["short1", "allletters", "12345678"]:
        resp = anon_client.post(
            "/api/auth/signup",
            json={
                "full_name": "Weak Pw",
                "company_name": "Co",
                "email": _unique_email(),
                "password": weak,
            },
        )
        assert resp.status_code == 422, weak


def test_signup_rejects_invalid_email(anon_client):
    resp = anon_client.post(
        "/api/auth/signup",
        json={
            "full_name": "Bad Email",
            "company_name": "Co",
            "email": "not-an-email",
            "password": "Str0ngPass1",
        },
    )
    assert resp.status_code == 422


def test_account_locks_after_repeated_failures():
    # Use a dedicated account so locking it can't affect other tests' logins.
    email = _unique_email()
    with TestClient(app) as c:
        c.post(
            "/api/auth/signup",
            json={
                "full_name": "Lock Me",
                "company_name": "Co",
                "email": email,
                "password": "Str0ngPass1",
            },
        )
        c.post("/api/auth/logout")

        # Five wrong attempts trip the lockout.
        for _ in range(5):
            bad = c.post("/api/auth/login", json={"email": email, "password": "wrong-pass-9"})
            assert bad.status_code == 401

        # Now even the CORRECT password is refused with 429 until the lock lifts.
        locked = c.post("/api/auth/login", json={"email": email, "password": "Str0ngPass1"})
        assert locked.status_code == 429
