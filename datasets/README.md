# Dataset provenance

The project targets open-circuit, short-circuit and missing-hole detection on PCB images. Dataset suitability is assessed against those labels and the actual inspection-camera domain.

## Dataset references

| Dataset | Domain | Relevance to this project |
|---|---|---|
| DeepPCB | PCB defects | PCB-specific source reference for defect-detection experiments |
| Tiny-Defect-Detection-for-PCB | PCB defects | PCB-specific source reference; annotation labels require mapping review |
| MVTec AD | Industrial anomaly detection across multiple object/texture categories | General anomaly-detection reference; not a direct source of the three PCB defect labels |
| NEU Surface Defect | Steel surface defects | General surface-inspection reference; not PCB imagery |
| KolektorSDD | Electrical commutator surface cracks | Industrial defect reference; not PCB imagery |
| Project camera captures | The assembled inspection station | Domain-specific evaluation and training material, subject to contributor permissions |

The committee-listed MVTec AD, NEU Surface Defect and KolektorSDD datasets are useful references for industrial anomaly detection, but their labels and image domains do not directly represent the three PCB target classes. PCB-specific data and project camera captures are required for task-aligned evaluation.

## Provenance policy

The source manifest records dataset identity, source URL, license/terms, annotation classes and whether use in a specific checkpoint is verified. A source is not described as training data unless the exact training configuration and records establish that it was used. Raw datasets are not included in this repository.
