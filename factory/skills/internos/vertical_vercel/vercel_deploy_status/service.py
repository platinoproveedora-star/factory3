from __future__ import annotations
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import _vercel_client as vc

_TERMINAL = {"READY", "ERROR", "CANCELED"}
_MAX_WAIT  = 180   # segundos
_INTERVAL  = 6


class VercelDeployStatusService:
    def ejecutar(self, ctx: dict) -> dict:
        deployment_id = ctx.get("deployment_id", "")
        wait          = ctx.get("wait", False)

        if not deployment_id:
            return {"ok": False, "error": "deployment_id requerido"}

        start = time.time()

        while True:
            r = vc.get(f"/v13/deployments/{deployment_id}")
            if not r["ok"]:
                return r

            d     = r["data"]
            state = d.get("readyState", "UNKNOWN")
            url   = f"https://{d.get('url', '')}"

            if state in _TERMINAL or not wait:
                elapsed = round(time.time() - start)
                return {"ok": True, "data": {
                    "state":      state,
                    "url":        url,
                    "elapsed_s":  elapsed,
                    "ready":      state == "READY",
                    "error_msg":  d.get("errorMessage") if state == "ERROR" else None,
                }}

            if time.time() - start > _MAX_WAIT:
                return {"ok": False, "error": f"Timeout {_MAX_WAIT}s — estado actual: {state}"}

            time.sleep(_INTERVAL)
