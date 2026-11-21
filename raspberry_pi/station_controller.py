#!/usr/bin/env python3
"""IR-triggered, single-board capture controller for the Raspberry Pi 5 station.

The GPIO assignments are supplied by the installation environment. The LED
GPIO switches an external MOSFET/relay driver; it must not power the LED strip.
This process does not control the conveyor motor.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSPECTION = ROOT / "raspberry_pi" / "run_inspection.py"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def required_gpio(name: str) -> int:
    raw = os.getenv(name, "").strip()
    if not raw.isdigit():
        raise RuntimeError(f"{name} must be set to the BCM GPIO number used by the actual wiring")
    pin = int(raw)
    if not 0 <= pin <= 27:
        raise RuntimeError(f"{name} must be a BCM GPIO in the range 0..27")
    return pin


def main() -> int:
    try:
        from gpiozero import Button, OutputDevice
    except ImportError:
        print(
            "gpiozero is required on Raspberry Pi OS. Install the Raspberry Pi OS "
            "python3-gpiozero package or add gpiozero to the active environment.",
            file=sys.stderr,
        )
        return 2

    if not INSPECTION.is_file():
        print(f"Inspection coordinator not found: {INSPECTION}", file=sys.stderr)
        return 2

    ir_pin = required_gpio("PCB_IR_GPIO")
    led_pin = required_gpio("PCB_LED_DRIVER_GPIO")
    if ir_pin == led_pin:
        raise RuntimeError("IR sensor and LED driver must use different GPIO pins")

    ir_active_low = env_bool("PCB_IR_ACTIVE_LOW", True)
    ir_pull_up = os.getenv("PCB_IR_PULL_UP", "off").strip().lower()
    pull_up = True if ir_pull_up == "on" else False if ir_pull_up == "off" else None
    led_active_high = not env_bool("PCB_LED_DRIVER_ACTIVE_LOW", False)

    camera_mode = os.getenv("PCB_CAMERA_MODE", "usb").strip().lower()
    if camera_mode not in {"usb", "picamera2"}:
        raise RuntimeError("PCB_CAMERA_MODE must be 'usb' or 'picamera2'")
    camera_index = os.getenv("PCB_CAMERA_INDEX", "0").strip()
    model_path = os.getenv("PCB_MODEL_PATH", "models/best.onnx").strip()
    output_dir = Path(os.getenv("PCB_OUTPUT_DIR", "inspection_runs")).expanduser()
    output_dir = output_dir if output_dir.is_absolute() else ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    settle = float(os.getenv("PCB_ILLUMINATION_SETTLE_SECONDS", "0.35"))
    cooldown = float(os.getenv("PCB_TRIGGER_COOLDOWN_SECONDS", "1.5"))
    confidence = os.getenv("PCB_CONFIDENCE_THRESHOLD", "0.25")
    iou = os.getenv("PCB_NMS_IOU_THRESHOLD", "0.45")
    publish = env_bool("PCB_FIREBASE_PUBLISH", False)

    if settle < 0 or cooldown < 0:
        raise RuntimeError("Illumination settle and trigger cooldown must be non-negative")

    active_state = not ir_active_low
    sensor = Button(
        ir_pin,
        pull_up=pull_up,
        active_state=active_state,
        bounce_time=0.12,
    )
    illumination = OutputDevice(
        led_pin,
        active_high=led_active_high,
        initial_value=False,
    )

    state_lock = threading.Lock()
    state = {"busy": False, "last_trigger": 0.0}

    def inspect_arrival() -> None:
        with state_lock:
            now_mono = time.monotonic()
            if state["busy"] or now_mono - state["last_trigger"] < cooldown:
                return
            state["busy"] = True
            state["last_trigger"] = now_mono

        board_id = "PCB-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-%f")
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", board_id)
        annotated = output_dir / f"{safe_id}_annotated.jpg"
        event_file = output_dir / f"{safe_id}.json"

        env = os.environ.copy()
        env["PCB_IR_SENSOR_STATUS"] = "TRIGGERED"
        env["PCB_ILLUMINATION_STATUS"] = "ON"
        command = [
            sys.executable,
            str(INSPECTION),
            "--weights", str((ROOT / model_path).resolve() if not Path(model_path).is_absolute() else Path(model_path)),
            "--board-id", board_id,
            "--conf", confidence,
            "--iou", iou,
            "--output", str(event_file),
            "--annotated", str(annotated),
        ]
        if camera_mode == "picamera2":
            command.append("--picamera2")
        else:
            if not camera_index.isdigit():
                print("PCB_CAMERA_INDEX must be a non-negative integer", file=sys.stderr)
                with state_lock:
                    state["busy"] = False
                return
            command.extend(["--camera", camera_index])
        if publish:
            command.append("--publish")

        print(f"[station] PCB arrival detected: {board_id}", flush=True)
        try:
            illumination.on()
            time.sleep(settle)
            completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
            if completed.returncode == 0:
                print(f"[station] Inspection event saved: {event_file}", flush=True)
            else:
                print(
                    f"[station] Inspection process returned code {completed.returncode}",
                    file=sys.stderr,
                    flush=True,
                )
        except Exception as exc:
            print(f"[station] Inspection failed: {exc}", file=sys.stderr, flush=True)
        finally:
            illumination.off()
            with state_lock:
                state["busy"] = False

    sensor.when_pressed = inspect_arrival
    illumination.off()

    print(
        "[station] Waiting for IR board-arrival events. "
        f"IR BCM GPIO={ir_pin}, LED-driver BCM GPIO={led_pin}, camera={camera_mode}.",
        flush=True,
    )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[station] Stopping station controller.", flush=True)
    finally:
        sensor.close()
        illumination.off()
        illumination.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
