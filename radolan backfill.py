#!/usr/bin/env python3
"""Einmaliger Rueckwaerts-Backfill des RADOLAN-Tagesarchivs (v1.0).

Fuellt radolan-archiv.json mit vergangenen Tagessummen. Zwei Quellen:
  1. historical/bin/JJJJ/  - monatsweise Tar-Archive, reicht Jahre zurueck
  2. recent/bin/           - Einzeldateien der letzten ~30 Tage (Luecken-Fueller)

Pixelgewichte, Parser und Archivformat werden aus radolan_regen importiert,
damit Backfill und Live-Pipeline garantiert denselben Punkt berechnen.

Steuerung ueber Umgebungsvariablen:
  BACKFILL_JAHR   z.B. "2024" -> genau dieses Kalenderjahr nachtragen
  BACKFILL_TAGE   Anzahl Tage rueckwaerts ab gestern            (Default 365)
  BACKFILL_FORCE  "1" -> auch bereits vollstaendige Tage neu rechnen

Hinweis: Das historische DWD-Archiv reicht nur bis zum vorletzten Jahr
(Stand 2026: bis 2024). Das laufende und das Vorjahr sind dort nicht
enthalten - fuer die letzten ~35 Tage springt recent/bin ein.
"""
import gzip, os, re, tarfile, tempfile, urllib.request
from datetime import datetime, timedelta, timezone, date

from radolan_regen import (PIXELS, TZ, UA, parse_mm, val,
                           archiv_laden, archiv_schreiben, tagessumme)

HIST = ("https://opendata.dwd.de/climate_environment/CDC/grids_germany/"
        "hourly/radolan/historical/bin/")
TS = re.compile(r"raa01-rw_10000-(\d{10})-dwd")
RECENT_TAGE = 35          # so weit reicht recent/bin erfahrungsgemaess zurueck


def punktwert(mm):
    """Bilinear gewichteter Wert am Hausstandort - identisch zur Live-Pipeline."""
    return sum(w * val(mm, r, c) for r, c, w in PIXELS)


def lokaler_tag(dt_utc):
    """Der RW-Zeitstempel markiert das ENDE der Stunde.
    Die Datei um lokal 00:00 gehoert damit noch zum Vortag."""
    return (dt_utc.astimezone(TZ) - timedelta(seconds=1)).date().isoformat()


def monatsdatei(jahr, monat):
    """Jahresverzeichnis auflisten und das Monatsarchiv per Regex finden.
    Bewusst kein fest verdrahteter Dateiname - die DWD-Namensschemata
    unterscheiden sich zwischen Jahrgaengen (RW-JJJJMM / RWJJJJMM)."""
    url = f"{HIST}{jahr}/"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"    Verzeichnis nicht lesbar: {str(e)[:70]}")
        return None
    muster = re.compile(rf'href="([^"]*RW[-_]?{jahr}{monat:02d}[^"?]*\.tar(?:\.gz)?)"', re.I)
    treffer = muster.findall(html)
    if not treffer:
        return None
    name = treffer[0]
    return name if name.startswith("http") else url + name.lstrip("./")


def monat_aus_tar(url, roh):
    """Monatsarchiv streamen und die Stundenwerte auf lokale Tage summieren."""
    with tempfile.NamedTemporaryFile(suffix=".tar") as tmp:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
            while True:
                block = r.read(1 << 20)
                if not block:
                    break
                tmp.write(block)
        tmp.flush()
        n = 0
        with tarfile.open(tmp.name) as tar:
            for m in tar:
                if not m.isfile():
                    continue
                t = TS.search(m.name)
                if not t:
                    continue
                dt = datetime.strptime(t.group(1), "%y%m%d%H%M").replace(tzinfo=timezone.utc)
                data = tar.extractfile(m).read()
                if data[:2] == b"\x1f\x8b":          # manche Jahrgaenge sind zusaetzlich gezippt
                    data = gzip.decompress(data)
                try:
                    v = punktwert(parse_mm(data))
                except Exception:
                    continue
                e = roh.setdefault(lokaler_tag(dt), {"mm": 0.0, "h": 0})
                e["mm"] += v
                e["h"] += 1
                n += 1
        return n


def main():
    force = os.environ.get("BACKFILL_FORCE", "") == "1"
    heute = datetime.now(TZ).date()
    jahr_env = os.environ.get("BACKFILL_JAHR", "").strip()
    if jahr_env:
        j = int(jahr_env)
        d = date(j, 1, 1)
        ziel = []
        while d.year == j and d < heute:
            ziel.append(d)
            d += timedelta(days=1)
        ziel.reverse()
        print(f"Jahresmodus {j}: {len(ziel)} Tage im Ziel.")
    else:
        tage_zurueck = int(os.environ.get("BACKFILL_TAGE", "365"))
        ziel = [heute - timedelta(days=i) for i in range(1, tage_zurueck + 1)]

    archiv = archiv_laden()
    offen = [d for d in ziel if force or not archiv.get(d.isoformat(), {}).get("voll")]
    if not offen:
        print("Nichts zu tun - alle Zieltage sind bereits vollstaendig.")
        return
    print(f"{len(offen)} von {len(ziel)} Tagen offen ({offen[-1]} bis {offen[0]}).")
    rest = {d.isoformat() for d in offen}

    # --- 1) historisches Monatsarchiv -------------------------------------
    roh = {}
    for (j, m) in sorted({(d.year, d.month) for d in offen}, reverse=True):
        print(f"  {j}-{m:02d}:")
        url = monatsdatei(j, m)
        if not url:
            print("    kein Monatsarchiv gefunden -> ggf. ueber recent/")
            continue
        try:
            n = monat_aus_tar(url, roh)
            print(f"    {url.rsplit('/', 1)[-1]}: {n} Stunden verarbeitet")
        except Exception as e:
            print(f"    Fehler: {str(e)[:80]} -> ggf. ueber recent/")

    for ds, e in roh.items():
        if ds in rest:
            archiv[ds] = {"mm": round(e["mm"], 2), "h": e["h"],
                          "voll": e["h"] >= 24, "q": "hist"}
            if e["h"] >= 24:
                rest.discard(ds)

    # --- 2) Luecken aus recent/ (nur im erreichbaren Fenster) --------------
    grenze = heute - timedelta(days=RECENT_TAGE)
    for ds in sorted(rest, reverse=True):
        d = date.fromisoformat(ds)
        if d < grenze:
            print(f"  {ds}: weder Monatsarchiv noch recent/ - uebersprungen")
            continue
        mm, ok = tagessumme(datetime(d.year, d.month, d.day, tzinfo=TZ))
        if ok > 0:
            archiv[ds] = {"mm": mm, "h": ok, "voll": ok >= 24, "q": "recent"}
            print(f"  {ds}: {mm} mm aus recent/ ({ok}/24 Stunden)")
        else:
            print(f"  {ds}: keine Daten verfuegbar")

    archiv_schreiben(archiv, datetime.now(timezone.utc).isoformat(timespec="seconds"))
    voll = sum(1 for v in archiv.values() if v.get("voll"))
    print(f"Archiv: {len(archiv)} Tage gespeichert, davon {voll} vollstaendig.")


if __name__ == "__main__":
    main()
