# Raspberry Pi 5 edge runtime

Raspberry Pi 5 is the edge-computing platform for the physical PCB inspection station. The station combines a conveyor, IR presence sensor, inspection camera and externally powered LED illumination.

## Runtime layout

- **Station input:** configurable IR GPIO input detects board arrival.
- **Illumination:** configurable GPIO output switches an external LED driver. The driver powers the LED strip; the Pi GPIO is a logic signal only.
- **Vision CPU path:** OpenCV preprocessing and YOLOv8 Nano inference through ONNX Runtime on the Pi ARM CPU.
- **Optional vision accelerator:** HailoRT on a Hailo NPU / AI HAT+ / AI HAT+ 2. This path is separate from the CPU fallback.
- **Advisory path:** Llama 3.2 Instruct through ExecuTorch on the Pi ARM CPU.
- **Operator and data:** event publication, advisory display and inspection history.

The station controller initiates a one-frame capture on an IR arrival event. It does not control the conveyor motor or emergency-stop circuit.

## Deployment identity

The Pi inference interface uses a 640 × 640 RGB input and the canonical class-ID order:

| ID | Class |
|---:|---|
| 0 | missing_hole |
| 1 | open_circuit |
| 2 | short_circuit |

The final ONNX model, the ExecuTorch model package and their measured performance records are separate release artifacts and are not bundled in the current source checkout.
