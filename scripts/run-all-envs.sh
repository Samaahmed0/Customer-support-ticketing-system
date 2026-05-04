#!/usr/bin/env bash
# run Development, Testing and Production at the same time
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose -p ticketing-parallel-dev --env-file .env.parallel.dev up -d --build
docker compose -p ticketing-parallel-test --env-file .env.parallel.test up -d --build
docker compose -p ticketing-parallel-prod --env-file .env.parallel.prod up -d --build

echo "Started three stacks."
echo "  Dev  Web UI: http://localhost:18080 · APIs: http://localhost:18001 (ticket) … Grafana http://localhost:13000"
echo "  Test Web UI: http://localhost:28080 · APIs: http://localhost:28001 … Grafana http://localhost:23000"
echo "  Prod Web UI: http://localhost:38080 · APIs: http://localhost:38001 … Grafana http://localhost:33000"
