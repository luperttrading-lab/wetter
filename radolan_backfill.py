#!/usr/bin/env python3
"""Rueckwaerts-Backfill des RADOLAN-Tagesarchivs (v2.0, mehrere Orte).

Fuellt radolan-archiv.json mit vergangenen Tagessummen. Zwei Quellen:
  1. historical/bin/JJJJ/  - monatsweise Tar-Archive, reicht Jahre zurueck
  2. recent/bin/           - Einzeldateien der letzten ~35 Tage (Luecken-Fueller)

v2.0: rechnet in einem Durchgang alle Orte aus radolan_regen.ORTE. Jede RW-Datei
wird weiterhin nur einmal gelesen und ausgepackt — der Mehraufwand fuer weitere
Standorte ist damit vernachlaessigbar, es kommen nur vier Multiplikationen je
Ort und Stunde dazu. Die Laufzeit bestimmt der Download, nicht die Rechnung.

Projektion, Parser und Archivformat kommen aus radolan_regen, damit Backfill und
Live-Pipeline garantiert dieselben Punkte berechnen.

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

from radolan_regen import (ORTE, HAUPT, TZ, UA, parse_mm, punktwert,
                           archiv_laden, archiv_laden_orte, archiv_schreiben,
                           tagessumme_alle)

HIST = ("https://opendata.dwd.de/climate_environment/CDC/grids_germany/"
        "hourly/radolan/historical/bin/")
TS = re.compile(r"raa01-rw_10000-(\d{10})-dwd")
RECENT_TAGE = 35          # so weit reicht recent/bin erfahrungsgemaess zurueck


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
    """Monatsarchiv streamen und die Stundenwerte auf lokale Tage summieren.
    roh[ort_id][datum] = {"mm": float, "h": int}"""
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
                    mm = parse_mm(data)
                except Exception:
                    continue
                ds = lokaler_tag(dt)
                for o in ORTE:                       # eine Datei, alle Orte
                    e = roh.setdefault(o["id"], {}).setdefault(ds, {"mm": 0.0, "h": 0})
                    e["mm"] += punktwert(mm, o["pixels"])
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

    print("Orte: " + ", ".join(f"{o['id']} ({o['lat']:.4f}N {o['lon']:.4f}E)" for o in ORTE))

    archiv = archiv_laden()            # Hauptort, altes Feld
    a_orte = archiv_laden_orte()       # je Ort
    for o in ORTE:
        a_orte.setdefault(o["id"], {})

    def fehlt(ds):
        """Offen, sobald EIN Ort den Tag noch nicht vollstaendig hat — sonst
        blieben neu hinzugefuegte Orte fuer immer leer, weil der Hauptort
        laengst gefuellt ist."""
        if force:
            return True
        for o in ORTE:
            if not a_orte[o["id"]].get(ds, {}).get("voll"):
                return True
        return not archiv.get(ds, {}).get("voll")

    offen = [d for d in ziel if fehlt(d.isoformat())]
    if not offen:
        print("Nichts zu tun - alle Zieltage sind fuer alle Orte vollstaendig.")
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

    haupt_roh = roh.get(HAUPT["id"], {})
    for ds, e in haupt_roh.items():
        if ds not in rest:
            continue
        for o in ORTE:
            eo = roh.get(o["id"], {}).get(ds)
            if eo:
                a_orte[o["id"]][ds] = {"mm": round(eo["mm"], 2), "h": eo["h"],
                                       "voll": eo["h"] >= 24, "q": "hist"}
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
        summen, ok = tagessumme_alle(datetime(d.year, d.month, d.day, tzinfo=TZ))
        if ok > 0:
            for o in ORTE:
                a_orte[o["id"]][ds] = {"mm": summen[o["id"]], "h": ok,
                                       "voll": ok >= 24, "q": "recent"}
            archiv[ds] = {"mm": summen[HAUPT["id"]], "h": ok, "voll": ok >= 24, "q": "recent"}
            print(f"  {ds}: {summen[HAUPT['id']]} mm aus recent/ ({ok}/24 Stunden)")
        else:
            print(f"  {ds}: keine Daten verfuegbar")

    archiv_schreiben(archiv, datetime.now(timezone.utc).isoformat(timespec="seconds"), a_orte)
    voll = sum(1 for v in archiv.values() if v.get("voll"))
    print(f"Archiv: {len(archiv)} Tage gespeichert, davon {voll} vollstaendig.")
    for o in ORTE:
        vo = sum(1 for v in a_orte[o["id"]].values() if v.get("voll"))
        print(f"   {o['id']:<12} {len(a_orte[o['id']]):>4} Tage, davon {vo} vollstaendig")


if __name__ == "__main__":
    main()
