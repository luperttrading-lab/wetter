#!/usr/bin/env python3
"""regen_radar.py -- Eicht das DWD-Radar an den Niederschlagsmessern am Boden.

WARUM
Am 16.09.2026 fiel in Wettenberg Niesel. Die Station mass 0,24 mm in der
Stunde, das Radar kam auf 0,09 mm - Faktor 2,7 zu wenig. Das ist kein
Zufall: Die Radarreflektivitaet waechst mit der sechsten Potenz des
Tropfendurchmessers. Ein Nieseltropfen von 0,2 mm reflektiert gegenueber
einem Regentropfen von 1 mm um den Faktor 0,2^6, also rund 15.000-mal
schwaecher. Die Z-R-Beziehung des Radars ist auf Regen geeicht, nicht auf
Niesel; bei feinen Tropfen unterschaetzt sie systematisch.

Die App zeigt seit v3.88 den Radarwert als Zustand an ("Niesel", "Regen").
Ist die Rate zu niedrig, rutscht echter Leichtregen faelschlich in die
Nieselklasse. Darum messen wir den Faktor, statt ihn zu schaetzen.

WAS DAS SKRIPT TUT
Fuer jede Station der Liste und jede abgeschlossene Stunde der letzten
Stunden: Stundensumme der Station (Bright Sky /weather) gegen die
Radarsumme derselben Stunde am selben Ort. Paare, bei denen beide Seiten
null sind, werden verworfen - sie tragen nichts bei und blaehen das Log.

WANN ES LAUFEN MUSS
Das Radararchiv von Bright Sky reicht nur rund acht Stunden zurueck
(geprueft am 16.09.2026: 8 h ja, 10 h nein). Ein taeglicher Lauf wuerde
also Luecken lassen; der Workflow laeuft alle sechs Stunden.

AUSWERTUNG
Je Intensitaetsklasse der Median von Station/Radar. Der Median, nicht das
Mittel: Ein verstopfter Regenmesser oder ein Radarartefakt soll das
Ergebnis nicht kippen. Ausgegeben wird nach regen-radar.json, sobald eine
Klasse genug Paare hat.
"""
import datetime as dt, json, math, os, subprocess, sys

LOG = "regen_radarlog.json"
AUS = "regen-radar.json"
MIN_PAARE = 30            # darunter ist der Median Rauschen
# Der DWD-Niederschlagsmesser ist eine Kippwaage und loest 0,1 mm auf: alles
# darunter steht als 0,0 in den Daten. Fuer den Quotienten Messung/Radar ist
# das toedlich, denn der Zaehler kann bei kleinen Mengen nur 0,0 oder 0,1
# sein - der Quotient springt entsprechend. Nachgerechnet am Log vom
# 20.09.2026: von 207 Paaren der Nieselklasse hatten 165, also 80 Prozent,
# eine Stationssumme von exakt 0,0. Der Median darueber war 0,0 und damit der
# "Faktor" ebenfalls 0,0 - haette die App ihn uebernommen, waere jeder
# Radarwert mit null multipliziert worden. Dass das nicht geschah, lag allein
# daran, dass 0.0 in Python falsy ist und die Ausgabe deshalb "-" schrieb.
# Ein Zufall, keine Absicherung.
# Darum zaehlen fuer den Faktor nur Stunden mit mindestens zwei Kippungen.
MIN_MESS = 0.2
TAGE_IM_LOG = 60          # aeltere Tage fallen raus, damit main nicht waechst
STUNDEN_ZURUECK = 7       # Archivgrenze des Radars liegt bei rund 8 h;
                          # geholt wird die Stunde DAVOR, also eine mehr
STUNDEN_VERZUG = 2        # die juengsten Stunden traegt der DWD noch nach

# Stationen: quer durch Deutschland, damit nicht eine Wetterlage alles
# bestimmt. Alle mit Niederschlagsmessung und SYNOP-Meldung.
STATIONEN = [
    ("Giessen/Wettenberg", 50.6017, 8.6439), ("Frankfurt/Main", 50.0259, 8.5213),
    ("Kassel", 51.2983, 9.4414),             ("Koeln/Bonn", 50.8659, 7.1427),
    ("Dortmund", 51.5056, 7.6122),           ("Muenster/Osnabrueck", 52.1344, 7.6969),
    ("Hamburg-Fuhlsbuettel", 53.6332, 9.9881),("Bremen", 53.0457, 8.7988),
    ("Hannover", 52.4635, 9.6942),           ("Berlin-Tegel", 52.5644, 13.3088),
    ("Leipzig/Halle", 51.4325, 12.2417),     ("Dresden-Klotzsche", 51.1280, 13.7550),
    ("Erfurt-Weimar", 50.9819, 10.9581),     ("Nuernberg", 49.5030, 11.0549),
    ("Muenchen-Flughafen", 48.3477, 11.8134),("Stuttgart-Echterdingen", 48.6883, 9.2235),
    ("Karlsruhe/Rheinstetten", 48.9731, 8.3339), ("Trier-Petrisberg", 49.7486, 6.6581),
    ("Saarbruecken", 49.2128, 7.1077),       ("Freiburg", 48.0233, 7.8343),
]


def hole(url, versuche=3):
    cmd = ["curl", "-sS", "--compressed", "--max-time", "60"]
    ca = os.environ.get("CURL_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
    if os.path.exists(ca):
        cmd += ["--cacert", ca]
    for _ in range(versuche):
        r = subprocess.run(cmd + [url], capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except Exception:
            continue
    return None


def radar_stunde(lat, lon, beginn):
    """Radarsumme in mm fuer die Stunde ab 'beginn' (UTC, aware).

    Ein Abruf mit date=beginn liefert den Lauf, der dort ansetzt; seine
    ersten zwoelf Fuenf-Minuten-Schritte decken genau diese Stunde ab und
    liegen am dichtesten an der Messung - spaetere Schritte desselben Laufs
    waeren Vorhersage. Genommen wird die Mittelzelle des 3x3-Rasters: Die
    Station misst an einem Punkt, das Maximum ueber neun Quadratkilometer
    waere systematisch zu hoch.
    """
    d = hole("https://api.brightsky.dev/radar?lat=%.4f&lon=%.4f&distance=1000"
             "&format=plain&tz=Europe/Berlin&date=%s"
             % (lat, lon, beginn.isoformat().replace("+00:00", "Z")))
    if not d or not d.get("radar"):
        return None
    ende = beginn + dt.timedelta(hours=1)
    summe, n = 0.0, 0
    for f in d["radar"]:
        t = dt.datetime.fromisoformat(f["timestamp"])
        if not (beginn <= t < ende):
            continue
        px = f.get("precipitation_5")
        if not px:
            continue
        rows = px if isinstance(px[0], list) else [px]
        summe += rows[len(rows) // 2][len(rows[0]) // 2] * 0.01   # 0,01 mm je Schritt
        n += 1
    return round(summe, 3) if n >= 10 else None    # unvollstaendige Stunde verwerfen


# Bright Sky mischt in /weather Messung und Vorhersage: Die frueheren
# Stunden kommen von der Station (observation_type "synop", "current" oder
# "historical"), die spaeteren aus dem Modell ("forecast"). Fuer eine
# Eichung taugt nur die Messung - sonst vergliche man Radar gegen Modell.
MESSTYPEN = ("synop", "current", "historical")


def station_stunden(name, lat, lon, von, bis):
    """Gemessene Stundensummen der Station als {ISO-Stunde UTC: mm}."""
    # last_date ist exklusiv: mit von=bis kaeme genau eine Stunde zurueck,
    # darum einen Tag drauf.
    d = hole("https://api.brightsky.dev/weather?lat=%.4f&lon=%.4f&date=%s&last_date=%s"
             % (lat, lon, von.date().isoformat(),
                (bis.date() + dt.timedelta(days=1)).isoformat()))
    if not d or not d.get("weather"):
        return {}, None
    typ = {s["id"]: s.get("observation_type") for s in (d.get("sources") or [])}
    namen = {s["id"]: s.get("station_name") for s in (d.get("sources") or [])}
    out, quelle = {}, None
    for w in d["weather"]:
        p = w.get("precipitation")
        if p is None:
            continue
        if typ.get(w.get("source_id")) not in MESSTYPEN:
            continue                      # Vorhersagestunde, nicht gemessen
        t = dt.datetime.fromisoformat(w["timestamp"]).astimezone(dt.timezone.utc)
        out[t.replace(minute=0, second=0, microsecond=0).isoformat()] = float(p)
        quelle = quelle or namen.get(w.get("source_id"))
    return out, quelle


def sammeln():
    jetzt = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    # Die letzten beiden Stunden ueberspringen: Um 10:20 stand die Summe
    # fuer 09:00-10:00 noch auf 0,0, obwohl es nieselte - der DWD traegt
    # Stundenwerte verzoegert nach. Ungepruefte Nullen wuerden den Faktor
    # nach unten ziehen.
    stunden = [jetzt - dt.timedelta(hours=h)
               for h in range(STUNDEN_VERZUG, STUNDEN_ZURUECK + 1)]
    von, bis = min(stunden), jetzt
    paare = []
    for name, lat, lon in STATIONEN:
        mess, quelle = station_stunden(name, lat, lon, von, bis)
        if not mess:
            print("  %-24s keine Messwerte" % name)
            continue
        n = 0
        for h in stunden:
            k = h.isoformat()
            if k not in mess:
                continue
            st = mess[k]
            # Der Zeitstempel einer DWD-Stundensumme bezeichnet das ENDE des
            # Intervalls: Der Wert zu 05:00 ist der Niederschlag von 04:00 bis
            # 05:00. Am 16.09.2026 an zehn Regenstunden geprueft - mit der
            # Stunde davor faellt der Median von Messung/Radar von 4,94 auf
            # 1,61, und Ausreisser wie Hannover mit Faktor 88 verschwinden.
            ra = radar_stunde(lat, lon, h - dt.timedelta(hours=1))
            if ra is None:
                continue
            if st == 0 and ra == 0:        # trockene Stunden tragen nichts bei
                continue
            paare.append({"t": k, "st": name, "mess": st, "radar": ra})
            n += 1
        print("  %-24s %2d Paare  (%s)" % (name, n, quelle or "?"))
    return paare


# Klassen nach der Radarrate, denn die ist es, die korrigiert werden soll.
# Grenzen wie in der App: unter 0,5 mm/h Niesel, darueber Regen.
KLASSEN = [("niesel", 0.0, 0.5), ("leicht", 0.5, 2.5), ("regen", 2.5, 1e9)]


def median(w):
    w = sorted(w)
    n = len(w)
    return w[n // 2] if n % 2 else 0.5 * (w[n // 2 - 1] + w[n // 2])


def auswerten(log):
    alle = [p for tag in log.values() for p in tag]
    out = {}
    for name, lo, hi in KLASSEN:
        # Das Radar muss etwas gesehen haben (sonst ist das Verhaeltnis nicht
        # definiert) und die Station genug, dass ihre Zahl etwas aussagt.
        w = [p for p in alle
             if lo <= p["radar"] < hi and p["radar"] > 0 and p["mess"] >= MIN_MESS]
        roh = sum(1 for p in alle if lo <= p["radar"] < hi and p["radar"] > 0)
        if len(w) < MIN_PAARE:
            out[name] = {"paare": len(w), "roh": roh, "faktor": None}
            continue
        v = sorted(p["mess"] / p["radar"] for p in w)
        m = median(v)
        # Ein Faktor von null oder nahe null kann nur ein Rechenfehler sein -
        # er wuerde die Anzeige stumm schalten. Lieber keine Korrektur.
        if not (0.2 <= m <= 10):
            out[name] = {"paare": len(w), "roh": roh, "faktor": None,
                         "verworfen": round(m, 3)}
            continue
        out[name] = {"paare": len(w), "roh": roh, "faktor": round(m, 2),
                     "q25": round(v[len(v) // 4], 2), "q75": round(v[3 * len(v) // 4], 2),
                     "mess_median": round(median([p["mess"] for p in w]), 2),
                     "radar_median": round(median([p["radar"] for p in w]), 2)}
    # Wie oft sieht die Station Regen, den das Radar ganz verpasst?
    verpasst = [p for p in alle if p["radar"] == 0 and p["mess"] > 0]
    out["_radar_blind"] = {"faelle": len(verpasst), "von": len(alle),
                           "mm_median": round(median([p["mess"] for p in verpasst]), 2) if verpasst else None}
    # Und umgekehrt: Wie oft sieht das Radar etwas, wo am Boden nichts
    # ankommt? Das ist die Zahl, an der die Schwelle der App haengt (v4.07,
    # 0,25 mm/h fuer "es regnet jetzt"). Aufgeschluesselt nach der Radarrate,
    # damit man sieht, ab wo das Signal traegt. Ein Treffer heisst dabei nur
    # "die Station mass mindestens 0,1 mm" - weniger kann sie nicht.
    leer = {}
    for lo, hi, nm in ((0.0, 0.1, "bis_0_1"), (0.1, 0.25, "0_1_bis_0_25"),
                       (0.25, 0.5, "0_25_bis_0_5"), (0.5, 1e9, "ab_0_5")):
        w = [p for p in alle if lo <= p["radar"] < hi and p["radar"] > 0]
        if w:
            leer[nm] = {"stunden": len(w),
                        "boden_trocken": sum(1 for p in w if p["mess"] == 0),
                        "anteil": round(sum(1 for p in w if p["mess"] == 0) / len(w), 2)}
    out["_boden_trocken"] = leer
    return out


def main():
    print("Radar-Eichung an den Bodenmessern, %s" % dt.datetime.now(dt.timezone.utc).strftime("%d.%m.%Y %H:%M UTC"))
    paare = sammeln()
    print("gesammelt: %d Paare" % len(paare))

    try:
        with open(LOG, encoding="utf-8") as fh:
            log = json.load(fh)
    except Exception:
        log = {}
    for p in paare:                         # nach Tag ablegen, doppelte Stunden ersetzen
        tag = p["t"][:10]
        log.setdefault(tag, [])
        log[tag] = [q for q in log[tag] if not (q["t"] == p["t"] and q["st"] == p["st"])]
        log[tag].append(p)
    for tag in log:
        log[tag].sort(key=lambda q: (q["t"], q["st"]))
    # Das Log wandert auf main, also darf es nicht unbegrenzt wachsen. Bei
    # vier Laeufen taeglich kaemen im Jahr rund 36.000 Paare zusammen; 60 Tage
    # reichen fuer einen stabilen Median und halten die Datei unter 300 KB.
    for tag in sorted(log)[:-TAGE_IM_LOG]:
        del log[tag]
    with open(LOG, "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False)

    erg = auswerten(log)
    print("\n%-8s %7s %6s %8s %9s %9s %11s %11s"
          % ("Klasse", "Paare", "roh", "Faktor", "25 %", "75 %", "Messung", "Radar"))
    for name, lo, hi in KLASSEN:
        e = erg[name]
        print("%-8s %7d %6d %8s %9s %9s %11s %11s"
              % (name, e["paare"], e.get("roh", 0),
                 ("%.2f" % e["faktor"]) if e.get("faktor") else "  -  ",
                 ("%.2f" % e["q25"]) if e.get("q25") else "  -  ",
                 ("%.2f" % e["q75"]) if e.get("q75") else "  -  ",
                 ("%.2f mm" % e["mess_median"]) if e.get("mess_median") else "  -  ",
                 ("%.2f mm" % e["radar_median"]) if e.get("radar_median") else "  -  "))
    b = erg["_radar_blind"]
    print("\nRadar sah nichts, Station mass etwas: %d von %d Paaren%s"
          % (b["faelle"], b["von"], (" (Median %.2f mm)" % b["mm_median"]) if b["mm_median"] else ""))
    print("Umgekehrt - Radar sah etwas, am Boden kam nichts an:")
    for nm, e in erg["_boden_trocken"].items():
        print("  Radarsumme %-13s %3d Stunden, davon %3d trocken (%.0f %%)"
              % (nm.replace("_", " ").replace("bis", "bis "), e["stunden"],
                 e["boden_trocken"], 100 * e["anteil"]))

    with open(AUS, "w", encoding="utf-8") as fh:
        json.dump({"stand": max(log) if log else None, "tage": len(log),
                   "paare": sum(len(v) for v in log.values()),
                   "regel": "Faktor = Median(Stationssumme / Radarsumme) je Stunde, "
                            "Klasse nach der Radarrate, ab %d Paaren; gezaehlt "
                            "werden nur Stunden mit mindestens %.1f mm an der "
                            "Station - darunter loest die Kippwaage nicht auf "
                            "und der Quotient waere Quantisierungsrauschen "
                            "(Feld \"roh\": Paare ohne diese Bedingung)"
                            % (MIN_PAARE, MIN_MESS),
                   "klassen": {n: {"von": lo, "bis": (None if hi > 1e8 else hi)} for n, lo, hi in KLASSEN},
                   "faktor": erg}, fh, ensure_ascii=False, indent=1)
    fertig = sum(1 for n, _, _ in KLASSEN if erg[n].get("faktor"))
    print("%s geschrieben (%d von %d Klassen belegt, %d Tage, %d Paare)"
          % (AUS, fertig, len(KLASSEN), len(log), sum(len(v) for v in log.values())))
    if fertig < len(KLASSEN):
        print("Solange eine Klasse leer ist, rechnet die App ohne Korrektur weiter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
