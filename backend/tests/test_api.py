import pytest


@pytest.mark.asyncio
class TestHealthEndpoint:

    async def test_health_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
class TestTasksAPI:

    async def test_submit_task_queued(self, client, session, admin_token):
        from app.core.security import hash_password
        from app.models.user import User
        user = User(
            username="admin_api_test",
            email="admin_api@test.com",
            hashed_password=hash_password("pass"),
            role="admin",
            data_clearance="confidential",
        )
        session.add(user)
        await session.flush()

        resp = await client.post(
            "/tasks",
            json={
                "agent_type": "incident_response",
                "priority": "medium",
                "input_text": "Check system status of web-01",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    async def test_invalid_agent_type_rejected(self, client, admin_token):
        resp = await client.post(
            "/tasks",
            json={
                "agent_type": "invalid_type",
                "priority": "medium",
                "input_text": "test",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    async def test_unauthorized_no_token(self, client):
        resp = await client.post(
            "/tasks",
            json={"agent_type": "incident_response", "priority": "medium", "input_text": "test"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestAuditAPI:

    async def test_admin_can_list_all_logs(self, client, admin_token):
        resp = await client.get("/audit", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_viewer_gets_own_logs_only(self, client, viewer_token):
        resp = await client.get("/audit", headers={"Authorization": f"Bearer {viewer_token}"})
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestKnowledgeAPI:

    async def test_knowledge_stats_admin(self, client, admin_token):
        resp = await client.get("/knowledge/stats", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_documents" in data

    async def test_knowledge_stats_viewer_forbidden(self, client, viewer_token):
        resp = await client.get("/knowledge/stats", headers={"Authorization": f"Bearer {viewer_token}"})
        assert resp.status_code == 403

    async def test_knowledge_search_operator(self, client, operator_token):
        resp = await client.post(
            "/knowledge/search",
            json={"query": "P1 incident escalation"},
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "retrieval_stats" in data

    async def test_compare_paths_admin_only(self, client, admin_token, operator_token):
        resp_admin = await client.get(
            "/knowledge/compare-paths?query=test",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp_admin.status_code == 200

        resp_op = await client.get(
            "/knowledge/compare-paths?query=test",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp_op.status_code == 403


@pytest.mark.asyncio
class TestApprovalsAPI:

    async def test_list_approvals_empty(self, client, admin_token):
        resp = await client.get("/approvals", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_review_nonexistent_approval(self, client, admin_token):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/approvals/{fake_id}/review",
            json={"action": "approve"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
