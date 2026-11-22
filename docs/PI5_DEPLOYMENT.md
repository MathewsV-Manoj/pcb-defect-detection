# Raspberry Pi 5 station deployment

This guide describes the Raspberry Pi-targeted software path: IR arming/capture, illumination command, OpenCV preprocessing, project-trained YOLO ONNX inference, text-only ExecuTorch advisory, local event logging and browser dashboard.

**The Pi 5 is the documented target platform.** The repository does not contain evidence that the final physical wiring, complete station cycle or offline test has passed. Complete the commissioning record before claiming physical operation.

## 1. Produce the project detector on the development machine

The Pi provisioner requires the project's own three-class ONNX export. It does not download or select a third-party PCB detector.

Follow datasets/README.md and pcb_engine_kit/README.md to prepare the actual project dataset, review source permissions and labels, group splits by physical board/capture session, and run the dataset audit. Train from the Ultralytics architecture YAML with pretrained=False. Preserve the exact best.pt and project_training_provenance.json.

Then evaluate and export using the same dataset and checkpoint:

```bash
python pcb_engine_kit/train_export.py validate \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --size 640 --device 0 \
  --report-out docs/results/project_test_metrics.json

python pcb_engine_kit/train_export.py export-onnx \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --size 640 --out deployment

python pcb_engine_kit/audit_release.py \
  --data datasets/processed/pcb3/data.yaml \
  --checkpoint runs/pcb/weights/best.pt \
  --output-dir docs/results
```

Copy deployment/best.onnx and deployment/best.onnx.json into models/ on the Pi. Do not edit the sidecar or substitute a different model after export. The sidecar contains the ONNX hash, source checkpoint hash, dataset audit hash and training-provenance hash. The provisioner refuses a model that does not carry the expected project-training metadata.

## 2. Provision the Pi runtime

Use 64-bit Raspberry Pi OS on a Raspberry Pi 5 with a suitable power supply/cooling and at least 12 GiB free storage for the documented model/build setup. First-time provisioning requires internet access for packages and the licensed Llama/ExecuTorch assets.

From the repository root, after copying the two ONNX files:

```bash
bash scripts/provision_pi5.sh
```

The provisioner:
- verifies the project ONNX SHA-256 and metadata;
- installs inference/runtime packages;
- downloads the separately licensed Llama 3.2 1B Instruct model and matching tokenizer;
- builds the ExecuTorch C++ runner on the Pi;
- preserves existing GPIO settings in raspberry_pi/.env;
- executes a software smoke test using a synthetic detector input and illustrative advisory event.

The smoke test does not prove PCB accuracy or physical station operation. The Llama model is third-party and is not a model trained by the project team. Review and comply with its upstream licence and use conditions.

## 3. Configure physical hardware

Open raspberry_pi/.env and enter the real BCM GPIO numbers and active polarities from the actual wiring. The provisioner deliberately does not guess these settings.

Confirm before powering the station:
- IR sensor output is compatible with the Pi's 3.3 V GPIO;
- the LED strip uses a suitable external supply and driver;
- the Pi GPIO is connected only to the driver's logic input;
- camera, conveyor, IR trigger and illumination are mechanically aligned.

The IR sensor indicates presence at its trigger point; it does not compute image coordinates. The controller does not command conveyor speed or direction.

## 4. Start and check the service

```bash
bash scripts/run_station_pi5.sh
```

From another terminal on the Pi:

```bash
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/status
```

Open http://PI_ADDRESS:8080/ from an operator laptop on the same trusted private LAN.

## 5. Verify detector and advisory behaviour

The decoder requires the native class order:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

A sidecar is required and must declare:
- the ONNX file SHA-256;
- VERIFIED_PROJECT_TRAINING provenance;
- random initialization from a YOLO architecture YAML;
- pretrained_weights_used = false;
- the exact three-class identity map;
- the corresponding checkpoint, dataset audit and provenance hashes.

An empty detection list means only that none of the configured target classes was detected in that frame. It is not a defect-free certification.

The Llama advisory receives structured detection text only. It does not change detector findings or make a final quality-release decision.

## 6. Complete and retain commissioning evidence

Follow docs/PI5_COMMISSIONING.md. Record actual pins/polarities, camera model and mode, software versions, model hashes, physical trigger/capture sequence, repeated cycles, test failures, offline run and measurements.

Do not claim target inference, live ExecuTorch, offline operation or physical cycle completion until the corresponding test record is saved. Do not invent performance values or copy numbers from other models/devices.

The HTTP service is intended for a trusted local network. Do not port-forward it or expose it directly to the public internet.
