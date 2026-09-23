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

DIE ZWEITE KLASSE: 70 BIS 90 PROZENT, ABER NUR BEI KLEINER STREUUNG
Die Schwelle 0,90 ist fuer einen gut vermessenen Ort zu streng. Wettenberg
hatte in 15 Tagen genau EINEN Tag ueber 90 % Sonne, aber sechs zwischen 70
und 90 %, die dasselbe sagen (Median 1,118 gegen 1,134, 1,5 % auseinander).
Der Faktor stand deshalb auf tage: 1 und wurde von der Schrumpfung auf
1,094 statt 1,113 gezogen.

Die Schwelle zu senken bleibt falsch - die 102-Stationstage-Statistik oben
gilt weiter. Stattdessen wird die Klasse 70-90 % JE STATION zugelassen,
wenn sie in sich stimmig ist. Zwei Bedingungen, beide noetig:

    mindestens MIN_TAGE_2 Tage   und   Streuung <= MAX_STREU_2

Die Mindestanzahl ist nicht Beiwerk, sie ist die halbe Regel: Ein einzelner
Tag hat Streuung 0,000 und saehe damit am vertrauenswuerdigsten aus.
Schneefernerhaus ist genau dieser Fall - ein 70-90-Tag, Streuung 0,000, und
er liegt 17,5 % neben den sieben Klartagen derselben Station.

Nachgemessen an den 24 Stationen, die BEIDES haben (>=90 % und 70-90 %),
Abweichung der beiden Mediane voneinander:

    ohne Mindestanzahl, SD<=0,06   18 zugelassen   Median 2,1 %   MAX 17,5 %
    ab 2 Tagen,         SD<=0,06   11 zugelassen   Median 1,2 %   max  4,2 %
    ab 3 Tagen,         SD<=0,06    6 zugelassen   Median 0,8 %   max  3,4 %

Die Grenze 0,06 ist nicht gerundet, sondern die Luecke in den Daten: die
Streuungen der Gruppen ab drei Tagen sind 0,035 0,037 0,038 0,045 0,048
0,054 | 0,069 0,076 0,089 0,291. Sie wirft die beiden schaedlichsten
Faelle hinaus (Langen +5,7 %, Schweinfurt -6,5 %) und laesst Wettenberg
(0,054) herein.

DER WAECHTER (23.09.2026)
Ein Stationsfaktor soll das GERAET erfassen, nicht einen Fehler des Modells.
Ist die Geo-Korrektur in uvCamsFaktor falsch, schlucken die Faktoren den
Fehler stillschweigend - und wo keine Station in der Naehe steht, bleibt er
stehen. Genau das ist bis v4.30 passiert: die Faktoren trugen einen
Breitentrend von +0,033 je Grad (t = 3,6), Norderney 1,175, Cuxhaven 1,227,
Stuttgart 0,930. Die Faktoren sahen einzeln plausibel aus, erst die
Regression ueber alle zeigte das Muster.

Darum prueft jeder Lauf, ob die Stationsmediane systematisch von Breite oder
Hoehe abhaengen: Regression roh ~ 1 + (Breite-50) + Hoehe[km] ueber alle
Stationen mit mindestens WAECHTER_TAGE Tagen. Liegt |t| fuer Breite oder Hoehe
ueber WAECHTER_T, steht in uv-station.json "alarm": true und im Lauf eine
WARNUNG - dann gehoert die Geo-Korrektur neu gefittet, nicht der Faktor
vergroessert. Der alte Fehler haette die Schwelle mit t = 3,6 gerissen.

Die Schwelle 3 statt 2: der Waechter laeuft taeglich, und bei t = 2 schluege
er bei rund jedem zwanzigsten Lauf ohne Grund an.

Jeder Stationstag wird in uv-station-protokoll.json festgehalten -
genommen oder verworfen, mit Grund, zum Nachpruefen.
"""
import json
import math

LOG = "uv_klarlog.json"
AUS = "uv-station.json"
MIN_SONNE = 0.90      # Anteil Sonnenschein 11-15 Uhr, damit ein Tag sicher zaehlt
MIN_SONNE_2 = 0.70    # zweite Klasse: nur zugelassen, wenn sie in sich stimmig ist
MIN_TAGE_2 = 3        # so viele Tage braucht die zweite Klasse (sonst ist SD=0 ein Artefakt)
MAX_STREU_2 = 0.06    # und so klein muss ihre Streuung sein
PROTOKOLL = "uv-station-protokoll.json"   # jeder Stationstag mit Grund
MIN_SICHER = 3        # ab so vielen Tagen gilt der Faktor nicht mehr als vorlaeufig
PRIOR = 0.43          # Gewicht der Pseudo-Beobachtung: ein Tag zaehlt zu 70 %
MIN_F, MAX_F = 0.80, 1.25
ABWEICHUNG = 0.05     # kleinere Abweichungen bleiben unkorrigiert
WAECHTER_TAGE = 3     # so viele Tage braucht eine Station fuer den Waechter
WAECHTER_MIN_ST = 10  # darunter rechnet der Waechter nicht
WAECHTER_T = 3.0      # ab diesem |t| schlaegt er an


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def streuung(xs):
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((v - m) ** 2 for v in xs) / (len(xs) - 1))


def waechter(punkte):
    """punkte: [(breite, hoehe_m, median_verh), ...]. Regression gegen Breite und
    Hoehe, gibt Steigungen, Fehler und t zurueck. Siehe DER WAECHTER oben."""
    D = [(la - 50.0, h / 1000.0, q) for la, h, q in punkte]
    n = len(D)
    if n < WAECHTER_MIN_ST:
        return {"stationen": n, "alarm": False,
                "hinweis": "zu wenige Stationen (mindestens %d)" % WAECHTER_MIN_ST}
    X = [[1.0, a, b] for a, b, _ in D]
    y = [q for _, _, q in D]
    m = 3
    A = [[sum(X[i][r] * X[i][c] for i in range(n)) for c in range(m)] for r in range(m)]
    M = [A[r][:] + [float(r == c) for c in range(m)] for r in range(m)]
    for i in range(m):
        p = max(range(i, m), key=lambda r: abs(M[r][i]))
        M[i], M[p] = M[p], M[i]
        d = M[i][i]
        if abs(d) < 1e-12:
            return {"stationen": n, "alarm": False, "hinweis": "Breite und Hoehe nicht trennbar"}
        M[i] = [v / d for v in M[i]]
        for r in range(m):
            if r != i:
                f = M[r][i]
                M[r] = [M[r][c] - f * M[i][c] for c in range(2 * m)]
    inv = [row[m:] for row in M]
    bv = [sum(X[i][r] * y[i] for i in range(n)) for r in range(m)]
    b = [sum(inv[r][c] * bv[c] for c in range(m)) for r in range(m)]
    rest = sum((y[i] - sum(X[i][j] * b[j] for j in range(m))) ** 2 for i in range(n))
    s2 = rest / (n - m)
    se = [math.sqrt(max(0.0, s2 * inv[i][i])) for i in range(m)]
    t = [b[i] / se[i] if se[i] > 0 else 0.0 for i in range(m)]
    alarm = abs(t[1]) >= WAECHTER_T or abs(t[2]) >= WAECHTER_T
    return {"stationen": n,
            "breite": {"steigung": round(b[1], 4), "fehler": round(se[1], 4), "t": round(t[1], 2)},
            "hoehe": {"steigung": round(b[2], 4), "fehler": round(se[2], 4), "t": round(t[2], 2)},
            "mittel": round(b[0], 3), "reststreuung": round(math.sqrt(s2), 3),
            "schwelle_t": WAECHTER_T, "alarm": alarm,
            "hinweis": ("Die Stationsfaktoren haengen systematisch an Breite oder Hoehe - "
                        "die Geo-Korrektur in uvCamsFaktor/cams_faktor neu fitten, "
                        "nicht die Faktoren vergroessern.") if alarm else "kein Trend"}


def main():
    with open(LOG, "r", encoding="utf-8") as fh:
        log = json.load(fh)

    # 1. Durchgang: alle brauchbaren Stationstage einsammeln und in die beiden
    #    Sonnenklassen einsortieren. Ob die zweite zaehlt, entscheidet sich erst,
    #    wenn ALLE Tage der Station beisammen sind - deshalb zwei Durchgaenge.
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
            if so < MIN_SONNE_2:
                prot.append({"d": datum, "st": slug, "genommen": False,
                             "sonne": round(so, 2), "verh": z["verh"],
                             "grund": "nur %.0f %% Sonne 11-15 Uhr (Schwelle %.0f %%) - "
                                      "Maximum waere ein Wolkenrand-Ausreisser"
                                      % (100 * so, 100 * MIN_SONNE_2)})
                continue
            e = je_station.setdefault(slug, {"klar": [], "teil": [], "la": z.get("la"),
                                             "h": z.get("h"), "name": z.get("name", slug)})
            e["klar" if so >= MIN_SONNE else "teil"].append(
                {"d": datum, "v": z["verh"], "so": so})

    # 2. Durchgang: je Station entscheiden, ob die Klasse 70-90 % mitzaehlt,
    #    und erst dann das Protokoll fuer diese Tage schreiben.
    out = {}
    fuer_waechter = []
    for slug, e in sorted(je_station.items()):
        teil = e["teil"]
        sd2 = streuung([t["v"] for t in teil])
        zweite = len(teil) >= MIN_TAGE_2 and sd2 <= MAX_STREU_2
        if teil:
            grund = ("%d Tage mit 70-90 %% Sonne, Streuung %.3f - stimmig, zaehlen mit"
                     % (len(teil), sd2)) if zweite else (
                     "%d Tage mit 70-90 %% Sonne, Streuung %.3f - %s"
                     % (len(teil), sd2,
                        "zu wenige (mindestens %d)" % MIN_TAGE_2 if len(teil) < MIN_TAGE_2
                        else "zu unruhig (hoechstens %.2f)" % MAX_STREU_2))
        for t in e["klar"]:
            prot.append({"d": t["d"], "st": slug, "genommen": True,
                         "sonne": round(t["so"], 2), "verh": t["v"], "grund": "klar"})
        for t in teil:
            prot.append({"d": t["d"], "st": slug, "genommen": zweite,
                         "sonne": round(t["so"], 2), "verh": t["v"], "grund": grund})

        tage = e["klar"] + (teil if zweite else [])
        if not tage:
            continue
        werte = [t["v"] for t in tage]
        n = len(werte)
        m = median(werte)
        if n >= WAECHTER_TAGE and e.get("la") is not None and e.get("h") is not None:
            fuer_waechter.append((e["la"], e["h"], m))
        f = max(MIN_F, min(MAX_F, 1 + (m - 1) * n / (n + PRIOR)))   # Schrumpfung zur 1
        if abs(f - 1) < ABWEICHUNG:
            continue
        out[slug] = {"faktor": round(f, 3), "roh": round(m, 3), "tage": n,
                     "vorlaeufig": n < MIN_SICHER,
                     "streuung": round(streuung(werte), 3),
                     "klare_tage": len(e["klar"]),
                     "teiltage": len(teil) if zweite else 0,
                     "teiltage_verworfen": 0 if zweite else len(teil),
                     "von": min(t["d"] for t in tage),
                     "bis": max(t["d"] for t in tage)}

    w = waechter(fuer_waechter)
    with open(AUS, "w", encoding="utf-8") as fh:
        json.dump({"stand": max(log) if log else None,
                   "waechter": w,
                   "regel": "Median(Messung/Modell) an Tagen mit >=%d %% Sonne; Tage mit "
                            "%d-%d %% zaehlen mit, wenn es je Station mindestens %d sind "
                            "und ihre Streuung hoechstens %.2f betraegt. Zur 1 gedaempft "
                            "mit n/(n+%.2f) - ein Tag zaehlt zu %.0f %%, geklemmt auf "
                            "%.2f-%.2f, unter %.0f %% Abweichung kein Faktor, unter %d "
                            "Tagen vorlaeufig"
                            % (100 * MIN_SONNE, 100 * MIN_SONNE_2, 100 * MIN_SONNE,
                               MIN_TAGE_2, MAX_STREU_2, PRIOR, 100 / (1 + PRIOR),
                               MIN_F, MAX_F, 100 * ABWEICHUNG, MIN_SICHER),
                   "stationen": out}, fh, ensure_ascii=False, indent=1)

    with open(PROTOKOLL, "w", encoding="utf-8") as fh:
        json.dump({"regel": "MIN_SONNE = %.0f %%; Klasse %.0f-%.0f %% nur bei >=%d Tagen und "
                            "Streuung <=%.2f je Station"
                            % (100 * MIN_SONNE, 100 * MIN_SONNE_2, 100 * MIN_SONNE,
                               MIN_TAGE_2, MAX_STREU_2),
                   "stationstage": prot}, fh, ensure_ascii=False, indent=1)
    gen = sum(1 for p in prot if p["genommen"])
    print("Protokoll: %d Stationstage, %d genommen, %d verworfen (%s)"
          % (len(prot), gen, len(prot) - gen, PROTOKOLL))
    print("uv-station.json: %d Stationen mit Faktor (von %d mit Daten)"
          % (len(out), len(je_station)))
    for slug, z in sorted(out.items(), key=lambda kv: -abs(kv[1]["faktor"] - 1)):
        print("  %-24s x%.3f  (roh %.3f, %d Tage = %d klar + %d teils%s, Streuung %.3f)"
              % (slug[:24], z["faktor"], z["roh"], z["tage"], z["klare_tage"],
                 z["teiltage"], ", vorlaeufig" if z["vorlaeufig"] else "", z["streuung"]))
    if w.get("breite"):
        print("\nWaechter (%d Stationen): Breite %+.4f je Grad (t = %+.1f), Hoehe %+.4f je km (t = %+.1f)"
              % (w["stationen"], w["breite"]["steigung"], w["breite"]["t"],
                 w["hoehe"]["steigung"], w["hoehe"]["t"]))
        print("  WARNUNG: " + w["hinweis"] if w["alarm"] else "  kein Trend - die Faktoren messen die Geraete")
    else:
        print("\nWaechter: " + w["hinweis"])
    neutral = len(je_station) - len(out)
    if neutral:
        print("  ohne Faktor (Abweichung unter %.0f %%): %d Stationen" % (100 * ABWEICHUNG, neutral))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
