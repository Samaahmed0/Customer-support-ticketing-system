# Customer Support Ticketing System

Python **FastAPI** microservices for tickets, support workflows, reporting, and notifications. The stack runs on **Linux** (recommended: **Ubuntu** with Docker Engine + Compose). Development on Windows is fine; build and run the containers on Ubuntu to match coursework requirements.

## What is in this repo

| Area | Purpose |
|------|---------|
| [services/ticket-service](services/ticket-service) | Ticket CRUD, status, Postgres, publishes RabbitMQ events |
| [services/support-service](services/support-service) | Assignments & messages, calls ticket-service over HTTP, publishes events |
| [services/reporting-service](services/reporting-service) | Async consumer + `/reports/summary` + Prometheus gauges |
| [services/notification-service](services/notification-service) | Async consumer; logs structured “notifications” for Loki |
| [shared](shared) | Shared Pydantic models and routing-key constants (`ticketing_shared` package) |
| [docker-compose.yml](docker-compose.yml) | Full stack: Postgres, RabbitMQ, apps, Prometheus, Grafana, Loki, Promtail |
| [.env.development](.env.development) / [.env.testing](.env.testing) / [.env.production](.env.production) | **Three environments** (log level, reload, workers) |
| [k8s](k8s) | Namespace, Postgres, RabbitMQ, four app Deployments/Services, example Secret |
| [monitoring](monitoring) | Prometheus scrape config, Grafana provisioning, Promtail config |
| [scripts/run-all-envs.sh](scripts/run-all-envs.sh) | **Optional** parallel stacks for strict “all envs at once” demos |

More detail: [docs/architecture.md](docs/architecture.md).

## Prerequisites (Ubuntu)

- Docker Engine and Docker Compose plugin (`docker compose version`).
- Optional: `kubectl` + a local cluster (**kind** / **minikube** / **k3d**) for Kubernetes.

## Quick start (Docker Compose)

From the repository root on **Linux**:

```bash
# One active stack at a time — pick an environment file:
docker compose --env-file .env.development up -d --build

# Switch later:
docker compose --env-file .env.development down
docker compose --env-file .env.testing up -d --build
```

### URLs (default host ports from `.env.*`)

| Service | URL |
|---------|-----|
| Ticket API (Swagger) | http://localhost:8001/docs |
| Support API | http://localhost:8002/docs |
| Reporting API | http://localhost:8003/docs |
| Notification API | http://localhost:8004/docs |
| RabbitMQ management | http://localhost:15672 (user/pass from env, default `ticketing` / `ticketing`) |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (default `admin` / `admin`) |
| Loki | http://localhost:3100 |

### Try the flow

1. Create a ticket: `POST http://localhost:8001/tickets` with JSON `{"title":"Login bug","description":"Cannot sign in"}`.
2. Add a support message: `POST http://localhost:8002/tickets/1/messages` with `{"agent_id":"agent-1","body":"We are investigating."}`.
3. Resolve: `POST http://localhost:8002/tickets/1/resolve`.
4. Open reporting summary: `GET http://localhost:8003/reports/summary`.
5. In Grafana → **Explore** → datasource **Loki** → query `{container=~".*notification.*"}` to see notification logs.

## Environments (Development / Testing / Production)

All behavior is controlled by **one** [docker-compose.yml](docker-compose.yml) and the chosen **env file**:

| File | Typical use |
|------|-------------|
| [.env.development](.env.development) | `LOG_LEVEL=DEBUG`, `UVICORN_EXTRA_ARGS=--reload`, single worker |
| [.env.testing](.env.testing) | `LOG_LEVEL=INFO`, no extra args (CI-like) |
| [.env.production](.env.production) | `LOG_LEVEL=WARNING`, `UVICORN_WORKERS=2`, no reload |

**RabbitMQ:** Compose creates user `ticketing` / `ticketing` (override with `RABBITMQ_USER`, `RABBITMQ_PASS`, `RABBITMQ_URL`). Guest is **not** used between containers (localhost-only in RabbitMQ).

### Optional: three stacks at once (heavy)

```bash
chmod +x scripts/run-all-envs.sh
./scripts/run-all-envs.sh
```

Uses [.env.parallel.dev](.env.parallel.dev), [.env.parallel.test](.env.parallel.test), [.env.parallel.prod](.env.parallel.prod) with different host ports and Compose project names.

## Building images locally

From repo root:

```bash
docker build -f docker/ticket-service/Dockerfile -t ticketing-ticket-service:latest .
docker build -f docker/support-service/Dockerfile -t ticketing-support-service:latest .
docker build -f docker/reporting-service/Dockerfile -t ticketing-reporting-service:latest .
docker build -f docker/notification-service/Dockerfile -t ticketing-notification-service:latest .
```

Compose `build:` uses the same Dockerfiles.

## Kubernetes (outline)

1. Build and load images into your cluster (example with **kind**):

   ```bash
   kind create cluster
   docker build -f docker/ticket-service/Dockerfile -t ticketing-ticket-service:latest .
   # … other three images …
   kind load docker-image ticketing-ticket-service:latest
   # … load the other images …
   ```

2. Create secrets from the example (edit passwords; keep `database-url` password aligned with `postgres-password`, and `rabbitmq-url` with `rabbitmq-password`):

   ```bash
   cp k8s/secret.example.yaml k8s/secret.yaml
   # edit k8s/secret.yaml
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/secret.yaml
   kubectl apply -f k8s/postgres.yaml
   kubectl apply -f k8s/rabbitmq.yaml
   kubectl apply -f k8s/apps.yaml
   ```

3. Port-forward to try APIs:

   ```bash
   kubectl -n ticketing port-forward svc/ticket-service 8001:8000
   ```

Monitoring in Kubernetes is **not** bundled here (add Prometheus Operator or Helm charts if required); Compose includes the full observability path for local demos.

## Assignment compliance (mapping)

| Requirement | Where |
|-------------|--------|
| Linux host | Run on Ubuntu; this README targets Linux commands. |
| Multiple containers communicating | [docker-compose.yml](docker-compose.yml) user-defined bridge network. |
| ≥3 distinct images | Four custom service images + `postgres` + `rabbitmq` + Prometheus stack images. |
| Dockerfiles (size-conscious) | Multi-stage, slim base: [docker/ticket-service/Dockerfile](docker/ticket-service/Dockerfile) (and siblings). |
| Dev / Test / Prod configurations | [.env.development](.env.development), [.env.testing](.env.testing), [.env.production](.env.production) + single Compose file. |
| All environments on one machine | Same machine, switch env files; optional [scripts/run-all-envs.sh](scripts/run-all-envs.sh). |
| Kubernetes orchestration | [k8s/](k8s/) manifests. |
| Documentation | This README + [docs/architecture.md](docs/architecture.md). |
| **Bonus:** async messaging | RabbitMQ topic exchange `ticketing.events`; see [docs/architecture.md](docs/architecture.md). |
| **Bonus:** monitoring & central logs | Prometheus + Grafana + Loki + Promtail in Compose; Promtail needs Docker socket (Linux). |

## License

Educational / coursework use.
