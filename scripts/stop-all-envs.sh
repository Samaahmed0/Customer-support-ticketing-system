#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose -p ticketing-parallel-dev  --env-file .env.parallel.dev  down
docker compose -p ticketing-parallel-test --env-file .env.parallel.test down
docker compose -p ticketing-parallel-prod --env-file .env.parallel.prod down

echo "Stopped three stacks."
