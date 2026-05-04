# Customer Support Ticketing System

 A customer support ticketing system built with Python microservices. Customers can submit tickets and track their status. Support agents can assign, reply and resolve tickets. The system uses RabbitMQ for async communication between services and includes a monitoring stack with Prometheus, Grafana and Loki.

---

## Project structure

- **`services/ticket-service/`**
  - Ticket CRUD and status tracking.
  - Stores tickets in Postgres.
  - Publishes ticket events to RabbitMQ.

- **`services/support-service/`**
  - Support workflow: assignments, messages and resolution.
  - Stores support tables in Postgres.
  - Calls ticket-service over HTTP when it needs ticket data/status updates.
  - Publishes support events to RabbitMQ.

- **`services/reporting-service/`**
  - Consumes events from RabbitMQ and updates aggregate counters in Postgres.
  - Exposes `/reports/summary` and Prometheus metrics.

- **`services/notification-service/`**
  - Consumes the same events as reporting.
  - In this demo it “delivers” notifications by writing structured logs (for Loki).

- **`shared/`**
  - Shared Pydantic schemas and routing-key constants (`ticketing_shared`).

- **`frontend/`**
  - Static HTML/CSS/vanilla-JS UI served through an nginx container.
  - Includes two tabs: **Customer portal** and **Support agent**.
  - Uses a reverse proxy (`/api/ticket`, `/api/support`, `/api/reporting`) so the browser stays same-origin.

- **`docker-compose.yml`**
  - Full local stack: Postgres, RabbitMQ, four services, web UI and optional observability components.

- **`k8s/`**
  - Kubernetes manifests for namespace, config, secrets, Postgres, RabbitMQ and app Deployments/Services.

- **`monitoring/`**
  - Prometheus scrape config, Grafana provisioning, Promtail config.

---

## Service responsibilities and communication

### Architecture
![Architecture](docs/images/arch.png)

### Synchronous (HTTP)

- Support-service → ticket-service: validate ticket exists and update ticket status when resolving.

### Asynchronous (RabbitMQ events)

- ticket-service publishes: `ticket.created`, `ticket.updated`
- support-service publishes: `support.message`, `support.resolved`
- reporting-service consumes all events and updates counters
- notification-service consumes all events and writes notification logs

---

## Local development (Docker Compose)

### Prerequisites

- Linux is recommended (Ubuntu). Windows is fine if Docker is working properly.
- Docker Engine + Docker Compose plugin:
  - `docker compose version`

### Environments (.env files)

The same `docker-compose.yml` runs in different modes depending on the chosen env file:

- **`.env.development`**: debug logs, auto-reload
- **`.env.testing`**: CI-like (no reload, INFO logs)
- **`.env.production`**: production-style (no reload, more workers, quieter logs)

Start one stack:

```bash
docker compose --env-file .env.development up -d --build
```

Stop it:

```bash
docker compose --env-file .env.development down
```

### URLs (default ports)

- Web UI: `http://localhost:8080`
- Ticket API (Swagger): `http://localhost:8001/docs`
- Support API (Swagger): `http://localhost:8002/docs`
- Reporting API (Swagger): `http://localhost:8003/docs`
- Notification API: `http://localhost:8004/health`
- RabbitMQ management: `http://localhost:15672` (default user/pass `ticketing` / `ticketing`)
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (default `admin` / `admin`)
- Loki: `http://localhost:3100`

### Quick demo flow

1. Create a ticket:
   - `POST http://localhost:8001/tickets`
   - Body: `{"title":"Login bug","description":"Cannot sign in"}`
2. Assign an agent:
   - `POST http://localhost:8002/tickets/1/assign`
   - Body: `{"agent_id":"agent-01"}`
3. Post a support message:
   - `POST http://localhost:8002/tickets/1/messages`
   - Body: `{"agent_id":"agent-01","body":"We are investigating."}`
4. Resolve the ticket:
   - `POST http://localhost:8002/tickets/1/resolve`
5. View reporting counters:
   - `GET http://localhost:8003/reports/summary`

---

## Observability (Compose)

This repository includes a simple observability stack in Compose:

- **Prometheus** scrapes `/metrics` from each service
- **Grafana** visualizes metrics and logs
- **Loki** stores logs
- **Promtail** ships Docker container logs to Loki (needs Docker socket access)

To test the notification demo:

- Generate events (create/update ticket, send support message, resolve).
- In Grafana → Explore → Loki, query logs for the notification container.

---

## Running all environments at once

For demonstration only (resource heavy), you can run development/testing/production-style stacks in parallel using different ports:

```bash
chmod +x scripts/run-all-envs.sh
./scripts/run-all-envs.sh
```

This uses:

- `.env.parallel.dev`
- `.env.parallel.test`
- `.env.parallel.prod`

---

## Kubernetes deployment (manifests)

### Prerequisites

- `kubectl`
- A Kubernetes cluster (kind, minikube, k3d)

### 1) Build images

From repo root, build the four service images (same Dockerfiles used by Compose):

```bash
docker build -f docker/ticket-service/Dockerfile -t ticketing-ticket-service:latest .
docker build -f docker/support-service/Dockerfile -t ticketing-support-service:latest .
docker build -f docker/reporting-service/Dockerfile -t ticketing-reporting-service:latest .
docker build -f docker/notification-service/Dockerfile -t ticketing-notification-service:latest .
```

### 2) Make images available to the cluster

If using **kind**, load them:

```bash
kind load docker-image ticketing-ticket-service:latest
kind load docker-image ticketing-support-service:latest
kind load docker-image ticketing-reporting-service:latest
kind load docker-image ticketing-notification-service:latest
```

If using a remote cluster, push images to a registry and update image names in the manifests.

### 3) Create secrets

`k8s/secret.example.yaml` is a template. Copy it and edit values:

```bash
cp k8s/secret.example.yaml k8s/secret.yaml
# edit k8s/secret.yaml
```

Keep the password fields consistent with the URLs inside the secret.

### 4) Apply manifests

Apply in this order:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/rabbitmq.yaml
kubectl apply -f k8s/apps.yaml
```

### 5) Access services

Use port-forwarding for local access:

```bash
kubectl -n ticketing port-forward svc/ticket-service 8001:8000
```

Then open `http://localhost:8001/docs`.

### Notes

- The Kubernetes manifests focus on the core platform (Postgres, RabbitMQ, services).
- The full monitoring stack is included in Compose; Kubernetes monitoring can be added separately (e.g., Helm charts / Prometheus Operator) if needed.

---

## Cleanup (Kubernetes)

Remove the namespace and everything inside it:

```bash
kubectl delete namespace ticketing
```

---

