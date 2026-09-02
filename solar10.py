#!/usr/bin/env python3
"""DWD-10-Minuten-Strahlungswerte je Station -> solar10.json

Warum: Die UV-Grafik der App soll die amtliche BfS-Messung (1-Minuten-Takt)
moeglichst treffen. Aus Stundenwerten geht das nicht - jede Zacke waere
erfunden. Der DWD veroeffentlicht fuer Stationen mit Strahlungsmessung
10-Minuten-Werte: Globalstrahlung GS_10, Diffusstrahlung DS_10 und
Sonnenscheindauer SD_10. Sechs Messwerte je Stunde statt einem.

Warum eine Action: opendata.dwd.de sendet keinen CORS-Header, der Browser
darf die ZIP nicht direkt laden. Wie bei RADOLAN und der BfS-Achse liest
dieses Skript serverseitig und legt ein kleines JSON ins Repo.

Quelle: https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/solar/
  now/    10minutenwerte_SOLAR_<id>_now.zip   heutiger Tag (UTC), ~1 KB, alle 10-30 min neu
  recent/ 10minutenwerte_SOLAR_<id>_akt.zip   letzte ~500 Tage, ~500 KB, einmal taeglich

Format der Textdatei (Semikolon, Leerzeichen):
  STATIONS_ID;MESS_DATUM;QN;DS_10;GS_10;SD_10;LS_10;eor
  MESS_DATUM = JJJJMMTThhmm in UTC, Stempel = ENDE des 10-Minuten-Intervalls
  DS_10, GS_10 in J/cm2 je 10 min   -> W/m2 Mittel: * 10000 / 600
  SD_10 in Stunden (max 0,1667)      -> Minuten: * 60
  -999 = fehlend

Ausgabe solar10.json (kompakt, ~10 KB):
  { "aktualisiert": ISO-UTC,
    "stationen": [ { "id","name","lat","lon","hoehe",
                     "t0": ISO-UTC des ersten Stempels, "dt_min": 10,
                     "gs": [W/m2|null,...], "ds": [...], "sd": [Minuten|null,...] } ] }
  Die Arrays sind lueckenlos ab t0 im 10-Minuten-Raster; die App rechnet
  Index -> Zeit selbst. Gehalten werden die letzten TAGE Tage (UTC).
"""
import io, json, os, sys, zipfile, urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/solar/"
OUT = "solar10.json"
TAGE = 2            # heute + gestern (UTC)
DT = 10             # Minuten

# Stationen mit Strahlungsmessung nahe den App-Standorten
# (Liste: now/zehn_now_sd_Beschreibung_Stationen.txt). Die App waehlt per
# Koordinaten die naechste; Wettenberg 0,6 km, Norden ~13 km.
STATIONEN = [
    {"id": "01639", "name": "Gießen/Wettenberg", "lat": 50.6017, "lon": 8.6439, "hoehe": 203},
    {"id": "03631", "name": "Norderney",             "lat": 53.7123, "lon": 7.1519, "hoehe": 12},
]

def hole(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "wetter-app solar10 (github action)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def parse_zip(data):
    """-> dict Stempel(datetime UTC) -> (gs W/m2 | None, ds W/m2 | None, sd min | None)"""
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
            if v <= -998:
                return None
            return round(v * faktor, nd)
        ds = val(f[3], 10000 / 600, 0)
        gs = val(f[4], 10000 / 600, 0)
        sd = val(f[5], 60, 1)
        out[ts] = (gs, ds, sd)
    return out

def lies_alt():
    """Bestehendes JSON -> {id: {stempel: (gs,ds,sd)}}"""
    if not os.path.exists(OUT):
        return {}
    try:
        j = json.load(open(OUT, encoding="utf-8"))
    except Exception:
        return {}
    alt = {}
    for st in j.get("stationen", []):
        try:
            t0 = datetime.strptime(st["t0"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        d = {}
        for i, gs in enumerate(st.get("gs", [])):
            ts = t0 + timedelta(minutes=DT * i)
            ds = st["ds"][i] if i < len(st.get("ds", [])) else None
            sd = st["sd"][i] if i < len(st.get("sd", [])) else None
            if gs is None and ds is None and sd is None:
                continue
            d[ts] = (gs, ds, sd)
        alt[st["id"]] = d
    return alt

def main():
    jetzt = datetime.now(timezone.utc)
    grenze = (jetzt - timedelta(days=TAGE - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    gestern = grenze  # 00:00 UTC des Vortags
    alt = lies_alt()
    stationen_out = []
    neu_geladen = 0
    for st in STATIONEN:
        werte = dict(alt.get(st["id"], {}))
        # heutiger Tag: kleine now-Datei
        try:
            werte.update(parse_zip(hole(BASE + f"now/10minutenwerte_SOLAR_{st['id']}_now.zip")))
            neu_geladen += 1
        except Exception as e:
            print(f"{st['id']}: now nicht geladen: {e}", file=sys.stderr)
        # Vortag fehlt (erster Lauf, Luecke)? -> grosse recent-Datei einmalig
        n_gestern = sum(1 for ts in werte if gestern <= ts < gestern + timedelta(days=1))
        if n_gestern < 100:
            try:
                rec = parse_zip(hole(BASE + f"recent/10minutenwerte_SOLAR_{st['id']}_akt.zip", timeout=120))
                for ts, v in rec.items():
                    if ts >= grenze and ts not in werte:
                        werte[ts] = v
                print(f"{st['id']}: Vortag aus recent nachgefuellt ({n_gestern} -> "
                      f"{sum(1 for ts in werte if gestern <= ts < gestern + timedelta(days=1))})")
            except Exception as e:
                print(f"{st['id']}: recent nicht geladen: {e}", file=sys.stderr)
        werte = {ts: v for ts, v in werte.items() if ts >= grenze}
        if not werte:
            continue
        t0 = min(werte)
        t1 = max(werte)
        n = int((t1 - t0).total_seconds() // (DT * 60)) + 1
        gs, ds, sd = [None] * n, [None] * n, [None] * n
        for ts, (g, d, s) in werte.items():
            i = int((ts - t0).total_seconds() // (DT * 60))
            if 0 <= i < n:
                gs[i], ds[i], sd[i] = g, d, s
        stationen_out.append({
            "id": st["id"], "name": st["name"], "lat": st["lat"], "lon": st["lon"], "hoehe": st["hoehe"],
            "t0": t0.strftime("%Y-%m-%dT%H:%MZ"), "dt_min": DT,
            "letzter": t1.strftime("%Y-%m-%dT%H:%MZ"),
            "gs": gs, "ds": ds, "sd": sd,
        })
        print(f"{st['id']} {st['name']}: {n} Intervalle, {t0:%d.%m. %H:%M} - {t1:%d.%m. %H:%M} UTC")
    if not stationen_out or neu_geladen == 0:
        print("nichts Neues - JSON bleibt", file=sys.stderr)
        return 0
    out = {"aktualisiert": jetzt.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "quelle": BASE, "stempel": "UTC, Ende des 10-Minuten-Intervalls",
           "einheiten": {"gs": "W/m2 Mittel (Globalstrahlung)", "ds": "W/m2 Mittel (Diffusstrahlung)", "sd": "Minuten Sonnenschein je 10 min"},
           "stationen": stationen_out}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
