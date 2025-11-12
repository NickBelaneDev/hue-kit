import requests
import time
import warnings
import os
warnings.filterwarnings("ignore")  # self-signed TLS der Bridge
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

APP_KEY = os.getenv("APP_KEY")
HUE_BRIDGE_IP = os.getenv("HUE_BRIDGE_IP")

HEADERS = {"hue-application-key": APP_KEY}
BASE    = f"https://{HUE_BRIDGE_IP}/clip/v2/resource"

def _get(path: str) -> dict:
    r = requests.get(f"{BASE}/{path}", headers=HEADERS, timeout=5, verify=False)
    r.raise_for_status()
    return r.json()

def _put(path: str, payload: dict) -> None:
    r = requests.put(f"{BASE}/{path}", headers=HEADERS, json=payload, timeout=5, verify=False)
    r.raise_for_status()

def list_grouped_lights() -> list[dict]:
    """Hilfsfunktion: gib alle grouped_lights zurück (für Debug-Ausgaben)."""
    return _get("grouped_light").get("data", [])

def find_grouped_light_id_by_name_or_owner(name_substring: str) -> str:
    """
    1) Direkter Treffer über grouped_light.metadata.name (v2-Name)
    2) Fallback: Suche room/zone mit Name enthält <substring>, dann nimm grouped_light mit owner.rid == room/zone.id
    """
    needle = name_substring.lower()

    # 1) Direkt im grouped_light-Namen suchen
    gl_data = list_grouped_lights()
    for gl in gl_data:
        meta = gl.get("metadata", {}) or {}
        name = (meta.get("name") or "").strip()
        if needle in name.lower():
            return gl["id"]

    # 2) Fallback über owner: room/zone mit Namen suchen
    owners = []
    for rtype in ("room", "zone"):
        for res in _get(rtype).get("data", []):
            rname = (res.get("metadata", {}).get("name") or "").strip()
            if needle in rname.lower():
                owners.append((rtype, res["id"], rname))

    if owners:
        # nimm den ersten passenden Owner und mappe zu grouped_light.owner.rid
        owner_rtype, owner_id, owner_name = owners[0]
        for gl in gl_data:
            owner = gl.get("owner") or {}
            if owner.get("rid") == owner_id and owner.get("rtype") == owner_rtype:
                return gl["id"]

    # Diagnose: zeig, was es gibt
    names_gl = [gl.get("metadata", {}).get("name", f"<ohne Name>") for gl in gl_data]
    rooms = [(r.get("metadata", {}).get("name",""), r["id"]) for r in _get("room").get("data",[])]
    zones = [(z.get("metadata", {}).get("name",""), z["id"]) for z in _get("zone").get("data",[])]
    print(names_gl)
    raise RuntimeError(
        "Kein passendes grouped_light gefunden.\n"
        f"Gesucht: '{name_substring}'\n"
        f"Vorhandene grouped_light Namen: {names_gl}\n"
        f"Vorhandene Rooms: {rooms}\n"
        f"Vorhandene Zones: {zones}"
    )

def set_group_on(grouped_light_id: str, on: bool, duration_ms: int | None = None):
    payload = {"on": {"on": on}}
    if duration_ms is not None:
        payload["dynamics"] = {"duration": int(duration_ms)}
    _put(f"grouped_light/{grouped_light_id}", payload)

def set_group_brightness(grouped_light_id: str, percent: float, duration_ms: int | None = None):
    percent = max(1.0, min(100.0, float(percent)))
    payload = {"dimming": {"brightness": percent}}
    if duration_ms is not None:
        payload["dynamics"] = {"duration": int(duration_ms)}
    _put(f"grouped_light/{grouped_light_id}", payload)

def pulse_brightness(name_substring: str, period_s: float, repetitions: int,
                     low_pct: float = 10.0, high_pct: float = 100.0,
                     ramp_ms: int | None = 0, keep_on: bool = True):
    gid = find_grouped_light_id_by_name_or_owner(name_substring)

    # Startzustand: an + hell
    #set_group_on(gid, True, duration_ms=ramp_ms)
    set_group_brightness(gid, high_pct, duration_ms=ramp_ms)

    bright = True
    t_next = time.perf_counter()

    for _ in range(repetitions):
        bright = not bright
        target = high_pct if bright else low_pct
        set_group_brightness(gid, target, duration_ms=ramp_ms)

        t_next += period_s
        dt = t_next - time.perf_counter()
        if dt > 0:
            time.sleep(dt)

    if keep_on:
        set_group_brightness(gid, high_pct, duration_ms=ramp_ms)
        set_group_on(gid, True, duration_ms=ramp_ms)


# Beispiel-Aufruf:
pulse_brightness("Sim", period_s=0.2, repetitions=5, low_pct=5.0, high_pct=100.0, ramp_ms=5)

#blink_grouped("Sim", period_s=1, repetitions=10, ramp_ms=0)  # ramp_ms optional: weiche Übergänge
list_grouped_lights()