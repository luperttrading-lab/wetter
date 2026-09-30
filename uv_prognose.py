#!/usr/bin/env python3
"""UV-Prognose gegen Messung: stimmt "erw." in der Kachel "UV heute"?

Die App zeigt frueh am Tag den ERWARTETEN Tageshoechstwert (Kachel "UV heute",
"3,1 erw."), abends den gemessenen ("3,3 gem."). Ob die Erwartung im Schnitt
stimmt, wusste bisher niemand. Dieses Skript oeffnet die LIVE-APP in einem
headless Chromium - also mit genau dem Rechenweg, den der Nutzer sieht - und
liest die Zahlen aus ihr aus. Kein zweites Modell in Python, das vom App-Code
abweichen koennte.

Zwei Laeufe am Tag (Workflow uv-prognose.yml):
  morgens  ~07:20: erwartetes Maximum von HEUTE (erw), Klarwert (klar), Zeit
  abends   ~22:00: gemessenes Maximum von heute (mess), dazu die Erwartung
                   fuer MORGEN (vortag) - so, wie die Kachel sie ab
                   Sonnenuntergang zeigt

Ergebnis: uv_prognose_log.json, je Datum ein Eintrag. Auswertung
(`python uv_prognose.py --auswerten`): Bias (erw - mess), Streuung, mittlerer
Fehler, getrennt fuer "morgens" und "Vortag".

Grenzen: Ein Tag ist ein Datenpunkt. Unter etwa zehn Tagen sagt die Auswertung
nichts; sie zeigt es an.
"""
import json, math, os, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo

APP = os.environ.get("APP_URL", "https://luperttrading-lab.github.io/wetter/")
LOG = "uv_prognose_log.json"
TZ = ZoneInfo("Europe/Berlin")

JS_BEREIT = """() => typeof uvTagRechnen === 'function' && typeof kzUvMax === 'function'
  && !!uvAirFull && Array.isArray(chartRows) && chartRows.length > 0
  && !!_solar10Json"""   # let-Variablen der App: nur mit blossem Namen erreichbar, nicht ueber window

JS_LESEN = """() => {
  const T = uvTagRechnen();
  const M = kzUvMorgen();
  const iso = ms => ms ? new Date(ms).toISOString() : null;
  const r2 = v => v == null ? null : Math.round(v * 100) / 100;
  return {
    klar: r2(kzUvMax()),
    erw: T && T.prog ? r2(T.prog.max) : null,
    erw_zeit: T && T.prog ? iso(T.prog.t) : null,
    mess: T && T.mess ? r2(T.mess.uv) : null,
    mess_zeit: T && T.mess ? iso(T.mess.t) : null,
    jetzt: T && T.jetzt ? r2(T.jetzt.uv) : null,
    morgen_erw: M ? r2(M.erw) : null,
    morgen_klar: M ? r2(M.klar) : null,
    morgen_zeit: M && M.t ? iso(M.t) : null,
    version: (document.querySelector('.ver') || {}).textContent || null,
    lat: LAT, lon: LON,
  };
}"""


def messen(pg, warte_s=90):
    """Seite laden lassen, bis alle Zutaten da sind, dann auslesen."""
    ende = time.time() + warte_s
    while time.time() < ende:
        try:
            if pg.evaluate(JS_BEREIT):
                break
        except Exception:
            pass
        pg.wait_for_timeout(2000)
    else:
        raise RuntimeError("App-Daten nicht rechtzeitig da")
    pg.wait_for_timeout(3000)   # Luft-/Solardaten setzen sich nach
    return pg.evaluate(JS_LESEN)


def eintragen(log, modus, m, jetzt):
    tag = jetzt.strftime("%Y-%m-%d")
    e = log.setdefault(tag, {})
    if modus == "morgens":
        e["morgens"] = {k: m[k] for k in ("klar", "erw", "erw_zeit", "mess", "version")}
        # wie die Kachel: erwartet = max(schon Gemessenes, Prognose fuer den Rest).
        # Nur morgens VOR dem Aufgang ist "erw" der ganze Tag; ein spaeter
        # Handstart des Workflows wuerde nur den Rest des Tages erfassen.
        e["morgens"]["erw_tag"] = max(v for v in (m["erw"], m["mess"]) if v is not None) \
            if (m["erw"] is not None or m["mess"] is not None) else None
        e["morgens"]["uhr"] = jetzt.strftime("%H:%M")
    else:
        e["abends"] = {k: m[k] for k in ("mess", "mess_zeit", "version")}
        e["abends"]["uhr"] = jetzt.strftime("%H:%M")
        # Erwartung fuer morgen, so wie die Kachel sie nach Sonnenuntergang zeigt
        if m["morgen_erw"] is not None:
            n = (jetzt.date().toordinal() + 1)
            nt = datetime.fromordinal(n).strftime("%Y-%m-%d")
            log.setdefault(nt, {})["vortag"] = {
                "erw": m["morgen_erw"], "klar": m["morgen_klar"],
                "erw_zeit": m["morgen_zeit"], "uhr": jetzt.strftime("%H:%M"),
                "version": m["version"]}
    return log


def statistik(paare):
    d = [e - m for e, m in paare]
    n = len(d)
    if n == 0:
        return None
    bias = sum(d) / n
    sd = math.sqrt(sum((x - bias) ** 2 for x in d) / (n - 1)) if n > 1 else None
    mae = sum(abs(x) for x in d) / n
    rel = [(e - m) / m * 100 for e, m in paare if m and m >= 0.5]
    return {"n": n, "bias": round(bias, 2), "sd": None if sd is None else round(sd, 2),
            "mae": round(mae, 2),
            "bias_pct": round(sum(rel) / len(rel), 1) if rel else None}


def auswerten(log):
    morg, vor = [], []
    for tag, e in sorted(log.items()):
        mess = (e.get("abends") or {}).get("mess")
        if mess is None:
            continue
        mo = e.get("morgens") or {}
        erw = mo.get("erw_tag", mo.get("erw"))
        if erw is not None:
            morg.append((erw, mess))
        if (e.get("vortag") or {}).get("erw") is not None:
            vor.append((e["vortag"]["erw"], mess))
    return {"morgens": statistik(morg), "vortag": statistik(vor),
            "hinweis": "unter 10 Tagen nicht belastbar"}


def main():
    args = sys.argv[1:]
    log = {}
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as fh:
            log = json.load(fh)
    if "--auswerten" in args:
        print(json.dumps(auswerten(log), ensure_ascii=False, indent=1))
        return
    jetzt = datetime.now(TZ)
    modus = args[0] if args and args[0] in ("morgens", "abends") \
        else ("morgens" if jetzt.hour < 12 else "abends")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 390, "height": 900}, timezone_id="Europe/Berlin")
        m = None
        for versuch in (1, 2):   # Open-Meteo antwortet einem geteilten Runner gelegentlich mit 429
            pg.goto(APP + ("?t=%d" % int(time.time())), wait_until="load", timeout=120000)
            try:
                m = messen(pg)
                break
            except RuntimeError as ex:
                print("Versuch", versuch, ex)
        b.close()
        if m is None:
            sys.exit("App lieferte keine Daten - nichts eingetragen")
    print(modus, json.dumps(m, ensure_ascii=False))
    log = eintragen(log, modus, m, jetzt)
    log["_auswertung"] = auswerten({k: v for k, v in log.items() if not k.startswith("_")})
    with open(LOG, "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
