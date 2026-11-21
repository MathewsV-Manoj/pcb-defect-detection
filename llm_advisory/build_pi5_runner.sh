#!/usr/bin/env bash
# Build the official ExecuTorch llama_main runner for Raspberry Pi 5.
# Preferred path: execute on the Pi itself so the runner is linked against its
# installed libc. An x86_64 cross-build must provide a matching Pi sysroot.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE="${EXECUTORCH_WORKSPACE:-${HOME}/executorch-rpi}"
EXECUTORCH_DIR="${EXECUTORCH_DIR:-${WORKSPACE}/executorch}"
BRANCH="${EXECUTORCH_BRANCH:-release/1.5}"
REVISION="${EXECUTORCH_REVISION:-985c1ceccc8bb8b6a32294f71aeb5d2f299562f7}"
DEST="${REPO_ROOT}/models/llama/runtime"
HOST_OS="$(uname -s)"
HOST_ARCH="$(uname -m)"

if [[ "$HOST_OS" != "Linux" ]]; then
  echo "ExecuTorch Pi 5 runner build requires Linux." >&2
  exit 2
fi
case "$HOST_ARCH" in
  aarch64|arm64) HOST_ARCH="aarch64" ;;
  x86_64|amd64) HOST_ARCH="x86_64" ;;
  *) echo "Unsupported build host architecture: $HOST_ARCH" >&2; exit 2 ;;
esac

if [[ "$HOST_ARCH" == "aarch64" ]]; then
  if [[ -r /proc/device-tree/model ]] && ! tr -d '\0' </proc/device-tree/model | grep -q "Raspberry Pi 5"; then
    echo "ARM64 host detected, but it is not identified as a Raspberry Pi 5." >&2
    echo "Run on the Pi 5 itself, or set EXECUTORCH_SYSROOT to the target Pi rootfs on x86_64." >&2
    exit 2
  fi
  SYSROOT="${EXECUTORCH_SYSROOT:-/}"
else
  SYSROOT="${EXECUTORCH_SYSROOT:-}"
  if [[ -z "$SYSROOT" || ! -d "$SYSROOT" ]]; then
    echo "Cross-compiling from x86_64 requires EXECUTORCH_SYSROOT to point to the target Pi's root filesystem." >&2
    echo "This prevents a GLIBC/CXXABI mismatch on Raspberry Pi OS." >&2
    exit 2
  fi
fi

for tool in git cmake python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing build prerequisite: $tool" >&2; exit 2; }
done
mkdir -p "$WORKSPACE"
if [[ ! -d "$EXECUTORCH_DIR/.git" ]]; then
  git clone --branch "$BRANCH" --depth 1 https://github.com/pytorch/executorch.git "$EXECUTORCH_DIR"
fi
cd "$EXECUTORCH_DIR"
git fetch --depth 1 origin "$REVISION"
git checkout --detach "$REVISION"
git submodule update --init --recursive

if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "cmake>=3.26,<4"
export PATH="$VIRTUAL_ENV/bin:$PATH"
if ! python -c "import executorch" >/dev/null 2>&1; then
  ./install_executorch.sh
fi

# The upstream setup script normally uses the ARM toolchain's bundled sysroot.
# On the Pi itself we override it with '/' so that the binary links against the
# exact libc/libstdc++ available on the running device. For x86_64 builds the
# caller must supply an extracted sysroot from the target Pi.
SETUP_SOURCE="${EXECUTORCH_DIR}/examples/raspberry_pi/setup.sh"
SETUP_SCRIPT="${EXECUTORCH_DIR}/examples/raspberry_pi/setup-local-sysroot.sh"
python - "$SETUP_SOURCE" "$SETUP_SCRIPT" "$SYSROOT" "${EXECUTORCH_BUILD_JOBS:-2}" <<'PY'
from pathlib import Path
import sys

source, destination, sysroot, jobs = sys.argv[1:]
text = Path(source).read_text(encoding="utf-8")
needle = 'set(CMAKE_SYSROOT "${TOOLCHAIN_PATH}/aarch64-none-linux-gnu/libc")'
replacement = f'set(CMAKE_SYSROOT "{sysroot}")'
if needle not in text:
    raise SystemExit("Could not patch the pinned ExecuTorch setup script's sysroot line.")
text = text.replace(needle, replacement, 1)
text = text.replace('cmake --build "$CMAKE_OUT_DIR" -j"$cpu_count" --target install --config Release',
                    f'cmake --build "$CMAKE_OUT_DIR" -j"{jobs}" --target install --config Release')
text = text.replace('cmake --build "$CMAKE_OUT_DIR/examples/models/llama" -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4) --config Release',
                    f'cmake --build "$CMAKE_OUT_DIR/examples/models/llama" -j{jobs} --config Release')
Path(destination).write_text(text, encoding="utf-8")
PY

cd "$EXECUTORCH_DIR"
bash "$SETUP_SCRIPT" pi5

RUNNER="${EXECUTORCH_DIR}/cmake-out/examples/models/llama/llama_main"
LIBRARY="${EXECUTORCH_DIR}/cmake-out/examples/models/llama/runner/libllama_runner.so"
if [[ ! -x "$RUNNER" || ! -f "$LIBRARY" ]]; then
  echo "Expected llama_main and libllama_runner.so were not produced." >&2
  exit 1
fi
mkdir -p "$DEST"
install -m 0755 "$RUNNER" "$DEST/llama_main"
install -m 0644 "$LIBRARY" "$DEST/libllama_runner.so"
git -C "$EXECUTORCH_DIR" rev-parse HEAD > "$DEST/executorch_commit.txt"
cat > "$DEST/build_info.txt" <<EOF
Target: Raspberry Pi 5, aarch64, CPU/XNNPACK path
ExecuTorch branch: $BRANCH
ExecuTorch revision: $REVISION
ExecuTorch commit: $(cat "$DEST/executorch_commit.txt")
Build host: $(uname -a)
Link sysroot: $SYSROOT
Build jobs: ${EXECUTORCH_BUILD_JOBS:-2}
Built at UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
rm -f "$SETUP_SCRIPT"
echo "Runner installed into: $DEST"
echo "Verify with: $DEST/llama_main --help"
