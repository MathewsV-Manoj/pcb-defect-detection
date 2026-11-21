# Physical-system demonstration

The demonstration video is the visual record of the built PCB inspection station and its operating sequence. It complements the source code and technical report by showing the hardware and the operator-facing inspection workflow in operation.

## Demonstrated sequence

1. **Inspection station:** conveyor assembly, inspection area, camera and Raspberry Pi 5.
2. **Board transport:** PCB moves along the conveyor into the inspection zone.
3. **IR arrival sensing:** the IR sensor detects the incoming PCB and initiates the capture cycle.
4. **Controlled illumination:** the external LED strip switches on through its driver to illuminate the PCB.
5. **Image acquisition:** the camera captures the illuminated board after the configured settling interval.
6. **Vision output:** the inspection application displays the detected defect class and localized image region.
7. **Structured inspection record:** board identity, timestamp, defect type, severity, location and confidence are recorded.
8. **Llama advisory:** the on-device advisory explains the structured finding, suggests operator verification and creates log text.
9. **Operator interface:** the alert, advisory and inspection history are displayed for review.

## Architecture shown in the demonstration

The physical sequence corresponds to the repository's IR-triggered station controller and inspection coordinator. The vision model and Llama advisory are separate local runtimes. The advisory consumes structured detection data only and does not inspect the camera image.

The demonstration video is supplied as the separate video deliverable for the project submission. This folder identifies the demonstration scope; the video media file is distributed separately.
