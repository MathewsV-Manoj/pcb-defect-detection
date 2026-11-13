"""Publish completed inspection events directly from the Pi to Firebase RTDB."""
from __future__ import annotations
import json, os, urllib.error, urllib.parse, urllib.request

def _url(path):
    base = os.environ.get("FIREBASE_DATABASE_URL","").strip().rstrip("/")
    if not base.startswith("https://"):
        raise RuntimeError("Set FIREBASE_DATABASE_URL to the HTTPS Realtime Database URL")
    url = f"{base}/{path.strip('/')}.json"
    token = os.environ.get("FIREBASE_AUTH_TOKEN")
    if token: url += "?" + urllib.parse.urlencode({"auth":token})
    return url

def _put(path,payload):
    req = urllib.request.Request(_url(path),data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json"},method="PUT")
    try:
        with urllib.request.urlopen(req,timeout=15) as res:
            if res.status not in (200,201): raise RuntimeError(f"Firebase HTTP {res.status}")
            res.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Firebase HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Firebase network error: {exc}") from exc

def publish_event(event):
    required={"record_id","board_id","timestamp","decision","source","detections"}
    missing=required.difference(event)
    if missing: raise ValueError(f"Missing event fields: {sorted(missing)}")
    key=urllib.parse.quote(str(event["record_id"]),safe="-_.")
    _put(f"inspections/{key}",event)
    _put("live",{
        "status":"inspection_complete","board_id":event["board_id"],
        "camera_status":"CONNECTED" if event["source"]=="LIVE" else "NOT_CONNECTED",
        "decision":event["decision"],"detections":event["detections"],
        "advisory":event.get("advisory"),"inference_latency_ms":event.get("inference_latency_ms"),
        "device_status":"Raspberry Pi 5","source":event["source"],"timestamp":event["timestamp"]
    })
