#!/usr/bin/env python3
"""Wolkendurchlass: aus welchem Exponenten wird aus Strahlung UV?

DIE FRAGE
Die App rechnet UV = Klarhimmel x Durchlass^p mit festem p = 0,5 (Wurzel).
Die Wurzel steht dafuer, dass UV Wolken besser durchdringt als die
Gesamtstrahlung: bei 25 % Strahlungsdurchlass kommt noch die Haelfte des
UV an. Am 07.09.2026 in Giessen zeigte der Zehn-Minuten-Vergleich gegen die
BfS-Messung aber ein gegenlaeufiges Muster:

  dichte Wolke (Durchlass 26-41 %)      Modell 8 bis 12 % ZU HOCH
  volle Sonne, aber Durchlass 74-84 %   Modell 8 bis 15 % ZU NIEDRIG

Der zweite Fall sind duenne hohe Schleier: die Sonne scheint durchgehend
(10 von 10 Minuten), die Waermestrahlung wird trotzdem gedaempft - und das
UV weit weniger als die Wurzel unterstellt. Ein einziger Exponent kann
beide Faelle nicht treffen. Ein von der Sonnenscheindauer abhaengiger
schon: bei durchgehender Sonne flacher, bei geschlossener Decke steiler.

WAS DIESES SKRIPT MACHT
Fuer jede BfS-Station mit einer DWD-Strahlungsstation in der Naehe werden
die Zehn-Minuten-Paare (Strahlungsdurchlass, gemessenes UV / Klarhimmel)
gesammelt und in uv_durchlasslog.json fortgeschrieben. Aus dem Log wird je
Sonnenschein-Klasse der Exponent geschaetzt - als Regression durch den
Ursprung ueber alle Punkte der Klasse:

    ln(q) = p * ln(dl)   ->   p = SUM(ln dl * ln q) / SUM(ln dl)^2

NICHT punktweise als Mittel von ln(q)/ln(dl): bei Durchlass nahe 100 % geht
ln(dl) gegen null, und winzige Ablesefehler im Bild lassen den Quotienten
explodieren. Am 07.09. ergab das in der Klasse "volle Sonne" p = 1,0 bei
einer Streuung von 8,9 - unbrauchbar. Die Regression gewichtet genau diese
Punkte von selbst schwach, weil ln(dl)^2 dort klein ist.

Als Guete wird das Bestimmtheitsmass r2 mitgeschrieben; ein Exponent mit
r2 unter MIN_R2 wird verworfen.

ZWEI WEITERE GROESSEN AUS DENSELBEN PAAREN

Tagesgang (Truebung): An klaren Punkten (volle Sonne, Durchlass ueber 92 %)
sollte Messung/Klarhimmel bei 1 liegen - und zwar den ganzen Tag. Am 06.09.
lag es vormittags leicht darueber und nachmittags 3,5 % darunter, in
Muenchen wie auf der Zugspitze gleich. Unsere Glocke ist symmetrisch um den
Sonnenhoechststand, die Wirklichkeit nicht: nachmittags truebt die Luft
durch Konvektion ein. Geschaetzt wird eine Gerade ueber der Stunde seit
Sonnenhoechststand.

Aufhellungsspitzen: Unsere Saeulen sind Zehn-Minuten-Mittel, das BfS misst
minuetlich. In einem Fenster mit Wolkenluecke liegt die Spitze deutlich
ueber dem Mittel - genau das, was die gestrichelte Linie zeigen soll. Aus
der BfS-Kurve (rund zwei Minuten je Bildspalte) wird je Fenster
Spitze/Mittel bestimmt und nach Sonnenschein-Klasse gemittelt. Damit steht
der Zuschlag auf Messwerten statt auf den bisher pauschalen 20 %.

Ergebnis: uv-durchlass.json, von der App gelesen. Solange zu wenige Punkte
je Klasse vorliegen, bleibt der Wert leer und die App rechnet mit 0,5
weiter.
"""
import datetime as dt
import io
import json
import math
import os
import re
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow fehlt: pip install pillow")

TZ = ZoneInfo("Europe/Berlin")
LOG = "uv_durchlasslog.json"
AUS = "uv-durchlass.json"
SOLAR = "https://raw.githubusercontent.com/luperttrading-lab/wetter/daten/solar10/"
BFS = "https://uvi.bfs.de/Tagesgrafiken/EEr_{slug}_{tag}.png"
CAMS = ("https://air-quality-api.open-meteo.com/v1/air-quality?latitude={la}&longitude={lo}"
        "&hourly=uv_index_clear_sky&past_days={pd}&forecast_days=1&timezone=Europe%2FBerlin")

MAX_KM = 25          # so nah muss die Strahlungsstation am BfS-Standort stehen
MIN_PUNKTE = 40      # so viele Paare braucht eine Klasse fuer einen Exponenten
MIN_R2 = 0.30        # darunter beschreibt der Exponent die Punkte nicht
STUNDEN = (9, 17)    # nur wo die Sonne hoch genug steht
# Sonnenschein-Klassen: (Name, min, max) in Minuten je Zehn-Minuten-Intervall
KLASSEN = [("voll", 9.5, 10.0), ("teils", 2.0, 9.5), ("keine", 0.0, 2.0)]

# Farbtabelle und Bildgeometrie AUS uv_klarcheck.py importieren, nicht
# abschreiben: der erste Anlauf trug erfundene Werte (0,2087/0,9663 statt
# 0,1250/0,9000). Die Zeitachse war dadurch gestaucht und verschoben, und
# das Verhaeltnis Messung/Klarhimmel fiel scheinbar um 60 % ueber den Tag -
# ein reiner Ablesefehler, der wie ein physikalischer Effekt aussah.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uv_klarcheck import BFSCOL, FARBEN, X0, X1, Y0, Y9  # noqa: E402

BAR_XS = (0.09, 0.08, 0.10, 0.07, 0.11, 0.06, 0.12)   # Spalten der Farbleiste


def hole(url, binaer=True):
    cmd = ["curl", "-sS", "--max-time", "90"]
    ca = os.environ.get("CURL_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
    if os.path.exists(ca):
        cmd += ["--cacert", ca]
    for _ in range(4):
        r = subprocess.run(cmd + [url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout if binaer else r.stdout.decode("utf-8", "replace")
        time.sleep(3)
    return None


def hole_json(url):
    d = hole(url, binaer=False)
    try:
        return json.loads(d)
    except Exception:
        return None


def achse_lesen(im):
    w, h = im.size
    for bx in BAR_XS:
        px = int(round(bx * w))
        f = 0.08
        while f <= 0.55:
            py = int(round(f * h))
            p = im.getpixel((px, py))[:3]
            best, bd = -1, 10 ** 9
            for i, c in enumerate(FARBEN):
                d = sum((a - b) ** 2 for a, b in zip(p, c))
                if d < bd:
                    bd, best = d, i
            if bd <= 1200:
                return best if best < 9 else 9
            f += 0.004
    return None


def messkurve(im, ax):
    """Oberkante der farbigen Balken je Spalte als {Stunde: UV}."""
    w, h = im.size
    x0, x1 = int(X0 * w), int(X1 * w)
    y9, y0 = int(Y9 * h), int(Y0 * h)

    def bunt(p):
        return any(sum((a - b) ** 2 for a, b in zip(p, c)) <= 900 for c in FARBEN)

    out = []
    for px in range(x0, x1 + 1):
        oben, luecke = None, 0
        for py in range(y0 - 3, y9 + 2, -1):
            if bunt(im.getpixel((px, py))[:3]):
                oben, luecke = py, 0
            else:
                luecke += 1
                if luecke > 2:
                    break
        if oben is not None:
            out.append((6.0 + (px - x0) / (x1 - x0) * 15.0,
                        (Y0 - oben / h) / (Y0 - Y9) * (ax + 0.5)))
    return out


def stationen_aus_app(pfad="index.html"):
    with open(pfad, encoding="utf-8") as fh:
        s = fh.read()
    m = re.search(r"const BFS_UV_STATIONS=\[(.*?)\n\];", s, re.S)
    if not m:
        return []
    out = []
    for e in re.finditer(r'\{slug:"([^"]+)",name:"([^"]*)",la:([\d.]+),lo:([\d.]+)\}', m.group(1)):
        out.append({"slug": e.group(1), "la": float(e.group(3)), "lo": float(e.group(4))})
    return out


def km(a, b, c, d):
    return math.hypot((a - c) * 111.32, (b - d) * 111.32 * math.cos(math.radians((a + c) / 2)))


def mu(u, la, lo):
    n = (u - dt.datetime(u.year, 1, 1, tzinfo=dt.timezone.utc)).total_seconds() / 86400
    g = 2 * math.pi * n / 365.25
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
           - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g))
    eq = (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
          - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g)) * 229.18
    hh = (u.hour + u.minute / 60 + lo / 15 + eq / 60 - 12) * 15 * math.pi / 180
    return max(0.0, math.sin(math.radians(la)) * math.sin(dec)
               + math.cos(math.radians(la)) * math.cos(dec) * math.cos(hh))


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def sammeln(datum):
    """Paare (Durchlass, UV/Klarhimmel, Sonnenminuten) fuer alle Stationen."""
    heute = dt.date.today().isoformat()
    gestern = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    tag = "yesterday" if datum == gestern else "today"
    pd = 2 if datum != heute else 0

    bfs_st = stationen_aus_app()
    liste = hole_json(SOLAR + "stationen.json?t=%d" % time.time())
    if not bfs_st or not liste:
        print("Stationsliste fehlt")
        return []
    strahl = [s for s in liste["stationen"] if s.get("gs") is not False]

    paare = []
    for b in bfs_st:
        nah = min((s for s in strahl), key=lambda s: km(b["la"], b["lo"], s["lat"], s["lon"]))
        d = km(b["la"], b["lo"], nah["lat"], nah["lon"])
        if d > MAX_KM:
            continue
        png = hole(BFS.format(slug=b["slug"].replace(" ", "%20"), tag=tag))
        if not png or png[:8] != b"\x89PNG\r\n\x1a\n":
            continue
        try:
            im = Image.open(io.BytesIO(png)).convert("RGB")
        except Exception:
            continue
        ax = achse_lesen(im)
        if not ax:
            continue
        kurve = messkurve(im, ax)
        if len(kurve) < 50:
            continue
        j = hole_json(SOLAR + nah["id"] + ".json?t=%d" % time.time())
        c = hole_json(CAMS.format(la=b["la"], lo=b["lo"], pd=pd))
        if not j or not c:
            continue
        csw = [v for t, v in zip(c["hourly"]["time"], c["hourly"]["uv_index_clear_sky"])
               if t.startswith(datum) and v is not None]
        if not csw:
            continue
        cs_max = max(csw)
        t0 = dt.datetime.strptime(j["t0"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
        mu_max = max(mu(t0 + dt.timedelta(hours=h / 4), b["la"], b["lo"]) for h in range(40, 70))
        n0 = len(paare)
        for i, g in enumerate(j["gs"]):
            u = t0 + dt.timedelta(minutes=10 * i) - dt.timedelta(minutes=5)
            loc = u.astimezone(TZ)
            if loc.strftime("%Y-%m-%d") != datum or not (STUNDEN[0] <= loc.hour < STUNDEN[1]):
                continue
            if g is None:
                continue
            m = mu(u, b["la"], b["lo"])
            if m < 0.20:            # tiefe Sonne: Durchlass und Bildablesung zu unsicher
                continue
            gc = 1098 * m * math.exp(-0.057 / m)
            if gc < 100:
                continue
            dl = g / gc
            if not (0.05 < dl < 1.05):
                continue
            hz = loc.hour + loc.minute / 60
            nahe = [v for t, v in kurve if abs(t - hz) < 0.09]
            if not nahe:
                continue
            uvm = sum(nahe) / len(nahe)
            # Spitze gegen Mittel im selben Zehn-Minuten-Fenster
            spitze = (max(nahe) / uvm) if (len(nahe) >= 3 and uvm > 0.3) else None
            glocke = cs_max * (m / mu_max) ** 2.42     # ohne Stationsfaktor: der kuerzt sich
            if glocke < 0.8 or uvm < 0.3:
                continue
            sd = j["sd"][i] if j.get("sd") and j["sd"][i] is not None else None
            paare.append({"st": b["slug"], "dl": round(dl, 4),
                          "q": round(uvm / glocke, 4), "sd": sd,
                          "h": round(hz, 2), "mu": round(m, 4),
                          "sp": round(spitze, 3) if spitze else None})
        if len(paare) > n0:
            print("  %-24s %3d Paare (Strahlung: %s, %.0f km)"
                  % (b["slug"][:24], len(paare) - n0, nah["name"][:16], d))
    return paare


def tagesgang(log):
    """Truebung ueber den Tag: Messung/Klarhimmel gegen Stunde, nur klare Punkte."""
    w = [p for tag in log.values() for p in tag
         if p.get("h") is not None and (p.get("sd") or 0) >= 9.5 and p["dl"] >= 0.92
         and 0.5 < p["q"] < 1.6]
    # JE STATION zentrieren: die Stationen tragen Offsets von 0,84 bis 1,20
    # (uv-station.json). Ungetrennt misst die Steigung diese Unterschiede statt
    # des Tagesgangs - beim ersten Versuch kam -68 % ueber sechs Stunden heraus,
    # weil manche Station nur vormittags klare Punkte hatte und eine andere nur
    # nachmittags. Nach Abzug des Stationsmittels bleibt der Tagesgang uebrig.
    # Nur Stationen mit Punkten VOR und NACH dem Hoechststand zaehlen, sonst
    # traegt eine Station nichts zur Steigung bei, verschiebt aber das Mittel.
    je = {}
    for q in w:
        je.setdefault(q["st"], []).append(q)
    w = []
    for st, qs in je.items():
        if not (any(q["h"] < 13.2 for q in qs) and any(q["h"] > 13.2 for q in qs)):
            continue
        m = sum(q["q"] for q in qs) / len(qs)
        for q in qs:
            w.append({"h": q["h"], "q": q["q"] / m, "st": st})
    if len(w) < MIN_PUNKTE:
        return {"punkte": len(w), "stationen": len(je), "steigung": None}
    # Stunde seit Sonnenhoechststand naeherungsweise: 13,2 Uhr Ortszeit
    x = [p["h"] - 13.2 for p in w]
    y = [p["q"] for p in w]
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx < 1e-9:
        return {"punkte": n, "steigung": None}
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    a0 = my - b * mx
    rest = sum((c - a0 - b * a) ** 2 for a, c in zip(x, y))
    ges = sum((c - my) ** 2 for c in y)
    sb = math.sqrt(rest / (n - 2) / sxx) if n > 2 else 0.0
    return {"punkte": n, "stationen": len(set(p["st"] for p in w)),
            "steigung": round(b, 4), "fehler": round(sb, 4),
            "mitte": round(a0, 4), "r2": round(1 - rest / ges, 3) if ges > 1e-9 else 0.0,
            "vormittags": round(a0 - 3 * b, 3), "nachmittags": round(a0 + 3 * b, 3)}


def spitzen(log):
    """Spitze/Mittel im Zehn-Minuten-Fenster, je Sonnenschein-Klasse."""
    out = {}
    for name, lo, hi in KLASSEN:
        w = [p["sp"] for tag in log.values() for p in tag
             if p.get("sp") and p.get("sd") is not None and lo <= p["sd"] < hi + 1e-9]
        if len(w) < MIN_PUNKTE:
            out[name] = {"punkte": len(w), "spitze": None}
            continue
        w.sort()
        out[name] = {"punkte": len(w), "spitze": round(median(w), 3),
                     "p90": round(w[int(0.90 * (len(w) - 1))], 3),
                     "max": round(w[-1], 3)}
    return out


def auswerten(log):
    """Je Klasse den Exponenten p aus q = dl^p schaetzen."""
    alle = [p for tag in log.values() for p in tag]
    out = {}
    for name, lo, hi in KLASSEN:
        w = [p for p in alle if p.get("sd") is not None and lo <= p["sd"] < hi + 1e-9
             and 0.08 < p["dl"] < 0.97 and p["q"] > 0.05]
        if len(w) < MIN_PUNKTE:
            out[name] = {"punkte": len(w), "p": None}
            continue
        x = [math.log(p["dl"]) for p in w]
        y = [math.log(p["q"]) for p in w]
        sxx = sum(a * a for a in x)
        if sxx < 1e-9:
            out[name] = {"punkte": len(w), "p": None}
            continue
        pk = sum(a * b for a, b in zip(x, y)) / sxx
        rest = sum((b - pk * a) ** 2 for a, b in zip(x, y))
        gesamt = sum(b * b for b in y)
        r2 = 1 - rest / gesamt if gesamt > 1e-9 else 0.0
        sp = math.sqrt(rest / (len(w) - 1) / sxx) if len(w) > 1 else 0.0
        out[name] = {"punkte": len(w),
                     "p": round(max(0.15, min(1.0, pk)), 3) if r2 >= MIN_R2 else None,
                     "p_roh": round(pk, 3), "r2": round(r2, 3),
                     "fehler": round(sp, 3),
                     "dl_mittel": round(sum(q["dl"] for q in w) / len(w), 3)}
    return out


def main():
    datum = sys.argv[1] if len(sys.argv) > 1 else \
        (dt.date.today() - dt.timedelta(days=1)).isoformat()
    print("Wolkendurchlass-Paare fuer %s" % datum)
    paare = sammeln(datum)
    print("gesammelt: %d Paare" % len(paare))

    try:
        with open(LOG, encoding="utf-8") as fh:
            log = json.load(fh)
    except Exception:
        log = {}
    if paare:
        log[datum] = paare
        with open(LOG, "w", encoding="utf-8") as fh:
            json.dump(log, fh, ensure_ascii=False)

    erg = auswerten(log)
    print("\n%-8s %8s %9s %9s %7s %9s" % ("Klasse", "Punkte", "Exponent", "+-", "r2", "Durchl."))
    for name, lo, hi in KLASSEN:
        e = erg[name]
        print("%-8s %8d %9s %9s %7s %9s"
              % (name, e["punkte"],
                 ("%.3f" % e["p"]) if e.get("p") else ("(%.3f)" % e["p_roh"]) if e.get("p_roh") else "  -  ",
                 ("%.3f" % e["fehler"]) if e.get("fehler") else "  -  ",
                 ("%.2f" % e["r2"]) if e.get("r2") is not None else "  -  ",
                 ("%.0f %%" % (100 * e["dl_mittel"])) if e.get("dl_mittel") else "  -  "))
    print("Exponent in Klammern = r2 unter %.2f, verworfen" % MIN_R2)
    tg = tagesgang(log)
    print("\nTagesgang der Truebung (klare Punkte, Messung/Klarhimmel):")
    if tg.get("steigung") is not None:
        print("  %d Punkte aus %d Stationen (je Station zentriert) | "
              "Steigung %+.4f je Stunde (+-%.4f) | r2 %.2f"
              % (tg["punkte"], tg.get("stationen", 0), tg["steigung"], tg["fehler"], tg["r2"]))
        print("  3 h vor Mittag %.3f -> 3 h danach %.3f  (%+.1f %%)"
              % (tg["vormittags"], tg["nachmittags"],
                 100 * (tg["nachmittags"] / tg["vormittags"] - 1)))
    else:
        print("  erst %d von %d noetigen Punkten" % (tg["punkte"], MIN_PUNKTE))

    sp = spitzen(log)
    print("\nAufhellungsspitzen (Spitze/Mittel im Zehn-Minuten-Fenster):")
    print("  %-8s %8s %8s %8s %8s" % ("Klasse", "Punkte", "Median", "90 %", "Maximum"))
    for name, lo, hi in KLASSEN:
        e = sp[name]
        print("  %-8s %8d %8s %8s %8s"
              % (name, e["punkte"],
                 ("%.3f" % e["spitze"]) if e.get("spitze") else "  -  ",
                 ("%.3f" % e["p90"]) if e.get("p90") else "  -  ",
                 ("%.3f" % e["max"]) if e.get("max") else "  -  "))

    fertig = sum(1 for e in erg.values() if e["p"])
    with open(AUS, "w", encoding="utf-8") as fh:
        json.dump({"stand": max(log) if log else None, "tage": len(log),
                   "regel": "UV = Klarhimmel x Durchlass^p, p je Sonnenschein-Klasse; "
                            "Regression ln(q)=p*ln(dl), ab %d Punkten und r2 %.2f" % (MIN_PUNKTE, MIN_R2),
                   "klassen": {n: {"von": lo, "bis": hi} for n, lo, hi in KLASSEN},
                   "p": erg, "tagesgang": tg, "spitzen": sp}, fh, ensure_ascii=False, indent=1)
    print("\n%s geschrieben (%d von %d Klassen belegt, %d Tage im Log)"
          % (AUS, fertig, len(KLASSEN), len(log)))
    if fertig < len(KLASSEN):
        print("Solange eine Klasse leer ist, rechnet die App mit 0,5 weiter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
