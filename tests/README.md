# Hardware acceptance and software verification

Before enabling the conveyor:
- Run inference on a small labelled validation set.
- Check class ID → class name mapping.
- Confirm boxes align with the original image after letterbox reversal.
- Test no detections, multiple detections and confidence/NMS threshold changes.
- Confirm failed inference never publishes PASS.
- Verify Firebase rejects unauthenticated access.
- Verify the physical stop mechanism independently of software.

Use approved project images and expected labels. No model metrics or expected sample predictions are fabricated in this repository.
