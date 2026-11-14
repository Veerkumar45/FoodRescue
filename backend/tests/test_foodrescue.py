
from datetime import date, datetime, timedelta, timezone


def future_date(days=30):
    return (date.today() + timedelta(days=days)).isoformat()


def past_date(days=1):
    return (date.today() - timedelta(days=days)).isoformat()


def create_verified_product(client, create_product, verify_product,
                            product_id="VERIFIED_PRODUCT", quantity=50):
    create_product(
        product_id=product_id,
        quantity=quantity
    )
    response = verify_product(product_id)
    assert response.status_code == 200, response.text
    return product_id


def create_donation(client, product_id, quantity=5, donation_id="TEST_DONATION"):
    return client.post(
        "/api/donations",
        json={
            "donation_id": donation_id,
            "product_id": product_id,
            "quantity": quantity,
            "note": "Automated test donation"
        }
    )


# --------------------------------------------------
# 1. HEALTH AND DASHBOARD
# --------------------------------------------------

def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_summary(client):
    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200

    data = response.json()
    assert "total_inventory" in data
    assert "products" in data
    assert "redistributed_units" in data
    assert "at_risk_products" in data
    assert "surplus_units" in data


# --------------------------------------------------
# 2. INVENTORY
# --------------------------------------------------

def test_add_product(client, create_product):
    product_id = create_product()

    response = client.get("/api/inventory")

    assert response.status_code == 200
    assert any(
        item["product_id"] == product_id
        for item in response.json()
    )


def test_duplicate_product_rejected(client, create_product):
    create_product()

    response = client.post(
        "/api/inventory",
        json={
            "product_id": "TEST_PRODUCT_001",
            "store_id": "STORE_001",
            "name": "Duplicate Product",
            "category": "Food",
            "unit": "kg",
            "expiry_date": future_date(),
            "quantity": 10
        }
    )

    assert response.status_code == 400


def test_unknown_store_rejected(client):
    response = client.post(
        "/api/inventory",
        json={
            "product_id": "UNKNOWN_STORE_PRODUCT",
            "store_id": "INVALID_STORE",
            "name": "Test Product",
            "category": "Food",
            "unit": "kg",
            "expiry_date": future_date(),
            "quantity": 10
        }
    )

    assert response.status_code == 400


def test_negative_inventory_quantity_rejected(client):
    response = client.post(
        "/api/inventory",
        json={
            "product_id": "NEGATIVE_PRODUCT",
            "store_id": "STORE_001",
            "name": "Negative Quantity",
            "category": "Food",
            "unit": "kg",
            "expiry_date": future_date(),
            "quantity": -5
        }
    )

    assert response.status_code == 422


def test_delete_inventory_product(client, create_product):
    product_id = create_product()

    response = client.delete(
        f"/api/inventory/{product_id}"
    )

    assert response.status_code == 200

    inventory = client.get("/api/inventory").json()

    assert not any(
        item["product_id"] == product_id
        for item in inventory
    )


def test_delete_unknown_product(client):
    response = client.delete(
        "/api/inventory/DOES_NOT_EXIST"
    )

    assert response.status_code == 404


# --------------------------------------------------
# 3. FOOD SAFETY VERIFICATION
# --------------------------------------------------

def test_authorized_product_verification(
    client, create_product, verify_product
):
    product_id = create_product()

    response = verify_product(product_id)

    assert response.status_code == 200
    assert response.json()["status"] == "verified"


def test_unauthorized_verification(client, create_product):
    product_id = create_product()

    response = client.post(
        f"/api/products/{product_id}/verify",
        params={
            "verifier_name": "Unauthorized User",
            "verifier_role": "customer"
        }
    )

    assert response.status_code == 403


def test_expired_product_cannot_be_verified(
    client, create_product, verify_product
):
    product_id = create_product(
        product_id="EXPIRED_PRODUCT",
        expiry_date=past_date()
    )

    response = verify_product(product_id)

    assert response.status_code == 400


def test_unknown_product_verification(client):
    response = client.post(
        "/api/products/UNKNOWN/verify",
        params={
            "verifier_name": "Test Admin",
            "verifier_role": "admin"
        }
    )

    assert response.status_code == 404


# --------------------------------------------------
# 4. SALES
# --------------------------------------------------

def test_valid_sale_reduces_inventory(client, create_product):
    product_id = create_product(quantity=50)

    response = client.post(
        "/api/sales",
        json={
            "event_id": "SALE_TEST_001",
            "product_id": product_id,
            "quantity": 5,
            "event_timestamp": datetime.now(
                timezone.utc
            ).isoformat()
        }
    )

    assert response.status_code == 200
    assert response.json()["processed"] == 1

    inventory = client.get("/api/inventory").json()
    product = next(
        item for item in inventory
        if item["product_id"] == product_id
    )

    assert product["quantity"] == 45


def test_sale_exceeding_stock_rejected(client, create_product):
    product_id = create_product(quantity=5)

    response = client.post(
        "/api/sales",
        json={
            "event_id": "SALE_TEST_002",
            "product_id": product_id,
            "quantity": 10,
            "event_timestamp": datetime.now(
                timezone.utc
            ).isoformat()
        }
    )

    assert response.status_code == 400

    inventory = client.get("/api/inventory").json()
    product = next(
        item for item in inventory
        if item["product_id"] == product_id
    )

    assert product["quantity"] == 5


def test_zero_quantity_sale_rejected(client, create_product):
    product_id = create_product()

    response = client.post(
        "/api/sales",
        json={
            "event_id": "SALE_ZERO",
            "product_id": product_id,
            "quantity": 0,
            "event_timestamp": datetime.now(
                timezone.utc
            ).isoformat()
        }
    )

    assert response.status_code == 422


def test_duplicate_sale_event_not_processed_twice(
    client, create_product
):
    product_id = create_product(quantity=50)

    payload = {
        "event_id": "DUPLICATE_SALE",
        "product_id": product_id,
        "quantity": 5,
        "event_timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }

    first = client.post("/api/sales", json=payload)
    second = client.post("/api/sales", json=payload)

    assert first.status_code == 200
    assert first.json()["processed"] == 1

    assert second.status_code == 200
    assert second.json()["duplicates"] == 1
    assert second.json()["processed"] == 0

    inventory = client.get("/api/inventory").json()
    product = next(
        item for item in inventory
        if item["product_id"] == product_id
    )

    assert product["quantity"] == 45


# --------------------------------------------------
# 5. DONATIONS
# --------------------------------------------------

def test_unverified_food_cannot_be_donated(
    client, create_product
):
    product_id = create_product()

    response = create_donation(
        client, product_id
    )

    assert response.status_code == 400
    assert "verified" in response.text.lower()


def test_valid_donation_reduces_inventory(
    client, create_product, verify_product
):
    product_id = create_verified_product(
        client, create_product, verify_product
    )

    response = create_donation(
        client, product_id, quantity=5
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    inventory = client.get("/api/inventory").json()
    product = next(
        item for item in inventory
        if item["product_id"] == product_id
    )

    assert product["quantity"] == 45


def test_donation_exceeding_stock_rejected(
    client, create_product, verify_product
):
    product_id = create_verified_product(
        client, create_product, verify_product,
        quantity=5
    )

    response = create_donation(
        client, product_id, quantity=10
    )

    assert response.status_code == 400


def test_expired_food_cannot_be_donated(
    client, create_product, verify_product
):
    product_id = create_product(
        product_id="EXPIRED_DONATION",
        expiry_date=past_date()
    )

    # Verification itself rejects the expired product.
    verify_response = verify_product(product_id)
    assert verify_response.status_code == 400

    response = create_donation(
        client, product_id
    )

    assert response.status_code == 400


def test_delete_pending_donation_restores_stock(
    client, create_product, verify_product
):
    product_id = create_verified_product(
        client, create_product, verify_product
    )

    donation = create_donation(
        client, product_id, quantity=10
    )

    assert donation.status_code == 200

    donation_id = donation.json()["donation_id"]

    deleted = client.delete(
        f"/api/donations/{donation_id}"
    )

    assert deleted.status_code == 200
    assert deleted.json()["restored_quantity"] == 10

    inventory = client.get("/api/inventory").json()
    product = next(
        item for item in inventory
        if item["product_id"] == product_id
    )

    assert product["quantity"] == 50


def test_accepted_donation_cannot_be_deleted(
    client, create_product, verify_product
):
    product_id = create_verified_product(
        client, create_product, verify_product
    )

    donation = create_donation(
        client, product_id, quantity=10
    )

    donation_id = donation.json()["donation_id"]

    matched = client.post(
        f"/api/donations/{donation_id}/match",
        params={"ngo_id": "NGO_001"}
    )

    assert matched.status_code == 200

    deleted = client.delete(
        f"/api/donations/{donation_id}"
    )

    assert deleted.status_code == 409


def test_unknown_donation_cannot_be_deleted(client):
    response = client.delete(
        "/api/donations/UNKNOWN_DONATION"
    )

    assert response.status_code == 404


# --------------------------------------------------
# 6. NGO MATCHING
# --------------------------------------------------

def test_valid_ngo_matching(
    client, create_product, verify_product
):
    product_id = create_verified_product(
        client, create_product, verify_product
    )

    donation = create_donation(
        client, product_id, quantity=10
    )

    donation_id = donation.json()["donation_id"]

    response = client.post(
        f"/api/donations/{donation_id}/match",
        params={"ngo_id": "NGO_001"}
    )

    assert response.status_code == 200

    donations = client.get("/api/donations").json()
    record = next(
        item for item in donations
        if item["donation_id"] == donation_id
    )

    assert record["status"] == "accepted"
    assert record["ngo_id"] == "NGO_001"


def test_insufficient_ngo_capacity_rejected(
    client, create_product, verify_product
):
    product_id = create_verified_product(
        client, create_product, verify_product,
        quantity=100
    )

    donation = create_donation(
        client, product_id, quantity=70
    )

    donation_id = donation.json()["donation_id"]

    response = client.post(
        f"/api/donations/{donation_id}/match",
        params={"ngo_id": "NGO_003"}
    )

    assert response.status_code == 400


def test_donation_cannot_be_matched_twice(
    client, create_product, verify_product
):
    product_id = create_verified_product(
        client, create_product, verify_product
    )

    donation = create_donation(
        client, product_id, quantity=10
    )

    donation_id = donation.json()["donation_id"]

    first = client.post(
        f"/api/donations/{donation_id}/match",
        params={"ngo_id": "NGO_001"}
    )

    second = client.post(
        f"/api/donations/{donation_id}/match",
        params={"ngo_id": "NGO_002"}
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_inactive_or_unknown_ngo_rejected(
    client, create_product, verify_product
):
    product_id = create_verified_product(
        client, create_product, verify_product
    )

    donation = create_donation(
        client, product_id, quantity=5
    )

    donation_id = donation.json()["donation_id"]

    response = client.post(
        f"/api/donations/{donation_id}/match",
        params={"ngo_id": "UNKNOWN_NGO"}
    )

    assert response.status_code == 404


# --------------------------------------------------
# 7. PREDICTIONS AND ANALYTICS
# --------------------------------------------------

def test_predictions_endpoint(client, create_product):
    product_id = create_product(
        product_id="PREDICTION_TEST",
        quantity=40,
        expiry_date=future_date(1)
    )

    response = client.get("/api/predictions")

    assert response.status_code == 200

    prediction = next(
        item for item in response.json()
        if item["product_id"] == product_id
    )

    assert prediction["risk"] == "High"
    assert prediction["surplus_quantity"] == 20


def test_daily_analytics_after_sale(client, create_product):
    product_id = create_product(quantity=50)

    client.post(
        "/api/sales",
        json={
            "event_id": "ANALYTICS_SALE",
            "product_id": product_id,
            "quantity": 7,
            "event_timestamp": datetime.now(
                timezone.utc
            ).isoformat()
        }
    )

    response = client.get("/api/analytics/daily")

    assert response.status_code == 200
    assert any(
        row["sales_units"] >= 7
        for row in response.json()
    )


def test_ngo_endpoint(client):
    response = client.get("/api/ngos")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_donations_endpoint(client):
    response = client.get("/api/donations")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# --------------------------------------------------
# 8. PIPELINE MONITOR
# --------------------------------------------------

def test_pipeline_process_valid_event(client, create_product):
    product_id = create_product(quantity=50)

    response = client.post(
        "/api/pipeline/process",
        json=[
            {
                "event_id": "PIPELINE_VALID_001",
                "event_type": "sale",
                "product_id": product_id,
                "quantity": 5,
                "event_timestamp": datetime.now(
                    timezone.utc
                ).isoformat()
            }
        ]
    )

    assert response.status_code == 200
    assert response.json()["processed"] == 1
    assert response.json()["rejected"] == 0


def test_pipeline_rejects_unknown_product(client):
    response = client.post(
        "/api/pipeline/process",
        json=[
            {
                "event_id": "PIPELINE_UNKNOWN_001",
                "event_type": "sale",
                "product_id": "UNKNOWN_PRODUCT",
                "quantity": 5,
                "event_timestamp": datetime.now(
                    timezone.utc
                ).isoformat()
            }
        ]
    )

    assert response.status_code == 200
    assert response.json()["rejected"] == 1


def test_pipeline_quality_endpoint(client):
    response = client.get("/api/pipeline/quality")

    assert response.status_code == 200

    data = response.json()

    assert "raw_events" in data
    assert "processed_events" in data
    assert "rejected_events" in data
    assert "checkpoint" in data


def test_pipeline_runs_endpoint(client):
    response = client.get("/api/pipeline/runs")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_pipeline_process_endpoint_rejects_invalid_body(client):
    response = client.post(
        "/api/pipeline/process",
        json={"not": "a list"}
    )

    assert response.status_code == 422
