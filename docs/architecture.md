# Architecture

## Microservices

| Service | Responsibility | Sync | Async |
|--------|----------------|------|-------|
| **ticket-service** | Ticket CRUD, status, source of truth in Postgres | HTTP `/tickets` | Publishes `ticket.*` to RabbitMQ |
| **support-service** | Assignments, agent messages, resolve workflow | HTTP to ticket-service; Postgres for support tables | Publishes `support.*` |
| **reporting-service** | Counters and `/reports/summary`; Prometheus gauges | HTTP | Consumes all routing keys; updates `reporting_counters` |
| **notification-service** | “Deliver” notifications (logs for this demo) | `/health`, `/metrics` | Consumes same events as reporting |

## Messaging

- Exchange: `ticketing.events` (topic, durable).
- Producers: ticket-service, support-service.
- Consumers: reporting-service (queue `reporting.events`), notification-service (queue `notification.events`).

## Data

- One PostgreSQL database (`ticketing`) for coursework simplicity. Each service owns its tables/schemas (`tickets`, `support_*`, `reporting_counters`).

## Observability

- **Prometheus** scrapes `/metrics` on each app.
- **Grafana** provisions Prometheus + Loki datasources and a sample dashboard.
- **Promtail** ships Docker container logs to **Loki** (requires Docker socket on Linux hosts).
