# Local execution and performance record

## Execution model

The intended production path is **on-device inference on the Raspberry Pi 5 CPU**. The laptop browser is an operator display only; it does not execute the vision model or the language model.

| Component | Runtime location | Runtime |
|---|---|---|
| IR trigger, illumination and camera control | Raspberry Pi 5 | GPIO, camera driver and local Python process |
| Image preprocessing | Raspberry Pi 5 | OpenCV |
| PCB defect detection | Raspberry Pi 5 CPU | ONNX Runtime with `CPUExecutionProvider`; YOLO ONNX file stored on the Pi |
| Advisory generation | Raspberry Pi 5 CPU | Llama 3.2 1B Instruct SpinQuant PTE through the ExecuTorch C++ `llama_main` runner |
| Inspection events and images | Raspberry Pi 5 local storage | Local JSON and image files |
| Operator dashboard | Served by Raspberry Pi 5; viewed in a laptop browser | Static HTML/JavaScript and same-origin HTTP requests to the Pi |
| Optional event replication | Off by default | Firebase Realtime Database; stores records only and does not run inference |

No external vision endpoint, hosted LLM endpoint or remote inference API is part of the configured inference path. The detector receives the captured image locally. The Llama component receives only the structured detector event as text. The browser sends an inspection request to the Pi and displays the response.

### What requires the internet, and what does not

Internet access is needed during provisioning when downloading Python packages, the published YOLO checkpoint, or the licensed Llama PTE/tokenizer. Build dependencies may also need to be downloaded when preparing the ExecuTorch runner.

After those assets and dependencies are installed on the Pi, **inference is designed to run without internet access**. The ONNX file, PTE file, tokenizer and ExecuTorch runner must already be present on local storage. The dashboard can be opened over a private LAN that has no WAN connection. For a fully isolated demonstration, keep `PCB_FIREBASE_PUBLISH=false`; this is the default in `raspberry_pi/.env.example`.

Firebase is an optional record-synchronization feature. Enabling it makes outbound HTTPS requests to Firebase, so the station is no longer network-isolated, but the vision and Llama algorithms still execute locally. Firebase is not required for capture, inference, the advisory or local event history.

## Offline demonstration checklist

Perform this check on the actual Raspberry Pi 5 after all model/runtime assets have been provisioned:

1. Confirm `models/best.onnx` and its sidecar `models/best.onnx.json` are present.
2. Confirm the Llama PTE, matching tokenizer and executable `models/llama/runtime/llama_main` are present.
3. Set `PCB_LLAMA_REQUIRED=true` and `PCB_FIREBASE_PUBLISH=false` in `raspberry_pi/.env`.
4. Start the station and open the dashboard from a browser on the same private LAN.
5. Disconnect the LAN's WAN/internet uplink while keeping the Pi and operator browser on the same LAN. Do not remove local connectivity between them.
6. Run a real inspection and verify that the event includes `advisory_runtime.status = "COMPLETED"`, the detector result is saved, and the annotated image is available.
7. Save the event JSON, the terminal log, model hashes and the completed commissioning sheet as evidence.

Until this offline test is completed and recorded, describe the system as **configured for offline local inference**, not as an offline test already passed.

## Performance references (external, not project measurements)

These figures provide comparison points only. They were produced by other authors on different models, datasets or hardware configurations.

### PCB detector reference

Sulojan Rajkumar's published six-class YOLOv8s PCB model reports the following on its author's 70-image / 286-box test split:

| Metric | Published result |
|---|---:|
| Precision | 97.2% |
| Recall | 91.2% |
| mAP@0.50 | 94.1% |
| mAP@0.50:0.95 | 50.3% |
| Inference time | 18.4 ms/image (author's test environment) |

Per-class mAP@0.50 for the three classes mapped into this application's event schema is 99.5% for `missing_hole`, 99.2% for `open_circuit` and 97.5% for upstream class `short` (mapped to `short_circuit`). The upstream checkpoint has six output classes; three are ignored by this application's three-class mapping. These are the publisher's measurements, not Raspberry Pi 5 measurements or results from this team's test set. Full provenance and class mapping are in [PCB_UPSTREAM_BASELINE.md](PCB_UPSTREAM_BASELINE.md).

### Raspberry Pi 5 vision-runtime reference

Arm's published Raspberry Pi 5 benchmark for its separate YOLO26n INT8 ONNX model reports p50 latency 166.050 ms, p90 173.912 ms, p99 179.881 ms, 6.02 frames/s and 154.22 MB peak memory. It uses a different model, quantization, output contract and NMS arrangement. It is an edge-runtime reference only and is not the latency or memory result of this PCB YOLO model. Details are in [REFERENCE_BENCHMARKS.md](REFERENCE_BENCHMARKS.md).

### Llama generation reference

Public Raspberry Pi 5 measurements for Llama 3.2 1B using llama.cpp/GGUF report approximately 10.8–14.5 generated tokens/s in their stated configurations. Those are not ExecuTorch SpinQuant PTE measurements. The ExecuTorch community model-card result for the matching SpinQuant PTE family is from a OnePlus 12 Android device, not a Raspberry Pi 5; it must not be copied as Pi performance. See [REFERENCE_BENCHMARKS.md](REFERENCE_BENCHMARKS.md).

### DLMR metric applicability

The 2026 DLMR paper means *Dual-Latent Memory Routing for Vision-Language Reasoning*. Its reported evaluations use multimodal language-model benchmarks and backbones such as Qwen2.5-VL and InternVL; they are not PCB defect-detection metrics and are not measurements of this Raspberry Pi/YOLO/ExecuTorch pipeline. DLMR scores are therefore not included as project performance results.

## Project measurements: not yet recorded

The repository contains benchmark scripts, but no valid Pi 5 benchmark output or project-owned held-out accuracy report is currently committed. The detector, full software pipeline and physical station must be measured separately.

Run the detector benchmark on the Raspberry Pi 5 with a representative image set:

```bash
python raspberry_pi/benchmark_onnx.py \
  --model models/best.onnx \
  --images /path/to/held_out_pcb_images \
  --warmup 5 --threads 2 \
  --out docs/results/pi_onnx_benchmark.json
```

Run the real still-image detector-plus-Llama path:

```bash
python raspberry_pi/benchmark_pipeline.py \
  --images /path/to/held_out_pcb_images \
  --model models/best.onnx \
  --warmup 1 \
  --out docs/results/pi_pipeline_benchmark.json
```

Report these measurements from the resulting JSON files:

- Detector preprocessing, inference and post-processing mean latency; p50, p95 and maximum total latency; sequential FPS; process peak RSS; start/end temperature.
- Full still-image pipeline wall time; detector latency; Llama response time; TTFT and generated tokens/s only when the selected runner exposes telemetry; peak child-process RSS.
- Physical capture-to-result time and successful/attempted cycles from repeated conveyor tests. This is not measured by either still-image benchmark.
- Power only from a calibrated external power meter. Neither CPU utilization nor temperature is a power measurement.

Detection accuracy is a separate labelled-data evaluation. Use a held-out split grouped by PCB design/capture session and report per-class precision, recall, F1, confusion matrix, mAP@0.50 and mAP@0.50:0.95. Do not convert upstream metrics or benchmark-reference values into project measurements.

## Evaluator-facing statement

> The vision detector and Llama advisory are designed to execute locally on the Raspberry Pi 5 CPU. OpenCV and ONNX Runtime perform image processing and YOLO inference on the Pi; Llama 3.2 1B runs through the ExecuTorch C++ runtime on the same device. The browser is only the operator interface. No cloud inference API is used. Firebase event synchronization is disabled by default and is not part of the inference path. After models and dependencies are provisioned, the system is designed to operate without internet access. Offline operation must be demonstrated with the Pi and operator browser on a private LAN and verified using a completed inspection event.
