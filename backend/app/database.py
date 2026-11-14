import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "foodrescue.db"

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS stores(
          store_id TEXT PRIMARY KEY, name TEXT NOT NULL, city TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS products(
          product_id TEXT PRIMARY KEY, store_id TEXT NOT NULL REFERENCES stores(store_id),
          name TEXT NOT NULL, category TEXT NOT NULL, unit TEXT NOT NULL,
          expiry_date TEXT NOT NULL, safety_status TEXT NOT NULL DEFAULT 'pending');
        CREATE TABLE IF NOT EXISTS inventory(
          product_id TEXT PRIMARY KEY REFERENCES products(product_id),
          quantity INTEGER NOT NULL CHECK(quantity >= 0), updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS raw_events(
          event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, payload TEXT NOT NULL,
          event_timestamp TEXT NOT NULL, ingestion_timestamp TEXT NOT NULL,
          batch_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS processed_events(
          event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, product_id TEXT NOT NULL,
          quantity INTEGER NOT NULL, event_timestamp TEXT NOT NULL, batch_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS rejected_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, reason TEXT NOT NULL,
          payload TEXT NOT NULL, batch_id TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ngos(
          ngo_id TEXT PRIMARY KEY, name TEXT NOT NULL, city TEXT NOT NULL,
          capacity_units INTEGER NOT NULL DEFAULT 100, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS donations(
          donation_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(product_id),
          quantity INTEGER NOT NULL, status TEXT NOT NULL, ngo_id TEXT REFERENCES ngos(ngo_id),
          created_at TEXT NOT NULL, note TEXT);
        CREATE TABLE IF NOT EXISTS donation_matches(
          match_id INTEGER PRIMARY KEY AUTOINCREMENT, donation_id TEXT NOT NULL,
          ngo_id TEXT NOT NULL, score REAL NOT NULL, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS pipeline_runs(
          run_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, status TEXT NOT NULL,
          received INTEGER NOT NULL, processed INTEGER NOT NULL, duplicates INTEGER NOT NULL,
          rejected INTEGER NOT NULL, late_events INTEGER NOT NULL, started_at TEXT NOT NULL,
          finished_at TEXT, error TEXT);
        CREATE TABLE IF NOT EXISTS pipeline_checkpoints(
          pipeline_name TEXT PRIMARY KEY, last_batch_id TEXT, last_event_timestamp TEXT);
        CREATE TABLE IF NOT EXISTS daily_aggregates(
          aggregate_date TEXT NOT NULL, store_id TEXT NOT NULL, sales_units INTEGER NOT NULL,
          PRIMARY KEY(aggregate_date, store_id));
        """)
        if not c.execute("SELECT 1 FROM stores LIMIT 1").fetchone():
            c.execute("INSERT INTO stores VALUES(?,?,?)", ("STORE_001","FreshMart Demo Store","Belagavi"))
            products = [
              ("PROD_001","STORE_001","Whole Wheat Bread","Bakery","pack","2026-11-15","pending",35),
              ("PROD_002","STORE_001","Fresh Milk","Dairy","litre","2026-11-15","pending",20),
              ("PROD_003","STORE_001","Apples","Produce","kg","2026-11-18","pending",15),
              ("PROD_004","STORE_001","Yogurt Cups","Dairy","cup","2026-11-16","pending",42),
              ("PROD_005","STORE_001","Bananas","Produce","kg","2026-11-17","pending",28),
            ]
            for p in products:
                c.execute("INSERT INTO products VALUES(?,?,?,?,?,?,?)", p[:7])
                c.execute("INSERT INTO inventory VALUES(?,?,datetime('now'))", (p[0],p[7]))
            c.executemany("INSERT INTO ngos VALUES(?,?,?,?,1)", [
              ("NGO_001","Belagavi Community Kitchen","Belagavi",120),
              ("NGO_002","Helping Hands Foundation","Belagavi",80),
              ("NGO_003","City Food Support","Belagavi",60)])
