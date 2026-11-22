# Local execution and project performance record

## Intended execution architecture

The application source is configured for a Raspberry Pi 5 target. The team reports that the physical build/tests are complete, but their commissioning records have not yet been committed. This document describes the intended runtime path and does not independently verify those tests.

| Component | Intended location | Software path | Current evidence |
|---|---|---|---|
| IR trigger, illumination and camera controller | Raspberry Pi 5 | GPIO/camera controller source | Team reports physical build/tests complete; commissioning evidence not yet in repository |
| Image preprocessing | Raspberry Pi 5 CPU | OpenCV | Source present; target test absent |
| PCB detector | Raspberry Pi 5 CPU | ONNX Runtime CPUExecutionProvider | Source present; project ONNX model absent |
| Text advisory | Raspberry Pi 5 CPU | Llama 3.2 1B Instruct through ExecuTorch C++ runner | Integration source present; model assets and target test absent |
| Event and image storage | Raspberry Pi local storage | JSON and image files | Source present; physical-use evidence absent |
| Operator dashboard | Served by Pi, viewed in browser | Static HTML/JavaScript and same-origin HTTP | Source present; target end-to-end evidence absent |
| Optional record replication | Off by default | Firebase Realtime Database | Optional source present; not used for inference |

The Llama foundation model is a third-party model, not trained by the project team. Its prompt receives the structured detection event only. It does not receive the PCB image, change detector predictions or control hardware.

## Internet and offline scope

Internet access is required for first-time installation and download of dependencies/model assets. Once the detector, Llama package, tokenizer and ExecuTorch runner are installed, the design is intended to run locally. Firebase synchronization is disabled by default; enabling it requires outbound network access for event-record replication.

Offline operation is **not yet demonstrated** by evidence in this repository. To verify it, keep the Raspberry Pi and browser on the same private LAN, disconnect the WAN uplink, run a real inspection and retain the event JSON, terminal log and model hashes.

## Accuracy reporting

No verified project accuracy metrics are included in this repository. The previously supplied screenshot could not be linked to an identified model checkpoint, dataset version, board-group split or raw evaluator output, so its values are not reproduced here.

The held-out test record remains `NOT_PROVIDED`. The code for producing an audited test report is present, but source-code presence is not a completed measurement. Do not claim precision, recall, F1, mAP, FPS, latency, power or reliability figures until the exact project model and measurement records are available.

No measurements from external PCB models, research papers, Raspberry Pi benchmark devices or Llama deployments are presented as project results.

## Measurements that still need to be produced

### Dataset and checkpoint provenance

Use the release audit before a model release:

```bash
python pcb_engine_kit/audit_release.py \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --output-dir docs/results
```

A release is not complete while either audit is NOT_PROVIDED, INCOMPLETE or UNVERIFIED.

### Held-out test accuracy

Evaluate only the held-out test split and use the exact checkpoint that has the matching training-provenance sidecar:

```bash
python pcb_engine_kit/train_export.py validate \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --size 640 --device 0 \
  --report-out docs/results/project_test_metrics.json
```

Record per-class precision, recall, F1, AP, test support, confusion matrix and reviewed false-positive/false-negative examples. Test groups must be separate physical PCB/design/capture groups, not merely alternate crops of training boards.

### Target Pi detector benchmark

After installing the exact project ONNX export on the actual Pi:

```bash
python raspberry_pi/benchmark_onnx.py \
  --model models/best.onnx \
  --images /path/to/held_out_pcb_images \
  --warmup 5 --threads 2 \
  --out docs/results/pi_onnx_benchmark.json
```

### Vision-plus-advisory pipeline benchmark

```bash
python raspberry_pi/benchmark_pipeline.py \
  --images /path/to/held_out_pcb_images \
  --model models/best.onnx \
  --warmup 1 \
  --out docs/results/pi_pipeline_benchmark.json
```

These scripts measure software processing of still images. They do not measure conveyor travel, IR trigger reliability, LED settling, physical camera capture or the full browser cycle. Record those through repeated physical commissioning tests.

### Physical cycle, memory and power

Record detector p50/p95 latency, throughput, peak process RAM, CPU temperature, Llama response-time telemetry where available, full capture-to-dashboard time, attempted/successful cycle counts, missed/duplicate triggers and failure counts. Measure power only with an external meter and retain its make/model and method. Do not infer wattage from CPU temperature or utilization.

## Current measured-project-results state

No project Pi latency, FPS, RAM, power, end-to-end cycle time, offline pass rate or independent test-set accuracy has been recorded in this repository. Blank values must remain blank until measured on the named target hardware. The external benchmark comparison documents have been removed so that outside model values cannot be mistaken for project measurements.
