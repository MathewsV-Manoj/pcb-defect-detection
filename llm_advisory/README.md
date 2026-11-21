# Llama advisory

The advisory runs after the YOLO detector. The Pi sends it the inspection event as text: board ID, timestamp, defect name, severity, location and confidence. It does not receive the camera image.

The model is not used to find defects or change the detector output. Its job is to explain the reported findings and suggest checks for the operator.

## Response format

The runner expects one JSON object with these fields:

- explanation: a short description of the findings;
- recommended_actions: a list of checks for the operator;
- severity_note: a note about the assigned or unassigned severity;
- log_entry: a concise line for the inspection record.

The runner rejects a response that is empty, invalid JSON or missing a required field. A failed response is shown as an advisory failure; it is not treated as a completed recommendation.

The prompt is assembled in prompt.py. The process wrapper is run_executorch.py.

## Model and tokenizer

The repository does not include Llama weights, an ExecuTorch .pte file or a tokenizer. These must be prepared separately.

The reference configuration in llama3_2_1b_xnnpack.example.yaml is for Llama 3.2 1B Instruct using the XNNPACK CPU backend. Before exporting, obtain the model files from Meta or an authorized Hugging Face repository and accept the model licence. The original files required by the export flow are:

- consolidated.00.pth
- params.json
- tokenizer.model

Do not upload the original checkpoint or tokenizer to this public source repository unless their licence explicitly permits redistribution.

On the machine used for export, install ExecuTorch and the LLM export dependencies in a dedicated Python environment. Follow the setup instructions for the exact ExecuTorch revision you intend to install. Then copy the example YAML, edit the checkpoint, parameter and output paths, and export:

~~~bash
git clone https://github.com/pytorch/executorch.git
cd executorch
bash install_executorch.sh
pip install -e ./extension/llm/tokenizers/

# Copy the example into this ExecuTorch checkout and edit its absolute paths.
cp /path/to/pcb-defect-detection/llm_advisory/llama3_2_1b_xnnpack.example.yaml ./llama3_2_1b_xnnpack.yaml

python -m extension.llm.export.export_llm \
  --config llama3_2_1b_xnnpack.yaml
~~~

The export command creates the .pte file at the path set in export.output_name. For the Llama 3.x tokenizer expected by the runner, copy the matching tokenizer.model file to a file named tokenizer.bin:

~~~bash
cp /path/to/tokenizer.model /path/to/tokenizer.bin
~~~

Keep the checkpoint identity, tokenizer hash, ExecuTorch Git commit, Python/PyTorch versions and export configuration with the model release. The .pte file and tokenizer must come from the same model release.

## Install the Python runner on the Pi

The Raspberry Pi needs an ExecuTorch build that includes the Python LLM runner binding and the XNNPACK operators used by the exported model. The Python runner API is experimental. Follow the Python-binding build instructions in the ExecuTorch LLM Runner documentation for the same source revision used to export the model.

Check the imports on the Pi before copying model files into the station:

~~~bash
python - <<'PY'
from executorch.extension.llm.custom_ops import custom_ops
from executorch.kernels import quantized
from executorch.extension.llm.runner import GenerationConfig, TextLLMRunner
print("TextLLMRunner is available")
PY
~~~

Set these environment variables in raspberry_pi/.env:

~~~text
PCB_LLAMA_MODEL_PATH=/absolute/path/to/pcb_llama3_2_1b_xnnpack.pte
PCB_LLAMA_TOKENIZER_PATH=/absolute/path/to/tokenizer.bin
PCB_LLAMA_REQUIRED=true
~~~

The runner is created in run_executorch.py. It uses TextLLMRunner with GenerationConfig and passes only the text prompt. The process resets its KV cache after generation.

## References

- [ExecuTorch: exporting LLMs](https://docs.pytorch.org/executorch/stable/llm/export-llm.html)
- [ExecuTorch: LLM Runner and Python bindings](https://github.com/pytorch/executorch/tree/main/extension/llm/runner)
- [Meta Llama downloads](https://www.llama.com/llama-downloads/)
