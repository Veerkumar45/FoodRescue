# Architecture

React/Vite frontend -> HTTP JSON REST -> FastAPI backend -> SQLite.

The backend owns validation, business rules, event processing, inventory mutation, aggregation, donation eligibility and persistence. The frontend never accesses SQLite directly.

## Batch transaction boundary

For each submitted batch, the processor creates a run row, inserts raw events, deduplicates by event_id, validates references and quantities, applies accepted sales to inventory, updates daily aggregates, writes processed/rejected outcomes, advances the checkpoint, and marks the run successful in one SQLite transaction. An exception rolls back the transaction.

## Trust boundaries

The event generator is synthetic. The surplus risk indicator is a transparent heuristic. Donation eligibility requires a human-verified product status and non-expired date; the application does not independently establish food safety.
