#!/usr/bin/env python3
"""ICON-D2-RUC gegen das, was die App heute zeigt - Messreihe fuer Giessen.

Auftrag (Nutzer, 21.10.2026): erst messen, dann in die App. RUC kommt nur in
index.html, wenn es an der Station messbar gewinnt.

Ein Aufruf (stuendlich aus ruc.yml, etwa 42 min nach der vollen Stunde):
  1. neuester VOLLSTAENDIGER RUC-Lauf (TOT_PREC und T_2M bis +14 h vorhanden)
  2. Werte um die Station Giessen/Wettenberg (DWD 01639) ausschneiden:
     naechste Gitterzelle sowie Mittel und Maximum aller Zellen bis 5 km
  3. zum SELBEN Zeitpunkt die Vergleichsvorhersagen: Open-Meteo best_match (das
     nutzt die App fuer die Stundenwerte) und icon_d2, dazu MOSMIX ueber Bright
     Sky. Nachtraeglich geht das nicht - Open-Meteo liefert nur den neuesten Lauf.
  4. eine JSON-Zeile an <daten>/ruc/JJJJ-MM-TT.jsonl anhaengen (UTC-Tag)

Die Messung (Wahrheit) holt erst ruc_auswertung.py, Tage spaeter, von Bright Sky.

Gitter: "r" ist beim DWD das NATIVE ICON-Dreiecksgitter (542 040 Zellen, kein
Laenge/Breite-Raster), CCSDS-gepackt - darum eccodes. Die Zellmitten stehen in
den Feldern CLAT/CLON; die Zellnummern um Giessen werden einmal bestimmt und in
<daten>/ruc/gitter.json gemerkt. Die naechste Zelle liegt 0,4 km neben der
Station (gemessen 21.10.2026), bis 5 km sind es 16 Zellen.

Zeitbezug: TOT_PREC ist seit Laufbeginn aufsummiert - Stundenregen h =
TOT_PREC(h) - TOT_PREC(h-1), gilt fuer [Lauf+h-1, Lauf+h). Gespeichert wird je
Wert die ENDzeit wie bei Bright Sky und Open-Meteo (Wert mit Stempel t = Stunde
vor t). T_2M ist ein Momentanwert zum Stempel.
"""
import concurrent.futures as cf
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.request

import numpy as np
import eccodes as ec

BASIS = "https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p"
STATION = {"id": "01639", "name": "Giessen/Wettenberg", "lat": 50.6017, "lon": 8.6439}
STUNDEN = 14            # RUC rechnet 14 h voraus
RADIUS_KM = 5.0
UA = {"User-Agent": "wetter-app ruc-vergleich (github.com/luperttrading-lab/wetter)"}


def holen(url, versuche=3, timeout=60):
    for i in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            fehler = e
            time.sleep(3 * (i + 1))
    raise fehler


def liste(url):
    return re.findall(r'href="([^"?/][^"]*)"', holen(url).decode("utf-8", "replace"))


def werte(daten):
    g = ec.codes_new_from_message(daten)
    try:
        return ec.codes_get_values(g), ec.codes_get(g, "numberOfDataPoints")
    finally:
        ec.codes_release(g)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%MZ")


def laeufe():
    """Laufverzeichnisse von TOT_PREC, neuester zuerst."""
    namen = [n.rstrip("/") for n in liste(f"{BASIS}/TOT_PREC/r/") if n.startswith("20")]
    return sorted(namen, reverse=True)


def vollstaendig(lauf):
    ziel = f"PT{STUNDEN:03d}H00M.grib2"
    return all(ziel in liste(f"{BASIS}/{v}/r/{lauf}/s/") for v in ("TOT_PREC", "T_2M"))


def gitter(datei):
    """Zellnummern um die Station; einmal aus CLAT/CLON bestimmt, dann gemerkt."""
    if os.path.exists(datei):
        with open(datei) as f:
            return json.load(f)
    lauf = laeufe()[0]
    felder = {}
    for v in ("CLAT", "CLON"):
        name = [n for n in liste(f"{BASIS}/{v}/r/{lauf}/s/") if n.endswith(".grib2")][0]
        felder[v], n = werte(holen(f"{BASIS}/{v}/r/{lauf}/s/{name}"))
    lat, lon = felder["CLAT"], felder["CLON"]
    km = np.sqrt((lat - STATION["lat"]) ** 2 + ((lon - STATION["lon"]) * math.cos(math.radians(STATION["lat"]))) ** 2) * 111.2
    i = int(np.argmin(km))
    ring = [int(j) for j in np.where(km <= RADIUS_KM)[0]]
    g = {"n": int(n), "zelle": i, "abstand_km": round(float(km[i]), 2),
         "zelle_lat": round(float(lat[i]), 4), "zelle_lon": round(float(lon[i]), 4),
         "ring": ring, "radius_km": RADIUS_KM, "station": STATION}
    os.makedirs(os.path.dirname(datei), exist_ok=True)
    with open(datei, "w") as f:
        json.dump(g, f)
    return g


def ruc_lauf(lauf, g):
    """Stundenregen (Zelle, Mittel und Max bis 5 km) und T_2M fuer +1..+14 h."""
    auftraege = [(v, h) for v in ("TOT_PREC", "T_2M") for h in range(1, STUNDEN + 1)]

    def eins(a):
        v, h = a
        w, n = werte(holen(f"{BASIS}/{v}/r/{lauf}/s/PT{h:03d}H00M.grib2"))
        if n != g["n"]:
            raise RuntimeError(f"Gitter geaendert: {n} statt {g['n']} Punkte")
        ring = w[g["ring"]]
        return a, (float(w[g["zelle"]]), ring)

    with cf.ThreadPoolExecutor(6) as ex:
        res = dict(ex.map(eins, auftraege))
    vor_p, vor_r = 0.0, np.zeros(len(g["ring"]))   # TOT_PREC zum Laufbeginn = 0
    regen, mittel, maxi, t2m = [], [], [], []
    for h in range(1, STUNDEN + 1):
        p, r = res[("TOT_PREC", h)]
        d = np.maximum(r - vor_r, 0)
        regen.append(round(max(p - vor_p, 0.0), 2))
        mittel.append(round(float(d.mean()), 2))
        maxi.append(round(float(d.max()), 2))
        vor_p, vor_r = p, r
        t2m.append(round(res[("T_2M", h)][0] - 273.15, 2))
    t0 = dt.datetime.strptime(lauf.replace("%3A", ":"), "%Y-%m-%dT%H:%M").replace(tzinfo=dt.timezone.utc)
    return {"lauf": iso(t0), "ende": [iso(t0 + dt.timedelta(hours=h)) for h in range(1, STUNDEN + 1)],
            "regen": regen, "regen5_mittel": mittel, "regen5_max": maxi, "t2m": t2m}


def open_meteo():
    """Was die App zeigt (best_match) und ICON-D2 allein, dazu der Laufzeitpunkt."""
    url = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&hourly=precipitation,temperature_2m&models=best_match,icon_d2"
           "&forecast_hours=16&timezone=GMT&timeformat=unixtime").format(**STATION)
    j = json.loads(holen(url, versuche=2))
    if j.get("error"):
        raise RuntimeError(j.get("reason"))
    h = j["hourly"]
    out = {"ende": [iso(dt.datetime.fromtimestamp(t, dt.timezone.utc)) for t in h["time"]]}
    for m in ("best_match", "icon_d2"):
        out[m] = {"regen": h.get(f"precipitation_{m}"), "t2m": h.get(f"temperature_2m_{m}")}
    try:
        meta = json.loads(holen("https://api.open-meteo.com/data/dwd_icon_d2/static/meta.json", versuche=1))
        out["lauf_icon_d2"] = iso(dt.datetime.fromtimestamp(meta["last_run_initialisation_time"], dt.timezone.utc))
    except Exception:
        pass
    return out


def mosmix(jetzt):
    bis = jetzt + dt.timedelta(hours=STUNDEN + 1)
    url = (f"https://api.brightsky.dev/weather?dwd_station_id={STATION['id']}"
           f"&date={iso(jetzt)}&last_date={iso(bis)}&tz=Etc/UTC")
    j = json.loads(holen(url, versuche=2))
    w = [x for x in j.get("weather", []) if dt.datetime.fromisoformat(x["timestamp"]) > jetzt]
    return {"ende": [iso(dt.datetime.fromisoformat(x["timestamp"])) for x in w],
            "regen": [x.get("precipitation") for x in w], "t2m": [x.get("temperature") for x in w]}


def main():
    ordner = os.path.join(sys.argv[1] if len(sys.argv) > 1 else ".", "ruc")
    os.makedirs(ordner, exist_ok=True)
    stand_datei = os.path.join(ordner, "stand.json")
    stand = json.load(open(stand_datei)) if os.path.exists(stand_datei) else {}
    jetzt = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)

    lauf = next((l for l in laeufe()[:4] if vollstaendig(l)), None)
    if not lauf:
        print("kein vollstaendiger RUC-Lauf unter den letzten vier")
        return 0
    if stand.get("lauf") == lauf:
        print(f"Lauf {lauf} schon erfasst - nichts zu tun")
        return 0

    satz = {"abruf": iso(jetzt), "station": STATION["id"]}
    g = gitter(os.path.join(ordner, "gitter.json"))
    try:
        satz["ruc"] = ruc_lauf(lauf, g)
    except Exception as e:
        print("RUC fehlgeschlagen:", e)
        return 1      # ohne RUC ist der Satz wertlos; der naechste Durchgang versucht es wieder
    for name, f in (("om", open_meteo), ("mosmix", lambda: mosmix(jetzt))):
        try:
            satz[name] = f()
        except Exception as e:
            satz[name] = None
            satz.setdefault("fehler", {})[name] = str(e)[:200]
    with open(os.path.join(ordner, jetzt.strftime("%Y-%m-%d") + ".jsonl"), "a") as f:
        f.write(json.dumps(satz, separators=(",", ":")) + "\n")
    with open(stand_datei, "w") as f:
        json.dump({"lauf": lauf, "abruf": satz["abruf"]}, f)
    r = satz["ruc"]
    print(f"Lauf {r['lauf']}: Regen +1..+14 h {r['regen']} mm, T2m +1 h {r['t2m'][0]} Grad;"
          f" Open-Meteo {'ok' if satz['om'] else 'FEHLT'}, MOSMIX {'ok' if satz['mosmix'] else 'FEHLT'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
