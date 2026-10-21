#!/usr/bin/env python3
"""Auswertung der Messreihe aus ruc.py: wer sagt den Regen in Giessen besser vorher?

Aufruf: ruc_auswertung.py <daten-ordner>  (liest <daten>/ruc/*.jsonl, schreibt
<daten>/ruc/auswertung.json und auswertung.md)

Wahrheit: Stundenwerte der Station Giessen/Wettenberg (DWD 01639) ueber Bright
Sky, nur Messungen (keine Vorhersagezeilen), Wert mit Stempel t = Stunde vor t.

Verglichen wird, was zum SELBEN Abrufzeitpunkt vorlag: je Satz und je Zielstunde
v das Paar (Vorlauf = v - Abruf, aufgerundet auf Stunden). Nur Paare, fuer die
ALLE Modelle einen Wert haben (gemeinsame Stichprobe) - sonst vergleicht man
verschiedene Wetterlagen.

Kennzahlen je Vorlaufgruppe:
  Regen ja/nein ab 0,1 mm/h (kleinste Stufe der Station; entspricht NOWCAST_TH
  der App) und ab 0,5 mm/h: Trefferquote POD, Fehlalarmquote FAR, CSI;
  mittlerer absoluter Fehler der Menge; Temperatur MAE und Bias.
Stundenwerte sind stark abhaengig (eine Regenfront = viele Stunden). Darum dazu
ein TAGESvergleich RUC gegen best_match (MAE des Regens je Tag) mit
Vorzeichentest - erst der sagt etwas ueber Zufall oder nicht.
"""
import datetime as dt
import glob
import json
import math
import os
import sys
import urllib.request

STATION = "01639"
GRUPPEN = [(1, 1), (2, 2), (3, 3), (4, 6), (7, 9), (10, 13)]
UA = {"User-Agent": "wetter-app ruc-vergleich (github.com/luperttrading-lab/wetter)"}


def holen(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read())


def zeit(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)


def messung(von, bis):
    """{Endzeit: (Regen mm, Temperatur)} - nur Messquellen, in Wochenstuecken."""
    out, a = {}, von
    while a < bis:
        b = min(a + dt.timedelta(days=7), bis)
        j = holen(f"https://api.brightsky.dev/weather?dwd_station_id={STATION}"
                  f"&date={a:%Y-%m-%dT%H:%MZ}&last_date={b:%Y-%m-%dT%H:%MZ}&tz=Etc/UTC")
        art = {s["id"]: s["observation_type"] for s in j.get("sources", [])}
        for w in j.get("weather", []):
            if art.get(w.get("source_id")) == "forecast":
                continue
            t = dt.datetime.fromisoformat(w["timestamp"]).astimezone(dt.timezone.utc)
            out[t] = (w.get("precipitation"), w.get("temperature"))
        a = b
    return out


def modelle(s):
    """{Modell: {Endzeit: (Regen, T2m)}} fuer einen Satz."""
    m = {}
    r = s.get("ruc")
    if r:
        m["RUC"] = {zeit(e): (r["regen"][i], r["t2m"][i]) for i, e in enumerate(r["ende"])}
        m["RUC 5 km"] = {zeit(e): (r["regen5_mittel"][i], r["t2m"][i]) for i, e in enumerate(r["ende"])}
    om = s.get("om")
    if om:
        for k, name in (("best_match", "App (best_match)"), ("icon_d2", "ICON-D2")):
            x = om.get(k) or {}
            if x.get("regen"):
                m[name] = {zeit(e): (x["regen"][i], (x.get("t2m") or [None] * 99)[i]) for i, e in enumerate(om["ende"])}
    mo = s.get("mosmix")
    if mo and mo.get("regen"):
        m["MOSMIX"] = {zeit(e): (mo["regen"][i], mo["t2m"][i]) for i, e in enumerate(mo["ende"])}
    return m


def kennzahlen(paare, schwelle):
    a = b = c = d = 0
    for f, y in paare:
        fj, yj = f >= schwelle, y >= schwelle
        a += fj and yj; b += fj and not yj; c += yj and not fj; d += not fj and not yj
    q = lambda z, n: round(z / n, 3) if n else None
    return {"treffer": a, "fehlalarm": b, "verpasst": c, "trocken_richtig": d,
            "POD": q(a, a + c), "FAR": q(b, a + b), "CSI": q(a, a + b + c)}


def vorzeichentest(besser, schlechter):
    n = besser + schlechter
    if not n:
        return None
    k = min(besser, schlechter)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return round(min(1.0, p), 4)


def main():
    ordner = os.path.join(sys.argv[1] if len(sys.argv) > 1 else ".", "ruc")
    saetze = []
    for f in sorted(glob.glob(os.path.join(ordner, "*.jsonl"))):
        saetze += [json.loads(z) for z in open(f) if z.strip()]
    if not saetze:
        print("keine Saetze")
        return 0
    jetzt = dt.datetime.now(dt.timezone.utc)
    grenze = jetzt - dt.timedelta(hours=3)          # juengste Messungen kommen spaet und werden noch korrigiert
    von = min(zeit(s["abruf"]) for s in saetze) - dt.timedelta(hours=1)
    wahr = messung(von, min(grenze, max(zeit(s["abruf"]) for s in saetze) + dt.timedelta(hours=15)))

    # gemeinsame Stichprobe: (Satz, Zielstunde) mit Messung und allen Modellen
    namen = ["RUC", "RUC 5 km", "App (best_match)", "ICON-D2", "MOSMIX"]
    paare = {n: {} for n in namen}                   # n -> Vorlauf -> [(f, y, ft, yt, tag)]
    fehlend = {n: 0 for n in namen}
    for s in saetze:
        ab = zeit(s["abruf"])
        m = modelle(s)
        for v, (y, yt) in wahr.items():
            if v <= ab or v > grenze or y is None:
                continue
            vl = math.ceil((v - ab).total_seconds() / 3600)
            if vl > 13:
                continue
            werte = {n: m.get(n, {}).get(v) for n in namen}
            for n in namen:
                if werte[n] is None or werte[n][0] is None:
                    fehlend[n] += 1
            if any(werte[n] is None or werte[n][0] is None for n in namen):
                continue
            for n in namen:
                f, ft = werte[n]
                paare[n].setdefault(vl, []).append((f, y, ft, yt, v.date().isoformat()))

    erg = {"stand": jetzt.strftime("%Y-%m-%d %H:%M UTC"), "saetze": len(saetze),
           "messstunden": len(wahr), "ausgelassen_fehlend": fehlend, "gruppen": {}}
    for g0, g1 in GRUPPEN + [(1, 13)]:
        key = f"{g0}-{g1} h" if g0 != g1 else f"{g0} h"
        erg["gruppen"][key] = {}
        for n in namen:
            p = [x for vl in range(g0, g1 + 1) for x in paare[n].get(vl, [])]
            if not p:
                continue
            tt = [(ft, yt) for _, _, ft, yt, _ in p if ft is not None and yt is not None]
            erg["gruppen"][key][n] = {
                "n": len(p), "regen_stunden_gemessen": sum(y >= 0.1 for _, y, *_ in p),
                "ab_0,1": kennzahlen([(f, y) for f, y, *_ in p], 0.1),
                "ab_0,5": kennzahlen([(f, y) for f, y, *_ in p], 0.5),
                "regen_MAE": round(sum(abs(f - y) for f, y, *_ in p) / len(p), 3),
                "t2m_MAE": round(sum(abs(a - b) for a, b in tt) / len(tt), 2) if tt else None,
                "t2m_bias": round(sum(a - b for a, b in tt) / len(tt), 2) if tt else None}

    # Tagesvergleich RUC gegen App, Regen-MAE ueber alle Vorlaufe 1-13 h
    tage = {}
    for n in ("RUC", "App (best_match)"):
        for vl, lst in paare[n].items():
            for f, y, _, _, tag in lst:
                tage.setdefault(tag, {}).setdefault(n, []).append(abs(f - y))
    besser = schlechter = gleich = 0
    for tag, d in tage.items():
        if len(d) < 2:
            continue
        a, b = sum(d["RUC"]) / len(d["RUC"]), sum(d["App (best_match)"]) / len(d["App (best_match)"])
        if abs(a - b) < 0.005:
            gleich += 1
        elif a < b:
            besser += 1
        else:
            schlechter += 1
    erg["tage_RUC_gegen_App"] = {"besser": besser, "schlechter": schlechter, "gleich": gleich,
                                 "p_vorzeichentest": vorzeichentest(besser, schlechter)}

    with open(os.path.join(ordner, "auswertung.json"), "w") as f:
        json.dump(erg, f, ensure_ascii=False, indent=1)
    zeilen = [f"# ICON-D2-RUC gegen die App - Station Giessen/Wettenberg", "",
              f"Stand {erg['stand']} · {erg['saetze']} Abrufe · Tagesvergleich RUC/App: "
              f"besser {besser}, schlechter {schlechter}, gleich {gleich}, p = {erg['tage_RUC_gegen_App']['p_vorzeichentest']}", ""]
    for key, d in erg["gruppen"].items():
        if not d:
            continue
        zeilen += [f"## Vorlauf {key}", "", "| Modell | n | Regenstd. | CSI 0,1 | POD | FAR | CSI 0,5 | MAE mm | T MAE | T Bias |",
                   "|---|---|---|---|---|---|---|---|---|---|"]
        for n, x in d.items():
            k1, k5 = x["ab_0,1"], x["ab_0,5"]
            zeilen.append(f"| {n} | {x['n']} | {x['regen_stunden_gemessen']} | {k1['CSI']} | {k1['POD']} | {k1['FAR']} | "
                          f"{k5['CSI']} | {x['regen_MAE']} | {x['t2m_MAE']} | {x['t2m_bias']} |")
        zeilen.append("")
    with open(os.path.join(ordner, "auswertung.md"), "w") as f:
        f.write("\n".join(zeilen))
    print("\n".join(zeilen[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
