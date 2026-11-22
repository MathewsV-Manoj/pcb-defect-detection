#!/usr/bin/env bash
# Provision the Raspberry Pi 5 runtime using the project's audited detector.
# No third-party PCB detector checkpoint is downloaded or substituted here.
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

MODEL="$ROOT/models/best.onnx"
MODEL_META="$ROOT/models/best.onnx.json"
if [[ ! -s "$MODEL" || ! -s "$MODEL_META" ]]; then
  echo "The project-trained ONNX detector is missing." >&2
  echo "Train, audit and export the detector on the development machine first." >&2
  echo "Copy deployment/best.onnx and deployment/best.onnx.json into models/ on this Pi." >&2
  exit 2
fi

python3 - "$MODEL" "$MODEL_META" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

model_path, metadata_path = map(Path, sys.argv[1:])
meta = json.loads(metadata_path.read_text(encoding="utf-8"))
digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
expected_classes = ["missing_hole", "open_circuit", "short_circuit"]
checks = {
    "ONNX SHA-256 matches sidecar": meta.get("sha256") == digest,
    "project training provenance is declared": meta.get("provenance_status") == "VERIFIED_PROJECT_TRAINING",
    "random initialization is declared": meta.get("initialization_method") == "random_initialization_from_yolo_yaml",
    "pretrained detector weights were not used": meta.get("pretrained_weights_used") is False,
    "class order matches deployment": meta.get("class_order") == expected_classes,
    "training checkpoint hash is recorded": bool(meta.get("checkpoint_sha256")),
    "dataset audit hash is recorded": bool(meta.get("dataset_audit_sha256")),
    "training provenance hash is recorded": bool(meta.get("training_provenance_sha256")),
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("Refusing unverified detector: " + "; ".join(failed))
print("Verified project-trained detector metadata:")
print("  ONNX SHA-256: " + digest)
print("  checkpoint SHA-256: " + meta["checkpoint_sha256"])
print("  dataset audit SHA-256: " + meta["dataset_audit_sha256"])
print("  training provenance SHA-256: " + meta["training_provenance_sha256"])
PY

AVAILABLE_KIB="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
if [[ -z "$AVAILABLE_KIB" || "$AVAILABLE_KIB" -lt 12582912 ]]; then
  echo "At least 12 GiB of free disk space is required for the Llama model and ExecuTorch build." >&2
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

echo "[1/7] Installing Raspberry Pi OS packages"
sudo apt-get update
sudo apt-get install -y \
  build-essential cmake curl git tar xz-utils \
  python3 python3-dev python3-venv python3-pip \
  python3-opencv python3-gpiozero \
  libopenblas-dev libomp-dev libgflags-dev libgoogle-glog-dev libfmt-dev libeigen3-dev

echo "[2/7] Creating the project virtual environment"
if [[ ! -d .venv ]]; then
  python3 -m venv --system-site-packages .venv
fi
PYTHON="$ROOT/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip setuptools wheel

echo "[3/7] Installing inference and model-download dependencies"
"$PYTHON" -m pip install -r raspberry_pi/requirements.txt "huggingface_hub>=0.30,<2"
"$PYTHON" -m pip check
"$PYTHON" - <<'PY'
import cv2
import numpy as np
import onnxruntime as ort

providers = ort.get_available_providers()
if "CPUExecutionProvider" not in providers:
    raise SystemExit("ONNX Runtime CPU provider unavailable: " + str(providers))
print("Verified runtime packages:")
print("  NumPy: " + np.__version__)
print("  OpenCV: " + cv2.__version__)
print("  ONNX Runtime: " + ort.__version__ + "; providers=" + str(providers))
PY

echo "[4/7] Rechecking the project ONNX model on this Pi"
"$PYTHON" - "$MODEL" "$MODEL_META" <<'PY'
import hashlib, json, sys
from pathlib import Path
model, sidecar = map(Path, sys.argv[1:])
metadata = json.loads(sidecar.read_text(encoding="utf-8"))
actual = hashlib.sha256(model.read_bytes()).hexdigest()
if metadata.get("sha256") != actual:
    raise SystemExit("Model hash changed after initial verification")
if metadata.get("class_order") != ["missing_hole", "open_circuit", "short_circuit"]:
    raise SystemExit("Unexpected PCB class order")
if metadata.get("pretrained_weights_used") is not False:
    raise SystemExit("The ONNX sidecar does not declare random-init project training")
print("Project ONNX artifact accepted: " + actual)
PY

echo "[5/7] Downloading the pinned Llama 3.2 1B ExecuTorch package"
"$PYTHON" llm_advisory/download_model.py

echo "[6/7] Building the ExecuTorch Pi 5 C++ runner against this Pi's own sysroot"
bash llm_advisory/build_pi5_runner.sh

echo "[7/7] Preserving GPIO configuration and verifying both local runtimes"
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

"$PYTHON" scripts/validate_pi5_runtime.py --model models/best.onnx --out docs/results/pi5_runtime_smoke_test.json

echo
echo "Provisioning and software smoke tests completed."
echo "Project detector: models/best.onnx"
echo "Llama model/runtime: models/llama/"
echo "Smoke-test record: docs/results/pi5_runtime_smoke_test.json"
echo
echo "IMPORTANT: review raspberry_pi/.env and set the real BCM pins/polarities."
echo "This script does not guess wiring or verify the physical station."
echo "Start the station with: bash scripts/run_station_pi5.sh"
