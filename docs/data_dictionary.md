# Data dictionary

| Table | Key fields | Purpose |
|---|---|---|
| stores | store_id (PK), name, city | Store master |
| products | product_id (PK), store_id (FK), category, expiry_date, safety_status | Product master and safety review status |
| inventory | product_id (PK/FK), quantity, updated_at | Current stock snapshot |
| raw_events | event_id (PK), payload, timestamps, batch_id | Original ingested events |
| processed_events | event_id (PK), product_id, quantity, event_timestamp | Accepted unique events |
| rejected_events | id (PK), event_id, reason, payload, batch_id | Quarantined records |
| ngos | ngo_id (PK), city, capacity_units, active | Receiving organization master |
| donations | donation_id (PK), product_id, quantity, status, ngo_id | Donation lifecycle |
| donation_matches | match_id (PK), donation_id, ngo_id, score, status | Matching decisions |
| pipeline_runs | run_id (PK), batch_id, counts, status, timestamps | Run observability |
| pipeline_checkpoints | pipeline_name (PK), last_batch_id, last_event_timestamp | Last committed position |
| daily_aggregates | aggregate_date + store_id (composite PK), sales_units | Daily sales metrics |

All timestamps are ISO-8601 strings. `quantity` values use the product's configured `unit`. Demo risk thresholds are not food-safety standards.
