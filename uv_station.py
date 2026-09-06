#!/usr/bin/env python3
"""Stationsabgleich fuer die schwarze "max. moeglich"-Kurve der App.

WOZU
Am wolkenfreien 06.09.2026 lagen 23 BfS-Stationen mit voller Sonne vor. Die
Messspitzen streuen gegen unsere Modellkurve um +-15 %, und zwar NICHT nach
Breite oder Hoehe: Klippeneck (929 m) misst -19 %, Hohenpeissenberg (972 m,
100 km entfernt, ebenfalls wolkenlos) +1 %, Wurmberg (941 m) +19 %. Das ist
keine Physik, das sind die Geraete. Ein Fit an die Messungen statt an die
DWD-Kurven senkt die Streuung nur von 0,47 auf 0,39 UV - der Rest ist je
Station konstant.

Giessen-Wettenberg misst an drei Tagen mit 40, 75 und 100 % Sonne +15, +12
und +13 % - ein Offset, kein Wettereffekt.

WAS DIESES SKRIPT MACHT
Aus uv_klarlog.json (fuehrt uv_klarcheck.py taeglich fort) wird je Station
der MEDIAN von Messung/Modell an Tagen mit genug Sonne gebildet und nach
uv-station.json geschrieben. Die App liest die Datei und hebt oder senkt
ihre schwarze Kurve, wenn der Ort nahe genug an der Station liegt.

Median statt Mittel: ein einzelner Tag mit Wolkenverstaerkung (Messung ueber
Klarhimmel) soll den Faktor nicht verschieben.

Grenzen: mindestens MIN_TAGE Tage, Faktor auf [MIN_F, MAX_F] geklemmt.
"""
import json
import math

LOG = "uv_klarlog.json"
AUS = "uv-station.json"
MIN_SONNE = 0.70      # Anteil Sonnenschein 11-15 Uhr, damit ein Tag zaehlt
MIN_TAGE = 3          # so viele Tage braucht eine Station fuer einen Faktor
MIN_F, MAX_F = 0.80, 1.25
ABWEICHUNG = 0.05     # kleinere Abweichungen bleiben unkorrigiert


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def main():
    with open(LOG, "r", encoding="utf-8") as fh:
        log = json.load(fh)

    je_station = {}
    for datum, tag in sorted(log.items()):
        for slug, z in tag.items():
            if not z.get("verh"):
                continue
            if (z.get("sonne") or 0) < MIN_SONNE:
                continue
            je_station.setdefault(slug, {"tage": [], "la": z.get("la"),
                                         "h": z.get("h"), "name": z.get("name", slug)})
            je_station[slug]["tage"].append({"d": datum, "v": z["verh"]})

    out = {}
    for slug, e in sorted(je_station.items()):
        werte = [t["v"] for t in e["tage"]]
        if len(werte) < MIN_TAGE:
            continue
        m = median(werte)
        if abs(m - 1) < ABWEICHUNG:
            continue
        f = max(MIN_F, min(MAX_F, m))
        sd = math.sqrt(sum((v - m) ** 2 for v in werte) / (len(werte) - 1)) if len(werte) > 1 else 0
        out[slug] = {"faktor": round(f, 3), "tage": len(werte),
                     "streuung": round(sd, 3),
                     "von": min(t["d"] for t in e["tage"]),
                     "bis": max(t["d"] for t in e["tage"])}

    with open(AUS, "w", encoding="utf-8") as fh:
        json.dump({"stand": max(log) if log else None,
                   "regel": "Median(Messung/Modell) an Tagen mit >=%d %% Sonne, "
                            "ab %d Tagen, geklemmt auf %.2f-%.2f, unter %.0f %% "
                            "Abweichung kein Faktor"
                            % (100 * MIN_SONNE, MIN_TAGE, MIN_F, MAX_F, 100 * ABWEICHUNG),
                   "stationen": out}, fh, ensure_ascii=False, indent=1)

    print("uv-station.json: %d Stationen mit Faktor (von %d mit Daten)"
          % (len(out), len(je_station)))
    for slug, z in sorted(out.items(), key=lambda kv: -abs(kv[1]["faktor"] - 1)):
        print("  %-24s x%.3f  (%d Tage, Streuung %.3f)"
              % (slug[:24], z["faktor"], z["tage"], z["streuung"]))
    ohne = [(s, len(e["tage"])) for s, e in je_station.items() if len(e["tage"]) < MIN_TAGE]
    if ohne:
        print("  noch zu wenige Tage: %d Stationen (%s ...)"
              % (len(ohne), ", ".join("%s %d" % o for o in sorted(ohne)[:4])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
