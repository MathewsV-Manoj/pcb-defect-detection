# On-device Llama advisory

The operator advisory is a text-only Llama pipeline designed to run on the Raspberry Pi 5 ARM CPU through ExecuTorch. It is independent of the vision runtime, which runs through ONNX Runtime on the CPU or optionally HailoRT on a Hailo NPU.

## Runtime implementation

- `prompt.py` builds the advisory prompt from board metadata and structured detector findings.
- `run_executorch.py` invokes the ExecuTorch LLM Python runner and writes advisory text with runtime telemetry.
- `../tests/test_advisory_contract.py` verifies that defect type, severity and location are included while image payloads are excluded.

The ExecuTorch runner uses text inputs only. It receives defect type, severity, location, confidence, board ID and timestamp. It does not receive the PCB image.

## Python runner build

The ExecuTorch LLM Runner Python bindings are experimental. They are provided by the ExecuTorch source build, not by the basic runtime package alone. The source build enables `EXECUTORCH_BUILD_PYBIND=ON` or uses the ExecuTorch install script that builds Python bindings. The installed runner module must expose the LLM Runner classes used by `run_executorch.py`.

The runner source uses `MultimodalRunner` with text inputs only. It does not call `make_image_input`, load image tensors or pass the PCB frame to the Llama model.

## Model

The reference model family is Llama 3.2 Instruct 1B or 3B. The `.pte` model and matching tokenizer binary are separate deployment artifacts. They are not bundled in the source checkout, and no Raspberry Pi inference benchmark is asserted here.

The runner uses the ExecuTorch LLM Python bindings. The documented API provides `MultimodalRunner`, `GenerationConfig`, `make_text_input` and text-only generation. The runner supplies text inputs only and does not call image-input helpers.

## Advisory output

The model is prompted to return a concise explanation, verification actions, a severity note and an inspection log entry. The advisory is stored separately from the original detection array. It cannot add, remove, relabel or suppress detector findings, infer severity from confidence, or make an independent PASS/REJECT decision.

## Runtime measurements

`run_executorch.py` records total response time and time to first generated token. Generation statistics exposed by the installed runner are retained in the JSON result. Tokens per second and peak memory are assessed separately using target-device profiling.

## Runtime references

- [ExecuTorch LLM Runner Python API](https://github.com/pytorch/executorch/tree/main/extension/llm/runner)
- [ExecuTorch Llama 3.2 model support and export workflow](https://github.com/pytorch/executorch/tree/main/examples/models/llama)