# Raspberry Pi 5 station deployment

This guide describes the implemented Raspberry Pi station path: IR arming, conveyor-triggered capture, OpenCV preprocessing, YOLO ONNX inference, ExecuTorch advisory, local event logging and the operator page.

## 1. Install the station software

Use 64-bit Raspberry Pi OS. From the repository root:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv python3-gpiozero
# Install only when using a CSI camera:
sudo apt install -y python3-picamera2

python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/requirements.txt
```

## 2. Configure the physical station

Copy the example environment file and edit it:

```bash
cp raspberry_pi/.env.example raspberry_pi/.env
nano raspberry_pi/.env
```

Set the BCM GPIO numbers to match the actual wiring. Check the IR sensor output polarity and pull-up setting. Set the LED driver polarity and camera mode. Do not copy example pin values without checking the physical connections.

The IR output must be compatible with the Pi's 3.3 V GPIO. The LED strip must use an external driver and power supply; the Pi pin is only the driver's logic input.

The controller does not read the `.env` file itself. Export its values before launching the service:

```bash
set -a
source raspberry_pi/.env
set +a
python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
```

Open `http://<RASPBERRY_PI_IP>:8080/` from a laptop on the same private network. Run `hostname -I` on the Pi to find its address.

## 3. Check the service and capture path

From another terminal on the Pi:

```bash
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/status
```

At the beginning of a session, hold a hand in front of the IR sensor for about three seconds and release it. The station should remain armed. The next IR activation should start one capture cycle. The station should switch on the LED driver, wait for the configured settling time, capture a frame and switch the LED off.

The sensor confirms presence at its trigger point. It does not measure exact image alignment; that depends on the mechanical station setup.

## 4. Install and check the YOLO ONNX detector

The station expects `models/best.onnx` and its companion metadata file `models/best.onnx.json`. These must be generated from the final three-class checkpoint using the instructions in `pcb_engine_kit/README.md`.

The deployment class order must be:

```text
0 missing_hole
1 open_circuit
2 short_circuit
```

Run a still-image check:

```bash
python raspberry_pi/inspect_image.py \
  --source /path/to/pcb_image.jpg \
  --weights models/best.onnx \
  --output /tmp/pcb_event.json \
  --annotated /tmp/pcb_annotated.jpg
```

Inspect the JSON and annotated image. A no-detection result only means no configured target class was detected in that frame.

## 5. Install the required Llama/ExecuTorch advisory

The Bharat AI-SoC Challenge requires a Llama-family advisory model deployed with ExecuTorch. The source checkout contains the text-only prompt and runner, but does not contain the exported `.pte` model, the matching tokenizer or the target-device ExecuTorch Python build.

Provide those files from the team's selected Llama model release. The model and tokenizer must be a matching pair, and the ExecuTorch runner build must support the operators used by the exported model. Record their hashes and the exact ExecuTorch revision/build.

Set the paths in `raspberry_pi/.env`:

```text
PCB_LLAMA_MODEL_PATH=/absolute/path/to/model.pte
PCB_LLAMA_TOKENIZER_PATH=/absolute/path/to/tokenizer.bin
PCB_LLAMA_REQUIRED=true
```

Verify the runner imports on the Pi before a station test:

```bash
python - <<'PY'
from executorch.extension.llm.custom_ops import custom_ops
from executorch.kernels import quantized
from executorch.extension.llm.runner import GenerationConfig, TextLLMRunner
print("TextLLMRunner imports passed")
PY
```

The ExecuTorch Python runner API is revision-dependent. Run the actual project advisory with the supplied model and tokenizer on the Pi; an import check alone is not a completed test.

## 6. Run the station workflow

1. Start the station service with the configured environment.
2. At session start, hold a hand in front of the IR sensor for about three seconds and release it.
3. Place a PCB on the conveyor.
4. Confirm the IR trigger starts capture and the LED driver switches off after capture.
5. Check the current frame in the laptop browser.
6. Press **Run inspection on Raspberry Pi**.
7. Confirm the annotated image, structured event and ExecuTorch advisory appear.
8. Move the next PCB to the trigger position; the station should capture it without another hand-hold.

Firebase event synchronization can be enabled through the station configuration. Local capture, detector inference and advisory generation run on the Pi.

For the challenge's local-execution demonstration, leave `PCB_FIREBASE_PUBLISH=false` (the example default). Model downloads and software installation happen during provisioning; after the model, tokenizer and ExecuTorch runner are on the Pi, inference is local. To test offline operation, disconnect only the WAN/internet uplink and keep the Pi and laptop browser connected to the same private LAN. A full loss of LAN connectivity would also disconnect the remote browser from the Pi-hosted dashboard. Follow [docs/LOCAL_EXECUTION_AND_PERFORMANCE.md](LOCAL_EXECUTION_AND_PERFORMANCE.md) and save the completed evidence.

## 7. Record target-device results

Run the detector benchmark on held-out representative PCB images:

```bash
python raspberry_pi/benchmark_onnx.py \
  --model models/best.onnx \
  --images /path/to/held_out_images \
  --warmup 5 \
  --threads 2 \
  --out docs/results/pi_onnx_benchmark.json
```

The benchmark reports preprocessing, ONNX inference and post-processing time, p50/p95 latency, sequential FPS, peak process memory and thermal readings. It does not measure Llama latency, power, capture-to-result time or detection accuracy. Measure those separately and record the method.

Complete `docs/PI5_COMMISSIONING.md` with actual pin mapping, runtime versions and test outcomes. Do not mark a physical test as passed until it has been run on the actual station.

The HTTP service is intended for a trusted local network. Do not port-forward it or expose it directly to the public internet.
