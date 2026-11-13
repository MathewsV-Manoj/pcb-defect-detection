PCB DEFECT DETECTION — POST-TRAINING HANDOFF INSTRUCTIONS

Context We are developing a PCB defect detection system for the Bharat
SoC AI Challenge. The current work is training a YOLOv8 Nano model. The
intended final defect classes are: 1. open_circuit 2. short_circuit 3.
missing_hole

IMPORTANT WORKFLOW We have two separate handoffs:

HANDOFF 1 — TRAINED MODEL TO HARDWARE TEAM After the current training
finishes, do NOT begin the full Llama/dashboard integration yet. First,
prepare and give the hardware team the trained vision model and the
minimum information needed to integrate it.

Before handing it over: - Confirm which dataset/classes the run actually
used. Do not assume it is the final three-class model unless data.yaml
and the training results confirm this. - Evaluate the model on
validation/test data and unseen PCB images. - Check per-class precision,
recall, mAP@50 and mAP@50–95. - Inspect the confusion matrix and sample
predictions for false positives and missed defects. - Identify the best
checkpoint (usually best.pt). - Export an inference-compatible format if
requested by the hardware team (for example ONNX), and verify that the
exported model produces consistent predictions. - Provide the class-name
mapping, input image size, preprocessing requirements, confidence
threshold and NMS settings. - Provide a small inference script and a few
permitted sample test images with expected outputs. - Clearly document
known limitations. Do not claim the model is production-ready based only
on mAP.

Hardware handoff package should include: - best.pt - optional verified
ONNX export - class names / class-ID mapping - model evaluation
results - inference script and dependency/version notes - input/output
specification - sample predictions and known limitations

HANDOFF 2 — COMPLETE APPLICATION DEVELOPMENT After the hardware team has
received the trained model and hardware integration has progressed,
continue development of the complete software application.

Planned additions: 1. OpenCV image acquisition/preprocessing pipeline.
2. YOLO inference module using the trained model. 3. Structured defect
records (JSON) containing board ID, class, confidence and bounding-box
coordinates. 4. A transparent severity/risk rule set, validated with the
inspection requirements. Do not invent severity from confidence alone.
5. Llama-family advisory component that receives structured detection
results and generates explanations and suggested inspection actions. 6.
ExecuTorch deployment for the Llama component, as required by the
supplied reference architecture. Verify model/runtime compatibility and
resource requirements before selecting a model. 7. Operator dashboard
showing the PCB image, bounding boxes, defect class, confidence,
advisory text and inspection history. 8. Logging and report generation.
9. Integration and testing on the agreed target hardware. 10. Measure
actual device latency, throughput/FPS, RAM use and reliability.

ARCHITECTURE TARGET PCB camera/image -> OpenCV preprocessing -> YOLOv8
defect detection -> Structured defect record -> Llama advisory through
ExecuTorch -> Operator dashboard and inspection log

IMPORTANT TECHNICAL NOTES - Do not replace or retrain YOLO without
evidence from evaluation that changes are needed. - Do not rename the
old six-class model as a three-class model. Verify the actual training
configuration and class mapping. - DeepPCB’s pin-hole class must not
automatically be treated as equivalent to a missing-hole defect. Verify
annotation meaning and dataset suitability. - Keep the vision model
responsible for detecting/localizing defects. The LLM should explain
structured findings; it should not be presented as the source of visual
defect detection. - The final application is a separate deliverable from
the trained model. The hardware team can receive the model first; the
integrated application, report and demo are prepared later. - Keep all
reported metrics tied to the exact dataset split and model checkpoint
that produced them.

NEXT ACTION WHEN TRAINING FINISHES First inspect the training run and
its dataset configuration. Then guide me step by step through evaluation
and preparation of the hardware handoff package. Do not jump ahead to
Llama or dashboard implementation until the trained model handoff is
ready.