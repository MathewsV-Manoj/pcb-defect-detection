#!/usr/bin/env bash
# One-command provisioning for the PCB inspection project on a 64-bit Pi 5.
# Downloads local models, exports YOLO to ONNX, builds the ExecuTorch runner,
# verifies both inference paths, and preserves any existing GPIO configuration.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "aarch64" ]]; then
  echo "Run this provisioner on a 64-bit Raspberry Pi OS installation on Raspberry Pi 5." >&2
  echo "Detected: $(uname -s) / $(uname -m)" >&2
  exit 2
fi
if [[ -r /proc/device-tree/model ]] && ! tr -d '\0' </proc/device-tree/model | grep -q "Raspberry Pi 5"; then
  echo "This script is configured for Raspberry Pi 5 hardware only." >&2
  exit 2
fi

AVAILABLE_KIB="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
if [[ -z "$AVAILABLE_KIB" || "$AVAILABLE_KIB" -lt 12582912 ]]; then
  echo "At least 12 GiB of free disk space is required for model assets and the ExecuTorch build." >&2
  df -h "$ROOT"
  exit 2
fi

TOTAL_MEM_KIB="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
if [[ "$TOTAL_MEM_KIB" -lt 4194304 ]]; then
  echo "Warning: less than 4 GiB RAM detected. Llama inference/build may be memory constrained." >&2
fi
if [[ "$TOTAL_MEM_KIB" -lt 6291456 ]]; then
  EXECUTORCH_BUILD_JOBS="${EXECUTORCH_BUILD_JOBS:-1}"
else
  EXECUTORCH_BUILD_JOBS="${EXECUTORCH_BUILD_JOBS:-2}"
fi
export EXECUTORCH_BUILD_JOBS
export EXECUTORCH_SYSROOT="/"
export PCB_FIREBASE_PUBLISH=false

echo "[1/8] Installing Raspberry Pi OS packages"
sudo apt-get update
sudo apt-get install -y \
  build-essential cmake curl git tar xz-utils \
  python3 python3-dev python3-venv python3-pip \
  python3-opencv python3-gpiozero \
  libopenblas-dev libomp-dev libgflags-dev libgoogle-glog-dev libfmt-dev libeigen3-dev

echo "[2/8] Creating the project virtual environment"
if [[ ! -d .venv ]]; then
  python3 -m venv --system-site-packages .venv
fi
PYTHON="$ROOT/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip setuptools wheel

echo "[3/8] Installing detector, ONNX and station dependencies"
"$PYTHON" -m pip install \
  -r raspberry_pi/requirements.txt \
  -r pcb_engine_kit/requirements-train.txt \
  -r pcb_engine_kit/requirements-export.txt \
  "huggingface_hub>=0.30,<2"

echo "[4/8] Downloading and verifying the attributed PCB YOLOv8s checkpoint"
"$PYTHON" models/pretrained/download_sulojan_pcb_yolov8s.py

echo "[5/8] Exporting the pretrained PCB detector to local ONNX"
"$PYTHON" pcb_engine_kit/train_export.py export-upstream-onnx \
  --weights models/pretrained/sulojan_pcb_yolov8s/best.pt \
  --size 640 \
  --out deployment_upstream
install -m 0644 deployment_upstream/best.onnx models/best.onnx
install -m 0644 deployment_upstream/best.onnx.json models/best.onnx.json

echo "[6/8] Downloading the pinned Llama 3.2 1B ExecuTorch package"
"$PYTHON" llm_advisory/download_model.py

echo "[7/8] Building the ExecuTorch Pi 5 C++ runner against this Pi's own sysroot"
bash llm_advisory/build_pi5_runner.sh

echo "[8/8] Preserving GPIO configuration and verifying both local runtimes"
ENV_FILE="$ROOT/raspberry_pi/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  cp raspberry_pi/.env.example "$ENV_FILE"
fi
"$PYTHON" - "$ENV_FILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
required = {
    "PCB_MODEL_PATH": "models/best.onnx",
    "PCB_LLAMA_MODEL_PATH": "models/llama/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte",
    "PCB_LLAMA_TOKENIZER_PATH": "models/llama/tokenizer.model",
    "PCB_LLAMA_RUNNER_PATH": "models/llama/runtime/llama_main",
    "PCB_LLAMA_BACKEND": "cli",
    "PCB_LLAMA_REQUIRED": "true",
    "PCB_SEVERITY_POLICY_PATH": "models/severity_policy.json",
    "PCB_FIREBASE_PUBLISH": "false",
}
lines = path.read_text(encoding="utf-8").splitlines()
seen = set()
output = []
for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        output.append(line)
        continue
    key = stripped.split("=", 1)[0].strip()
    if key in required:
        output.append(f"{key}={required[key]}")
        seen.add(key)
    else:
        output.append(line)
for key, value in required.items():
    if key not in seen:
        output.append(f"{key}={value}")
path.write_text("\n".join(output) + "\n", encoding="utf-8")
PY

"$PYTHON" scripts/validate_pi5_runtime.py --out docs/results/pi5_runtime_smoke_test.json

echo
echo "Provisioning and software smoke tests completed."
echo "Local models: models/best.onnx and models/llama/"
echo "Smoke-test record: docs/results/pi5_runtime_smoke_test.json"
echo
echo "IMPORTANT: review raspberry_pi/.env and set the real BCM pins/polarities."
echo "The script deliberately does not guess IR or LED-driver wiring."
echo "Start the station with: bash scripts/run_station_pi5.sh"
