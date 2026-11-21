# Raspberry Pi commissioning record

Use this checklist when the final detector and advisory files have been copied to the Pi. Record the actual hardware settings and measured results. Do not tick a test because the source code contains the corresponding function.

## Before powering the station

- [ ] Confirm the conveyor, camera and IR sensor are mechanically fixed.
- [ ] Check that the camera sees the PCB area when the board is at the IR trigger point.
- [ ] Check the sensor output voltage against the Pi's 3.3 V GPIO limit.
- [ ] Confirm the LED strip uses its external driver and a suitable supply. The Pi pin must only drive the driver's logic input.
- [ ] Confirm the motor supply, LED supply and Pi ground arrangement with the hardware wiring diagram.
- [ ] Record the real BCM pin assignments below. Do not copy example values without checking the wiring.

| Signal | BCM pin | Active/polarity setting | Checked |
|---|---:|---|---|
| IR sensor output | ______ | PCB_IR_ACTIVE_LOW=______ | [ ] |
| LED driver input | ______ | PCB_LED_DRIVER_ACTIVE_LOW=______ | [ ] |
| Camera | ______ | USB index or CSI | [ ] |

## Software and model files

From the repository root on the Pi:

~~~bash
source .venv/bin/activate
python -m pip show onnxruntime opencv-python gpiozero
ls -lh models/best.onnx
ls -lh "$PCB_LLAMA_MODEL_PATH" "$PCB_LLAMA_TOKENIZER_PATH"
~~~

For a CSI camera, confirm that Picamera2 is installed. Confirm that the ONNX file is the one produced from the final three-class checkpoint and that its class order is:

~~~text
0 missing_hole
1 open_circuit
2 short_circuit
~~~

The Llama .pte file and tokenizer must be a matching pair. Check that the Pi environment can import the runner and its operator registrations:

~~~bash
python - <<'PY'
from executorch.extension.llm.custom_ops import custom_ops
from executorch.kernels import quantized
from executorch.extension.llm.runner import GenerationConfig, TextLLMRunner
print("TextLLMRunner imports passed")
PY
~~~

## Start the station

Copy the real settings to raspberry_pi/.env, export them and start the controller from the repository root:

~~~bash
set -a
source raspberry_pi/.env
set +a
python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
~~~

From another terminal on the Pi, check the service:

~~~bash
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/status
~~~

Open http://<RASPBERRY_PI_IP>:8080/ from a laptop on the same private network.

## Test the station sequence

Run each test first with no PCB, then with a PCB in the normal conveyor position.

| Test | Expected result | Pass |
|---|---|---|
| Start controller | State is WAITING_FOR_ARM; LED is off | [ ] |
| Short IR activation | Station does not arm | [ ] |
| Hold IR for 3 seconds and release | State becomes WAITING_FOR_BOARD; armed is true | [ ] |
| Place a PCB on the conveyor | IR trigger starts one capture cycle | [ ] |
| Capture | LED turns on during settling/capture and turns off afterwards | [ ] |
| Browser preview | The displayed frame is the current PCB, not the previous board | [ ] |
| Press Run | Browser request is accepted once; repeated clicks do not start a second run | [ ] |
| Vision result | Annotated image and event JSON are saved | [ ] |
| Advisory | Valid four-field JSON advisory appears; detector findings are unchanged | [ ] |
| Next board | A new IR activation starts the next capture without another hand-hold | [ ] |

Repeat the last capture-and-run test with at least 20 boards or board passes. Record missed triggers, duplicate captures, unreadable frames and failed inference runs. A single successful cycle is not enough to establish reliability.

## Check image inference separately

Use a labelled or representative PCB image for this test:

~~~bash
python raspberry_pi/inspect_image.py \
  --source /path/to/pcb_test_image.jpg \
  --weights models/best.onnx \
  --output /tmp/pcb_event.json \
  --annotated /tmp/pcb_annotated.jpg
~~~

Check that the event contains the correct class names, class IDs, confidence scores and boxes. A no-detection result must be described as “no configured target detected in this frame”, not as proof that the PCB is defect-free.

## Measure Pi vision runtime

Use a held-out folder of representative PCB images. Do not use training images for the reported benchmark.

~~~bash
python raspberry_pi/benchmark_onnx.py \
  --model models/best.onnx \
  --images /path/to/held_out_images \
  --warmup 5 \
  --threads 2 \
  --out docs/results/pi_onnx_benchmark.json
~~~

The script reports preprocessing, ONNX inference and post-processing time, p50/p95 latency, sequential FPS, peak process RSS, device details and thermal readings. It does not measure camera-to-result time, Llama latency, power or accuracy. Record those separately.

| Measurement | Result | Method / instrument |
|---|---|---|
| Pi model and RAM | ____________________ | /proc/cpuinfo, free -h |
| OS and kernel | ____________________ | /etc/os-release, uname -a |
| Vision p50 / p95 | ____________________ | Benchmark JSON |
| Vision sequential FPS | ____________________ | Benchmark JSON |
| Full capture-to-result time | ____________________ | Timed physical runs |
| Llama TTFT / tokens per second | ____________________ | Advisory JSON |
| Peak RAM | ____________________ | Benchmark JSON / free |
| CPU temperature | ____________________ | Thermal sysfs / vcgencmd |
| Power at idle / capture / inference | ____________________ | External power meter |
| Successful cycles / attempted cycles | ____________________ | Station test log |

## Save the evidence

Keep these files with the submission:

- final best.pt, best.onnx and ONNX metadata JSON;
- final dataset import manifest, split list and training/validation output;
- Llama .pte, tokenizer identity and ExecuTorch build version;
- benchmark JSON and the raw test-image list;
- inspection event JSON and annotated images from representative boards;
- a short video showing the full physical sequence and the dashboard result;
- this checklist with the actual pin mapping and test outcomes.

Do not publish a pass result for a test that was skipped. If a step fails, record the error and the change made before repeating it.
