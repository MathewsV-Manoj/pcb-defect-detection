# Llama advisory on Raspberry Pi 5

The Bharat AI-SoC Challenge requires a Llama-family model deployed with ExecuTorch. This project uses a text-only advisory boundary: the vision detector creates a structured inspection event, then the ExecuTorch runner receives that event as text.

The advisory runner does not receive the PCB image or image path. It must not add, remove, relabel or suppress detector findings, infer severity from confidence, or make an independent PASS/REJECT decision.

## Source files

- `prompt.py` builds the Llama 3.x chat-formatted prompt from the event fields.
- `run_executorch.py` loads the structured event, runs ExecuTorch `TextLLMRunner`, validates the four-field JSON response and reports runtime telemetry.
- `raspberry_pi/run_inspection.py` coordinates vision inference, advisory generation, local event logging and configured Firebase synchronization.

## Required runtime files

The source repository does not contain the exported ExecuTorch `.pte` model, its matching tokenizer or the ExecuTorch Python runner build. These are required to run the advisory and must be supplied as a matching model/runtime package.

Set these environment variables on the Raspberry Pi:

```text
PCB_LLAMA_MODEL_PATH=/absolute/path/to/model.pte
PCB_LLAMA_TOKENIZER_PATH=/absolute/path/to/tokenizer.bin
PCB_LLAMA_REQUIRED=true
```

Build/install the ExecuTorch Python LLM runner and the operators required by the selected model. Keep the exact ExecuTorch revision, build flags, model identity, tokenizer identity, Python/PyTorch versions and SHA-256 hashes with the release record. The actual model/tokenizer pair must be run on the target Pi; successful Python imports alone are not sufficient.

## Advisory response contract

The model must return one JSON object with exactly these fields:

- `explanation`: non-empty string;
- `recommended_actions`: array of non-empty strings;
- `severity_note`: non-empty string;
- `log_entry`: non-empty string.

The current detector emits `UNASSESSED` severity. The advisory must state this and request operator review; it must not turn confidence into a severity rating.

## Release status

The prompt builder, runner source and response validation are in the repository. The model package, matching tokenizer and verified ExecuTorch runtime are not. Do not describe on-device Llama inference as completed until the package has been installed and demonstrated on the Raspberry Pi.
