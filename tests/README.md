# Software contract tests

The automated test suite covers:

- Structured Llama advisory input, including defect type, severity and location; image payloads and image paths are excluded.
- Atomic image submission into the queued-image workflow.
- Rejection of archive paths that attempt directory traversal.
- Canonical defect class order across the Pi detector, dataset converter, exporter and TFLite worker.
- Required severity/location fields in the inspection-event schema and example.
- Architecture SVG validity.
- Dashboard IR/LED status fields, severity/location history columns and removal of demo-only controls.
- Station-controller linkage to the complete vision/advisory inspection coordinator.
- Dashboard JavaScript syntax when Node.js is available in the CI runner.

GitHub Actions compiles the Python sources and runs the test suite on pushes and pull requests to the main branch. These software checks do not represent Raspberry Pi 5 performance measurements or physical camera/conveyor commissioning.
