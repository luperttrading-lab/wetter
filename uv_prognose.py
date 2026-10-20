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

Seit 20.10.2026: GitHub startet geplante Laeufe oft 3-5 Stunden zu spaet (der
07:20-Lauf kam um 12:11, der 22:05-Lauf um 01:28 am Folgetag). Bis dahin
entschied die UHRZEIT des Laufs ueber die Rolle - der verspaetete Morgenlauf
wurde so zum Abendlauf und verbuchte als "gemessenes Maximum" den Stand von
11:15, also VOR der Tagesspitze. Jetzt entscheidet der SONNENSTAND, und ein
Lauf ausserhalb seines Fensters traegt nichts ein:
  morgens  gueltig bis 2 h nach Sonnenaufgang und solange gemessen < 0,5
           (sonst steckt schon Gemessenes in "erw"); der erste gueltige zaehlt
  abends   gueltig ab 1 h vor Sonnenuntergang bis Mitternacht (die Spitze ist
           dann vorbei und die 10-Minuten-Station hat sie geliefert); der
           hoechste Wert zaehlt, "vortag" (Erwartung fuer morgen) der erste
Der Workflow startet deshalb je drei Laeufe pro Fenster. Alte Eintraege ohne
diese Pruefung: Abendlauf vor 13:00 gilt als ungueltig (vor der Spitze).
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
    auf: (() => { try { return sunMoment(new Date(), true); } catch (e) { return null; } })(),
    unter: (() => { try { return sunMoment(new Date(), false); } catch (e) { return null; } })(),
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


def fenster(m, jetzt_ms):
    """Welche Rolle darf dieser Lauf uebernehmen? (Sonnenstand statt Uhrzeit)"""
    auf, unter = m.get("auf"), m.get("unter")
    if auf is None or unter is None:
        return None
    if jetzt_ms < auf + 2 * 3600e3 and (m.get("mess") is None or m["mess"] < 0.5):
        return "morgens"
    if jetzt_ms >= unter - 3600e3:
        return "abends"
    return None


def eintragen(log, modus, m, jetzt, gueltig=True):
    tag = jetzt.strftime("%Y-%m-%d")
    e = log.setdefault(tag, {})
    if modus == "morgens":
        alt = e.get("morgens")
        if alt and alt.get("gueltig", True) and gueltig:
            print("morgens schon eingetragen um", alt.get("uhr"), "- bleibt")
            return log
        e["morgens"] = {k: m[k] for k in ("klar", "erw", "erw_zeit", "mess", "version")}
        # wie die Kachel: erwartet = max(schon Gemessenes, Prognose fuer den Rest).
        e["morgens"]["erw_tag"] = max(v for v in (m["erw"], m["mess"]) if v is not None) \
            if (m["erw"] is not None or m["mess"] is not None) else None
        e["morgens"]["uhr"] = jetzt.strftime("%H:%M")
        e["morgens"]["gueltig"] = gueltig
    else:
        alt = e.get("abends")
        if alt and alt.get("gueltig", True) and gueltig and (alt.get("mess") or 0) >= (m["mess"] or 0):
            print("abends: eingetragenes Maximum", alt.get("mess"), ">= jetzt", m["mess"], "- bleibt")
        else:
            e["abends"] = {k: m[k] for k in ("mess", "mess_zeit", "version")}
            e["abends"]["uhr"] = jetzt.strftime("%H:%M")
            e["abends"]["gueltig"] = gueltig
        # Erwartung fuer morgen, so wie die Kachel sie nach Sonnenuntergang zeigt
        if m["morgen_erw"] is not None and gueltig:
            n = (jetzt.date().toordinal() + 1)
            nt = datetime.fromordinal(n).strftime("%Y-%m-%d")
            if not (log.get(nt, {}).get("vortag") or {}).get("gueltig"):
                log.setdefault(nt, {})["vortag"] = {
                    "erw": m["morgen_erw"], "klar": m["morgen_klar"],
                    "erw_zeit": m["morgen_zeit"], "uhr": jetzt.strftime("%H:%M"),
                    "version": m["version"], "gueltig": True}
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


def _gilt(x, rolle):
    """Neue Eintraege tragen "gueltig"; alte (vor 20.10.2026) nach der Uhrzeit:
    ein Abendlauf vor 13:00 kam vor der Tagesspitze."""
    if "gueltig" in x:
        return bool(x["gueltig"])
    return not (rolle == "abends" and (x.get("uhr") or "00:00") < "13:00")


def auswerten(log):
    morg, vor = [], []
    for tag, e in sorted(log.items()):
        ab = e.get("abends") or {}
        mess = ab.get("mess")
        if mess is None or not _gilt(ab, "abends"):
            continue
        mo = e.get("morgens") or {}
        erw = mo.get("erw_tag", mo.get("erw"))
        if erw is not None and _gilt(mo, "morgens"):
            morg.append((erw, mess))
        if (e.get("vortag") or {}).get("erw") is not None:
            vor.append((e["vortag"]["erw"], mess))
    return {"morgens": statistik(morg), "vortag": statistik(vor),
            "hinweis": "unter 10 Tagen nicht belastbar" if len(morg) < 10 else
                       "ab 10 Tagen: Richtung belastbar, Groesse noch grob"}


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
    erzwungen = args[0] if args and args[0] in ("morgens", "abends") else None
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
    rolle = fenster(m, time.time() * 1000)
    modus = erzwungen or rolle
    print("Lauf", jetzt.strftime("%H:%M"), "Fenster:", rolle, "Modus:", modus, json.dumps(m, ensure_ascii=False))
    if modus is None:
        print("ausserhalb beider Fenster (zwischen morgens und abends) - nichts eingetragen")
        return
    log = eintragen(log, modus, m, jetzt, gueltig=(modus == rolle))
    log["_auswertung"] = auswerten({k: v for k, v in log.items() if not k.startswith("_")})
    with open(LOG, "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
