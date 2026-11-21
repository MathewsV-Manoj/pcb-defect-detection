# Llama 3.2 1B ExecuTorch deployment assets

The project is configured to use **Llama 3.2 1B Instruct, SpinQuant INT4/EO8,
exported for ExecuTorch** on the Raspberry Pi 5 CPU.

The approximately 1.14 GB `.pte` file and matching `tokenizer.model` are fetched
locally by the pinned downloader. They are deliberately not committed to this
Git repository.

## Download the pinned pair

From the repository root:

```bash
python -m pip install "huggingface_hub>=0.30,<2"
hf auth login
python llm_advisory/download_model.py
```

The downloader pins Hugging Face revision
`911221e0f49d3354cbd4697a9c09feee25cadec7`, checks that the model, tokenizer,
configuration files and model card are present, and writes SHA-256 hashes to
`download_manifest.json`.

The community-exported repository is public at the time of this revision, so Hugging Face login is normally not needed. If access controls change, follow the model repository's authentication instructions. The Llama 3.2 license and acceptable-use policy still apply. Do not upload the model or tokenizer to this project's public GitHub repository.

## Build the Raspberry Pi 5 runtime

The recommended setup is to build on the 64-bit Raspberry Pi 5 itself. The project provisioner handles the full dependency/model/runtime sequence with one command:

```bash
bash scripts/provision_pi5.sh
```

The runner build uses the Pi's own root filesystem as the linker sysroot, so the resulting binary matches the installed Pi libc. A cross-build from x86_64 must set `EXECUTORCH_SYSROOT` to a copy of the target Pi root filesystem; do not deploy a binary built against a different GLIBC version.

```bash
bash llm_advisory/build_pi5_runner.sh
```

The script pins an ExecuTorch 1.5 revision and runs its official Raspberry Pi 5 setup script with a Pi-compatible sysroot. It copies the resulting
`llama_main` executable, `libllama_runner.so` and the resolved ExecuTorch
commit into the ignored local directory `models/llama/runtime/`.

Copy `models/llama/` (including model, tokenizer and runtime directory) to
the Raspberry Pi. Keep the model manifest and runtime build information with
the project test record.

## Smoke-test the actual target

On the Pi, from the project root:

```bash
export LD_LIBRARY_PATH="$PWD/models/llama/runtime:$LD_LIBRARY_PATH"
models/llama/runtime/llama_main --model_path=models/llama/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte \
  --tokenizer_path=models/llama/tokenizer.model --temperature=0 --seq_len=128 \
  --prompt="<|begin_of_text|><|start_header_id|>user<|end_header_id|>Reply with the JSON object: {\"ok\":true}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
```

Then run the application's advisory smoke test with a real inspection event:

```bash
export PCB_LLAMA_MODEL_PATH="$PWD/models/llama/Llama-3.2-1B-Instruct-SpinQuant_INT4_EO8.pte"
export PCB_LLAMA_TOKENIZER_PATH="$PWD/models/llama/tokenizer.model"
export PCB_LLAMA_RUNNER_PATH="$PWD/models/llama/runtime/llama_main"
python llm_advisory/run_executorch.py \
  --event schemas/example-event.json \
  --model "$PCB_LLAMA_MODEL_PATH" \
  --tokenizer "$PCB_LLAMA_TOKENIZER_PATH" \
  --runner "$PCB_LLAMA_RUNNER_PATH"
```

The project runner uses ExecuTorch's text-only C++ `llama_main` interface.
The image is not sent to Llama; only the structured event is supplied.
Llama text is advisory and cannot modify YOLO detections or control the
conveyor, illumination or other machinery. A human operator remains
responsible for disposition and safety.

The upstream Llama 3.2 Acceptable Use Policy also restricts use in
operations of critical infrastructure, transportation technologies and heavy
machinery. This prototype must remain a supervised, non-critical laboratory
demonstration; do not deploy its Llama component in any restricted operational
setting. A textual advisory that cannot control actuators is an important
safeguard, but does not override the upstream use restrictions. Review the
current policy before every deployment.


## License and redistribution

The upstream model is marked `llama3.2`. Review and comply with the Meta Llama
3.2 Community License, acceptable-use policy and the model repository's
conditions before download, use or redistribution. This repository provides
only a downloader and references; it does not redistribute Meta model weights.
