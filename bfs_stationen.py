#!/usr/bin/env python3
"""
bfs_stationen.py  --  liest die Stationsliste des BfS-UV-Messnetzes aus.

Die Bild-URLs der Tagesgrafiken brauchen einen BfS-internen Slug, der vom
Anzeigenamen abweicht und nicht zu erraten ist: "Bösel" heisst dort
"Boesel_B", "Osnabrück" heisst "Belm-Osnabrueck". Statt zu raten, holt dieses
Skript die Uebersichtsseite, folgt jeder Stationsseite und liest dort
  - den Slug aus der Bild-URL  (EEr_<slug>_today.png)
  - Koordinaten und Hoehe aus der Tabelle
Schreibt bfs-stationen.json. Daraus lassen sich STATIONEN in bfs_achse.py und
die Stationsliste der App pflegen, ohne dass jemand Namen abtippt.

Laeuft selten (einmal im Monat reicht) — die Liste aendert sich kaum.
"""
import json, re, sys, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
      "Accept": "text/html,application/xhtml+xml"}
UEBERSICHT = ("https://www.bfs.de/DE/themen/opt/uv/uv-index/"
              "aktuelle-tagesverlaeufe/aktuell_node.html")
BASIS = "https://www.bfs.de"
AUSGABE = "bfs-stationen.json"

RE_DETAIL = re.compile(r'href="([^"]*aktuelle-tagesverlaeufe/_documents/[^"]+_node\.html)"')

# Die Uebersichtsseite laedt ihre Links per JavaScript nach — ein erster Lauf
# fand null Seiten. Die SEITENNAMEN sind aber ableitbar (kleingeschrieben, ohne
# Umlaute), anders als die kryptischen Bild-Slugs ("Boesel_B"). Deshalb wird die
# Liste hier gefuehrt und jede Seite direkt geholt; den Slug liefert dann die
# Seite selbst. Fehlende Seiten werden uebersprungen.
SEITEN = [
    "andernach", "berlin", "bonn", "boesel", "chieming", "cuxhaven", "dortmund",
    "duderstadt", "eckernfoerde", "fichtelberg", "friedrichshafen", "genthin",
    "giessen", "goerlitz", "groemitz", "hamburg", "hohenpeissenberg", "kassel",
    "klippeneck", "kulmbach", "langen", "lindenberg", "lueneburg", "melpitz",
    "muenchen", "norderney", "osnabrueck", "salzgitter", "sankt-augustin",
    "schauinsland", "schweinfurt", "stuttgart", "sylt", "tholey", "todendorf",
    "waldhof", "waldmuenchen", "wasserkuppe", "weissenburg", "wurmberg",
    "zingst", "zirchow", "zugspitze",
]
DETAIL_URL = ("https://www.bfs.de/DE/themen/opt/uv/uv-index/"
              "aktuelle-tagesverlaeufe/_documents/{name}_node.html")
RE_SLUG   = re.compile(r'uvi\.bfs\.de/Tagesgrafiken/EEr_([^_]+(?:_[A-Za-z0-9]+)*?)_today\.png')
RE_NAME   = re.compile(r'<title>[^<]*Messwerte für ([^<]+?)\s*</title>')
RE_KOORD  = re.compile(r'(\d{1,2})°(\d{1,2})\'(\d{1,2})"\s*Nord\s*(\d{1,3})°(\d{1,2})\'(\d{1,2})"\s*Ost')
RE_HOEHE  = re.compile(r'(\d+)\s*Meter über Meeresspiegel')


def hole(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def grad(g, m, s):
    return round(int(g) + int(m) / 60 + int(s) / 3600, 4)


def main():
    # Zuerst die Uebersichtsseite versuchen — findet sie Links, sind sie
    # verlaesslicher als die gefuehrte Liste (neue Stationen kommen mit).
    seiten = []
    try:
        html = hole(UEBERSICHT)
        for pfad in RE_DETAIL.findall(html):
            url = pfad if pfad.startswith("http") else BASIS + pfad
            if url not in seiten:
                seiten.append(url)
    except Exception as e:
        print("Uebersichtsseite nicht lesbar:", str(e)[:60])
    if seiten:
        print(f"{len(seiten)} Seiten aus der Uebersicht.\n")
    else:
        seiten = [DETAIL_URL.format(name=n) for n in SEITEN]
        print(f"Uebersicht ohne Links — gefuehrte Liste mit {len(seiten)} Seiten.\n")

    stationen = []
    for url in seiten:
        try:
            seite = hole(url)
        except Exception as e:
            kurz = url.rsplit('/', 1)[-1].replace("_node.html", "")
            print(f"  {kurz:<24} nicht erreichbar ({str(e)[:30]})")
            continue
        m_slug = RE_SLUG.search(seite)
        if not m_slug:
            print(f"  {url.rsplit('/',1)[-1]:<34} keine Bild-URL gefunden")
            continue
        slug = m_slug.group(1)
        name = (RE_NAME.search(seite).group(1).strip()
                if RE_NAME.search(seite) else slug)
        # Umlaute im Namen ohne HTML-Entities
        name = (name.replace("&auml;", "ä").replace("&ouml;", "ö")
                    .replace("&uuml;", "ü").replace("&szlig;", "ß"))
        eintrag = {"slug": slug, "name": name}
        k = RE_KOORD.search(re.sub(r"\s+", " ", seite))
        if k:
            eintrag["lat"] = grad(k.group(1), k.group(2), k.group(3))
            eintrag["lon"] = grad(k.group(4), k.group(5), k.group(6))
        h = RE_HOEHE.search(seite)
        if h:
            eintrag["hoehe_m"] = int(h.group(1))
        stationen.append(eintrag)
        koord = (f"{eintrag['lat']:.4f}N {eintrag['lon']:.4f}E"
                 if "lat" in eintrag else "ohne Koordinaten")
        print(f"  {name:<24} slug={slug:<24} {koord}")

    stationen.sort(key=lambda s: s["name"])
    with open(AUSGABE, "w", encoding="utf-8") as fh:
        json.dump({"stand": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "quelle": UEBERSICHT,
                   "anzahl": len(stationen),
                   "stationen": stationen}, fh, ensure_ascii=False, indent=1)

    ohne = [s["name"] for s in stationen if "lat" not in s]
    print(f"\n{len(stationen)} Stationen geschrieben nach {AUSGABE}.")
    if ohne:
        print("ohne Koordinaten:", ", ".join(ohne))
    print("\nSlugs zum Einsetzen in bfs_achse.py:")
    print("STATIONEN = [")
    zeile = "    "
    for s in stationen:
        stueck = f'"{s["slug"]}", '
        if len(zeile) + len(stueck) > 78:
            print(zeile.rstrip()); zeile = "    "
        zeile += stueck
    if zeile.strip():
        print(zeile.rstrip())
    print("]")


if __name__ == "__main__":
    main()
