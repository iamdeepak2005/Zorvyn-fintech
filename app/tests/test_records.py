"""
Zorvyn Fintech - Record Tests.
Tests for financial record creation, idempotency, validation, and ownership.
"""

from datetime import date


class TestRecordCreation:
    """Test financial record creation and validation."""

    def test_create_record_success(self, client, admin_token):
        """Should create a record with valid data."""
        response = client.post(
            "/api/v1/records",
            json={
                "amount": 2500.50,
                "type": "INCOME",
                "category": "Salary",
                "date": "2026-03-15",
                "notes": "Monthly salary",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["amount"] == 2500.50
        assert data["data"]["type"] == "INCOME"
        assert data["data"]["category"] == "Salary"

    def test_create_record_amount_must_be_positive(self, client, admin_token):
        """Amount must be > 0."""
        response = client.post(
            "/api/v1/records",
            json={
                "amount": -100.00,
                "type": "EXPENSE",
                "category": "Test",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422

    def test_create_record_zero_amount_rejected(self, client, admin_token):
        """Amount of 0 should be rejected."""
        response = client.post(
            "/api/v1/records",
            json={
                "amount": 0,
                "type": "INCOME",
                "category": "Test",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422

    def test_create_record_invalid_type_rejected(self, client, admin_token):
        """Invalid record type should be rejected."""
        response = client.post(
            "/api/v1/records",
            json={
                "amount": 100.00,
                "type": "INVALID",
                "category": "Test",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422

    def test_create_record_missing_required_fields(self, client, admin_token):
        """Missing required fields should be rejected."""
        response = client.post(
            "/api/v1/records",
            json={"amount": 100.00},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422


class TestRecordIdempotency:
    """Test idempotency key support for POST /records."""

    def test_idempotency_prevents_duplicates(self, client, admin_token):
        """Same idempotency key should return same result without creating duplicate."""
        payload = {
            "amount": 500.00,
            "type": "EXPENSE",
            "category": "Rent",
            "date": "2026-03-01",
        }
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Idempotency-Key": "unique-key-123",
        }

        # First request
        resp1 = client.post("/api/v1/records", json=payload, headers=headers)
        assert resp1.status_code == 201

        # Second request with same key
        resp2 = client.post("/api/v1/records", json=payload, headers=headers)
        assert resp2.status_code == 201

        # Should return same data
        assert resp1.json()["data"]["id"] == resp2.json()["data"]["id"]

    def test_different_idempotency_keys_create_separate_records(self, client, admin_token):
        """Different idempotency keys should create separate records."""
        payload = {
            "amount": 500.00,
            "type": "EXPENSE",
            "category": "Rent",
            "date": "2026-03-01",
        }

        resp1 = client.post(
            "/api/v1/records",
            json=payload,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Idempotency-Key": "key-1",
            },
        )
        resp2 = client.post(
            "/api/v1/records",
            json=payload,
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Idempotency-Key": "key-2",
            },
        )
        assert resp1.json()["data"]["id"] != resp2.json()["data"]["id"]


class TestRecordOwnership:
    """Test data ownership enforcement (IDOR prevention)."""

    def test_viewer_sees_only_own_records(self, client, admin_token, viewer_token, viewer_user):
        """VIEWER should only see their own records."""
        # Create a record as admin
        client.post(
            "/api/v1/records",
            json={
                "amount": 1000.00,
                "type": "INCOME",
                "category": "Salary",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Viewer lists records — should see 0 (admin's record is not theirs)
        response = client.get(
            "/api/v1/records",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["total"] == 0

    def test_viewer_cannot_access_other_users_record(
        self, client, admin_token, viewer_token
    ):
        """VIEWER should get 403 when trying to access admin's record (IDOR prevention)."""
        # Create a record as admin
        create_resp = client.post(
            "/api/v1/records",
            json={
                "amount": 1000.00,
                "type": "INCOME",
                "category": "Salary",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        record_id = create_resp.json()["data"]["id"]

        # Viewer tries to access it — should be denied
        response = client.get(
            f"/api/v1/records/{record_id}",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    def test_admin_can_access_any_record(self, client, admin_token):
        """ADMIN should be able to access all records."""
        create_resp = client.post(
            "/api/v1/records",
            json={
                "amount": 1000.00,
                "type": "INCOME",
                "category": "Salary",
                "date": "2026-03-15",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        record_id = create_resp.json()["data"]["id"]

        response = client.get(
            f"/api/v1/records/{record_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200


class TestRecordSoftDelete:
    """Test soft delete functionality."""

    def test_soft_delete_sets_deleted_at(self, client, admin_token):
        """Soft delete should set deleted_at, not physically remove."""
        create_resp = client.post(
            "/api/v1/records",
            json={
                "amount": 100.00,
                "type": "EXPENSE",
                "category": "Test",
                "date": "2026-03-01",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        record_id = create_resp.json()["data"]["id"]

        # Delete
        del_resp = client.delete(
            f"/api/v1/records/{record_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 200

        # Should not appear in normal listing
        list_resp = client.get(
            "/api/v1/records",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert list_resp.json()["data"]["total"] == 0

    def test_admin_can_see_deleted_with_flag(self, client, admin_token):
        """ADMIN can include deleted records with include_deleted=true."""
        create_resp = client.post(
            "/api/v1/records",
            json={
                "amount": 100.00,
                "type": "EXPENSE",
                "category": "Test",
                "date": "2026-03-01",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        record_id = create_resp.json()["data"]["id"]

        # Soft delete
        client.delete(
            f"/api/v1/records/{record_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # List with include_deleted
        list_resp = client.get(
            "/api/v1/records?include_deleted=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert list_resp.json()["data"]["total"] == 1


class TestRecordFiltering:
    """Test filtering, pagination, and sorting."""

    def test_filter_by_type(self, client, admin_token):
        """Should filter records by type."""
        # Create income and expense
        for record_type in ["INCOME", "EXPENSE"]:
            client.post(
                "/api/v1/records",
                json={
                    "amount": 100.00,
                    "type": record_type,
                    "category": "Test",
                    "date": "2026-03-15",
                },
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        # Filter by INCOME
        resp = client.get(
            "/api/v1/records?type=INCOME",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.json()["data"]["total"] == 1
        assert resp.json()["data"]["items"][0]["type"] == "INCOME"

    def test_pagination(self, client, admin_token):
        """Should paginate results correctly."""
        # Create 5 records
        for i in range(5):
            client.post(
                "/api/v1/records",
                json={
                    "amount": 100.00 + i,
                    "type": "INCOME",
                    "category": f"Cat-{i}",
                    "date": "2026-03-15",
                },
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        # Page 1 with limit 2
        resp = client.get(
            "/api/v1/records?page=1&limit=2",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()["data"]
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3

    def test_search_in_notes(self, client, admin_token):
        """Should search in notes field."""
        client.post(
            "/api/v1/records",
            json={
                "amount": 100.00,
                "type": "INCOME",
                "category": "Test",
                "date": "2026-03-15",
                "notes": "special keyword here",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.post(
            "/api/v1/records",
            json={
                "amount": 200.00,
                "type": "EXPENSE",
                "category": "Other",
                "date": "2026-03-15",
                "notes": "nothing",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = client.get(
            "/api/v1/records?search=special",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.json()["data"]["total"] == 1
