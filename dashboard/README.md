# Firebase dashboard

Static HTML dashboard listening to Firebase Realtime Database `/live` and `/inspections`. It displays session/history/defect data and deliberately does not display a live camera preview.

Replace the `PASTE_...` placeholders in `firebaseConfig` with your Firebase Web App config. Host on HTTPS. Configure Authentication and restrictive database rules.

Trial scenarios in the page are simulation-only; they do not write demo records into Firebase and do not control the conveyor or GPIO.
