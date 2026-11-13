#!/usr/bin/env python3
"""Baut metar-stationen.json: alle METAR-/ASOS-Stationen, die in den letzten 3 Tagen gemeldet haben.

Quelle: Iowa Environmental Mesonet (Iowa State University), currents.json mit networkclass=ASOS.
Die App braucht die Liste, um ausserhalb des DWD-Gebiets die naechste Flughafen-Messung zu finden (v6.83);
die Messwerte selbst holt sie direkt von IEM (obhistory.json, CORS erlaubt).

Aufruf (Repo-Wurzel):  python3 tools/metar_stationen.py
Die Antwort von IEM ist rund 50 MB gross und braucht etwa 15 s. Stationen aendern sich selten - die Datei von Hand
neu bauen, wenn Orte ohne Station auffallen.
"""
import json, sys, urllib.request, datetime

URL = "https://mesonet.agron.iastate.edu/api/1/currents.json?networkclass=ASOS&minutes=4320"
ZIEL = "metar-stationen.json"


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "wetter-app-stationsliste"})
    with urllib.request.urlopen(req, timeout=120) as r:
        daten = json.load(r)["data"]
    netze, idx, s = [], {}, []
    for x in daten:
        n = x.get("network") or ""
        if not n.endswith("ASOS"):          # nur METAR/ASOS, keine Messnetze (DCP, RWIS, BUFR ...)
            continue
        la, lo = x.get("lat"), x.get("lon")
        if la is None or lo is None or x.get("tmpf") is None:
            continue
        if n not in idx:
            idx[n] = len(netze); netze.append(n)
        name = " ".join(str(x.get("name") or x["station"]).split())[:32]
        s.append([x["station"], idx[n], round(la, 3), round(lo, 3), name])
    s.sort(key=lambda z: (z[1], z[0]))
    aus = {"stand": datetime.date.today().isoformat(),
           "quelle": "Iowa Environmental Mesonet, currents.json networkclass=ASOS (letzte 3 Tage)",
           "felder": ["id", "netz", "lat", "lon", "name"], "netze": netze, "s": s}
    with open(ZIEL, "w", encoding="utf-8") as f:
        json.dump(aus, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(s)} Stationen in {len(netze)} Netzen -> {ZIEL}")


if __name__ == "__main__":
    sys.exit(main())
