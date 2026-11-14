
import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "foodrescue_test.db"

    # Redirect all database operations to the temporary database.
    monkeypatch.setattr(database, "DB_PATH", test_db)

    # Initialize tables and demo reference data.
    database.init_db()

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def create_product(client):
    def _create_product(
        product_id="TEST_PRODUCT_001",
        quantity=50,
        expiry_date=None,
        safety_status="pending",
        name="Test Orange Juice"
    ):
        from datetime import date, timedelta

        if expiry_date is None:
            expiry_date = (
                date.today() + timedelta(days=30)
            ).isoformat()

        response = client.post(
            "/api/inventory",
            json={
                "product_id": product_id,
                "store_id": "STORE_001",
                "name": name,
                "category": "Beverages",
                "unit": "bottle",
                "expiry_date": expiry_date,
                "quantity": quantity,
                "safety_status": safety_status
            }
        )

        assert response.status_code == 200, response.text
        return product_id

    return _create_product


@pytest.fixture
def verify_product(client):
    def _verify(product_id):
        return client.post(
            f"/api/products/{product_id}/verify",
            params={
                "verifier_name": "Test Admin",
                "verifier_role": "admin"
            }
        )

    return _verify
