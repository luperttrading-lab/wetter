#!/usr/bin/env python3
"""
radolan_regen.py  --  Tagesniederschlag fuer Lutz' Standort (Erlental, Wettenberg)
aus DWD RADOLAN-RW (1 km, stationsgeeicht), bilinear interpoliert.

Schreibt radolan.json fuer die Wetter-App. Laeuft stuendlich per GitHub-Action.
Zusatz (v1.1): schreibt die Tagessummen des 3x3-Kranzes um den eigenen Pixel mit,
zur Pruefung, wie stark die Nachbarkacheln abweichen.
Zusatz (v1.2): schreibt radolan.json nur, wenn mindestens eine echte Radar-Stunde
geholt wurde. Verhindert, dass ein Lauf ohne Daten (z.B. kurz nach lokaler
Mitternacht, bevor die ersten RW-Bilder des Tages existieren) die guten
Vortagsdaten mit einer leeren Datei ueberschreibt.
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
UA   = {"User-Agent": "wetter-giessen-radolan/1.2 (GitHub Action)"}

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

ARCHIV = "radolan-archiv.json"                      # v1.3: Tagessummen-Archiv

def tagessumme(midnight_local_day):
    """Vollstaendige Tagessumme eines lokalen Tages: Stunden 01:00..24:00.
    Die 24. Stunde liegt im RW-Bild um 00:00 des Folgetages - genau die, die der
    letzte Lauf des Tages (23:35) noch nicht kennen kann."""
    start_utc = midnight_local_day.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    total, ok = 0.0, 0
    for i in range(1, 25):
        try:
            mm = parse_mm(fetch_rw(start_utc + timedelta(hours=i)))
            total += sum(w * val(mm, r, c) for r, c, w in PIXELS)
            ok += 1
        except Exception:
            pass
    return round(total, 2), ok

def archiv_laden():
    try:
        with open(ARCHIV, "r", encoding="utf-8") as f:
            a = json.load(f)
        t = a.get("tage")
        return t if isinstance(t, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, ValueError, AttributeError):
        return {}

def archiv_schreiben(tage, stand):
    with open(ARCHIV, "w", encoding="utf-8") as f:
        json.dump({"quelle": "DWD RADOLAN-RW (1 km, stationsgeeicht)",
                   "ort": "Erlental 50.6480N 8.6741E",
                   "aktualisiert": stand,
                   "tage": dict(sorted(tage.items()))}, f, ensure_ascii=False, indent=1)

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

    # --- Schutz gegen leere Ueberschreibung (v1.2) ---
    # Wenn keine einzige Stunde echte Radar-Daten geliefert hat, die bestehende
    # radolan.json NICHT anfassen. Das passiert v.a. beim naechtlichen Lauf
    # (00:35 MESZ), wenn fuer den neuen lokalen Tag noch keine RW-Bilder existieren:
    # dann waere hours leer bzw. alle Abrufe 404, und eine leere Datei
    # (summe_mm=0, stunden_erwartet=0) wuerde die guten Vortagsdaten ersetzen.
    if ok == 0:
        print(f"Keine Radar-Stunde geholt (erwartet {len(hours)}, ok 0) "
              f"- radolan.json bleibt unveraendert.")
        return

    umgebung = [[{"pixel": [r, c], "mm": round(kranz[(r, c)], 2), "eigenes": (r, c) == HOME}
                 for c in KRANZ_COLS] for r in KRANZ_ROWS]

    # --- letzten Tag mit Regen merken (vor dem Ueberschreiben altes JSON lesen) ---
    # So bleibt die Info erhalten, auch wenn heute trocken ist und das JSON ueberschrieben wird.
    heute_str = midnight_local.strftime("%Y-%m-%d")
    summe     = round(total, 2)
    letzter_regen = None
    try:
        with open("radolan.json", "r", encoding="utf-8") as f:
            alt = json.load(f)
        lr = alt.get("letzter_regen")
        if isinstance(lr, dict) and lr.get("mm", 0) > 0 and lr.get("datum"):
            letzter_regen = {"datum": lr["datum"], "mm": round(float(lr["mm"]), 2)}
        # der zuletzt geschriebene Tag selbst war ein Regentag? -> Kandidat
        if alt.get("summe_mm", 0) > 0 and alt.get("datum"):
            kand = {"datum": alt["datum"], "mm": round(float(alt["summe_mm"]), 2)}
            if letzter_regen is None or kand["datum"] >= letzter_regen["datum"]:
                letzter_regen = kand
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        pass
    # heutiger Regen hat Vorrang
    if summe > 0:
        letzter_regen = {"datum": heute_str, "mm": summe}

    out = {
        "datum":            heute_str,
        "summe_mm":         summe,
        "stunden_ok":       ok,
        "stunden_erwartet": len(hours),
        "stunden":          details,
        "umgebung_3x3":     umgebung,
        "letzter_regen":    letzter_regen,
        "aktualisiert":     now_utc.isoformat(timespec="seconds"),
        "quelle":           "DWD RADOLAN-RW (1 km, stationsgeeicht)",
        "methode":          "bilinear, Erlental 50.6480N 8.6741E",
    }
    with open("radolan.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))

    # --- Tagessummen-Archiv (v1.3) -------------------------------------------
    # Heutiger Zwischenstand wird bei jedem Lauf ueberschrieben (idempotent).
    # Der Vortag wird einmalig komplett nachgerechnet, weil ihm sonst die
    # Stunde 23-24 fehlt; nach spaetestens 3 Versuchen wird er so akzeptiert,
    # wie er ist, damit dauerhaft fehlende RW-Bilder keine Endlosversuche ausloesen.
    tage = archiv_laden()
    tage[heute_str] = {"mm": summe, "h": ok, "voll": False}
    gestern  = midnight_local - timedelta(days=1)
    g_str    = gestern.strftime("%Y-%m-%d")
    g_eintr  = tage.get(g_str, {})
    if not g_eintr.get("voll") and g_eintr.get("v", 0) < 3:
        g_mm, g_ok = tagessumme(gestern)
        if g_ok > 0:
            tage[g_str] = {"mm": g_mm, "h": g_ok, "voll": g_ok >= 24,
                           "v": g_eintr.get("v", 0) + 1}
            print(f"Archiv: {g_str} finalisiert -> {g_mm} mm ({g_ok}/24 Stunden)")
    archiv_schreiben(tage, now_utc.isoformat(timespec="seconds"))
    print(f"Archiv: {len(tage)} Tage gespeichert.")

if __name__ == "__main__":
    main()
