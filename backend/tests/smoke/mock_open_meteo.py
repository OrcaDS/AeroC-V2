from __future__ import annotations

import json
import os
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import parse_qs, urlparse


SUCCESS_TIMESTAMP = 1_784_347_200
SECOND_TIMESTAMP = SUCCESS_TIMESTAMP + 3600
FAILED_LATITUDE = "-6.917500"
POLLUTANTS = (
    "pm2_5",
    "pm10",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
)


class State:
    def __init__(self) -> None:
        self.mode = "success"
        self.requests = Counter()
        self.lock = Lock()


STATE = State()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {"status": "ok", "mode": STATE.mode})
            return
        if parsed.path == "/stats":
            with STATE.lock:
                payload = {"mode": STATE.mode, "requests": dict(STATE.requests)}
            self._json(200, payload)
            return
        if parsed.path != "/v1/air-quality":
            self._json(404, {"error": "not_found"})
            return

        params = parse_qs(parsed.query)
        latitude = f"{float(params['latitude'][0]):.6f}"
        with STATE.lock:
            STATE.requests[f"{STATE.mode}:{latitude}"] += 1
            mode = STATE.mode

        if mode == "partial" and latitude == FAILED_LATITUDE:
            self._json(503, {"error": "deterministic_partial_failure"})
            return

        timestamp = SUCCESS_TIMESTAMP if mode == "success" else SECOND_TIMESTAMP
        hourly = {"time": [timestamp]}
        units = {}
        for index, pollutant in enumerate(POLLUTANTS, start=1):
            hourly[pollutant] = [float(index * 10)]
            units[pollutant] = "μg/m³"

        self._json(
            200,
            {
                "hourly": hourly,
                "hourly_units": units,
            },
        )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/control":
            self._json(404, {"error": "not_found"})
            return
        mode = parse_qs(parsed.query).get("mode", [None])[0]
        if mode not in {"success", "partial", "recovery"}:
            self._json(400, {"error": "invalid_mode"})
            return
        with STATE.lock:
            STATE.mode = mode
        self._json(200, {"mode": mode})

    def log_message(self, format: str, *args) -> None:
        return

    def _json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    port = int(os.environ.get("MOCK_OPEN_METEO_PORT", "8081"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
