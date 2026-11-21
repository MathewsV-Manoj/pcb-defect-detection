# Operator page

The Pi serves index.html from raspberry_pi/station_controller.py. Open the Pi's address from a laptop on the same private network.

## Using the page

1. Arm the station once with a three-second hand hold in front of the IR sensor.
2. Release the sensor and load a PCB onto the conveyor.
3. When the board reaches the IR trigger point, the Pi turns on the LED driver and captures a frame.
4. Check the image shown on the page.
5. Press **Run inspection on Raspberry Pi**.
6. The Pi runs the detector and advisory, then updates the page with the result.

The station remains armed for the next PCB until the controller is restarted.

## API routes

- GET /api/status — station, sensor, capture and inference state.
- GET /api/capture.jpg — raw captured frame.
- GET /api/annotated.jpg — detector output.
- GET /api/history — recent local event records.
- POST /api/run-inspection — starts processing on the Pi.

The browser only displays information and sends the run request. It does not load model weights or run inference. Firebase is optional; the page uses the Pi API for capture and inspection.
