# Llama advisory pipeline

The selection architecture requires a Llama-family model deployed locally through ExecuTorch. The advisory pipeline runs on the Raspberry Pi 5 ARM CPU and is separate from the visual-detection runtime.

## Model and runtime

The reference model family is **Llama 3.2 Instruct 1B or 3B**. A pretrained instruction-tuned model with a constrained structured prompt is sufficient for the initial advisory workflow; fine-tuning is not a prerequisite.

ExecuTorch is the reference on-device runtime for this pipeline. The Llama model does not need to run on Hailo. HailoRT, when present, accelerates the vision pipeline only.

## Input contract

The advisory receives a structured inspection event containing:
- Defect type.
- Severity (LOW, MEDIUM, HIGH or UNASSESSED).
- Location (bounding box, normalized centre and optional board zone).
- Vision confidence.
- Board ID and timestamp.

It does not receive the raw PCB image. The prompt builder is implemented in `prompt.py`.

## Output responsibilities

The advisory generates:
1. A concise explanation of the detector findings.
2. Suggested operator verification or corrective actions.
3. A structured inspection log entry.

It does not detect defects, view image pixels, modify detection classes or confidence, infer severity from confidence, or independently issue a PASS/REJECT decision. When severity is UNASSESSED, the advisory must preserve that state and request human review rather than inventing a rating.

## Runtime boundary

The repository contains the prompt-construction source. The ExecuTorch runtime package and quantized model binary are separate deployment assets and are not bundled in this source checkout. Advisory performance is evaluated independently using time to first token, tokens per second, total response time and memory on the target Pi.
