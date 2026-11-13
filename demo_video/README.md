# PCB Inspection Demonstration Video

This folder is the repository location for the project's demonstration video.

## Upload the video

Upload the final video into this folder using the following filename:

`pcb_inspection_demo.mp4`

On GitHub:

1. Open the `demo_video` folder.
2. Select **Add file → Upload files**.
3. Upload `pcb_inspection_demo.mp4`.
4. Commit the upload to the `main` branch.

After the upload, add or update the video link in the root `README.md` so evaluators can open it directly.

## Recommended video sequence

For a clear technical demonstration, show the complete inspection sequence:

1. **Inspection setup:** the PCB inspection station, camera and conveyor arrangement.
2. **Board positioning:** a PCB entering or being placed at the imaging position.
3. **Image acquisition:** the camera capturing the PCB.
4. **Visual detection:** YOLO output showing the predicted defect class, confidence and localized bounding box.
5. **Inspection record:** the generated board ID, timestamp, result and detection details.
6. **Data publication:** the corresponding inspection event appearing in Firebase Realtime Database.
7. **Dashboard update:** the latest inspection, defect information and inspection history appearing in the web dashboard.
8. **Operator advisory:** the optional text guidance generated from the structured detector findings.
9. **Repeat inspection:** another board or defect example, showing that the process can be demonstrated with more than one sample.

Use actual system footage and actual application outputs. Clearly distinguish live inspection results from any simulated dashboard demonstration scenes.
