#!/usr/bin/env python3
"""DWD-Pollenflug-Gefahrenindex -> pollen.json fuer die App (Kachel "Pollen").

Die DWD-Datei (opendata.dwd.de/.../s31fg.json) traegt keinen CORS-Kopf - der
Browser darf sie nicht direkt lesen. Dieser Lauf holt sie einmal am Tag und
legt eine kompakte Fassung neben die App (rund 5 KB, gleiche Herkunft).

Index je Pollenart und Tag: "0", "0-1", "1", "1-2", "2", "2-3", "3"
(keine ... hohe Belastung). Drei Tage: heute, morgen, uebermorgen - bezogen
auf den Tag von "stand" (der DWD aktualisiert gegen 11 Uhr). Die App rechnet
das auf den aktuellen Tag um.
"""
import json, sys, urllib.request

URL = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"
ARTEN = ["Hasel", "Erle", "Esche", "Birke", "Graeser", "Roggen", "Beifuss", "Ambrosia"]


def main():
    with urllib.request.urlopen(URL, timeout=60) as f:
        d = json.load(f)
    reg = {}
    for c in d["content"]:
        rid = c["partregion_id"] if c["partregion_id"] != -1 else c["region_id"]
        p = c["Pollen"]
        reg[str(rid)] = {
            "n": c["partregion_name"] or c["region_name"],
            "p": {a: [p[a]["today"], p[a]["tomorrow"], p[a]["dayafter_to"]] for a in ARTEN if a in p},
        }
    if len(reg) < 20:
        sys.exit(f"nur {len(reg)} Regionen - Datei unvollstaendig, nichts geschrieben")
    out = {"stand": d.get("last_update"), "naechste": d.get("next_update"), "r": reg}
    neu = json.dumps(out, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    try:
        alt = open("pollen.json", encoding="utf-8").read().strip()
    except FileNotFoundError:
        alt = ""
    if neu == alt:
        print("unveraendert")
        return
    with open("pollen.json", "w", encoding="utf-8") as f:
        f.write(neu + "\n")
    print("geschrieben", len(neu), "Bytes, Stand", out["stand"])


if __name__ == "__main__":
    main()
