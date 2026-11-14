
import json
import uuid
from datetime import datetime, timezone

from .database import db


def process_events(events):
    batch_id = "BATCH_" + uuid.uuid4().hex[:10].upper()
    run_id = "RUN_" + uuid.uuid4().hex[:10].upper()
    started = datetime.now(timezone.utc).isoformat()

    processed = 0
    duplicates = 0
    rejected = 0
    late = 0

    with db() as c:
        c.execute(
            """INSERT INTO pipeline_runs
            (run_id, batch_id, status, received, processed,
             duplicates, rejected, late_events, started_at)
            VALUES (?, ?, 'running', ?, 0, 0, 0, 0, ?)""",
            (run_id, batch_id, len(events), started)
        )

        for e in events:
            payload = json.dumps(e, default=str)
            eid = str(e.get("event_id", "")) if isinstance(e, dict) else ""
            event_ts = str(e.get("event_timestamp", "")) if isinstance(e, dict) else ""

            ing_ts = (
                str(e.get("ingestion_timestamp") or datetime.now(timezone.utc).isoformat())
                if isinstance(e, dict)
                else datetime.now(timezone.utc).isoformat()
            )

            try:
                if not isinstance(e, dict):
                    raise ValueError("Event must be a JSON object")

                if not eid or not e.get("product_id") or not event_ts:
                    raise ValueError(
                        "Missing event_id, product_id or event_timestamp"
                    )

                if int(e.get("quantity", 0)) <= 0:
                    raise ValueError("quantity must be greater than zero")

                c.execute(
                    """INSERT OR IGNORE INTO raw_events
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        eid,
                        e.get("event_type", "sale"),
                        payload,
                        event_ts,
                        ing_ts,
                        batch_id
                    )
                )

                if c.execute("SELECT changes()").fetchone()[0] == 0:
                    duplicates += 1
                    continue

                product = c.execute(
                    "SELECT product_id FROM products WHERE product_id = ?",
                    (e["product_id"],)
                ).fetchone()

                if not product:
                    rejected += 1
                    c.execute(
                        """INSERT INTO rejected_events
                        (event_id, reason, payload, batch_id, created_at)
                        VALUES (?, ?, ?, ?, ?)""",
                        (eid, "Unknown product_id", payload, batch_id, ing_ts)
                    )
                    continue

                qty = int(e["quantity"])

                if e.get("event_type", "sale") == "sale":
                    current = c.execute(
                        "SELECT quantity FROM inventory WHERE product_id = ?",
                        (e["product_id"],)
                    ).fetchone()

                    if not current or current["quantity"] < qty:
                        rejected += 1
                        c.execute(
                            """INSERT INTO rejected_events
                            (event_id, reason, payload, batch_id, created_at)
                            VALUES (?, ?, ?, ?, ?)""",
                            (
                                eid,
                                "Insufficient inventory",
                                payload,
                                batch_id,
                                ing_ts
                            )
                        )
                        continue

                    c.execute(
                        """UPDATE inventory
                        SET quantity = quantity - ?, updated_at = ?
                        WHERE product_id = ?""",
                        (qty, ing_ts, e["product_id"])
                    )

                    day = event_ts[:10]

                    store_id = c.execute(
                        "SELECT store_id FROM products WHERE product_id = ?",
                        (e["product_id"],)
                    ).fetchone()["store_id"]

                    c.execute(
                        """INSERT INTO daily_aggregates
                        VALUES (?, ?, ?)
                        ON CONFLICT(aggregate_date, store_id)
                        DO UPDATE SET sales_units =
                        sales_units + excluded.sales_units""",
                        (day, store_id, qty)
                    )

                if event_ts < ing_ts:
                    try:
                        from datetime import datetime as dt

                        a = dt.fromisoformat(event_ts.replace("Z", "+00:00"))
                        b = dt.fromisoformat(ing_ts.replace("Z", "+00:00"))

                        if (b - a).total_seconds() > 300:
                            late += 1

                    except Exception:
                        pass

                c.execute(
                    """INSERT INTO processed_events
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        eid,
                        e.get("event_type", "sale"),
                        e["product_id"],
                        qty,
                        event_ts,
                        batch_id
                    )
                )

                processed += 1

            except Exception as exc:
                rejected += 1

                c.execute(
                    """INSERT INTO rejected_events
                    (event_id, reason, payload, batch_id, created_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    (eid or None, str(exc), payload, batch_id, ing_ts)
                )

        latest_event = max(
            [
                str(x.get("event_timestamp", ""))
                for x in events
                if isinstance(x, dict)
            ] or [""]
        )

        c.execute(
            """INSERT INTO pipeline_checkpoints
            VALUES ('sales_ingestion', ?, ?)
            ON CONFLICT(pipeline_name)
            DO UPDATE SET
            last_batch_id = excluded.last_batch_id,
            last_event_timestamp = excluded.last_event_timestamp""",
            (batch_id, latest_event)
        )

        c.execute(
            """UPDATE pipeline_runs
            SET status = 'success',
                processed = ?,
                duplicates = ?,
                rejected = ?,
                late_events = ?,
                finished_at = ?
            WHERE run_id = ?""",
            (
                processed,
                duplicates,
                rejected,
                late,
                datetime.now(timezone.utc).isoformat(),
                run_id
            )
        )

    return {
        "run_id": run_id,
        "batch_id": batch_id,
        "received": len(events),
        "processed": processed,
        "duplicates": duplicates,
        "rejected": rejected,
        "late_events": late
    }
