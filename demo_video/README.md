# Physical-system demonstration

The project demonstration video documents the built conveyor-based PCB inspection station and the operator-controlled Raspberry Pi workflow.

## Demonstrated operating sequence

1. **Station arming:** at the beginning of the station session, an operator holds a hand in front of the IR sensor for approximately three seconds. The station remains armed for subsequent PCB cycles.
2. **Release and loading:** the sensor is released and a PCB is placed on the conveyor.
3. **Conveyor transport:** the belt moves the PCB towards the camera position.
4. **Board-position confirmation:** the IR sensor detects the PCB at the camera position.
5. **Controlled illumination:** the external LED strip is switched on through its driver.
6. **Camera capture:** the Raspberry Pi captures and saves the illuminated PCB frame.
7. **Laptop preview:** the Raspberry Pi-hosted website displays the captured image in the laptop browser for verification.
8. **Operator run command:** the operator clicks **Run inspection on Raspberry Pi**. The browser sends a command to the Pi station service.
9. **Edge vision:** OpenCV preprocessing and YOLO defect localization run on the Raspberry Pi.
10. **On-device advisory:** the Llama/ExecuTorch process receives structured findings and returns an explanation, verification actions and log text.
11. **Operator results:** the decision, detections, coordinates, confidence, annotated output and event history appear in the UI.

The video demonstrates the physical station and the operator workflow; the public repository contains the corresponding station controller, Pi-hosted dashboard, inspection coordinator, vision source and advisory runner.
