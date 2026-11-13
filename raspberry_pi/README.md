# Raspberry Pi 5 edge inference

Target: Raspberry Pi 5 + 64-bit Raspberry Pi OS + ONNX Runtime CPU for the initial three-class detector.

Install:
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r raspberry_pi/requirements.txt
```
For CSI camera support, install Raspberry Pi OS package `python3-picamera2`.

Put the verified 3-class `best.onnx` in `models/best.onnx`. Expected class order:
```
0 missing_hole
1 open_circuit
2 short_circuit
```
Input is NCHW float32 `[1,3,640,640]`; Pi 5 handoff notes describe raw output `[1,7,8400]` (or transposed). Confirm the actual model graph before use.

Single image:
```bash
python raspberry_pi/inspect_image.py --source /path/to/pcb.jpg --weights models/best.onnx
```
One frame from USB camera:
```bash
python raspberry_pi/inspect_image.py --camera 0 --weights models/best.onnx
```
One frame from CSI camera:
```bash
python raspberry_pi/inspect_image.py --picamera2 --weights models/best.onnx
```
This is one-shot capture, not a continuous conveyor controller. GPIO motor pins and trigger wiring have not been verified, so no assumed pin mapping is included.

Firebase direct publishing:
```bash
export FIREBASE_DATABASE_URL="https://YOUR_DATABASE_URL"
export FIREBASE_AUTH_TOKEN="YOUR_AUTH_TOKEN"
python raspberry_pi/inspect_image.py --source /path/to/pcb.jpg --weights models/best.onnx --publish
```
Use Authentication and restrictive Realtime Database rules; never commit credentials.
Measure p50/p95 latency, FPS, RAM, temperature and missed defects on the actual Pi 5.
