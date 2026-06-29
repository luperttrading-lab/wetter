#!/usr/bin/env python3
"""
radolan_regen.py  --  Tagesniederschlag fuer Lutz' Standort (Erlental, Wettenberg)
aus DWD RADOLAN-RW (1 km, stationsgeeicht), bilinear interpoliert.

Schreibt radolan.json fuer die Wetter-App. Laeuft stuendlich per GitHub-Action.
Zusatz (v1.1): schreibt die Tagessummen des 3x3-Kranzes um den eigenen Pixel mit,
zur Pruefung, wie stark die Nachbarkacheln abweichen.
"""
import gzip, json, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np

# --- Feste Eichung fuer Standort 50.6479651 N, 8.6740943 E (Erlental) ---
PIXELS = [  # bilineare 4-Pixel-Gewichtung (row, col, gewicht)
    (409, 425, 0.522),
    (409, 424, 0.334),
    (408, 425, 0.088),
    (408, 424, 0.056),
]
HOME = (409, 425)                                  # eigenes Pixel (Mitte des Kranzes)
KRANZ_ROWS = (410, 409, 408)                        # Nord -> Sued (oben = Nord)
KRANZ_COLS = (424, 425, 426)                        # West -> Ost
NROW = NCOL = 900
BASE = "https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/radolan/recent/bin/"
TZ   = ZoneInfo("Europe/Berlin")
UA   = {"User-Agent": "wetter-giessen-radolan/1.1 (GitHub Action)"}

def fetch_rw(dt_utc):
    name = f"raa01-rw_10000-{dt_utc:%y%m%d%H%M}-dwd---bin.gz"
    req  = urllib.request.Request(BASE + name, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return gzip.decompress(r.read())

def parse_mm(raw):
    etx  = raw.index(0x03)
    body = raw[etx + 1 : etx + 1 + NROW * NCOL * 2]
    data = np.frombuffer(body, dtype="<u2").reshape(NROW, NCOL)
    nod  = (data & 0x2000) != 0
    return np.where(nod, np.nan, (data & 0x0FFF) * 0.1)

def val(mm, r, c):
    v = mm[r, c]
    return 0.0 if np.isnan(v) else float(v)

def main():
    now_utc        = datetime.now(timezone.utc)
    midnight_local = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc      = midnight_local.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    last_full      = now_utc.replace(minute=0, second=0, microsecond=0)

    hours, t = [], start_utc + timedelta(hours=1)
    while t <= last_full:
        hours.append(t); t += timedelta(hours=1)

    total, ok, details = 0.0, 0, []
    kranz = {(r, c): 0.0 for r in KRANZ_ROWS for c in KRANZ_COLS}

    for h in hours:
        lbl = h.astimezone(TZ).strftime("%H:%M")
        try:
            mm = parse_mm(fetch_rw(h))
            v  = sum(w * val(mm, r, c) for r, c, w in PIXELS)
            total += v; ok += 1
            for (r, c) in kranz:
                kranz[(r, c)] += val(mm, r, c)
            details.append({"stunde": lbl, "mm": round(v, 2)})
        except urllib.error.HTTPError as e:
            details.append({"stunde": lbl, "mm": None,
                            "status": "noch nicht verfuegbar" if e.code == 404 else f"HTTP {e.code}"})
        except Exception as e:
            details.append({"stunde": lbl, "mm": None, "fehler": str(e)[:80]})

    umgebung = [[{"pixel": [r, c], "mm": round(kranz[(r, c)], 2), "eigenes": (r, c) == HOME}
                 for c in KRANZ_COLS] for r in KRANZ_ROWS]

    out = {
        "datum":            midnight_local.strftime("%Y-%m-%d"),
        "summe_mm":         round(total, 2),
        "stunden_ok":       ok,
        "stunden_erwartet": len(hours),
        "stunden":          details,
        "umgebung_3x3":     umgebung,
        "aktualisiert":     now_utc.isoformat(timespec="seconds"),
        "quelle":           "DWD RADOLAN-RW (1 km, stationsgeeicht)",
        "methode":          "bilinear, Erlental 50.6480N 8.6741E",
    }
    with open("radolan.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
