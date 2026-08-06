import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user, require_roles
from app.main import app

client = TestClient(app)


def test_me_requires_token():
    # Token gonderilmezse 401 donmeli (Supabase'e hic gidilmez).
    response = client.get("/me")
    assert response.status_code == 401


def test_me_returns_current_user_when_authenticated():
    # get_current_user'i sahte bir kullaniciyla degistiriyoruz (Supabase'e gitmeden).
    fake = CurrentUser(id="u1", email="user@example.com", full_name="Test User", role="manager")
    app.dependency_overrides[get_current_user] = lambda: fake
    try:
        response = client.get("/me")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "u1"
        assert body["role"] == "manager"
    finally:
        app.dependency_overrides.clear()


def test_require_roles_allows_matching_role():
    checker = require_roles("admin", "manager")
    user = CurrentUser(id="u2", role="admin")
    # checker bir bagimlilik fonksiyonu; user'i dogrudan gecerek mantigini test ediyoruz.
    result = checker(user)
    assert result is user


def test_require_roles_blocks_other_role():
    checker = require_roles("admin", "manager")
    user = CurrentUser(id="u3", role="employee")
    with pytest.raises(HTTPException) as exc:
        checker(user)
    assert exc.value.status_code == 403
