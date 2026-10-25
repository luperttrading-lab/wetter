#!/usr/bin/env python3
"""DWD-Warnungen als Nachricht aufs Handy (v5.67, Nutzer 25.10.2026: "wenn die Warnung reinkommt eine Mitteilung
aufs Handy - nur bei wirklich schweren, einstellbar").

Weg: Bright Sky /alerts (amtliche DWD-Warnungen, dieselbe Quelle wie die Karten in der App) -> ntfy.sh -> ntfy-App
auf dem iPhone. Der Kanal (Topic) steht NICHT im Repo (das ist oeffentlich), sondern im GitHub-Secret NTFY_TOPIC;
wer den Namen kennt, koennte mitlesen oder Nachrichten schicken.

Orte und Mindeststufe stehen in warnung.json. Gemeldet wird jede Warnung einmal je Ort; als "dieselbe" gilt sie bei
gleichem Ereignis, gleicher Stufe und gleichem Beginn - verlaengert der DWD nur das Ende, kommt keine zweite
Nachricht, wird sie hochgestuft, schon. Der Stand liegt in einer JSON-Datei (--stand), die der Workflow im Zweig
warn-stand aufbewahrt.

  python warnung.py --stand stand.json     # einmal pruefen und melden
  python warnung.py --test                 # Testnachricht schicken
"""
import argparse, datetime, json, os, sys, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
RANG = {"minor": 1, "moderate": 2, "severe": 3, "extreme": 4}
STUFE = {1: "Stufe 1 · Wetterwarnung", 2: "Stufe 2 · markantes Wetter", 3: "Stufe 3 · Unwetter", 4: "Stufe 4 · extremes Unwetter"}
PRIO = {1: 3, 2: 4, 3: 5, 4: 5}          # ntfy: 3 normal, 4 hoch, 5 dringend
APP = "https://luperttrading-lab.github.io/wetter/"
WT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def hole(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wetter-app-warnung (github.com/luperttrading-lab/wetter)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def senden(topic, titel, text, prio, tags, klick=None):
    # JSON-Veroeffentlichung: Umlaute im Titel gehen so ohne Kopfzeilen-Kodierung durch
    body = {"topic": topic, "title": titel, "message": text, "priority": prio, "tags": tags}
    if klick:
        body["click"] = klick
    req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def zeit(iso):
    if not iso:
        return ""
    t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
    return f"{WT[t.weekday()]} {t:%H:%M}"


def zeitraum(a, jetzt):
    on, ex = a.get("onset"), a.get("expires")
    if on and datetime.datetime.fromisoformat(on.replace("Z", "+00:00")) > jetzt:
        return f"{zeit(on)} – {zeit(ex)} Uhr" if ex else f"ab {zeit(on)} Uhr"
    return f"bis {zeit(ex)} Uhr" if ex else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stand", default="stand.json")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "warnung.json"))
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        print("NTFY_TOPIC fehlt - nichts zu tun (GitHub-Secret anlegen)")
        return 0
    cfg = json.load(open(a.config, encoding="utf-8"))
    ab = RANG.get(cfg.get("ab", "moderate"), 2)

    if a.test:
        st = senden(topic, "TEST · Wetter-App",
                    "So kommt eine Warnung an. Gemeldet wird ab " + STUFE[ab].split(" · ")[0] + " für "
                    + ", ".join(o["name"] for o in cfg["orte"]) + ". Keine echte Warnung.", 4, ["warning", "test_tube"], APP)
        print("Testnachricht:", st)
        return 0

    try:
        stand = json.load(open(a.stand, encoding="utf-8"))
    except Exception:
        stand = {}
    gesendet = stand.get("gesendet", {})
    jetzt = datetime.datetime.now(datetime.timezone.utc)
    # Abgelaufenes vergessen (mit einem Tag Puffer)
    for k, ex in list(gesendet.items()):
        try:
            if datetime.datetime.fromisoformat(ex.replace("Z", "+00:00")) < jetzt - datetime.timedelta(days=1):
                del gesendet[k]
        except Exception:
            del gesendet[k]

    neu = 0
    for o in cfg["orte"]:
        try:
            d = hole(f"https://api.brightsky.dev/alerts?lat={o['lat']}&lon={o['lon']}")
        except Exception as e:
            print(f"{o['name']}: Abruf fehlgeschlagen ({e})")
            continue
        for w in d.get("alerts", []):
            r = RANG.get(str(w.get("severity", "")).lower(), 0)
            if r < ab:
                continue
            ev = (w.get("event_de") or w.get("event_en") or "Wetterwarnung").strip()
            key = f"{o['name']}|{ev}|{r}|{w.get('onset', '')}"
            if key in gesendet:
                continue
            zeilen = [STUFE[r] + (" · Vorabinformation" if "VORAB" in (w.get("headline_de") or "").upper() else ""),
                      zeitraum(w, jetzt)]
            besch = (w.get("description_de") or "").strip()
            if besch:
                zeilen.append(besch if len(besch) <= 220 else besch[:217].rstrip() + " …")
            klick = APP + "?" + urllib.parse.urlencode({"lat": o["lat"], "lon": o["lon"], "name": o["name"]})
            try:
                st = senden(topic, f"{ev} – {o['name']}", "\n".join(z for z in zeilen if z), PRIO[r], ["warning"], klick)
            except Exception as e:
                print(f"{o['name']}: {ev} - Senden fehlgeschlagen ({e})")
                continue
            gesendet[key] = w.get("expires") or (jetzt + datetime.timedelta(days=2)).isoformat()
            neu += 1
            print(f"gemeldet: {o['name']} | {ev} | Stufe {r} | {zeitraum(w, jetzt)} | HTTP {st}")
    stand["gesendet"] = gesendet
    json.dump(stand, open(a.stand, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{neu} neue Meldung(en), {len(gesendet)} im Stand")
    return 0


if __name__ == "__main__":
    sys.exit(main())
