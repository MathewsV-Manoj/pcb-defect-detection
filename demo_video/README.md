# Demonstration video

The repository contains `pcb-inspection-demo.mp4`. The project team has confirmed that the demonstration video is complete. The checklist below is retained as a final quality-control reference; this audit has not independently inspected the video frames/audio.

## Required content check

- [ ] Full station is visible: conveyor, camera, IR sensor, LED illumination and Raspberry Pi.
- [ ] Initial three-second IR hand-hold and release are shown.
- [ ] The station remains armed after release.
- [ ] A PCB moves to the camera trigger point and activates the IR sensor.
- [ ] The LED driver illuminates the board and the camera captures a frame.
- [ ] The captured image appears on the Pi-hosted operator page.
- [ ] The operator presses **Run inspection on Raspberry Pi**.
- [ ] The Pi performs local inference and produces a structured inspection result.
- [ ] The annotated image and defect classes/confidence are visible.
- [ ] The Llama/ExecuTorch advisory is shown running on the device.
- [ ] The dashboard displays the resulting inspection.
- [ ] A subsequent PCB can be captured without repeating the initial arming gesture.

The video should use the actual Pi-hosted page, actual camera frames and actual inference results. Do not use a simulated dashboard result as proof of live hardware operation. Do not show Wi-Fi passwords, Firebase tokens or other credentials.

For the submission form, provide a shareable public/unlisted video URL if the form does not accept the repository MP4 directly.
