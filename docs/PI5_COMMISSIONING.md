# Raspberry Pi 5 commissioning record

Complete this form on the actual Raspberry Pi 5 station after the project ONNX model, Llama package and matching ExecuTorch runner have been installed. A source file or successful export command is not proof that a physical test passed. Do not fill unknown values by guesswork.

## Hardware safety and wiring

- [ ] Confirm conveyor, camera and IR sensor are mechanically fixed.
- [ ] Confirm camera field of view at the IR trigger point.
- [ ] Verify that the IR sensor output voltage is safe for the Pi's 3.3 V GPIO.
- [ ] Confirm LED strip uses an appropriate external driver and power supply.
- [ ] Confirm the Pi GPIO is connected only to the LED driver's logic input.
- [ ] Record and verify the real BCM pin assignments.

| Signal | BCM pin | Polarity/configuration | Physically checked |
|---|---|---|---|
| IR sensor output | ______ | PCB_IR_ACTIVE_LOW = ______ | [ ] |
| LED driver input | ______ | PCB_LED_DRIVER_ACTIVE_LOW = ______ | [ ] |
| Camera | ______ | USB index or CSI model/mode | [ ] |

## Project model and audit files

Before provisioning, train and export the project model on the development machine. It must have been initialized from an Ultralytics architecture YAML with pretrained=False. The Pi provisioner does not download a third-party PCB detector.

Copy both files into models/ on the Pi:
- models/best.onnx
- models/best.onnx.json

The sidecar must match the ONNX file SHA-256 and declare VERIFIED_PROJECT_TRAINING, random initialization, pretrained_weights_used=false and the project three-class order. Keep the source best.pt, project_training_provenance.json, dataset data.yaml, audit.json and portable audit JSON files outside the model folder for reproducibility.

On the development machine, run:

```bash
python pcb_engine_kit/audit_release.py \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --output-dir docs/results
```

Only proceed with a release after reviewing the dataset and checkpoint audit results. Do not alter a report manually to create a pass.

On the actual Pi, run:

```bash
bash scripts/provision_pi5.sh
```

The provisioner installs the Pi runtime, retrieves the separately licensed Llama foundation model/tokenizer, builds ExecuTorch and runs a software smoke test. It does not verify wiring or the mechanical station.

## Software and model identity

| Item | Actual value |
|---|---|
| Raspberry Pi model and RAM | ____________________ |
| Raspberry Pi OS / kernel | ____________________ |
| Python version | ____________________ |
| OpenCV version | ____________________ |
| ONNX Runtime version | ____________________ |
| Project checkpoint SHA-256 | ____________________ |
| Dataset import-manifest SHA-256 | ____________________ |
| Dataset audit SHA-256 | ____________________ |
| ONNX model SHA-256 | ____________________ |
| ONNX sidecar provenance status | ____________________ |
| Llama model identity / SHA-256 | ____________________ |
| Tokenizer SHA-256 | ____________________ |
| ExecuTorch revision/build | ____________________ |
| Camera model and mode | ____________________ |

Expected detector class order:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

## Start and check the station

```bash
bash scripts/run_station_pi5.sh
```

From another terminal:

```bash
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/status
```

Open the dashboard from a laptop on the same trusted LAN. Record date, operator and exact software/model hashes used.

## Physical sequence checks

| Test | Expected observation | Pass/fail / notes |
|---|---|---|
| Start controller | WAITING_FOR_ARM; illumination off | |
| Short IR activation | Does not arm | |
| Hold IR for the configured arming interval and release | Armed state remains | |
| PCB reaches trigger point | One capture cycle starts | |
| Illumination | Driver activates during capture and turns off afterward | |
| Browser preview | Current captured frame is displayed | |
| Operator starts inspection | One inference request is accepted | |
| Detector output | Annotated image and event JSON are saved | |
| Advisory | ExecuTorch returns the expected structured fields | |
| Next PCB | New capture occurs without another arming gesture | |

Repeat at least 20 cycles. Record actual attempts, successful cycles, missed triggers, duplicate captures, unreadable frames, detector errors, advisory errors and any manual intervention. Do not calculate success rate from incomplete logs.

## Held-out detector check

Use a labelled image from a board group excluded from training and validation:

```bash
python raspberry_pi/inspect_image.py \
  --source /path/to/held_out_pcb_image.jpg \
  --weights models/best.onnx \
  --output /tmp/pcb_event.json \
  --annotated /tmp/pcb_annotated.jpg
```

Review class ID, label, confidence and box coordinates against the annotation. Save the input, output JSON and annotated image. This individual smoke check is not a replacement for the held-out metrics report.

## Pi measurements

```bash
python raspberry_pi/benchmark_onnx.py \
  --model models/best.onnx \
  --images /path/to/held_out_images \
  --warmup 5 --threads 2 \
  --out docs/results/pi_onnx_benchmark.json
```

| Measurement | Actual result | Evidence/method |
|---|---|---|
| Detector p50 / p95 latency | | Benchmark JSON |
| Sequential FPS | | Benchmark JSON |
| Peak RAM | | Benchmark JSON |
| CPU temperature | | Thermal reading |
| Full capture-to-result time | | Physical-cycle timing |
| Llama time to first token | | Runtime telemetry; blank if unavailable |
| Llama generated tokens per second | | Runtime telemetry; blank if unavailable |
| Successful cycles / attempted cycles | | Full station log |
| Power | | External power meter only |

Do not substitute figures from published papers or other hardware. Power must be measured with an external meter; temperature and CPU utilization are not power measurements.

## Offline operation

- [ ] Configure Firebase event synchronization off.
- [ ] Keep the Pi and operator laptop connected to the same private LAN.
- [ ] Disconnect the WAN/internet uplink only.
- [ ] Run a real capture, detector inference and Llama advisory.
- [ ] Confirm local event JSON and annotated image are saved.
- [ ] Save the event, terminal log, model hashes and date.
- [ ] Record PASS only if the full workflow completed without internet.

## Evidence to retain

- Exact best.pt, its provenance sidecar and SHA-256.
- Exact ONNX model and metadata sidecar.
- Completed import manifest, source/label hashes and generated dataset audit.
- Held-out test output and example predictions.
- Pi runtime smoke-test JSON.
- Llama model/tokenizer identities and build information.
- Actual BCM pin mapping and this completed commissioning sheet.
- Repeated-cycle log and offline test evidence.
- Demonstration video showing the actual hardware and model outputs.

Record failures as failures. Leave skipped or unmeasured fields blank. Do not claim that the station passed a test that was not conducted.
