# Operator dashboard

The dashboard presents the latest PCB inspection state and retained inspection events from Firebase Realtime Database.

The operator view includes:
- Board and inspection decision.
- Camera and conveyor state fields.
- IR board-presence state at capture.
- External LED illumination state at capture.
- Defect type, severity, image location and confidence.
- Llama advisory text.
- Inspection history and CSV export.

The dashboard is a presentation layer. Image preprocessing, vision inference and Llama advisory generation execute locally on the Raspberry Pi 5. Firebase provides optional record synchronization and does not execute either model.

The HTML source is `index.html`. Firebase configuration is deployment-specific and private credentials are not included in the repository.
