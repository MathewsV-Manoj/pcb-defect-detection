# Llama advisory component (not a trained visual model)

The project plan mentions a Llama-family advisory stage, with ExecuTorch deployment to be evaluated. This repository does **not** contain a fine-tuned GPT/Llama checkpoint, tokenizer, or model weights. No custom GPT model training has been verified.

The advisory receives structured YOLO output only: board ID, class name, confidence, bounding box, and approved inspection procedure. It must not inspect pixels, create/relabel/suppress detections, or issue a PASS decision. It is an optional operator explanation layer.

## Prompt rules
```text
You are an inspection support assistant.
Use only structured YOLO findings and approved inspection procedures.
Do not claim to have viewed the PCB image.
Do not add, remove, relabel or modify detector findings.
Do not convert confidence into a probability of failure.
Do not issue a PASS/REJECT decision.
Explain reported findings and suggest a human verification step.
If there are no detections, say only that no configured target was detected.
```

Before ExecuTorch deployment, verify the selected Llama model, tokenizer, conversion format, quantization, ARM64 support, memory and measured Pi 5 latency. Llama is optional and must not block YOLO inspection.
