#!/usr/bin/env python3
"""
bfs_achse.py  --  liest die Y-Achse der amtlichen BfS-Tagesgrafiken aus.

Das BfS legt die Skala seiner UV-Grafiken je Tag und Station neu fest (0-6,
0-8, 0-10 ...). Die App legt eigene Kurven ueber dieses Bild und muss die Skala
dafuer kennen — im Browser ist sie nicht auslesbar, weil der BfS-Server den
Bildzugriff fuer fremde Seiten sperrt (CORS). Hier geht es, weil das Skript das
Bild direkt laedt.

Gelesen wird die Farbleiste am linken Rand: sie reicht von UV 0 unten bis zum
Achsenmaximum oben. Die oberste Farbe verraet also die Skala. Abgetastet wird
eine Spalte in der Leiste von oben nach unten bis zur ersten Farbe, die
eindeutig zur BfS-Farbtabelle gehoert.

Schreibt bfs-achse.json:
  { "stand": "...", "achsen": { "Giessen-Wettenberg": { "2026-09-01": 6, "2026-08-31": 8 }, ... } }

Laeuft per GitHub-Action; Stationen sind die, die die App kennt.
"""
import io, json, sys, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    from PIL import Image
except ImportError:
    print("Pillow fehlt: pip install pillow", file=sys.stderr)
    sys.exit(1)

TZ = ZoneInfo("Europe/Berlin")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
      "Referer": "https://www.bfs.de/",
      "Accept": "image/png,image/*;q=0.8,*/*;q=0.5"}
BASIS = "https://uvi.bfs.de/Tagesgrafiken/EEr_{slug}_{tag}.png"
AUSGABE = "bfs-achse.json"

# Alle Stationen, die die App kennt (aus index.html, BFS_ST)
STATIONEN = [
    "Andernach", "Belm-Osnabrueck", "Berlin", "Bonn", "Chieming", "Dortmund",
    "Eckernfoerde", "Fichtelberg", "Friedrichshafen", "Genthin",
    "Giessen-Wettenberg", "Goerlitz", "Groemitz", "Hamburg", "Hohenpeissenberg",
    "Kassel", "Klippeneck", "Kulmbach", "Langen", "Lindenberg", "Lueneburg",
    "Melpitz", "Muenchen", "Norderney", "Salzgitter", "Schauinsland",
    "Schneefernerhaus", "Stuttgart", "Tholey", "Todendorf", "Waldmuenchen",
    "Weissenburg", "Zingst", "Zirchow",
    # v1.1: die neun bis dahin fehlenden Stationen der BfS-Karte. Die Slugs
    # folgen keinem Muster — mal mit "_B", mal mit Leerzeichen, mal mit
    # Ortsteil. Sie wurden einzeln aus den BfS-Seiten abgelesen, weil weder
    # Raten noch automatisches Auslesen ging: bfs.de sperrt Zugriffe aus
    # Rechenzentren, und damit auch den GitHub-Runner.
    "Boesel_B",                # Boesel
    "Cuxhaven_B",              # Cuxhaven
    "Duderstadt_B",            # Duderstadt
    "Sankt Augustin",          # Sankt Augustin (Leerzeichen!)
    "Schweinfurt_Wasserlosen", # Schweinfurt
    "Sylt_Tinnum",             # Sylt (Westerland)
    "Waldhof_Falkenstein",     # Waldhof
    "Wasserkuppe bei Fulda",   # Wasserkuppe (Leerzeichen!)
    "Wurmberg_B",              # Wurmberg
]


# BfS-Farbtabelle: Index = UV-Wert (identisch mit BFSCOL in der App)
BFSCOL = ["#006300", "#00a014", "#81c600", "#fff800", "#ffd100",
          "#ffa600", "#ff7200", "#ff4a00", "#ff0000", "#ff0078"]
FARBEN = [(int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)) for h in BFSCOL]

# Spalten, in denen die Farbleiste gesucht wird (Anteil der Bildbreite).
# Am Screenshot nachgemessen liegt sie bei etwa 6,5 bis 12 %; die erste Fassung
# tastete bei 5,5 % ab und traf das Weiss links daneben — 68 von 68 Bildern
# "Leiste nicht gefunden". Mehrere Spalten fangen Layout-Unterschiede ab.
BAR_XS = (0.09, 0.08, 0.10, 0.07, 0.11, 0.06, 0.12)
# Abtastbereich (Anteil der Bildhoehe): oberhalb der Legende bis Mitte
Y_VON, Y_BIS, Y_SCHRITT = 0.08, 0.55, 0.004
# maximaler quadratischer Farbabstand, der noch als Treffer gilt
TOLERANZ = 1200


def naechste_farbe(rgb):
    """Index der naechsten BfS-Farbe und quadratischer Abstand."""
    best, bd = -1, 10**9
    for i, (R, G, B) in enumerate(FARBEN):
        d = (rgb[0]-R)**2 + (rgb[1]-G)**2 + (rgb[2]-B)**2
        if d < bd:
            bd, best = d, i
    return best, bd


def achse_aus_uv(uv_index):
    """Oberste Leistenfarbe = UV i -> Achse ist genau i.

    Bis September 2026 rundete diese Funktion auf die naechste GERADE Stufe
    (4, 6, 8, 10, 12) - in der Annahme, das BfS skaliere nur gerade. Das
    stimmt nicht: Muenchen hatte am 03.09.2026 eine Achse 0-7, die oberste
    Leistenfarbe war #ff4a00 (UV 7), geschrieben wurde 8. Die App zeichnete
    ihre Kurven dadurch mit dem Nenner 8,5 statt 7,5, also rund 12 Prozent zu
    flach - genau das war am Bild zu sehen.
    In 172 gespeicherten Messungen kam deshalb nie eine 7 oder 9 vor,
    sondern nur 6 (148x), 8 (20x) und 10 (4x).

    Grenze nach oben: die Farbtabelle endet bei UV 9. Ist die oberste Farbe
    die neunte, kann die Achse 9 oder hoeher sein - dann wird 10 geliefert,
    weil eine zu kleine Achse die Kurven abschneiden wuerde, eine etwas zu
    grosse sie nur staucht."""
    return 10 if uv_index >= 9 else uv_index


def achse_lesen(png_bytes):
    """Liefert (achse, grund). achse ist None, wenn nichts Eindeutiges gefunden wurde.
    Der Grund enthaelt bei Misserfolg die Bildmasse und eine Farbprobe, damit man
    ohne das Bild sieht, wo die Abtastung hinschaut."""
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = im.size
    for bx in BAR_XS:
        px = int(round(bx * w))
        f = Y_VON
        while f <= Y_BIS:
            py = int(round(f * h))
            if 0 <= py < h:
                r, g, b, a = im.getpixel((px, py))
                if a >= 200:
                    idx, dist = naechste_farbe((r, g, b))
                    if dist <= TOLERANZ:
                        return achse_aus_uv(idx), f"Leistenfarbe {BFSCOL[idx]} bei x={px} y={py} ({w}x{h})"
            f += Y_SCHRITT
    # Diagnose: Farbprobe in der Mitte des Suchbereichs
    proben = []
    for bx in (0.06, 0.09, 0.12):
        px = int(round(bx * w)); py = int(round(0.30 * h))
        r, g, b, a = im.getpixel((min(px, w-1), min(py, h-1)))
        proben.append(f"x{px}:#{r:02x}{g:02x}{b:02x}")
    return None, f"Leiste nicht gefunden ({w}x{h}; Proben bei y=30%: {' '.join(proben)})"


def bild_holen(slug, tag):
    # v1.1: Leerzeichen im Slug ("Sankt Augustin") muessen als %20 in die URL.
    url = BASIS.format(slug=urllib.parse.quote(slug), tag=tag)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        daten = r.read()
        ct = r.headers.get("Content-Type", "")
        if daten[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"kein PNG (Content-Type {ct}, {len(daten)} Bytes)")
        return daten


def main():
    heute = datetime.now(TZ).date()
    gestern = heute - timedelta(days=1)
    # bisherigen Stand laden, damit aeltere Tage erhalten bleiben
    try:
        with open(AUSGABE, "r", encoding="utf-8") as fh:
            alt = json.load(fh).get("achsen", {})
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        alt = {}
    achsen = {k: dict(v) for k, v in alt.items() if isinstance(v, dict)}

    ok = fehl = 0
    gruende = {}
    for slug in STATIONEN:
        achsen.setdefault(slug, {})
        for tag, datum in (("today", heute), ("yesterday", gestern)):
            ds = datum.isoformat()
            try:
                png = bild_holen(slug, tag)
                achse, grund = achse_lesen(png)
            except urllib.error.HTTPError as e:
                achse, grund = None, f"HTTP {e.code}"
            except Exception as e:
                achse, grund = None, str(e)[:60]
            if achse is not None:
                achsen[slug][ds] = achse
                ok += 1
                print(f"{slug:<20} {ds}  Achse {achse:>2}   ({grund})")
            else:
                fehl += 1
                gruende[f"{slug}|{ds}"] = grund
                print(f"{slug:<20} {ds}  --        ({grund})")

    # nur die letzten 45 Tage je Station behalten
    grenze = (heute - timedelta(days=45)).isoformat()
    for slug in achsen:
        achsen[slug] = {d: v for d, v in achsen[slug].items() if d >= grenze}

    with open(AUSGABE, "w", encoding="utf-8") as fh:
        json.dump({"stand": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "quelle": "BfS-Tagesgrafiken, Farbleiste ausgelesen",
                   "achsen": dict(sorted(achsen.items())),
                   "gelesen": ok, "nicht_lesbar": fehl,
                   "gruende": gruende}, fh, ensure_ascii=False, indent=1)
    print(f"\n{ok} gelesen, {fehl} nicht lesbar. Geschrieben: {AUSGABE}")


if __name__ == "__main__":
    main()
