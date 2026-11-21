# Set up the Raspberry Pi station

This guide covers the Pi-hosted website, sensor control, camera capture and local inspection process. Complete the GPIO and model checks before trying the full conveyor sequence.

## 1. Install the station software

Use 64-bit Raspberry Pi OS. From the repository root:

~~~bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv python3-gpiozero

# Only for a CSI camera:
sudo apt install -y python3-picamera2

python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/requirements.txt
~~~

## 2. Set the hardware values

Copy the example environment file and edit it:

~~~bash
cp raspberry_pi/.env.example raspberry_pi/.env
nano raspberry_pi/.env
~~~

Set the BCM GPIO numbers to match the actual wiring. Check the IR sensor's output polarity and whether it needs a pull-up. Set the LED driver polarity and camera mode. Do not use the example values as a wiring diagram.

The IR output must be compatible with the Pi's 3.3 V GPIO. The LED strip needs an external driver and supply; the Pi pin is only the driver's logic input.

The controller reads environment variables. It does not load the .env file itself. From the repository root, export the values before launching the service:

~~~bash
set -a
source raspberry_pi/.env
set +a
python raspberry_pi/station_controller.py --host 0.0.0.0 --port 8080
~~~

Open http://<RASPBERRY_PI_IP>:8080/ from a laptop on the same private network. Run hostname -I on the Pi to find its address.

## 3. Check the service

From another terminal on the Pi:

~~~bash
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/status
~~~

The page should show the station waiting for the initial three-second hand hold. After the hand is removed, it should stay armed for the session. The next IR activation starts a capture cycle. It should not ask for the three-second hold again until the controller is restarted.

The camera-position IR event confirms presence at the sensor. It does not measure exact image alignment; that depends on the mechanical position of the board and camera.

## 4. Install the vision model

The station expects models/best.onnx. Export it from the final three-class YOLO checkpoint using the instructions in pcb_engine_kit/README.md. Copy both best.onnx and its best.onnx.json metadata file into the models folder on the Pi.

The model must use this class order:

~~~text
0 missing_hole
1 open_circuit
2 short_circuit
~~~

Before trying the camera, test one image with the ONNX model:

~~~bash
python raspberry_pi/inspect_image.py \
  --source /path/to/pcb_image.jpg \
  --weights models/best.onnx \
  --output /tmp/pcb_event.json \
  --annotated /tmp/pcb_annotated.jpg
~~~

Inspect the JSON and annotated image. A no-detection result only means that the three configured classes were not detected in that frame.

## 5. Install the Llama advisory

The complete inspection sequence also needs an ExecuTorch .pte file and its matching tokenizer. The repository does not contain either file. Follow llm_advisory/README.md to obtain the Llama 3.2 Instruct files, export the model and build the Python TextLLMRunner support for the same ExecuTorch revision.

Set the two paths in raspberry_pi/.env:

~~~text
PCB_LLAMA_MODEL_PATH=/absolute/path/to/model.pte
PCB_LLAMA_TOKENIZER_PATH=/absolute/path/to/tokenizer.bin
PCB_LLAMA_REQUIRED=true
~~~

The Python runner API is experimental. Check the Python bindings, operator registrations, exported model and tokenizer together on this Pi before running the full station. Do not assume that a model that runs on a workstation will run on the Pi unchanged.

## 6. Run the complete sequence

1. Start the station service.
2. At session start, hold a hand in front of the IR sensor for about three seconds and release it.
3. Place a PCB on the conveyor.
4. Check that the LED turns on during capture and then turns off.
5. Confirm that the latest frame appears in the laptop browser.
6. Check the board and camera view, then press Run inspection on Raspberry Pi.
7. Confirm that the detector output and advisory appear and that a local event JSON is written.
8. Move the next PCB into the trigger position. The station should capture it without another hand-hold.

Keep Firebase disabled until the local process works. Firebase only copies the event record; the models always run on the Pi.

## 7. Record the target-device results

Run the ONNX runtime benchmark with representative held-out images:

~~~bash
python raspberry_pi/benchmark_onnx.py \
  --model models/best.onnx \
  --images /path/to/held_out_images \
  --warmup 5 \
  --threads 2 \
  --out docs/results/pi_onnx_benchmark.json
~~~

The benchmark reports preprocessing, ONNX inference and post-processing times, p50/p95 latency, sequential FPS, peak process memory and thermal readings. It does not measure the camera-to-result time, Llama speed, power or detection accuracy. Measure those separately and record the equipment and method used.

Use docs/PI5_COMMISSIONING.md to record the GPIO assignments, repeated capture tests, model identity, runtime versions and measured results. Do not mark a physical test as passed until it has been run on the actual station.

The station service is intended for a trusted local network. Do not port-forward it or expose it directly to the public internet.
