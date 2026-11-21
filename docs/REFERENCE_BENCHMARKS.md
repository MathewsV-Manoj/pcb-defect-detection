# Raspberry Pi 5 performance references (not project results)

**Important:** The values below are published measurements from other projects
and models. They are engineering reference points only. They are not results
from this PCB inspection station, are not guaranteed for this hardware setup,
and must never be copied into the project's measured-results table.

## Visual inference reference

Arm published measurements for its separate **YOLO26n INT8 ONNX** model on a
Raspberry Pi 5 (Cortex-A76, 4 cores, 64-bit Raspberry Pi OS, ONNX Runtime
1.29.0 CPU provider, 4 threads, 640x640 input, batch 1, 100 warm-up and 100
timed runs):

| Metric | Published reference |
|---|---:|
| p50 end-to-end latency | 166.050 ms |
| p90 end-to-end latency | 173.912 ms |
| p99 end-to-end latency | 179.881 ms |
| Throughput | 6.02 frames/s |
| Peak memory | 154.22 MB |
| ONNX model size | 3.966 MB |

Source and complete setup: [Arm YOLO26n Raspberry Pi 5 model card](https://huggingface.co/Arm/yolo26n-640-int8-onnx-raspberrypi5).

**Not directly comparable to this project.** Arm's result uses YOLO26n, static INT8
quantization, a one2one NMS-free head and a different output contract. This
repository currently targets a three-class YOLOv8 Nano export and class-wise NMS.
The 166 ms / 6.02 FPS values therefore must not be presented as the performance
of this PCB detector. Arm's accuracy result is on COCO 2017, not PCB defects.

## Llama on Raspberry Pi 5 reference

Two public results indicate that a quantized 1B Llama model can run on a Pi 5,
but these are GGUF/Q4_K_M results and not the project's ExecuTorch SpinQuant
PTE artifact:

| Source | Pi 5 configuration | Published generation speed | Other reported figures |
|---|---|---:|---|
| ai-tier snapshot 2026-10-27 (measurement 2026-10-19) | Pi 5 16 GB; Llama 3.2 1B Instruct Q4_K_M; 4 CPU threads; one request | 14.5 tokens/s | 85 prompt tokens/s; 5 s first token; 27.9 s task time; 1,796 MiB peak memory |
| EdgeLLM-Bench (source credited to davidscarth / edge-ai-study, 2026-05-27) | Pi 5 16 GB; Llama 3.2 1B IT Q4_K_M; llama.cpp b9307 CPU/OpenBLAS; NVMe and Active Cooler; one reported test | 10.8 tokens/s | 72.9 prompt tokens/s |

Sources:
- [ai-tier: Llama 3.2 1B Instruct on Pi 5](https://ai-tier.com/results/raspberry-pi-5/llama-3-2-1b-instruct/)
- [EdgeLLM-Bench: Raspberry Pi 5 Llama 3.2 1B IT](https://edgellm-bench.vercel.app/guides/raspberry-pi-5-llama-3-2-1b-it-tokens-per-second)

These figures give an order-of-magnitude reference for a Pi 5 with 16 GB RAM.
They are not ExecuTorch results and should not be used to predict this project's
exact TTFT, tokens/s, RAM use or total inspection cycle. The actual result
depends on the PTE build, prompt length, context length, CPU cooling, memory
pressure, runtime version and operating system.

## Exact SpinQuant PTE model-card reference (different device)

The model card for the **same Llama 3.2 1B SpinQuant PTE family** reports
ExecuTorch ARM CPU results on an **Android OnePlus 12**, not a Raspberry Pi 5:
50.2 generated tokens/s, 0.3 s time-to-first-token, 260.5 prompt tokens/s,
1,083 MB PTE file size and 1,921 MB RSS. The TTFT uses a 64-token prompt.
These numbers are useful for model-file and memory planning, but they are
phone results and must not be represented as Pi 5 results.

Source: [ExecuTorch community model card — inference time](https://huggingface.co/executorch-community/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8-ET).

## Project measurements: currently unpopulated

Run these commands on the actual Pi after copying the final model assets and
held-out PCB images:

    # Detector only: preprocessing + ONNX + detector post-processing
    python raspberry_pi/benchmark_onnx.py \
      --model models/best.onnx \
      --images /path/to/held_out_pcb_images \
      --warmup 5 --threads 2 \
      --out docs/results/pi_onnx_benchmark.json

    # Complete still-image software path: vision + Llama advisory
    python raspberry_pi/benchmark_pipeline.py \
      --images /path/to/held_out_pcb_images \
      --model models/best.onnx \
      --warmup 1 \
      --out docs/results/pi_pipeline_benchmark.json

The first report measures detector preprocessing, ONNX execution and
post-processing. The second invokes the production coordinator for each
still image and measures image-to-advisory wall-clock time, detector time,
Llama response time, TTFT and token rate where the runner exposes them. The
second test does **not** include conveyor trigger, physical capture, LED
settling or browser display time. Use the commissioning form to time complete
physical cycles separately.

Power is not inferred from CPU load or temperature. Measure it with an
external USB-C power meter and record meter model, sampling method, idle draw
and loaded draw. Accuracy requires annotated held-out boards and must be
reported separately as per-class precision, recall, F1 and mAP.

No project measurement is entered in this document. Leave results unfilled
until the named scripts have run on the team's actual Raspberry Pi 5.
