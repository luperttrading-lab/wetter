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

Ab dem ERSTEN Tag wird ein Faktor geschrieben, aber zur 1 hin gedaempft:
    faktor = 1 + (median - 1) * n / (n + PRIOR)
Das ist die uebliche Schrumpfung zum neutralen Wert; PRIOR ist das Gewicht
der Pseudo-Beobachtung "kein Fehler". Mit PRIOR = 0,43 zaehlt ein Tag zu
70 %, zwei zu 82 %, drei zu 87 %, fuenf zu 92 %, zehn zu 96 %.

Warum nicht PRIOR = 1 (ein Tag zu 50 %), die vorsichtigere Wahl: Die App
hat genau einen Nutzer, der die amtliche BfS-Grafik direkt darunter sieht.
Ein zu grosser Faktor faellt binnen eines Tages auf und ist am naechsten
Lauf korrigiert - die Richtung frueher zu sehen ist mehr wert als die
halbe Vorsicht. Bei mehreren Nutzern waere PRIOR = 1 die richtige Wahl.

Unter MIN_SICHER Tagen gilt der Faktor als vorlaeufig; die App schreibt
das dazu.

Grenzen: Faktor auf [MIN_F, MAX_F] geklemmt.

WARUM MIN_SONNE = 0,90 UND NICHT 0,70
Das Tagesmaximum der Messung allein ist an durchbrochenen Tagen wertlos:
es ist dann ein Wolkenrand-Ausreisser und liegt UEBER dem Klarhimmelwert.
An 102 Stationstagen (05.-07.09.2026) nachgemessen, Median von
Messung/Modell nach Sonnenanteil der Mittagsstunden:

    unter 50 % Sonne   36 Tage   Median 0,944   Streuung 0,251
    50 bis 70 %        16 Tage   Median 1,209   Streuung 0,122
    70 bis 90 %        14 Tage   Median 1,036   Streuung 0,106
    ueber 90 %         36 Tage   Median 0,982   Streuung 0,089

Die Klasse 50-70 % ist der Ausreisser-Bereich: 9 von 16 Tagen ueber 1,15.
Genau dort greift eine Schwelle von 0,70 noch mit. Ab 90 % Sonne sinkt die
Streuung auf ein Drittel. Der frueher benutzte Wert 0,70 liess die
Wolkenrand-Tage teilweise durch.

Jeder Stationstag wird in uv-station-protokoll.json festgehalten -
genommen oder verworfen, mit Grund, zum Nachpruefen.
"""
import json
import math

LOG = "uv_klarlog.json"
AUS = "uv-station.json"
MIN_SONNE = 0.90      # Anteil Sonnenschein 11-15 Uhr, damit ein Tag zaehlt
PROTOKOLL = "uv-station-protokoll.json"   # jeder Stationstag mit Grund
MIN_SICHER = 3        # ab so vielen Tagen gilt der Faktor nicht mehr als vorlaeufig
PRIOR = 0.43          # Gewicht der Pseudo-Beobachtung: ein Tag zaehlt zu 70 %
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
    prot = []
    for datum, tag in sorted(log.items()):
        for slug, z in sorted(tag.items()):
            so = z.get("sonne")
            if not z.get("verh"):
                prot.append({"d": datum, "st": slug, "genommen": False,
                             "grund": "kein Verhaeltnis (Messung oder Modell fehlt)"})
                continue
            if so is None:
                prot.append({"d": datum, "st": slug, "genommen": False,
                             "grund": "keine Sonnenscheindauer in Reichweite"})
                continue
            if so < MIN_SONNE:
                prot.append({"d": datum, "st": slug, "genommen": False,
                             "sonne": round(so, 2), "verh": z["verh"],
                             "grund": "nur %.0f %% Sonne 11-15 Uhr (Schwelle %.0f %%) - "
                                      "Maximum waere ein Wolkenrand-Ausreisser"
                                      % (100 * so, 100 * MIN_SONNE)})
                continue
            prot.append({"d": datum, "st": slug, "genommen": True,
                         "sonne": round(so, 2), "verh": z["verh"], "grund": "klar"})
            je_station.setdefault(slug, {"tage": [], "la": z.get("la"),
                                         "h": z.get("h"), "name": z.get("name", slug)})
            je_station[slug]["tage"].append({"d": datum, "v": z["verh"]})

    out = {}
    for slug, e in sorted(je_station.items()):
        werte = [t["v"] for t in e["tage"]]
        n = len(werte)
        m = median(werte)
        f = max(MIN_F, min(MAX_F, 1 + (m - 1) * n / (n + PRIOR)))   # Schrumpfung zur 1
        if abs(f - 1) < ABWEICHUNG:
            continue
        sd = math.sqrt(sum((v - m) ** 2 for v in werte) / (n - 1)) if n > 1 else 0
        out[slug] = {"faktor": round(f, 3), "roh": round(m, 3), "tage": n,
                     "vorlaeufig": n < MIN_SICHER,
                     "streuung": round(sd, 3),
                     "von": min(t["d"] for t in e["tage"]),
                     "bis": max(t["d"] for t in e["tage"])}

    with open(AUS, "w", encoding="utf-8") as fh:
        json.dump({"stand": max(log) if log else None,
                   "regel": "Median(Messung/Modell) an Tagen mit >=%d %% Sonne, "
                            "zur 1 gedaempft mit n/(n+%.2f) - ein Tag zaehlt zu "
                            "%.0f %%, geklemmt auf %.2f-%.2f, unter %.0f %% "
                            "Abweichung kein Faktor, unter %d Tagen vorlaeufig"
                            % (100 * MIN_SONNE, PRIOR, 100 / (1 + PRIOR),
                               MIN_F, MAX_F, 100 * ABWEICHUNG, MIN_SICHER),
                   "stationen": out}, fh, ensure_ascii=False, indent=1)

    with open(PROTOKOLL, "w", encoding="utf-8") as fh:
        json.dump({"regel": "MIN_SONNE = %.0f %% Sonnenschein 11-15 Uhr" % (100 * MIN_SONNE),
                   "stationstage": prot}, fh, ensure_ascii=False, indent=1)
    gen = sum(1 for p in prot if p["genommen"])
    print("Protokoll: %d Stationstage, %d genommen, %d verworfen (%s)"
          % (len(prot), gen, len(prot) - gen, PROTOKOLL))
    print("uv-station.json: %d Stationen mit Faktor (von %d mit Daten)"
          % (len(out), len(je_station)))
    for slug, z in sorted(out.items(), key=lambda kv: -abs(kv[1]["faktor"] - 1)):
        print("  %-24s x%.3f  (roh %.3f, %d Tage%s, Streuung %.3f)"
              % (slug[:24], z["faktor"], z["roh"], z["tage"],
                 ", vorlaeufig" if z["vorlaeufig"] else "", z["streuung"]))
    neutral = len(je_station) - len(out)
    if neutral:
        print("  ohne Faktor (Abweichung unter %.0f %%): %d Stationen" % (100 * ABWEICHUNG, neutral))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
