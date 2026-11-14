
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, date
import uuid

from .database import db, init_db
from .schemas import ProductIn, SaleIn, DonationIn
from .processor import process_events

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="FoodRescue API",
    version="1.0.0",
    description="Food surplus intelligence and redistribution prototype",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)



@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "FoodRescue API"
    }


# --------------------------------------------------
# DASHBOARD SUMMARY
# --------------------------------------------------

@app.get("/api/dashboard/summary")
def summary():
    with db() as c:
        total = c.execute(
            "SELECT COALESCE(SUM(quantity),0) n FROM inventory"
        ).fetchone()["n"]

        products = c.execute(
            "SELECT COUNT(*) n FROM products"
        ).fetchone()["n"]

        donations = c.execute(
            """SELECT COALESCE(SUM(quantity),0) n
               FROM donations
               WHERE status IN ('accepted','collected','delivered')"""
        ).fetchone()["n"]

        predictions = prediction_rows(c)

        at_risk = len([
            p for p in predictions
            if p["risk"] in ("High", "Medium")
        ])

        surplus = sum(
            p["surplus_quantity"] for p in predictions
        )

        return {
            "total_inventory": total,
            "products": products,
            "redistributed_units": donations,
            "at_risk_products": at_risk,
            "surplus_units": surplus
        }


# --------------------------------------------------
# FOOD WASTE PREDICTION
# --------------------------------------------------

def prediction_rows(c):
    rows = c.execute("""
        SELECT p.*, i.quantity
        FROM products p
        JOIN inventory i USING(product_id)
    """).fetchall()

    out = []
    today = date.today()

    for r in rows:
        try:
            days = (
                date.fromisoformat(r["expiry_date"]) - today
            ).days
        except (ValueError, TypeError):
            days = 99

        q = r["quantity"]

        # Transparent demo heuristic, not trained ML.
        if days <= 1 or (q >= 30 and days <= 3):
            risk = "High"
        elif days <= 3 or q >= 25:
            risk = "Medium"
        else:
            risk = "Low"

        surplus = max(0, q - 20) if risk != "Low" else 0

        reasons = []

        if days <= 3:
            reasons.append(
                f"Expiry in {max(days, 0)} day(s)"
            )

        if q >= 25:
            reasons.append("Stock above demo threshold")

        out.append({
            "product_id": r["product_id"],
            "name": r["name"],
            "category": r["category"],
            "quantity": q,
            "unit": r["unit"],
            "expiry_date": r["expiry_date"],
            "days_to_expiry": days,
            "risk": risk,
            "surplus_quantity": surplus,
            "safety_status": r["safety_status"],
            "reasons": reasons
        })

    return out


@app.get("/api/predictions")
def predictions():
    with db() as c:
        return prediction_rows(c)


# --------------------------------------------------
# INVENTORY
# --------------------------------------------------

@app.get("/api/inventory")
def inventory():
    with db() as c:
        return [
            dict(r)
            for r in c.execute("""
                SELECT p.*, i.quantity, i.updated_at
                FROM products p
                JOIN inventory i USING(product_id)
                ORDER BY p.name
            """).fetchall()
        ]


@app.post("/api/inventory")
def add_product(p: ProductIn):
    with db() as c:
        if c.execute(
            "SELECT 1 FROM stores WHERE store_id=?",
            (p.store_id,)
        ).fetchone() is None:
            raise HTTPException(400, "Unknown store_id")

        try:
            c.execute(
                "INSERT INTO products VALUES(?,?,?,?,?,?,?)",
                (
                    p.product_id,
                    p.store_id,
                    p.name,
                    p.category,
                    p.unit,
                    p.expiry_date,
                    p.safety_status
                )
            )

            c.execute(
                "INSERT INTO inventory VALUES(?,?,?)",
                (
                    p.product_id,
                    p.quantity,
                    datetime.now(timezone.utc).isoformat()
                )
            )

        except Exception as e:
            raise HTTPException(400, str(e))

    return {
        "message": "Product added",
        "product_id": p.product_id
    }


# --------------------------------------------------
# DELETE INVENTORY PRODUCT
# --------------------------------------------------

@app.delete("/api/inventory/{product_id}")
def delete_product(product_id: str):
    with db() as c:
        product = c.execute(
            "SELECT product_id FROM products WHERE product_id=?",
            (product_id,)
        ).fetchone()

        if not product:
            raise HTTPException(404, "Product not found")

        # Preserve donation history.
        existing_donation = c.execute(
            "SELECT 1 FROM donations WHERE product_id=? LIMIT 1",
            (product_id,)
        ).fetchone()

        if existing_donation:
            raise HTTPException(
                409,
                "Cannot delete this product because it has donation records"
            )

        try:
            c.execute(
                "DELETE FROM inventory WHERE product_id=?",
                (product_id,)
            )

            c.execute(
                "DELETE FROM products WHERE product_id=?",
                (product_id,)
            )

        except Exception:
            raise HTTPException(
                409,
                "Product cannot be deleted because it is referenced by other records"
            )

    return {
        "message": "Product deleted successfully",
        "product_id": product_id
    }


# --------------------------------------------------
# FOOD SAFETY VERIFICATION
# --------------------------------------------------

@app.post("/api/products/{product_id}/verify")
def verify_product(
    product_id: str,
    verifier_name: str,
    verifier_role: str
):
    allowed_roles = [
        "admin",
        "food_safety_officer"
    ]

    if verifier_role not in allowed_roles:
        raise HTTPException(
            403,
            "Only an authorized food safety officer can verify food"
        )

    with db() as c:
        product = c.execute(
            """SELECT product_id, expiry_date, safety_status
               FROM products
               WHERE product_id=?""",
            (product_id,)
        ).fetchone()

        if not product:
            raise HTTPException(404, "Product not found")

        try:
            expiry = date.fromisoformat(product["expiry_date"])
        except (ValueError, TypeError):
            raise HTTPException(400, "Invalid product expiry date")

        if expiry <= date.today():
            raise HTTPException(
                400,
                "Expired products cannot be verified"
            )

        c.execute(
            """UPDATE products
               SET safety_status='verified'
               WHERE product_id=?""",
            (product_id,)
        )

    return {
        "message": "Food verified successfully",
        "product_id": product_id,
        "verified_by": verifier_name,
        "status": "verified"
    }


# --------------------------------------------------
# SALES
# --------------------------------------------------

@app.post("/api/sales")
def record_sale(s: SaleIn):
    result = process_events([
        {
            "event_id": s.event_id,
            "event_type": "sale",
            "product_id": s.product_id,
            "quantity": s.quantity,
            "event_timestamp": s.event_timestamp
        }
    ])

    if result["rejected"]:
        raise HTTPException(
            400,
            {
                "message": "Sale rejected",
                "pipeline": result
            }
        )

    return result


# --------------------------------------------------
# NGO MANAGEMENT
# --------------------------------------------------

@app.get("/api/ngos")
def ngos():
    with db() as c:
        return [
            dict(r)
            for r in c.execute(
                "SELECT * FROM ngos WHERE active=1"
            ).fetchall()
        ]


# --------------------------------------------------
# DONATIONS
# --------------------------------------------------

@app.get("/api/donations")
def donations():
    with db() as c:
        return [
            dict(r)
            for r in c.execute("""
                SELECT
                    d.*,
                    p.name product_name,
                    n.name ngo_name
                FROM donations d
                JOIN products p USING(product_id)
                LEFT JOIN ngos n USING(ngo_id)
                ORDER BY created_at DESC
            """).fetchall()
        ]


@app.post("/api/donations")
def create_donation(d: DonationIn):
    with db() as c:
        row = c.execute(
            "SELECT quantity FROM inventory WHERE product_id=?",
            (d.product_id,)
        ).fetchone()

        if not row:
            raise HTTPException(404, "Product not found")

        if d.quantity <= 0:
            raise HTTPException(
                400,
                "Donation quantity must be greater than zero"
            )

        if d.quantity > row["quantity"]:
            raise HTTPException(
                400,
                "Donation quantity exceeds stock"
            )

        p = c.execute(
            """SELECT expiry_date, safety_status
               FROM products
               WHERE product_id=?""",
            (d.product_id,)
        ).fetchone()

        if not p:
            raise HTTPException(404, "Product details not found")

        if date.fromisoformat(p["expiry_date"]) <= date.today():
            raise HTTPException(
                400,
                "Expired products cannot be donated"
            )

        if p["safety_status"] != "verified":
            raise HTTPException(
                400,
                "Food must be marked verified by an authorized person before donation"
            )

        did = d.donation_id or "DON_" + uuid.uuid4().hex[:8]

        c.execute(
            """UPDATE inventory
               SET quantity=quantity-?, updated_at=?
               WHERE product_id=?""",
            (
                d.quantity,
                datetime.now(timezone.utc).isoformat(),
                d.product_id
            )
        )

        c.execute(
            "INSERT INTO donations VALUES(?,?,?,?,?,?,?)",
            (
                did,
                d.product_id,
                d.quantity,
                "pending",
                None,
                datetime.now(timezone.utc).isoformat(),
                d.note
            )
        )

    return {
        "message": "Donation request created",
        "donation_id": did,
        "status": "pending"
    }


# --------------------------------------------------
# DELETE PENDING DONATION
# --------------------------------------------------

@app.delete("/api/donations/{donation_id}")
def delete_donation(donation_id: str):
    with db() as c:
        donation = c.execute(
            """SELECT donation_id, product_id, quantity, status
               FROM donations
               WHERE donation_id=?""",
            (donation_id,)
        ).fetchone()

        if not donation:
            raise HTTPException(404, "Donation not found")

        if str(donation["status"]).lower() != "pending":
            raise HTTPException(
                409,
                "Only pending donations can be deleted. "
                "Accepted or completed donations must be preserved."
            )

        # Protect any donation that already has matching history.
        existing_match = c.execute(
            """SELECT 1
               FROM donation_matches
               WHERE donation_id=?
               LIMIT 1""",
            (donation_id,)
        ).fetchone()

        if existing_match:
            raise HTTPException(
                409,
                "This donation has matching history and cannot be deleted."
            )

        # Restore the reserved quantity to inventory.
        inventory_row = c.execute(
            "SELECT quantity FROM inventory WHERE product_id=?",
            (donation["product_id"],)
        ).fetchone()

        if not inventory_row:
            raise HTTPException(
                409,
                "Inventory record not found; donation was not deleted."
            )

        c.execute(
            """UPDATE inventory
               SET quantity=quantity+?, updated_at=?
               WHERE product_id=?""",
            (
                donation["quantity"],
                datetime.now(timezone.utc).isoformat(),
                donation["product_id"]
            )
        )

        c.execute(
            "DELETE FROM donations WHERE donation_id=?",
            (donation_id,)
        )

    return {
        "message": "Donation deleted and inventory stock restored.",
        "donation_id": donation_id,
        "restored_quantity": donation["quantity"]
    }


# --------------------------------------------------
# DONATION MATCHING
# --------------------------------------------------

@app.post("/api/donations/{donation_id}/match")
def match_donation(
    donation_id: str,
    ngo_id: str
):
    with db() as c:
        d = c.execute(
            "SELECT * FROM donations WHERE donation_id=?",
            (donation_id,)
        ).fetchone()

        n = c.execute(
            "SELECT * FROM ngos WHERE ngo_id=? AND active=1",
            (ngo_id,)
        ).fetchone()

        if not d or not n:
            raise HTTPException(
                404,
                "Donation or active NGO not found"
            )

        if d["status"] != "pending":
            raise HTTPException(
                409,
                "Only pending donations can be matched"
            )

        if d["quantity"] > n["capacity_units"]:
            raise HTTPException(
                400,
                "NGO capacity is insufficient"
            )

        c.execute(
            """UPDATE donations
               SET ngo_id=?, status='accepted'
               WHERE donation_id=?""",
            (ngo_id, donation_id)
        )

        c.execute(
            """INSERT INTO donation_matches
               (donation_id, ngo_id, score, status)
               VALUES(?,?,?,?)""",
            (
                donation_id,
                ngo_id,
                1.0,
                "accepted"
            )
        )

    return {
        "message": "Donation matched",
        "ngo_id": ngo_id
    }


# --------------------------------------------------
# ANALYTICS
# --------------------------------------------------

@app.get("/api/analytics/daily")
def daily():
    with db() as c:
        return [
            dict(r)
            for r in c.execute(
                "SELECT * FROM daily_aggregates ORDER BY aggregate_date"
            ).fetchall()
        ]


# --------------------------------------------------
# PIPELINE MONITOR
# --------------------------------------------------

@app.get("/api/pipeline/runs")
def runs():
    with db() as c:
        return [
            dict(r)
            for r in c.execute("""
                SELECT *
                FROM pipeline_runs
                ORDER BY started_at DESC
                LIMIT 30
            """).fetchall()
        ]


@app.get("/api/pipeline/quality")
def quality():
    with db() as c:
        checkpoint_row = c.execute(
            "SELECT * FROM pipeline_checkpoints"
        ).fetchone()

        return {
            "raw_events": c.execute(
                "SELECT COUNT(*) n FROM raw_events"
            ).fetchone()["n"],

            "processed_events": c.execute(
                "SELECT COUNT(*) n FROM processed_events"
            ).fetchone()["n"],

            "rejected_events": c.execute(
                "SELECT COUNT(*) n FROM rejected_events"
            ).fetchone()["n"],

            "checkpoint": (
                dict(checkpoint_row)
                if checkpoint_row else None
            )
        }


@app.post("/api/pipeline/process")
def process_batch(events: list[dict]):
    try:
        return process_events(events)

    except Exception as e:
        raise HTTPException(
            500,
            f"Batch failed: {e}"
        )
