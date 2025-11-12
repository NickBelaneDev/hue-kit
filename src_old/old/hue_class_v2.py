import os, time, warnings, random
from typing import Iterable, Optional
import requests
from dotenv import load_dotenv, find_dotenv

warnings.filterwarnings("ignore")
load_dotenv(find_dotenv())

class HueGroup:
    def __init__(self, group_hint: str, bridge_ip: Optional[str]=None, app_key: Optional[str]=None, timeout_s: float=5.0):
        self.bridge_ip = bridge_ip or os.getenv("HUE_BRIDGE_IP")
        self.app_key   = app_key   or os.getenv("APP_KEY")
        if not self.bridge_ip or not self.app_key:
            raise ValueError("HUE_BRIDGE_IP oder APP_KEY fehlt.")
        self.timeout_s = timeout_s
        self.base  = f"https://{self.bridge_ip}/clip/v2/resource"

        # PERSISTENTE SESSION (Keep-Alive)
        self.session = requests.Session()
        self.session.headers.update({"hue-application-key": self.app_key})

        self.group_hint = group_hint
        self.grouped_light_id = self._resolve_grouped_light_id(group_hint)
        #self.grouped_light_id = "02089710-e819-47ea-a324-9b15efb6092e"
        # Debounce-Cache
        self._last_on: Optional[bool] = None
        self._last_bri: Optional[float] = None

    # ---- HTTP helpers
    def _get(self, path: str) -> dict:
        r = self.session.get(f"{self.base}/{path}", timeout=self.timeout_s, verify=False)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, payload: dict) -> None:
        r = self.session.put(f"{self.base}/{path}", json=payload, timeout=self.timeout_s, verify=False)
        r.raise_for_status()

    # ---- Resolve grouped_light
    def _resolve_grouped_light_id(self, hint: str) -> str:
        needle = hint.lower().strip()
        gl_data = self._get("grouped_light").get("data", [])

        for gl in gl_data:
            name = (gl.get("metadata", {}).get("name") or "").strip()
            if needle in name.lower():
                return gl["id"]

        owners = []
        for rtype in ("room", "zone"):
            for res in self._get(rtype).get("data", []):
                rname = (res.get("metadata", {}).get("name") or "").strip()

                if needle in rname.lower():
                    owners.append((rtype, res["id"]))

        if owners:
            owner_rtype, owner_id = owners[0]
            for gl in gl_data:
                owner = gl.get("owner") or {}

                if owner.get("rid") == owner_id and owner.get("rtype") == owner_rtype:
                    return gl["id"]

        raise RuntimeError(f"Kein grouped_light zu '{hint}' gefunden.")

    # ---- Primitive Setter (mit Debounce)
    def set_on(self, on: bool, duration_ms: Optional[int]=None) -> None:
        if self._last_on is not None and self._last_on == bool(on) and duration_ms is None:
            return  # Debounce

        payload = {"on": {"on": bool(on)}}

        if duration_ms is not None:
            payload["dynamics"] = {"duration": int(duration_ms)}

        self._put(f"grouped_light/{self.grouped_light_id}", payload)
        self._last_on = bool(on)

    def set_brightness(self, percent: float, duration_ms: Optional[int]=None, eps: float=0.05) -> None:
        p = max(1.0, min(100.0, float(percent)))

        if self._last_bri is not None and abs(self._last_bri - p) <= eps and duration_ms is None:
            return  # Debounce

        payload = {"dimming": {"brightness": p}}

        if duration_ms is not None:
            payload["dynamics"] = {"duration": int(duration_ms)}

        self._put(f"grouped_light/{self.grouped_light_id}", payload)
        self._last_bri = p

    def set_color_temperature(self, mirek: int, duration_ms: Optional[int]=None) -> None:
        m = max(100, min(6500, int(mirek)))
        payload = {"color_temperature": {"mirek": m}}

        if duration_ms is not None:
            payload["dynamics"] = {"duration": int(duration_ms)}

        self._put(f"grouped_light/{self.grouped_light_id}", payload)

    def set_xy(self, x: float, y: float, duration_ms: Optional[int]=None) -> None:
        xf, yf = max(0.0, min(1.0, float(x))), max(0.0, min(1.0, float(y)))
        payload = {"color": {"xy": {"x": xf, "y": yf}}}

        if duration_ms is not None:
            payload["dynamics"] = {"duration": int(duration_ms)}

        self._put(f"grouped_light/{self.grouped_light_id}", payload)

    def turn_on(self, brightness_pct: float=100.0, duration_ms: Optional[int]=None) -> None:
        self.set_on(True, duration_ms=duration_ms)
        self.set_brightness(brightness_pct, duration_ms=duration_ms)

    def turn_off(self, duration_ms: Optional[int]=None) -> None:
        self.set_on(False, duration_ms=duration_ms)


    # -------- Effekte --------
    def pulse_brightness(self, period_s: float, repetitions: int,
                         low_pct: float = 10.0, high_pct: float = 100.0,
                         ramp_ms: Optional[int] = 0, keep_on: bool = True,
                         max_rps: Optional[float] = None) -> None:
        """
        Overrun-sichere Version:
        - Frames droppen bei Überlauf
        - (optional) weiches RPS-Limit über min_sleep
        """
        # Ramp nicht zu groß wählen (Überschneidungen vermeiden)
        if ramp_ms and ramp_ms > period_s * 500:  # >50% der Periode
            ramp_ms = int(period_s * 300)  # z.B. auf 30% kappen

        # Optionales RPS-Limit (zusätzlich zur Periodik)
        min_sleep = (1.0 / max_rps) if max_rps and max_rps > 0 else 0.0

        self.set_on(True, duration_ms=ramp_ms)
        self.set_brightness(high_pct, duration_ms=ramp_ms)

        bright = True
        t_next = time.perf_counter()

        for _ in range(int(repetitions)):
            # Zielwert berechnen
            bright = not bright
            target = high_pct if bright else low_pct

            # --- Request senden
            start = time.perf_counter()
            self.set_brightness(target, duration_ms=ramp_ms)
            req_time = time.perf_counter() - start

            # --- Takt weiterschieben
            t_next += period_s
            now = time.perf_counter()
            dt = t_next - now

            if dt > 0:
                # RPS-Limit respektieren (falls gesetzt)
                if min_sleep > 0 and dt < min_sleep:
                    extra = min_sleep - dt
                    # nur schlafen wenn es hilft, sonst normal warten
                    time.sleep(dt + extra)
                else:
                    time.sleep(dt)
            else:
                # OVERrun: Frames droppen und Slot vorspulen
                missed = int((-dt) // period_s) + 1
                t_next += missed * period_s
                # Kein zusätzliches sleep -> wir sind bereits zu spät
                # (nächster Schritt wird zeitlich korrekt anvisiert)

if __name__ == "__main__":
    hue = HueGroup("BackLights")

    # Dein Random-Muster als Generator:
    # deaktivieren
    #hue._put("behavior_instance/a6986bf9-3116-4da3-ab9f-b640ad319387", {"enabled": False})
    # ... pulse fahren ...
    # wieder aktivieren (falls gewünscht)

    hue.pulse_brightness(period_s=0.300, repetitions=12, ramp_ms=10)
    #hue._put("behavior_instance/a6986bf9-3116-4da3-ab9f-b640ad319387", {"enabled": True})