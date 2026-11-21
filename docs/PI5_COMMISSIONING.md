# Raspberry Pi 5 commissioning record

Complete this sheet on the actual station after the final detector, Llama model and matching tokenizer have been installed. Do not mark a test as passed because source code contains the corresponding function.

## Hardware safety and wiring

- [ ] Confirm the conveyor, camera and IR sensor are mechanically fixed.
- [ ] Confirm that the camera sees the PCB at the IR trigger point.
- [ ] Check the IR sensor output voltage against the Pi's 3.3 V GPIO limit.
- [ ] Confirm the LED strip uses its external driver and suitable supply.
- [ ] Confirm the Pi GPIO drives only the driver's logic input.
- [ ] Record and verify the real BCM pin assignments.

| Signal | BCM pin | Polarity/configuration | Checked |
|---|---:|---|---|
| IR sensor output | ______ | `PCB_IR_ACTIVE_LOW` = ______ | [ ] |
| LED driver input | ______ | `PCB_LED_DRIVER_ACTIVE_LOW` = ______ | [ ] |
| Camera | ______ | USB index or CSI | [ ] |

## Software and model files

The Llama deployment route is committed in the repository. Download the
licensed model/tokenizer pair on a machine with Hugging Face access and build
the Pi 5 runtime on a Linux x86_64 host, then copy models/llama to the Pi:

    python -m pip install "huggingface_hub>=0.30,<2"
    hf auth login
    python llm_advisory/download_model.py
    # On a Linux x86_64 build host:
    bash llm_advisory/build_pi5_runner.sh

The Llama 3.2 1B Instruct PTE and matching tokenizer are local files and are
not tracked by Git. The runner build script records the ExecuTorch commit.
Copy the complete models/llama directory to the Pi before continuing.

From the repository root on the Pi:

```bash
source .venv/bin/activate
set -a
source raspberry_pi/.env
set +a
python -m pip show onnxruntime opencv-python gpiozero
ls -lh models/best.onnx models/best.onnx.json
ls -lh "$PCB_LLAMA_MODEL_PATH" "$PCB_LLAMA_TOKENIZER_PATH"
ls -lh "$PCB_LLAMA_RUNNER_PATH" models/llama/runtime/libllama_runner.so
```

Record the exact versions and model identities:

| Item | Value |
|---|---|
| Raspberry Pi model and RAM | ____________________ |
| Raspberry Pi OS / kernel | ____________________ |
| Python version | ____________________ |
| OpenCV version | ____________________ |
| ONNX Runtime version | ____________________ |
| YOLO checkpoint SHA-256 | ____________________ |
| ONNX model SHA-256 | ____________________ |
| Llama model identity / SHA-256 | ____________________ |
| Tokenizer identity / SHA-256 | ____________________ |
| ExecuTorch revision/build | ____________________ |
| Camera model and mode | ____________________ |

Confirm the detector class order:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

## Start and check the station

```bash
set -a
source raspberry_pi/.env
set +a
python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
```

From another terminal:

```bash
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/status
```

Open `http://<RASPBERRY_PI_IP>:8080/` from a laptop on the same network.

## Physical sequence tests

| Test | Expected result | Pass |
|---|---|---|
| Start controller | State is `WAITING_FOR_ARM`; LED is off | [ ] |
| Short IR activation | Station does not arm | [ ] |
| Hold IR for about three seconds and release | Station changes to armed/waiting-for-board state | [ ] |
| First PCB reaches trigger point | One capture cycle starts | [ ] |
| Capture illumination | LED driver switches on during capture and off afterward | [ ] |
| Browser preview | Current captured frame is displayed | [ ] |
| Operator starts inspection | Request is accepted once | [ ] |
| Detector result | Annotated image and event JSON are saved | [ ] |
| ExecuTorch advisory | Valid four-field advisory is returned | [ ] |
| Next PCB | New frame is captured without repeating the initial hand-hold | [ ] |

Repeat the capture-and-inspection cycle at least 20 times. Record all attempts, successful cycles, missed triggers, duplicate captures, unreadable frames, detector failures and advisory failures.

## Detection check

Use a held-out image with known annotations:

```bash
python raspberry_pi/inspect_image.py \
  --source /path/to/pcb_test_image.jpg \
  --weights models/best.onnx \
  --output /tmp/pcb_event.json \
  --annotated /tmp/pcb_annotated.jpg
```

Check class IDs, class names, confidence, bounding boxes and annotated output. A no-detection result must be described as “no configured target detected in this frame”, not proof that the PCB is defect-free.

Keep test predictions, false positives and missed defects with the report.

## Raspberry Pi measurements

```bash
python raspberry_pi/benchmark_onnx.py \
  --model models/best.onnx \
  --images /path/to/held_out_images \
  --warmup 5 \
  --threads 2 \
  --out docs/results/pi_onnx_benchmark.json
```

| Measurement | Result | Method/evidence |
|---|---|---|
| Detector p50 / p95 latency | ____________________ | Benchmark JSON |
| Sequential FPS | ____________________ | Benchmark JSON |
| Peak RAM | ____________________ | Benchmark JSON |
| CPU temperature | ____________________ | Thermal reading |
| Full capture-to-result time | ____________________ | Timed physical cycles |
| Llama time to first token | ____________________ | ExecuTorch PyTorchObserver or Python binding telemetry; otherwise null |
| Llama tokens per second | ____________________ | Parsed from generated-token count and measured inference interval; otherwise null |
| Successful cycles / attempted cycles | ____________________ | Station log |
| Power | ____________________ | External power meter, if measured |

## Vision-plus-Llama software pipeline benchmark

After the model and runner smoke tests pass, run the production coordinator
against a folder of held-out PCB images:

    python raspberry_pi/benchmark_pipeline.py \
      --images /path/to/held_out_images \
      --model models/best.onnx \
      --warmup 1 \
      --out docs/results/pi_pipeline_benchmark.json

This benchmark invokes the real detector and ExecuTorch advisory once per
image. It measures image-to-advisory process wall time, detector latency and
the Llama fields exposed by the selected runner. It does not include physical
IR triggering, camera capture, conveyor timing, LED settling or browser
delivery. Record those in the physical-cycle table above. Power must be
measured with an external meter.

## Evidence to retain

- Final `best.pt`, `best.onnx` and ONNX metadata JSON.
- Actual dataset import manifest, board-level split and generated audit.
- Final validation/test results and prediction examples.
- Llama model/tokenizer identities and hashes; ExecuTorch build details.
- Raspberry Pi benchmark JSON and held-out image list.
- Representative event JSON files and annotated images.
- Actual demonstration video.
- This commissioning sheet with real pin mapping and test outcomes.

Record failed tests as failed. Do not report unmeasured values or mark skipped stages as passed.
