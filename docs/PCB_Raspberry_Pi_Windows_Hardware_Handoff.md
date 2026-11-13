# PCB Defect Detection — Hardware Handoff Guide

**For:** Hardware/integration engineer using Windows  
**Deployment target:** Raspberry Pi 5

## 1. Model details

The latest training run is the **three-class model**:

| Class ID | Class name |
|---:|---|
| 0 | `missing_hole` |
| 1 | `open_circuit` |
| 2 | `short_circuit` |

Model input: **640 × 640 RGB image**.

The exported YOLO ONNX model is expected to have a raw output shape similar to **`[1, 7, 8400]`** (4 box values plus 3 class scores). The inference application must decode this output and apply confidence filtering and non-maximum suppression (NMS). Raw ONNX output is not yet a final list of detections.

> **Important: use the three-class model only.** The earlier `runs/pcb/` model was a six-class model. The latest three-class training output shown in the training log is under `runs/pcb3/`. Do not use the older six-class `runs/pcb/weights/best.pt` or `best.onnx`.

## 2. Check the ZIP on Windows

1. Save the ZIP received from the model-training engineer.
2. Right-click it and select **Extract All**.
3. Open the extracted folder.
4. Confirm that it contains:
   - `best.pt` — PyTorch reference/fallback model.
   - `best.onnx` — ONNX model for deployment.
   - A class-name file or documentation listing the three classes in the exact order above.

If the ZIP contains only `best.pt`, or the files came from the old `runs/pcb/` folder, request a corrected ZIP before integration. **Do not use the old six-class ONNX model.**

## 3. Optional: test ONNX on Windows

Open **PowerShell** in the extracted model folder.

Create and activate a Python environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install ultralytics onnx onnxruntime opencv-python
```

If PowerShell blocks environment activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Check that the ONNX file is valid:

```powershell
python -c "import onnx; m=onnx.load('best.onnx'); onnx.checker.check_model(m); print('ONNX model is valid')"
```

Run a test prediction, replacing the image path:

```powershell
yolo predict task=detect model=best.onnx source="C:\path\to\pcb_test_image.jpg" imgsz=640 device=cpu
```

The annotated result should appear under a `runs\detect\predict` folder. Check that class names and bounding boxes are sensible. A successful Windows test does not prove Raspberry Pi performance; test on the Pi separately.

## 4. Transfer the model to Raspberry Pi 5

Copy `best.onnx` and the class-name file to the Pi using a USB drive or `scp`.

Example from Windows PowerShell (replace the Pi username and IP address):

```powershell
scp .\best.onnx .\class_names.txt pi@<PI_IP_ADDRESS>:/home/pi/pcb_model/
```

If needed, create the destination folder on the Pi first:

```bash
mkdir -p ~/pcb_model
```

Do not copy the Windows `.venv` folder to the Pi. Python environments are platform-specific.

## 5. Set up Raspberry Pi 5

Use **64-bit Raspberry Pi OS**. On the Pi, open Terminal:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv
mkdir -p ~/pcb_model
cd ~/pcb_model
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install onnxruntime numpy
```

Check the runtime:

```bash
python -c "import onnxruntime as ort; print('ONNX Runtime:', ort.__version__); print('Providers:', ort.get_available_providers())"
```

For the initial deployment, use the CPU execution provider. The model was trained on an NVIDIA GPU, but Raspberry Pi 5 will run this model on its CPU unless a separately supported accelerator is added.

If `onnxruntime` cannot be installed for the Pi's Python/OS version, do not install an unofficial wheel. Send the exact error to the model-training engineer so a compatible runtime can be selected.

## 6. Camera and inference integration

The hardware/integration engineer should:

1. Capture a frame from the selected camera.
2. Convert the frame to RGB.
3. Resize/letterbox it to **640 × 640**, preserving aspect ratio and recording the padding.
4. Convert pixel values to floating point and normalize to **0–1**.
5. Arrange the input tensor as **NCHW**: `[1, 3, 640, 640]`.
6. Run inference with ONNX Runtime using the CPU provider.
7. Decode the YOLO output, apply confidence filtering and NMS, and reverse the resize/padding to map boxes onto the original camera frame.
8. Display or transmit the class name, confidence, and bounding-box coordinates.

Use this exact class order:

```text
0: missing_hole
1: open_circuit
2: short_circuit
```

Do not guess the preprocessing or post-processing implementation. Confirm the ONNX input/output names and shapes from the model, and compare decoded detections against the Windows test results. The model file alone does not include camera capture or the complete application logic.

## 7. Acceptance tests

Before connecting the model to the complete hardware system, record:

- [ ] ONNX model loads successfully on Raspberry Pi 5.
- [ ] A known PCB image produces detections without a runtime error.
- [ ] The three class IDs map to the correct class names.
- [ ] Bounding boxes align with defects in the original image.
- [ ] Confidence threshold and NMS threshold are configurable.
- [ ] Live camera inference runs continuously without memory errors.
- [ ] Average inference time and approximate FPS are measured on the Pi.
- [ ] Results are checked on multiple PCB boards, lighting conditions, and defect sizes.

Record the Raspberry Pi OS version, Python version, ONNX Runtime version, camera model, inference time, and FPS.

## 8. Limitations

- The model detects only the three trained categories: missing hole, open circuit, and short circuit.
- Do not describe it as detecting every possible PCB defect.
- Training validation metrics do not guarantee real-world accuracy. Test with actual camera images and representative PCB samples.
- Do not retrain, rename, or reorder classes during hardware integration without coordinating with the model-training engineer.
- Keep the original `best.pt` and `best.onnx` files unchanged. Make a separate copy before conversion or optimization.

## 9. Report back to the model-training engineer

After integration, send:

1. Confirmation that the ONNX model loads on the Pi.
2. A sample original camera frame and its annotated detection result.
3. Inference time per frame and approximate FPS.
4. Any false positives, missed defects, or incorrect class labels.
5. Full error text if installation or inference fails.

This feedback will determine whether further training, threshold tuning, or deployment optimization is required.