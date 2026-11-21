# Software contract tests

The repository includes automated checks for:

- Structured Llama advisory input: defect type, severity and location are included, while image data and image paths are excluded.
- Atomic image submission into the queued-image workflow.
- Rejection of archive paths that attempt directory traversal.

The GitHub Actions workflow runs Python compilation and both test groups on pushes and pull requests to the main branch. These software checks do not represent Raspberry Pi 5 performance measurements or physical camera/conveyor commissioning.
