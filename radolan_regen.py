#!/usr/bin/env python3
"""
radolan_regen.py  --  Tagesniederschlag fuer Lutz' Standort (Erlental, Wettenberg)
aus DWD RADOLAN-RW (1 km, stationsgeeicht), bilinear interpoliert.

Schreibt radolan.json fuer die Wetter-App. Laeuft stuendlich per GitHub-Action.
Kein pyproj noetig: Pixel + Gewichte sind vorab fest geeicht (siehe unten).
"""
import gzip, json, sys, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np

# --- Feste Eichung fuer Standort 50.6479651 N, 8.6740943 E (Erlental) ---
# Bilineare 4-Pixel-Gewichtung im RADOLAN-900x900-Gitter (row = Sued->Nord, col = West->Ost).
# Verifiziert: Projektion gegen DWD-Benchmark (0.3 µ°), Lage 395 m vom Pixelzentrum, Orientierung an echter Karte.
PIXELS = [  # (row, col, gewicht)
    (409, 425, 0.522),
    (409, 424, 0.334),
    (408, 425, 0.088),
    (408, 424, 0.056),
]
NROW = NCOL = 900
BASE = "https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/radolan/recent/bin/"
TZ   = ZoneInfo("Europe/Berlin")
UA   = {"User-Agent": "wetter-giessen-radolan/1.0 (GitHub Action)"}

def fetch_rw(dt_utc):
    """Holt + entpackt die RW-Datei mit Endzeitstempel dt_utc (volle Stunde, UTC)."""
    name = f"raa01-rw_10000-{dt_utc:%y%m%d%H%M}-dwd---bin.gz"
    req  = urllib.request.Request(BASE + name, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return gzip.decompress(r.read())

def bilinear_mm(raw):
    """Parst RADOLAN-Binaer und gibt den bilinear interpolierten Wert (mm) am Standort."""
    etx  = raw.index(0x03)                       # Header endet mit ETX
    body = raw[etx + 1 : etx + 1 + NROW * NCOL * 2]
    data = np.frombuffer(body, dtype="<u2").reshape(NROW, NCOL)
    nod  = (data & 0x2000) != 0                  # Fehlkennung (ausserhalb Radar)
    mm   = np.where(nod, np.nan, (data & 0x0FFF) * 0.1)   # untere 12 Bit = 0.1 mm
    val = 0.0
    for r, c, w in PIXELS:
        v = mm[r, c]
        val += w * (0.0 if np.isnan(v) else float(v))
    return val

def main():
    now_utc        = datetime.now(timezone.utc)
    midnight_local = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc      = midnight_local.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    last_full      = now_utc.replace(minute=0, second=0, microsecond=0)

    # nicht-ueberlappende Stundensummen: Endzeiten start+1h ... jetzt
    hours, t = [], start_utc + timedelta(hours=1)
    while t <= last_full:
        hours.append(t); t += timedelta(hours=1)

    total, ok, details = 0.0, 0, []
    for h in hours:
        lbl = h.astimezone(TZ).strftime("%H:%M")
        try:
            v = bilinear_mm(fetch_rw(h))
            total += v; ok += 1
            details.append({"stunde": lbl, "mm": round(v, 2)})
        except urllib.error.HTTPError as e:
            if e.code == 404:                    # Datei noch nicht da (Latenz) -> still ueberspringen
                details.append({"stunde": lbl, "mm": None, "status": "noch nicht verfuegbar"})
            else:
                details.append({"stunde": lbl, "mm": None, "fehler": f"HTTP {e.code}"})
        except Exception as e:
            details.append({"stunde": lbl, "mm": None, "fehler": str(e)[:80]})

    out = {
        "datum":             midnight_local.strftime("%Y-%m-%d"),
        "summe_mm":          round(total, 2),
        "stunden_ok":        ok,
        "stunden_erwartet":  len(hours),
        "stunden":           details,
        "aktualisiert":      now_utc.isoformat(timespec="seconds"),
        "quelle":            "DWD RADOLAN-RW (1 km, stationsgeeicht)",
        "methode":           "bilinear, Erlental 50.6480N 8.6741E",
    }
    with open("radolan.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
