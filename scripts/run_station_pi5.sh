#!/usr/bin/env bash
# Start the Pi-hosted station using the provisioned local models/runtime.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f raspberry_pi/.env ]]; then
  echo "Missing raspberry_pi/.env. Run bash scripts/provision_pi5.sh first." >&2
  exit 2
fi
if [[ ! -x .venv/bin/python ]]; then
  echo "Missing project virtual environment. Run bash scripts/provision_pi5.sh first." >&2
  exit 2
fi
set -a
source raspberry_pi/.env
set +a
export LD_LIBRARY_PATH="$ROOT/models/llama/runtime:${LD_LIBRARY_PATH:-}"
exec "$ROOT/.venv/bin/python" raspberry_pi/station_controller.py --host "${PCB_STATION_HOST:-0.0.0.0}" --port "${PCB_STATION_PORT:-8080}"
