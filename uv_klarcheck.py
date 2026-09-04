#!/usr/bin/env python3
"""uv_klarcheck.py -- Vergleicht an einem WOLKENFREIEN Tag drei Klarhimmel-
Quellen und sagt, welche der Realitaet naeher kommt.

Hintergrund
-----------
Die App zeichnet ihre Klarhimmel-Glocke nach CAMS (uv_index_clear_sky von
Open-Meteo). Die amtlichen BfS-Tagesgrafiken enthalten bei einem Teil der
Stationen zusaetzlich die "Clear-Sky-Prognose (DWD)" als graue Linie. Am
03.09.2026 ueber 13 Stationen verglichen, ergab sich ein sehr klarer
Zusammenhang mit dem Breitengrad:

    Korrelation r = 0,970,  Steigung +5,7 Prozentpunkte je Breitengrad,
    Nulldurchgang bei 49,9 Grad Nord.

Suedlich davon liegt CAMS unter dem DWD (Schauinsland -14,4 %), noerdlich
darueber (Sylt +29,3 %). Die reine Sonnenhoehe (UV ~ sin h ^ 2,4) liegt
zwischen beiden: von Muenchen nach Sylt faellt der DWD um 38,5 %, die
Sonnenhoehe erklaert 23,9 %, CAMS faellt nur um 12,8 %.

Wer recht hat, entscheidet nur eine echte Messung an einem klaren Tag -
dann faellt die gemessene Kurve mit der Klarhimmelkurve zusammen. Am
03.09. war es ueberall bewoelkt, deshalb dieses Skript: Es prueft
taeglich, ob ein Tag klar genug war, und rechnet nur dann.

Bildauswertung
--------------
Geometrie wie in der App kalibriert: x 0,125..0,900 = 6..21 Uhr,
y 0,900..0,100 = 0..Achse+0,5.
Die graue Linie hat den Kernwert rgb(128,128,128); Antialiasing daneben
liegt bei 175..196, die gepunkteten Gitterlinien bei 219, der Plotrahmen
bei 0..72. Auf den Kern zu filtern trennt alles sauber. Vier einfachere
Ansaetze scheiterten: die oberste Graugruppe je Spalte las den
Legendenrahmen (alle Stationen ergaben exakt Achse+0,46), die Verfolgung
vom rechten Rand lief auf der x-Achse, ein Mittagsfenster traf den
Rahmen, und ein Gitterausschluss verlor die Bahn.

Aufruf:  python3 uv_klarcheck.py [YYYY-MM-DD]
Ohne Datum wird der gestrige Tag geprueft (die Bilder heissen dann
"_yesterday.png").
"""

import json
import math
import io
import os
import re
import sys
import datetime
import subprocess

try:
    from PIL import Image
except ImportError:
    sys.exit("PIL fehlt:  pip install pillow")

# ---- Bildgeometrie (an vier Bildern nachgemessen, siehe index.html v3.41) ----
X0, X1 = 0.1250, 0.9000        # 6 Uhr .. 21 Uhr
Y9, Y0 = 0.1000, 0.9000        # Achse+0,5 .. 0

BFSCOL = ["#006300", "#00a014", "#81c600", "#fff800", "#ffd100",
          "#ffa600", "#ff7200", "#ff4a00", "#ff0000", "#ff0078"]
FARBEN = [(int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)) for h in BFSCOL]

# Ab wie vielen klaren Stationen lohnt die Auswertung
MIN_KLAR = 5
# Messung gilt als "klar", wenn ihr Scheitel so nah an der Clear-Sky-Linie liegt
KLAR_SCHWELLE = 0.92


def hole(url, versuche=3):
    for _ in range(versuche):
        r = subprocess.run(["curl", "-s", "--max-time", "35", url],
                           capture_output=True)
        if r.stdout[:8] == b"\x89PNG\r\n\x1a\n":
            return r.stdout
    return None


def stationen_aus_app(pfad="index.html"):
    """Liest die BfS-Stationsliste samt Koordinaten aus der App."""
    with io.open(pfad, encoding="utf-8") as fh:
        s = fh.read()
    m = re.search(r"const BFS_UV_STATIONS\s*=\s*(\[.*?\]);", s, re.S)
    if not m:
        return []
    out = []
    for e in re.findall(r"\{([^}]*)\}", m.group(1)):
        sl = re.search(r'slug\s*:\s*"([^"]*)"', e)
        nm = re.search(r'name\s*:\s*"([^"]*)"', e)
        la = re.search(r"\bla\s*:\s*(-?[\d.]+)", e)
        lo = re.search(r"\blo\s*:\s*(-?[\d.]+)", e)
        if sl and la and lo:
            out.append({"slug": sl.group(1),
                        "name": nm.group(1) if nm else sl.group(1),
                        "la": float(la.group(1)), "lo": float(lo.group(1))})
    return out


def achse_lesen(im):
    """Achsenmaximum aus der obersten Farbe der Leiste (ganzzahlig, v3.68)."""
    w, h = im.size
    for bx in (0.09, 0.08, 0.10, 0.07, 0.11, 0.06, 0.12):
        px = int(round(bx * w))
        f = 0.08
        while f <= 0.55:
            py = int(round(f * h))
            p = im.getpixel((px, py))
            best, bd = -1, 10 ** 9
            for i, (R, G, B) in enumerate(FARBEN):
                d = (p[0] - R) ** 2 + (p[1] - G) ** 2 + (p[2] - B) ** 2
                if d < bd:
                    bd, best = d, i
            if bd <= 1200:
                # v1.1: Die Farbtabelle endet bei 9; ob darueber noch Felder
                # liegen (Achse 10 oder 12), zaehlt bfs_achse.felder_oberhalb.
                # Vorher wurde jede oberste 9 zur 10 - Schneefernerhaus hatte
                # am 02.-04.09.2026 eine 0-9-Achse.
                if best == len(FARBEN) - 1:
                    import bfs_achse
                    best += bfs_achse.felder_oberhalb(im.convert("RGBA"), px, py)
                return best
            f += 0.004
    return None


def _kern(im, px, y9, y0):
    """y-Mitten der Linienkerne rgb(128) in dieser Spalte."""
    tr = []
    for py in range(y9 + 3, y0 - 2):
        p = im.getpixel((px, py))
        if abs(p[0] - p[1]) < 6 and abs(p[1] - p[2]) < 6 and abs(p[0] - 128) <= 14:
            tr.append(py)
    gr, letzte = [], None
    for py in tr:
        if letzte is None or py - letzte > 2:
            gr.append([])
        gr[-1].append(py)
        letzte = py
    return [sum(g) / len(g) for g in gr]


def clearsky_kurve(im, ax):
    """Graue DWD-Linie als [(Stunde, UV)]. Leer, wenn das Bild keine hat."""
    w, h = im.size
    x0, x1 = int(X0 * w), int(X1 * w)
    y9, y0 = int(Y9 * h), int(Y0 * h)
    mitte = (x0 + x1) // 2
    start = None
    for d in range(0, 60):                     # Start nahe der Mitte, dort
        for px in (mitte + d, mitte - d):      # steht kein Legendenkasten
            g = _kern(im, px, y9, y0)
            if len(g) == 1:
                start = (px, g[0])
                break
        if start:
            break
    if not start:
        return []
    bahn = {start[0]: start[1]}
    for richtung in (1, -1):
        letzte, px, luecke = start[1], start[0] + richtung, 0
        while x0 <= px <= x1:
            g = _kern(im, px, y9, y0)
            if g:
                nah = min(g, key=lambda y: abs(y - letzte))
                if abs(nah - letzte) <= 3 + luecke:
                    bahn[px], letzte, luecke = nah, nah, 0
                else:
                    luecke += 1
            else:
                luecke += 1
            if luecke > 25:
                break
            px += richtung
    return [(6.0 + (px - x0) / (x1 - x0) * 15.0,
             (Y0 - bahn[px] / h) / (Y0 - Y9) * (ax + 0.5))
            for px in sorted(bahn)]


def mess_scheitel(im, ax):
    """Hoechster Punkt der farbigen Messbalken.

    Von UNTEN nach oben gelesen und beim ersten Abriss gestoppt: die Balken
    stehen auf der Grundlinie, der Legendenkasten mit seinem bunten
    Balkensymbol schwebt darueber. Ihn mitzulesen ergab an allen Stationen
    denselben Wert (6,23 bei Achse 6, das ist die Symbolhoehe)."""
    w, h = im.size
    x0, x1 = int(X0 * w), int(X1 * w)
    y9, y0 = int(Y9 * h), int(Y0 * h)

    def bunt(p):
        for (R, G, B) in FARBEN:
            if (p[0] - R) ** 2 + (p[1] - G) ** 2 + (p[2] - B) ** 2 <= 900:
                return True
        return False

    best = 0.0
    for px in range(x0, x1 + 1):
        oben = None
        luecke = 0
        for py in range(y0 - 3, y9 + 2, -1):
            if bunt(im.getpixel((px, py))):
                oben = py
                luecke = 0
            else:
                luecke += 1
                # Abbruch auch dann, wenn noch nichts gefunden wurde: sonst
                # laeuft die Spalte bis in den Legendenkasten hinauf. Genau
                # das passierte bei Berlin - ein einzelner oranger Pixel des
                # Legenden-Balkensymbols bei x=109, y=64 ergab UV 6,23 statt
                # der tatsaechlichen 3,7.
                if luecke > 2:
                    break
        if oben is not None:
            u = (Y0 - oben / h) / (Y0 - Y9) * (ax + 0.5)
            if u > best:
                best = u
    return best


def cams_scheitel(stationen, datum):
    """uv_index_clear_sky je Ort am Datum, ein einziger Abruf."""
    lat = ",".join("%.4f" % s["la"] for s in stationen)
    lon = ",".join("%.4f" % s["lo"] for s in stationen)
    url = ("https://api.open-meteo.com/v1/forecast?latitude=" + lat +
           "&longitude=" + lon +
           "&hourly=uv_index_clear_sky&past_days=5&forecast_days=1"
           "&timezone=Europe%2FBerlin")
    # v1.2: ueber hole() statt curl - dieselbe Verbindung wie die Bilder
    # (Proxy und Zertifikat aus der Umgebung). Mit curl ohne CA-Bundle kam
    # in der Sandbox nichts zurueck, und die Auswertung teilte durch null.
    try:
        d = json.loads(hole(url).decode("utf-8"))
    except Exception as e:
        print("CAMS nicht erreichbar:", str(e)[:80])
        return {}
    if not isinstance(d, list):
        d = [d]
    out = {}
    for s, o in zip(stationen, d):
        werte = [v for t, v in zip(o["hourly"]["time"],
                                   o["hourly"]["uv_index_clear_sky"])
                 if t.startswith(datum) and v is not None]
        if werte:
            out[s["slug"]] = max(werte)
    return out


def main():
    datum = sys.argv[1] if len(sys.argv) > 1 else \
        (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    gestern = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    endung = "yesterday" if datum == gestern else "today"

    st = stationen_aus_app()
    if not st:
        sys.exit("BFS_UV_STATIONS nicht gefunden - aus dem Repo-Wurzelverzeichnis starten")

    print("UV-Klarhimmel-Pruefung fuer %s (%d Stationen)\n" % (datum, len(st)))
    treffer = []
    for s in st:
        png = hole("https://uvi.bfs.de/Tagesgrafiken/EEr_%s_%s.png" % (s["slug"], endung))
        if not png:
            continue
        im = Image.open(io.BytesIO(png)).convert("RGB")
        ax = achse_lesen(im)
        if ax is None:
            continue
        cs = clearsky_kurve(im, ax)
        if len(cs) < 80:
            continue                       # Bild ohne DWD-Kurve
        sch = max(cs, key=lambda t: t[1])
        if not (11.0 <= sch[0] <= 15.5):
            continue                       # Scheitel unplausibel
        mess = mess_scheitel(im, ax)
        treffer.append({"slug": s["slug"], "name": s["name"], "la": s["la"],
                        "lo": s["lo"], "ax": ax, "dwd": sch[1],
                        "uhr": sch[0], "mess": mess,
                        "klarheit": mess / sch[1] if sch[1] > 0 else 0})

    if not treffer:
        print("Keine Station mit DWD-Klarhimmelkurve lesbar.")
        return 1

    klar = [t for t in treffer if t["klarheit"] >= KLAR_SCHWELLE]
    print("%-24s %6s %6s %8s" % ("Station", "DWD", "Messung", "Verhaeltnis"))
    for t in sorted(treffer, key=lambda x: -x["klarheit"]):
        print("%-24s %6.2f %6.2f %8.2f%s" %
              (t["name"][:24], t["dwd"], t["mess"], t["klarheit"],
               "  klar" if t["klarheit"] >= KLAR_SCHWELLE else ""))
    print("\n%d von %d Stationen klar (Schwelle %.2f)" %
          (len(klar), len(treffer), KLAR_SCHWELLE))

    if len(klar) < MIN_KLAR:
        print("Zu bewoelkt - keine Auswertung. Morgen erneut pruefen.")
        return 0

    cams = cams_scheitel([{"la": t["la"], "lo": t["lo"], "slug": t["slug"]}
                          for t in klar], datum)
    zeilen = [t for t in klar if t["slug"] in cams]
    for t in zeilen:
        t["cams"] = cams[t["slug"]]
    if not zeilen:
        print("Klarer Tag, aber keine CAMS-Werte - Auswertung entfaellt.")
        return 1

    print("\n=== KLARER TAG - Auswertung ===\n")
    print("%-24s %6s %7s %7s %7s" % ("Station", "Breite", "Messung", "DWD", "CAMS"))
    for t in sorted(zeilen, key=lambda x: x["la"]):
        print("%-24s %6.2f %7.2f %7.2f %7.2f" %
              (t["name"][:24], t["la"], t["mess"], t["dwd"], t["cams"]))

    def statistik(name, feld):
        rel = [100 * (t[feld] - t["mess"]) / t["mess"] for t in zeilen]
        n = len(rel)
        m = sum(rel) / n
        sd = math.sqrt(sum((x - m) ** 2 for x in rel) / (n - 1)) if n > 1 else 0
        # Zusammenhang mit dem Breitengrad
        la = [t["la"] for t in zeilen]
        mla = sum(la) / n
        cov = sum((a - mla) * (b - m) for a, b in zip(la, rel)) / (n - 1) if n > 1 else 0
        sla = math.sqrt(sum((v - mla) ** 2 for v in la) / (n - 1)) if n > 1 else 1
        b = cov / sla ** 2 if sla else 0
        r = cov / (sla * sd) if sla and sd else 0
        print("  %-6s gegen Messung: %+6.1f %% (Streuung %.1f Pp) | "
              "Breite: r=%+.3f, %+.2f Pp je Grad" % (name, m, sd, r, b))

    print("\nAbweichung vom gemessenen Scheitel (%d Stationen):" % len(zeilen))
    statistik("DWD", "dwd")
    statistik("CAMS", "cams")
    print("\nDie Quelle mit der kleineren Abweichung und der flacheren "
          "Breitenabhaengigkeit trifft die Realitaet besser.")
    with open("uv_klarcheck_%s.json" % datum, "w") as fh:
        json.dump(zeilen, fh, ensure_ascii=False, indent=1)
    print("\nRohdaten: uv_klarcheck_%s.json" % datum)
    return 0


if __name__ == "__main__":
    sys.exit(main())
