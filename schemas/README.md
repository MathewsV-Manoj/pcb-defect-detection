# Inspection event

inspection-event.schema.json describes the JSON record written by the Pi after an inspection. example-event.json shows the expected field layout.

A detection contains its class ID and name, confidence, bounding box, severity and normalized centre location. Severity is separate from confidence. Until a board-specific severity policy is configured, the detector reports UNASSESSED.

The example is for checking the record format. It is not a real model prediction or a measured result.
