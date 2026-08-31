#!/usr/bin/env python3
"""
radolan_regen.py  --  Tagesniederschlag aus DWD RADOLAN-RW (1 km, stationsgeeicht),
bilinear interpoliert. Schreibt radolan.json fuer die Wetter-App.

v2.0: MEHRERE ORTE. Bisher war genau ein Punkt (Erlental) mit handkalibrierten
Pixelgewichten fest verdrahtet. Jetzt steht in ORTE eine Liste, die Gewichte
werden aus der RADOLAN-Projektion berechnet.

  Nachweis der Umrechnung: Fuer Erlental liefert gewichte() exakt die frueher
  von Hand bestimmten Werte (409,425,0.522) (409,424,0.334) (408,425,0.088)
  (408,424,0.056). Die Formel ist damit an der bisherigen Eichung geprueft.

Das Ausgabeformat bleibt abwaertskompatibel: radolan.json enthaelt weiterhin
die Felder des Hauptorts auf oberster Ebene (summe_mm, stunden, umgebung_3x3 …),
zusaetzlich einen Block "orte" mit allen Standorten. Eine aeltere App-Fassung
liest also unveraendert weiter.

Frueher: v1.1 3x3-Kranz · v1.2 Schutz gegen leere Ueberschreibung ·
v1.3 Tagessummen-Archiv.
"""
import gzip, json, math, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np

# --------------------------------------------------------------------------
# Standorte. Der erste ist der Hauptort und fuellt zusaetzlich die oberste
# Ebene von radolan.json (Abwaertskompatibilitaet).
# --------------------------------------------------------------------------
ORTE = [
    {"id": "wettenberg",  "name": "Erlental, Wettenberg", "lat": 50.6479651, "lon": 8.6740943},
    {"id": "huettenberg", "name": "H\u00fcttenberg",       "lat": 50.5055647, "lon": 8.6226918},
    {"id": "norden",      "name": "Norden",                "lat": 53.5941,    "lon": 7.2066},
]

NROW = NCOL = 900
BASE = "https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/radolan/recent/bin/"
TZ   = ZoneInfo("Europe/Berlin")
UA   = {"User-Agent": "wetter-giessen-radolan/2.0 (GitHub Action)"}
ARCHIV = "radolan-archiv.json"

# --------------------------------------------------------------------------
# RADOLAN-Projektion: polarstereographisch, Referenz 60 N / 10 E, R = 6370.04 km.
# X0/Y0 sind die amtlichen Eckkoordinaten des 900x900-RW-Gitters; das halbe
# Kilometer Abzug bringt von der Pixelecke auf die Pixelmitte, auf die sich
# die Indizes beziehen.
# --------------------------------------------------------------------------
_R = 6370.040
_PHI0 = math.radians(60.0)
_LAM0 = math.radians(10.0)
_X0, _Y0 = -523.4622, -4658.645


def gitter(lat, lon):
    """(row, col) im RW-Gitter als Kommazahl. row zaehlt von Sueden nach Norden,
    genau wie die Zeilenachse des entpackten Arrays."""
    phi, lam = math.radians(lat), math.radians(lon)
    m = (1 + math.sin(_PHI0)) / (1 + math.sin(phi))
    x = _R * m * math.cos(phi) * math.sin(lam - _LAM0)
    y = -_R * m * math.cos(phi) * math.cos(lam - _LAM0)
    return y - _Y0 - 0.5, x - _X0 - 0.5


def gewichte(lat, lon):
    """Bilineare 4-Pixel-Gewichtung [(row, col, gewicht), …], absteigend."""
    fr, fc = gitter(lat, lon)
    r0, c0 = int(math.floor(fr)), int(math.floor(fc))
    dr, dc = fr - r0, fc - c0
    p = [(r0 + 1, c0 + 1, dr * dc),
         (r0 + 1, c0,     dr * (1 - dc)),
         (r0,     c0 + 1, (1 - dr) * dc),
         (r0,     c0,     (1 - dr) * (1 - dc))]
    return sorted([(r, c, round(w, 3)) for r, c, w in p if w > 0], key=lambda t: -t[2])


def _pruefe_ort(o):
    fr, fc = gitter(o["lat"], o["lon"])
    if not (1 <= fr <= NROW - 2 and 1 <= fc <= NCOL - 2):
        raise ValueError(f"{o['id']}: liegt ausserhalb des RADOLAN-Gitters "
                         f"(row {fr:.1f}, col {fc:.1f})")
    o["pixels"] = gewichte(o["lat"], o["lon"])
    o["home"]   = (int(round(fr)), int(round(fc)))
    o["kranz_rows"] = (o["home"][0] + 1, o["home"][0], o["home"][0] - 1)   # Nord -> Sued
    o["kranz_cols"] = (o["home"][1] - 1, o["home"][1], o["home"][1] + 1)   # West -> Ost
    return o


ORTE = [_pruefe_ort(o) for o in ORTE]
HAUPT = ORTE[0]

# Rueckwaertskompatible Namen: aeltere Skripte (radolan_backfill.py) importieren
# PIXELS als Modulvariable des Hauptorts.
PIXELS = HAUPT["pixels"]
HOME = HAUPT["home"]


def fetch_rw(dt_utc):
    name = f"raa01-rw_10000-{dt_utc:%y%m%d%H%M}-dwd---bin.gz"
    req = urllib.request.Request(BASE + name, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return gzip.decompress(r.read())


def parse_mm(raw):
    etx = raw.index(0x03)
    body = raw[etx + 1: etx + 1 + NROW * NCOL * 2]
    data = np.frombuffer(body, dtype="<u2").reshape(NROW, NCOL)
    nod = (data & 0x2000) != 0
    return np.where(nod, np.nan, (data & 0x0FFF) * 0.1)


def val(mm, r, c):
    v = mm[r, c]
    return 0.0 if np.isnan(v) else float(v)


def punktwert(mm, pixels=None):
    """Bilinear gewichteter Wert. Ohne Angabe fuer den Hauptort — so bleibt der
    Aufruf aus radolan_backfill.py unveraendert gueltig."""
    return sum(w * val(mm, r, c) for r, c, w in (pixels or PIXELS))


def tagessumme(midnight_local_day, pixels=None):
    """Vollstaendige Tagessumme eines lokalen Tages: Stunden 01:00..24:00.
    Die 24. Stunde liegt im RW-Bild um 00:00 des Folgetages - genau die, die der
    letzte Lauf des Tages (23:35) noch nicht kennen kann."""
    start_utc = midnight_local_day.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    total, ok = 0.0, 0
    for i in range(1, 25):
        try:
            mm = parse_mm(fetch_rw(start_utc + timedelta(hours=i)))
            total += punktwert(mm, pixels)
            ok += 1
        except Exception:
            pass
    return round(total, 2), ok


def tagessumme_alle(midnight_local_day):
    """Wie tagessumme(), aber fuer alle Orte in einem Durchgang — jede RW-Datei
    wird nur einmal geholt. Das ist der Grund, warum mehrere Orte kaum laenger
    dauern als einer."""
    start_utc = midnight_local_day.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    summen = {o["id"]: 0.0 for o in ORTE}
    ok = 0
    for i in range(1, 25):
        try:
            mm = parse_mm(fetch_rw(start_utc + timedelta(hours=i)))
        except Exception:
            continue
        for o in ORTE:
            summen[o["id"]] += punktwert(mm, o["pixels"])
        ok += 1
    return {k: round(v, 2) for k, v in summen.items()}, ok


def archiv_laden():
    try:
        with open(ARCHIV, "r", encoding="utf-8") as f:
            a = json.load(f)
        t = a.get("tage")
        return t if isinstance(t, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, ValueError, AttributeError):
        return {}


def archiv_laden_orte():
    """Archivteil je Ort: {"huettenberg": {"2026-08-31": {...}}}"""
    try:
        with open(ARCHIV, "r", encoding="utf-8") as f:
            a = json.load(f)
        t = a.get("orte")
        return t if isinstance(t, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, ValueError, AttributeError):
        return {}


def archiv_schreiben(tage, stand, orte=None):
    """tage = Hauptort (altes Feld, bleibt fuer aeltere App-Fassungen erhalten),
    orte = {ort_id: {datum: eintrag}} fuer alle Standorte."""
    daten = {"quelle": "DWD RADOLAN-RW (1 km, stationsgeeicht)",
             "ort": f"{HAUPT['name']} {HAUPT['lat']:.4f}N {HAUPT['lon']:.4f}E",
             "aktualisiert": stand,
             "tage": dict(sorted(tage.items()))}
    if orte:
        daten["orte"] = {k: dict(sorted(v.items())) for k, v in orte.items()}
        daten["ort_liste"] = [{"id": o["id"], "name": o["name"],
                               "lat": o["lat"], "lon": o["lon"]} for o in ORTE]
    with open(ARCHIV, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1)


def main():
    now_utc = datetime.now(timezone.utc)
    midnight_local = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = midnight_local.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    last_full = now_utc.replace(minute=0, second=0, microsecond=0)

    hours, t = [], start_utc + timedelta(hours=1)
    while t <= last_full:
        hours.append(t)
        t += timedelta(hours=1)

    # je Ort: Summe, Stundendetails, 3x3-Kranz
    st = {o["id"]: {"total": 0.0, "details": [],
                    "kranz": {(r, c): 0.0 for r in o["kranz_rows"] for c in o["kranz_cols"]}}
          for o in ORTE}
    ok = 0

    for h in hours:
        lbl = h.astimezone(TZ).strftime("%H:%M")
        try:
            mm = parse_mm(fetch_rw(h))          # eine Datei, alle Orte
        except urllib.error.HTTPError as e:
            hinweis = {"stunde": lbl, "mm": None,
                       "status": "noch nicht verfuegbar" if e.code == 404 else f"HTTP {e.code}"}
            for o in ORTE:
                st[o["id"]]["details"].append(dict(hinweis))
            continue
        except Exception as e:
            hinweis = {"stunde": lbl, "mm": None, "fehler": str(e)[:80]}
            for o in ORTE:
                st[o["id"]]["details"].append(dict(hinweis))
            continue
        ok += 1
        for o in ORTE:
            s = st[o["id"]]
            v = punktwert(mm, o["pixels"])
            s["total"] += v
            for (r, c) in s["kranz"]:
                s["kranz"][(r, c)] += val(mm, r, c)
            s["details"].append({"stunde": lbl, "mm": round(v, 2)})

    # --- Schutz gegen leere Ueberschreibung (v1.2) ---
    if ok == 0:
        print(f"Keine Radar-Stunde geholt (erwartet {len(hours)}, ok 0) "
              f"- radolan.json bleibt unveraendert.")
        return

    heute_str = midnight_local.strftime("%Y-%m-%d")

    # --- letzten Regentag je Ort aus der alten Datei uebernehmen -------------
    alt_orte, alt_top = {}, {}
    try:
        with open("radolan.json", "r", encoding="utf-8") as f:
            alt_top = json.load(f)
        alt_orte = alt_top.get("orte") or {}
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        pass

    def letzter_regen(oid, summe):
        vor = alt_orte.get(oid) or (alt_top if oid == HAUPT["id"] else {})
        lr = vor.get("letzter_regen")
        erg = None
        if isinstance(lr, dict) and lr.get("mm", 0) > 0 and lr.get("datum"):
            erg = {"datum": lr["datum"], "mm": round(float(lr["mm"]), 2)}
        if vor.get("summe_mm", 0) > 0 and vor.get("datum"):
            kand = {"datum": vor["datum"], "mm": round(float(vor["summe_mm"]), 2)}
            if erg is None or kand["datum"] >= erg["datum"]:
                erg = kand
        if summe > 0:
            erg = {"datum": heute_str, "mm": summe}
        return erg

    orte_out = {}
    for o in ORTE:
        s = st[o["id"]]
        summe = round(s["total"], 2)
        umgebung = [[{"pixel": [r, c], "mm": round(s["kranz"][(r, c)], 2),
                      "eigenes": (r, c) == o["home"]}
                     for c in o["kranz_cols"]] for r in o["kranz_rows"]]
        orte_out[o["id"]] = {
            "name": o["name"], "lat": o["lat"], "lon": o["lon"],
            "datum": heute_str, "summe_mm": summe,
            "stunden_ok": ok, "stunden_erwartet": len(hours),
            "stunden": s["details"], "umgebung_3x3": umgebung,
            "letzter_regen": letzter_regen(o["id"], summe),
            "methode": f"bilinear, {o['lat']:.4f}N {o['lon']:.4f}E",
        }

    haupt = orte_out[HAUPT["id"]]
    out = {
        # oberste Ebene = Hauptort, damit aeltere App-Fassungen unveraendert lesen
        "datum": heute_str,
        "summe_mm": haupt["summe_mm"],
        "stunden_ok": ok,
        "stunden_erwartet": len(hours),
        "stunden": haupt["stunden"],
        "umgebung_3x3": haupt["umgebung_3x3"],
        "letzter_regen": haupt["letzter_regen"],
        "aktualisiert": now_utc.isoformat(timespec="seconds"),
        "quelle": "DWD RADOLAN-RW (1 km, stationsgeeicht)",
        "methode": haupt["methode"],
        "orte": orte_out,
        "ort_liste": [{"id": o["id"], "name": o["name"], "lat": o["lat"], "lon": o["lon"]}
                      for o in ORTE],
    }
    with open("radolan.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for oid, d in orte_out.items():
        print(f"{oid:<12} {d['summe_mm']:>6.2f} mm  ({ok}/{len(hours)} Stunden)")

    # --- Tagessummen-Archiv ---------------------------------------------------
    tage = archiv_laden()
    a_orte = archiv_laden_orte()
    for o in ORTE:
        a_orte.setdefault(o["id"], {})
        a_orte[o["id"]][heute_str] = {"mm": orte_out[o["id"]]["summe_mm"], "h": ok, "voll": False}
    tage[heute_str] = {"mm": haupt["summe_mm"], "h": ok, "voll": False}

    gestern = midnight_local - timedelta(days=1)
    g_str = gestern.strftime("%Y-%m-%d")
    g_eintr = tage.get(g_str, {})
    if not g_eintr.get("voll") and g_eintr.get("v", 0) < 3:
        g_summen, g_ok = tagessumme_alle(gestern)
        if g_ok > 0:
            for o in ORTE:
                a_orte[o["id"]][g_str] = {"mm": g_summen[o["id"]], "h": g_ok,
                                          "voll": g_ok >= 24, "v": g_eintr.get("v", 0) + 1}
            tage[g_str] = {"mm": g_summen[HAUPT["id"]], "h": g_ok, "voll": g_ok >= 24,
                           "v": g_eintr.get("v", 0) + 1}
            print(f"Archiv: {g_str} finalisiert -> {g_summen[HAUPT['id']]} mm ({g_ok}/24 Stunden)")

    archiv_schreiben(tage, now_utc.isoformat(timespec="seconds"), a_orte)
    print(f"Archiv: {len(tage)} Tage, {len(a_orte)} Orte gespeichert.")


if __name__ == "__main__":
    main()
