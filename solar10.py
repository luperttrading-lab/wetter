#!/usr/bin/env python3
"""DWD-10-Minuten-Strahlungswerte ALLER Stationen -> Verzeichnis solar10/

Warum: Die UV-Grafik der App zeichnet gemessene Saeulen aus Globalstrahlung
(GS_10), Diffusstrahlung (DS_10) und Sonnenschein (SD_10) im 10-Minuten-Raster.
Der DWD veroeffentlicht diese Werte fuer rund 60 Stationen; die App sucht sich
beim Ortswechsel die naechste (Radius 30 km) und laedt nur deren Datei.

Warum eine Action: opendata.dwd.de sendet keinen CORS-Header, der Browser darf
die ZIPs nicht direkt laden. Dieses Skript liest serverseitig und schreibt
kleine JSON-Dateien. Der Workflow legt sie in den Branch "daten" OHNE Historie
(jeder Lauf ersetzt den einen Commit) - sonst wuerden 60 Dateien mal 68 Laeufe
am Tag das Repo um rund 1 GB im Jahr aufblaehen.

Quelle: https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/solar/
  now/zehn_now_sd_Beschreibung_Stationen.txt  Stationsliste (latin1, Festbreite)
  now/10minutenwerte_SOLAR_<id>_now.zip       heutiger Tag (UTC), ~1 KB
  recent/10minutenwerte_SOLAR_<id>_akt.zip    letzte ~500 Tage, ~500 KB (nur zum Nachfuellen)

Format der Textdatei: STATIONS_ID;MESS_DATUM;QN;DS_10;GS_10;SD_10;LS_10;eor
  MESS_DATUM = JJJJMMTThhmm UTC, Stempel = ENDE des 10-Minuten-Intervalls
  DS_10, GS_10 in J/cm2 je 10 min -> W/m2 Mittel: * 10000 / 600
  SD_10 in Stunden -> Minuten: * 60 ; -999 = fehlend

Ausgabe (OUT/):
  stationen.json  { aktualisiert, stationen: [ {id,name,lat,lon,hoehe,letzter,
                    gs: misst Globalstrahlung, sd: misst Sonnenschein} ] }
  <id>.json       { id, t0: ISO-UTC des ersten Stempels, dt_min: 10, letzter,
                    gs: [W/m2|null], ds: [...], sd: [Minuten|null] }   lueckenlos ab t0
Aufruf: solar10.py [--alt VERZEICHNIS_MIT_ALTEM_STAND] [--out VERZEICHNIS]
"""
import io, json, os, re, sys, zipfile, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

BASE = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/solar/"
TAGE = 2            # heute + gestern (UTC)
DT = 10             # Minuten
INAKTIV_TAGE = 5    # Station gilt als aktiv, wenn "bis_datum" juenger ist

def arg(name, default):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default

ALT = arg("--alt", "solar10")
OUT = arg("--out", "solar10")

def hole(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "wetter-app solar10 (github action)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def stationsliste():
    txt = hole(BASE + "now/zehn_now_sd_Beschreibung_Stationen.txt").decode("latin1")
    grenze = (datetime.now(timezone.utc) - timedelta(days=INAKTIV_TAGE)).strftime("%Y%m%d")
    out = []
    for line in txt.splitlines()[2:]:
        m = re.match(r"\s*(\d{5})\s+(\d{8})\s+(\d{8})\s+(-?\d+)\s+([\d.]+)\s+([\d.]+)\s+(.+?)\s{2,}(\S.*?)\s{2,}", line)
        if not m or m.group(3) < grenze:
            continue
        out.append({"id": m.group(1), "name": m.group(7).strip(), "lat": float(m.group(5)),
                    "lon": float(m.group(6)), "hoehe": int(m.group(4))})
    return out

def parse_zip(data):
    out = {}
    zf = zipfile.ZipFile(io.BytesIO(data))
    name = [n for n in zf.namelist() if n.startswith("produkt_")][0]
    for line in zf.read(name).decode("latin1").splitlines()[1:]:
        f = [x.strip() for x in line.split(";")]
        if len(f) < 7:
            continue
        try:
            ts = datetime.strptime(f[1], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        def val(s, faktor, nd):
            try:
                v = float(s)
            except ValueError:
                return None
            return None if v <= -998 else round(v * faktor, nd)
        out[ts] = (val(f[4], 10000 / 600, 0), val(f[3], 10000 / 600, 0), val(f[5], 60, 1))
    return out

def lies_alt(sid):
    p = os.path.join(ALT, sid + ".json")
    if not os.path.exists(p):
        return {}
    try:
        st = json.load(open(p, encoding="utf-8"))
        t0 = datetime.strptime(st["t0"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    except Exception:
        return {}
    d = {}
    for i, gs in enumerate(st.get("gs", [])):
        ds = st["ds"][i] if i < len(st.get("ds", [])) else None
        sd = st["sd"][i] if i < len(st.get("sd", [])) else None
        if gs is None and ds is None and sd is None:
            continue
        d[t0 + timedelta(minutes=DT * i)] = (gs, ds, sd)
    return d

def station(st, grenze, gestern):
    sid = st["id"]
    werte = dict(lies_alt(sid))
    try:
        werte.update(parse_zip(hole(BASE + f"now/10minutenwerte_SOLAR_{sid}_now.zip")))
    except Exception as e:
        return None, f"{sid} {st['name']}: now nicht geladen: {e}"
    n_gestern = sum(1 for ts in werte if gestern <= ts < gestern + timedelta(days=1))
    if n_gestern < 100:
        try:
            rec = parse_zip(hole(BASE + f"recent/10minutenwerte_SOLAR_{sid}_akt.zip", timeout=120))
            for ts, v in rec.items():
                if ts >= grenze and ts not in werte:
                    werte[ts] = v
        except Exception as e:
            pass   # dann eben nur heute
    werte = {ts: v for ts, v in werte.items() if ts >= grenze}
    if not werte:
        return None, f"{sid} {st['name']}: keine Werte"
    t0, t1 = min(werte), max(werte)
    n = int((t1 - t0).total_seconds() // (DT * 60)) + 1
    gs, ds, sd = [None] * n, [None] * n, [None] * n
    for ts, (g, d, s) in werte.items():
        i = int((ts - t0).total_seconds() // (DT * 60))
        if 0 <= i < n:
            gs[i], ds[i], sd[i] = g, d, s
    return {"id": sid, "t0": t0.strftime("%Y-%m-%dT%H:%MZ"), "dt_min": DT,
            "letzter": t1.strftime("%Y-%m-%dT%H:%MZ"), "gs": gs, "ds": ds, "sd": sd}, None

def main():
    jetzt = datetime.now(timezone.utc)
    grenze = (jetzt - timedelta(days=TAGE - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    gestern = grenze
    liste = stationsliste()
    print(f"{len(liste)} aktive Stationen laut DWD-Liste")
    os.makedirs(OUT, exist_ok=True)
    ok = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for st, (daten, fehler) in zip(liste, ex.map(lambda s: station(s, grenze, gestern), liste)):
            if fehler:
                print(fehler, file=sys.stderr)
                continue
            with open(os.path.join(OUT, st["id"] + ".json"), "w", encoding="utf-8") as f:
                json.dump(daten, f, ensure_ascii=False, separators=(",", ":"))
            # Nicht jede Station der Sonnenschein-Liste misst Strahlung (Muenchen-Stadt,
            # Ostenfeld, Grosser Arber liefern nur SD_10). Die App braucht das VOR dem
            # Laden der Datei, um die passende Station zu waehlen.
            ok.append(dict(st, letzter=daten["letzter"],
                           gs=sum(1 for v in daten["gs"] if v is not None) > 30,
                           sd=sum(1 for v in daten["sd"] if v is not None) > 30))
    if not ok:
        print("keine Station geladen - nichts geschrieben", file=sys.stderr)
        return 1
    with open(os.path.join(OUT, "stationen.json"), "w", encoding="utf-8") as f:
        json.dump({"aktualisiert": jetzt.strftime("%Y-%m-%dT%H:%M:%SZ"), "quelle": BASE,
                   "stempel": "UTC, Ende des 10-Minuten-Intervalls",
                   "einheiten": {"gs": "W/m2 Mittel (Globalstrahlung)", "ds": "W/m2 Mittel (Diffusstrahlung)", "sd": "Minuten Sonnenschein je 10 min"},
                   "stationen": ok}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(ok)} Stationen geschrieben nach {OUT}/")
    return 0

if __name__ == "__main__":
    sys.exit(main())
