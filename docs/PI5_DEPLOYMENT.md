# Raspberry Pi 5 deployment notes

The active Pi path in this repository uses ONNX Runtime CPU, based on the project-specific Pi 5 handoff. A separate earlier development document describes a Pi 4 and TFLite/LiteRT kit. Treat that as a historical reference only; no validated TFLite model binary was found.

## Verified design facts from the handoff document
- Device target: Raspberry Pi 5, 64-bit Raspberry Pi OS.
- Initial inference provider: ONNX Runtime CPU.
- Model target: three-class YOLO model from `runs/pcb3/`.
- Class order: 0 `missing_hole`, 1 `open_circuit`, 2 `short_circuit`.
- Input: 640 × 640 RGB.
- Expected raw ONNX output: approximately `[1, 7, 8400]`; inspect the actual exported graph.

## Current limitations
- The committed inference entry point captures one frame only, not continuous conveyor operation.
- GPIO pin assignments, motor driver wiring, sensor trigger, emergency-stop circuit and belt timing were not provided in a verified wiring diagram. No pin mapping is guessed.
- The detector file itself is not present yet.
- Firebase can publish records once credentials/rules are configured.
- Llama/ExecuTorch has not been loaded or benchmarked on the Pi.

## Bring-up gates
1. Verify ONNX file identity, hash, inputs/outputs and class order.
2. Compare predictions against the reference PyTorch checkpoint on the same test images.
3. Verify camera acquisition independently.
4. Commission conveyor/sensor control against actual hardware wiring and safe-stop logic.
5. Measure Pi 5 latency, throughput, RAM and temperature over a sustained session.
6. Add Llama advisory only after YOLO → Firebase → dashboard works reliably.
