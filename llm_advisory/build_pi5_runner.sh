#!/usr/bin/env bash
# Build official ExecuTorch llama_main for Raspberry Pi 5 on Linux x86_64.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE="${EXECUTORCH_WORKSPACE:-${HOME}/executorch-rpi}"
EXECUTORCH_DIR="${EXECUTORCH_DIR:-${WORKSPACE}/executorch}"
BRANCH="${EXECUTORCH_BRANCH:-release/1.5}"
DEST="${REPO_ROOT}/models/llama/runtime"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  echo "Build host must be Linux x86_64 (e.g. Ubuntu 22.04/24.04)." >&2; exit 2
fi
for tool in git cmake python3; do
  command -v "${tool}" >/dev/null 2>&1 || { echo "Missing build prerequisite: ${tool}" >&2; exit 2; }
done
mkdir -p "${WORKSPACE}"
if [[ ! -d "${EXECUTORCH_DIR}/.git" ]]; then
  git clone --branch "${BRANCH}" --depth 1 https://github.com/pytorch/executorch.git "${EXECUTORCH_DIR}"
fi
cd "${EXECUTORCH_DIR}"
git fetch --depth 1 origin "${BRANCH}"
git checkout "${BRANCH}"
git submodule update --init --recursive
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
if ! python -c "import executorch" >/dev/null 2>&1; then ./install_executorch.sh; fi

# Official setup downloads the ARM toolchain, configures the Pi5 build and
# builds llama_main plus libllama_runner.so.
./examples/raspberry_pi/setup.sh pi5
RUNNER="${EXECUTORCH_DIR}/cmake-out/examples/models/llama/llama_main"
LIBRARY="${EXECUTORCH_DIR}/cmake-out/examples/models/llama/runner/libllama_runner.so"
if [[ ! -x "${RUNNER}" || ! -f "${LIBRARY}" ]]; then
  echo "Expected llama_main and libllama_runner.so were not produced." >&2; exit 1
fi
mkdir -p "${DEST}"
install -m 0755 "${RUNNER}" "${DEST}/llama_main"
install -m 0644 "${LIBRARY}" "${DEST}/libllama_runner.so"
git -C "${EXECUTORCH_DIR}" rev-parse HEAD > "${DEST}/executorch_commit.txt"
cat > "${DEST}/build_info.txt" <<EOF
Target: Raspberry Pi 5, aarch64, CPU/XNNPACK path
ExecuTorch branch: ${BRANCH}
ExecuTorch commit: $(cat "${DEST}/executorch_commit.txt")
Build host: $(uname -a)
Built at UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
echo "Runner installed into: ${DEST}"
echo "Copy the complete models/llama/runtime directory to the Pi."
echo "On the Pi, verify with: models/llama/runtime/llama_main --help"
