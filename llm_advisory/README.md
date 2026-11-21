# On-device Llama advisory — ExecuTorch

## Role in the inspection system

The advisory pipeline is a required component of the complete PCB inspection workflow. It runs locally on the Raspberry Pi 5 ARM CPU using ExecuTorch and a Llama 3.2 Instruct 1B or 3B model.

Vision and advisory inference are separate:

- The vision runtime detects, classifies and localizes PCB defects.
- The advisory runtime explains the structured findings, recommends operator verification actions and generates log text.
- The advisory does not receive image pixels or a camera frame.

The vision runtime may be ONNX Runtime on the Pi CPU or an optional HailoRT vision path. Hailo does not replace the ExecuTorch advisory.

## Input contract

`prompt.py` constructs the Llama prompt from:

- Board ID and inspection timestamp.
- Defect type.
- Assigned severity.
- Image-coordinate bounding box and normalized location.
- Detector confidence.

No image, image path or pixel tensor is included.

## Advisory output

The model is prompted to return JSON with four fields:

| Key | Content |
|---|---|
| `explanation` | Concise explanation of the structured finding |
| `recommended_actions` | Operator verification steps |
| `severity_note` | Severity context, including human review when severity is UNASSESSED |
| `log_entry` | Human-readable inspection log text |

The advisory is bounded by the inspection record. It cannot add, remove, relabel or suppress detections, infer severity from confidence, or independently issue a PASS/REJECT decision. The detector output remains unchanged.

## Runtime implementation

| File | Responsibility |
|---|---|
| `prompt.py` | Builds the text-only structured prompt |
| `run_executorch.py` | Loads the ExecuTorch model and tokenizer, runs text generation and captures telemetry |
| `../raspberry_pi/run_inspection.py` | Calls the advisory after vision inference and appends the result to the local inspection event |

The runner uses ExecuTorch's `TextLLMRunner`, which is the text-only runner for Llama-family models. The implementation imports the LLM custom-op and quantized-kernel registration modules before loading the model. The ExecuTorch build must expose the Python LLM runner bindings (`EXECUTORCH_BUILD_PYBIND=ON`) and the exported `.pte` model must match the runtime, tokenizer and registered operators.

## Model packaging

The reference model family is Llama 3.2 Instruct 1B or 3B. The exported ExecuTorch `.pte` model and matching tokenizer binary are separate deployment artifacts and are not stored in the public source repository. They must be built for the Pi's ARM64 runtime and tested with the exact ExecuTorch build that provides the `TextLLMRunner` Python extension. The model package and tokenizer must be a matched pair for the runner.

Fine-tuning is not required for the structured advisory workflow. A pretrained Instruct model with a controlled prompt is the reference configuration.

## Runtime telemetry

The runner records:

- Time to first generated token.
- Total response time.
- Generated-token statistics exposed by the ExecuTorch runner.
- Tokens per second when the installed runner exposes compatible timing statistics.
- Process peak resident memory where supported.

These measurements are captured on the target Pi 5 for advisory benchmarking. They are not inferred from workstation performance.

## Offline execution

The advisory model runs locally on the Pi. Internet access is not part of the inference path; model and tokenizer assets are present on the device before an inspection session begins.

## Runtime references

- [ExecuTorch LLM Runner Python API](https://github.com/pytorch/executorch/tree/main/extension/llm/runner)
- [ExecuTorch Llama model support and export workflow](https://github.com/pytorch/executorch/tree/main/examples/models/llama)
