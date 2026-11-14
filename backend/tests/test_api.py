from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

def test_health():
    init_db()
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"

def test_dashboard_shape():
    with TestClient(app) as client:
        data=client.get("/api/dashboard/summary").json()
        assert "total_inventory" in data
        assert "at_risk_products" in data
