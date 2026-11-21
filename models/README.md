# Model files

The Raspberry Pi application expects the vision detector at models/best.onnx. Export this file from the final three-class YOLO checkpoint with:

~~~bash
cd pcb_engine_kit
python train_export.py export-onnx --weights runs/pcb/weights/best.pt --size 640 --out deployment
~~~

Copy deployment/best.onnx to this folder as best.onnx. Keep best.onnx.json beside it; that file records the class order, input contract and SHA-256 hash. The source checkout does not contain the final trained detector.

The class order used by the Pi application is:

~~~text
0 missing_hole
1 open_circuit
2 short_circuit
~~~

The Llama advisory uses ExecuTorch TextLLMRunner. Its .pte model and matching tokenizer are kept outside this public source repository. The export configuration example and setup steps are in llm_advisory/README.md.

release_manifest.json records which model files are present and which checks have actually been completed. A source file or export script is not a substitute for a tested model binary.
