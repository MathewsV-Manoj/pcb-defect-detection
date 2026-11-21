# Operator dashboard

The dashboard presents the latest PCB inspection state and retained inspection events from Firebase Realtime Database. Its operator view includes camera and conveyor state, IR board-presence sensing, external LED illumination status, defect findings, model metadata, advisory text and inspection history.

The dashboard is a presentation layer. Image preprocessing, visual inference and the on-device Llama advisory pipeline execute on the edge device. Firebase provides record synchronization and is not an inference runtime.

The HTML source is `index.html`. Live configuration is environment-specific and is not committed with private credentials.
