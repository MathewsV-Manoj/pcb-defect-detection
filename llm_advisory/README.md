# Required Llama advisory — ExecuTorch on Raspberry Pi 5

The on-device advisory is an implemented part of the inspection pipeline, not
an optional cloud feature. The default configuration uses **Llama 3.2 1B
Instruct SpinQuant INT4/EO8**, its matching tokenizer, and the ExecuTorch
C++ `llama_main` runner on the Raspberry Pi 5 CPU.

The YOLO model remains the authority for detection. Llama receives structured
detection records as text, writes an operator explanation and checks, and
cannot modify detector labels, suppress detections, issue an independent
PASS/REJECT decision, or control the conveyor/illumination. A human operator
makes the disposition decision.

## 1. Download the model and matching tokenizer

Run from the repository root on a machine with internet access:

```bash
python -m pip install "huggingface_hub>=0.30,<2"
hf auth login
python llm_advisory/download_model.py
```

The script downloads the exact pinned revision from:

- Repository: `executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET`
- Revision: `911221e0f49d3354cbd4697a9c09feee25cadec7`
- Model: `Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte`
- Tokenizer: `tokenizer.model`

The .pte artifact is about 1.14 GB. The model page declares the llama3.2
license. Hugging Face authentication and license acceptance may be required.
The downloader writes local SHA-256 hashes to
`models/llama/download_manifest.json`. Large model files are ignored by Git
and are not uploaded to this repository.

## 2. Build the official Pi 5 runner

On a separate Linux x86_64 host with CMake 3.26+, Git and Python 3.10–3.14:

```bash
bash llm_advisory/build_pi5_runner.sh
```

This checks out ExecuTorch `release/1.5` and runs its Raspberry Pi 5 setup
script. The output is copied to `models/llama/runtime/`:

- `llama_main`
- `libllama_runner.so`
- `executorch_commit.txt`
- `build_info.txt`

Copy the local `models/llama/` directory, including the model, tokenizer and
runtime, to the project directory on the Raspberry Pi. Do not upgrade the
Pi's system GLIBC to work around a binary mismatch; rebuild the runner against
a compatible sysroot/build environment instead.

## 3. Configure the inspection station

The checked-in `raspberry_pi/.env.example` contains the default paths. Copy it
to `raspberry_pi/.env`, check the GPIO/camera settings, then load it before
starting the station:

```bash
cp raspberry_pi/.env.example raspberry_pi/.env
# Edit real BCM pins, polarities and camera mode in raspberry_pi/.env
set -a
source raspberry_pi/.env
set +a
python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
```

The default settings require Llama:
- `PCB_LLAMA_REQUIRED=true`
- `PCB_LLAMA_BACKEND=cli`
- `PCB_LLAMA_SEQ_LEN=1024`
- `PCB_LLAMA_TIMEOUT_SECONDS=180`

Do not disable the required advisory setting for the submitted demonstration.
Vision-only mode is reserved for hardware commissioning while the Llama
package is being installed.

## 4. Smoke test and run one event

First test the actual model/tokenizer/runtime pair on the Pi using
`llama_main --help` and the short prompt in
[models/llama/README.md](../models/llama/README.md). Then run:

```bash
export LD_LIBRARY_PATH="$PWD/models/llama/runtime:${LD_LIBRARY_PATH:-}"
python llm_advisory/run_executorch.py \
  --event schemas/example-event.json \
  --model models/llama/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte \
  --tokenizer models/llama/tokenizer.model \
  --runner models/llama/runtime/llama_main
```

The runner validates a single JSON object with exactly these keys:

- `explanation`: concise description of the supplied findings;
- `recommended_actions`: array of operator checks;
- `severity_note`: explicitly preserves `UNASSESSED` until an approved
  board-specific severity policy exists;
- `log_entry`: concise inspection record text.

Output parsing rejects malformed JSON and mismatched keys. Model output is
advisory; it is never merged into or allowed to change the detector's findings.

## Runtime and measurements

The production/default backend is ExecuTorch's C++ CLI runner. Its process
wall-clock response time and process peak RSS are recorded. This wrapper does
not currently receive stable per-token callbacks from the C++ CLI, so TTFT
and tokens/second are stored as null rather than guessed. The optional Python
TextLLMRunner backend is available only when the ExecuTorch Python bindings
and matching kernels are built and installed.

Measure actual Pi performance with
`raspberry_pi/benchmark_pipeline.py`. It invokes the production coordinator
for a folder of still images, records detector latency and full
image-to-advisory wall time, and excludes physical conveyor/camera/LED/browser
latency. Record actual physical cycles separately in
`docs/PI5_COMMISSIONING.md`.

The Meta Llama 3.2 Acceptable Use Policy restricts use in operations of
critical infrastructure, transportation technologies and heavy machinery.
Keep this deployment within a supervised educational/laboratory demonstration
and outside those operational contexts. A text-only advisory that cannot
control actuators is a useful safety boundary, but it does not override the
upstream license restrictions. Review the current policy before use.

## Model license and safe scope

Review the Meta Llama 3.2 Community License, acceptable-use policy and the
upstream model repository's access/redistribution terms. This repository does
not contain or redistribute the model weights. The Llama component is an
operator-facing textual assistant only; it must not be used to control
industrial machinery or replace qualified engineering inspection.
