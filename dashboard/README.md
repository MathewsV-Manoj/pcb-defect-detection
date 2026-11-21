# Pi-hosted operator dashboard

The operator dashboard is served by `raspberry_pi/station_controller.py` from this directory. It is accessed remotely from a laptop browser using the Raspberry Pi's IP address and configured HTTP port.

## Operator sequence

1. Hold a hand in front of the IR sensor for approximately three seconds to arm the station.
2. Release the sensor and place the PCB on the conveyor.
3. The conveyor transports the board to the camera position.
4. The IR input's next active transition triggers illumination and image capture.
5. The Pi serves the captured image to the browser for verification.
6. The operator selects **Run inspection on Raspberry Pi**.
7. The browser sends `POST /api/run-inspection` to the Pi.
8. The Pi runs OpenCV/YOLO and the separate Llama/ExecuTorch advisory; the page displays the returned status and event data.

## Browser-to-Pi API

- `GET /api/status` — live station, capture and inference state.
- `GET /api/capture.jpg` — captured frame for operator review.
- `GET /api/annotated.jpg` — annotated detector output.
- `GET /api/history` — recent local JSON inspection events.
- `POST /api/run-inspection` — starts the Pi-side inspection process.

The dashboard does not perform inference in the browser. It is an operator console for the Raspberry Pi's local camera, vision and advisory processes. Use it only over a trusted private network.

Firebase Realtime Database is optional for synchronizing completed records; the local run button and image preview use the Pi-hosted API directly.
