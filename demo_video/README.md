# Demonstration video

The video still needs to be recorded on the physical station. This shot list is a guide for that recording; it is not a substitute for the video.

## Suggested recording order

| Shot | What to film | What the viewer should be able to see |
|---|---|---|
| 1 | Full station, powered off | Conveyor, camera, IR sensor, LED strip and Raspberry Pi |
| 2 | Operator holds a hand in front of the IR sensor | Continuous hold for about three seconds |
| 3 | Operator releases the sensor | Dashboard changes to the armed/waiting state |
| 4 | PCB placed on the conveyor | Board moving towards the inspection area |
| 5 | Close view of the IR trigger point | Sensor activates as the PCB reaches the camera area |
| 6 | LED and camera | LED turns on, frame is captured and LED turns off |
| 7 | Laptop browser | The captured frame appears on the Pi-hosted page |
| 8 | Operator clicks Run inspection | Button acknowledges the request |
| 9 | Raspberry Pi processing | Show the Pi terminal/log if useful; do not show secrets or tokens |
| 10 | Dashboard result | Show the annotated image, class, confidence, location and advisory |
| 11 | Second PCB | Show that the station remains armed and accepts the next board |

## Recording notes

- Use the actual Pi-hosted dashboard address, not a locally opened copy of the HTML file.
- Keep the camera frame and the dashboard readable.
- Include at least one real inspection result from the final model.
- Show both the captured image and the annotated image.
- Do not use the hidden simulation mode or edited screenshots as proof of hardware operation.
- If a stage fails during filming, correct it and record another take. Do not hide a failed run by presenting it as a successful live inspection.
- Do not show Wi-Fi passwords, Firebase tokens, model download tokens or other credentials.

## Suggested narration

“This is the PCB inspection station. At the start of a session, the operator holds a hand in front of the IR sensor for about three seconds. After the sensor is released, the station stays armed. The PCB travels along the conveyor and the IR sensor triggers capture when the board reaches the camera area. The Raspberry Pi switches on the LED driver and saves an image. The operator checks the image in the browser and starts inspection from the laptop. The Pi runs the detector locally and returns the annotated result and operator advisory to the page.”

Keep the narration consistent with what the camera actually shows. The IR sensor confirms board presence at its trigger point; it does not measure precise image alignment.
