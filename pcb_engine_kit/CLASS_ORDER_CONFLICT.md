# Critical: the supplied files contain conflicting class orders

Two separate project artifacts specify different class maps:

## A. Training/export code in this ZIP
`dataset.py`, `train_export.py`, and `engine.py` all define/use:
| ID | Class |
|---:|---|
| 0 | open_circuit |
| 1 | short_circuit |
| 2 | missing_hole |

The TFLite exporter writes this order into its `metadata.json`, and the folder engine asserts it.

## B. Separate Raspberry Pi 5 hardware handoff
`docs/PCB_Raspberry_Pi_Windows_Hardware_Handoff.md` says:
| ID | Class |
|---:|---|
| 0 | missing_hole |
| 1 | open_circuit |
| 2 | short_circuit |

## Required resolution
Do not guess and do not edit a class list to fit the desired names. Inspect the exact trained checkpoint's `names`, training `data.yaml`, `args.yaml`, training logs and export metadata. Whichever mapping is present in the actual final weights must be treated as authoritative. Then align the dataset, decoder, metadata, ONNX/TFLite file and UI labels to that same mapping. Save the evidence and add a model hash in `models/release_manifest.json`.

Until resolved, neither the kit's TFLite model path nor the root Pi 5 ONNX script should be declared validated against the same checkpoint.
