import pytest


class TestSecurity:

    def test_hash_and_verify_roundtrip(self):
        from app.core.security import hash_password, verify_password
        pw = "supersecretpassword123!"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed)
        assert not verify_password("wrongpassword", hashed)

    def test_access_token_roundtrip(self):
        from app.core.security import create_access_token, decode_token
        data = {"sub": "alice", "role": "admin", "clearance": "confidential"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload["sub"] == "alice"
        assert payload["type"] == "access"

    def test_refresh_token_type(self):
        from app.core.security import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "bob"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_invalid_token_raises(self):
        from app.core.security import decode_token
        with pytest.raises(ValueError):
            decode_token("not.a.valid.token")

    def test_clearance_level_ordering(self):
        from app.core.security import clearance_level
        assert clearance_level("public") < clearance_level("internal")
        assert clearance_level("internal") < clearance_level("confidential")

    def test_can_access_hierarchy(self):
        from app.core.security import can_access
        assert can_access("confidential", "public")
        assert can_access("confidential", "internal")
        assert can_access("confidential", "confidential")
        assert can_access("internal", "public")
        assert can_access("internal", "internal")
        assert not can_access("internal", "confidential")
        assert not can_access("public", "internal")

    def test_accessible_levels(self):
        from app.core.security import accessible_levels
        assert accessible_levels("public") == ["public"]
        assert accessible_levels("internal") == ["public", "internal"]
        assert accessible_levels("confidential") == ["public", "internal", "confidential"]


@pytest.mark.asyncio
class TestAuthAPI:

    async def test_login_success(self, client, session):
        from app.core.security import hash_password
        from app.models.user import User
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("testpass123"),
            role="operator",
            data_clearance="internal",
        )
        session.add(user)
        await session.flush()

        resp = await client.post("/auth/login", json={"username": "testuser", "password": "testpass123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client, session):
        from app.core.security import hash_password
        from app.models.user import User
        user = User(
            username="testuser2",
            email="test2@example.com",
            hashed_password=hash_password("correctpass"),
            role="viewer",
            data_clearance="public",
        )
        session.add(user)
        await session.flush()

        resp = await client.post("/auth/login", json={"username": "testuser2", "password": "wrongpass"})
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/auth/login", json={"username": "nobody", "password": "pass"})
        assert resp.status_code == 401

    async def test_me_endpoint(self, client, admin_token):
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "admin"

    async def test_invalid_token_returns_401(self, client):
        resp = await client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert resp.status_code == 401

    async def test_clearance_in_token_payload(self, operator_token):
        from app.core.security import decode_token
        payload = decode_token(operator_token)
        assert payload["clearance"] == "internal"
