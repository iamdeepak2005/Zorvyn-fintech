"""
Zorvyn Fintech - RBAC Tests.
Tests role-based access control enforcement across all endpoints.
Verifies the access control matrix is correctly enforced.
"""


class TestRBACAccessControl:
    """Test that RBAC is properly enforced per the access control matrix."""

    # ── Admin Endpoints ────────────────────────────────────

    def test_admin_can_create_user(self, client, admin_token):
        """ADMIN should be able to create users."""
        response = client.post(
            "/api/v1/admin/users",
            json={
                "name": "New User",
                "email": "newuser@test.com",
                "password": "password123",
                "role": "ANALYST",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == "newuser@test.com"

    def test_analyst_cannot_create_user(self, client, analyst_token):
        """ANALYST should NOT be able to create users (403)."""
        response = client.post(
            "/api/v1/admin/users",
            json={
                "name": "Bad User",
                "email": "bad@test.com",
                "password": "password123",
                "role": "VIEWER",
            },
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert response.status_code == 403

    def test_viewer_cannot_create_user(self, client, viewer_token):
        """VIEWER should NOT be able to create users (403)."""
        response = client.post(
            "/api/v1/admin/users",
            json={
                "name": "Bad User",
                "email": "bad@test.com",
                "password": "password123",
                "role": "VIEWER",
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_admin_can_list_users(self, client, admin_token):
        """ADMIN should be able to list users."""
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_analyst_cannot_list_users(self, client, analyst_token):
        """ANALYST should NOT be able to list users."""
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert response.status_code == 403

    # ── Record Endpoints ───────────────────────────────────

    def test_admin_can_create_record(self, client, admin_token):
        """ADMIN should be able to create records."""
        response = client.post(
            "/api/v1/records",
            json={
                "amount": 1000.00,
                "type": "INCOME",
                "category": "Salary",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        assert response.json()["success"] is True

    def test_analyst_cannot_create_record(self, client, analyst_token):
        """ANALYST should NOT be able to create records."""
        response = client.post(
            "/api/v1/records",
            json={
                "amount": 1000.00,
                "type": "INCOME",
                "category": "Salary",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert response.status_code == 403

    def test_viewer_cannot_create_record(self, client, viewer_token):
        """VIEWER should NOT be able to create records."""
        response = client.post(
            "/api/v1/records",
            json={
                "amount": 1000.00,
                "type": "INCOME",
                "category": "Salary",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_all_roles_can_list_records(self, client, admin_token, analyst_token, viewer_token):
        """All roles should be able to list records."""
        for token in [admin_token, analyst_token, viewer_token]:
            response = client.get(
                "/api/v1/records",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

    def test_analyst_cannot_update_record(self, client, admin_token, analyst_token):
        """ANALYST should NOT be able to update records."""
        # First create a record as admin
        create_resp = client.post(
            "/api/v1/records",
            json={
                "amount": 500.00,
                "type": "EXPENSE",
                "category": "Food",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        record_id = create_resp.json()["data"]["id"]

        # Try to update as analyst
        response = client.patch(
            f"/api/v1/records/{record_id}",
            json={"amount": 999.00},
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert response.status_code == 403

    def test_viewer_cannot_delete_record(self, client, admin_token, viewer_token):
        """VIEWER should NOT be able to delete records."""
        # Create a record
        create_resp = client.post(
            "/api/v1/records",
            json={
                "amount": 500.00,
                "type": "EXPENSE",
                "category": "Food",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        record_id = create_resp.json()["data"]["id"]

        response = client.delete(
            f"/api/v1/records/{record_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    # ── Dashboard Endpoints ────────────────────────────────

    def test_admin_can_access_dashboard(self, client, admin_token):
        """ADMIN should access dashboard endpoints."""
        endpoints = [
            "/api/v1/dashboard/summary",
            "/api/v1/dashboard/category-breakdown",
            "/api/v1/dashboard/trends",
            "/api/v1/dashboard/recent",
            "/api/v1/dashboard/insights",
        ]
        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert response.status_code == 200, f"Failed for {endpoint}"

    def test_analyst_can_access_dashboard(self, client, analyst_token):
        """ANALYST should access dashboard endpoints."""
        endpoints = [
            "/api/v1/dashboard/summary",
            "/api/v1/dashboard/category-breakdown",
            "/api/v1/dashboard/trends",
            "/api/v1/dashboard/recent",
            "/api/v1/dashboard/insights",
        ]
        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {analyst_token}"},
            )
            assert response.status_code == 200, f"Failed for {endpoint}"

    def test_viewer_cannot_access_dashboard(self, client, viewer_token):
        """VIEWER should NOT access dashboard endpoints."""
        endpoints = [
            "/api/v1/dashboard/summary",
            "/api/v1/dashboard/category-breakdown",
            "/api/v1/dashboard/trends",
            "/api/v1/dashboard/recent",
            "/api/v1/dashboard/insights",
        ]
        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {viewer_token}"},
            )
            assert response.status_code == 403, f"Should be forbidden for VIEWER: {endpoint}"

    # ── CSV Export ──────────────────────────────────────────

    def test_viewer_cannot_export(self, client, viewer_token):
        """VIEWER should NOT be able to export CSV."""
        response = client.get(
            "/api/v1/records/export",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_analyst_can_export(self, client, analyst_token):
        """ANALYST should be able to export CSV."""
        response = client.get(
            "/api/v1/records/export",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert response.status_code == 200

    # ── Inactive User ──────────────────────────────────────

    def test_inactive_user_rejected(self, client, inactive_user):
        """Inactive users should be rejected globally."""
        from app.core.security import create_access_token
        token = create_access_token(
            data={"user_id": inactive_user.id, "role": inactive_user.role.value}
        )
        response = client.get(
            "/api/v1/records",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    # ── Unauthenticated ────────────────────────────────────

    def test_unauthenticated_request_rejected(self, client):
        """Requests without token should be rejected."""
        response = client.get("/api/v1/records")
        assert response.status_code == 403

    # ── Health Check (public) ──────────────────────────────

    def test_health_check_public(self, client):
        """Health check should be accessible without auth."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
