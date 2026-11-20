#!/usr/bin/env python3
"""Abfuhrkalender Landkreis Aurich (C-Trace) -> muell-aurich.json fuer die App (Kachel "Muellabfuhr").

Der Landkreis Aurich fuehrt seinen Abfuhrkalender ueber C-Trace
(apps.c-trace.de/web.aurich-abfallkalender). Der Dienst sendet KEINEN CORS-Kopf - der Browser
darf ihn nicht lesen. Dieser Lauf holt den oeffentlichen Kalender fuer die Gemeinden in GEMEINDEN
und legt eine kompakte Fassung neben die App (gleiche Herkunft, ~20 KB gzip). In der App waehlt
man Gemeinde, Strasse und - nur wo die Strasse geteilt ist - die Hausnummer; nichts davon
verlaesst das Geraet.

Der Dienst liefert eine Kalenderdatei je HAUSNUMMER (leere Hausnummer -> HTTP 500), es gibt
keine Abfuhrbezirke in der Schnittstelle. Je Strasse werden darum Stichproben gezogen: erste,
mittlere und letzte Nummer, getrennt nach gerade/ungerade. Sind alle gleich, gilt der Kalender
fuer die ganze Strasse. Sonst wird die Liste so lange halbiert, bis jedes Stueck an beiden
Enden denselben Kalender hat (angenommen: dazwischen auch). Rund 3000-4000 Abrufe je Lauf.

Ein VOLLER Lauf passiert nur, wenn noetig: keine Daten, aelter als VOLL_TAGE, oder die
Stichprobe (PROBEN Strassen) liefert andere Termine als gespeichert - so kommt der neue
Jahreskalender (meist im Dezember) von selbst. Sonst bleibt die Datei unveraendert.
Vergangene Termine aus der alten Datei bleiben eine Woche stehen (Jahreswechsel).

Aufruf: python3 muell_aurich.py [--voll] [--max N]   (--max: nur N Strassen, zum Pruefen)
"""
import json, re, sys, time, hashlib, datetime, urllib.request, urllib.parse, urllib.error

B = "https://apps.c-trace.de/web.aurich-abfallkalender"
UA = {"User-Agent": "Mozilla/5.0 (wetter-app muellkalender; github.com/luperttrading-lab/wetter)"}
DATEI = "muell-aurich.json"
# (Gemeinde, Ort im Dienst, Rahmen S/N/W/O aus OSM/Nominatim, 20.11.2026)
GEMEINDEN = [("Norden", "Norden", [53.4968, 53.6684, 7.0872, 7.2762])]
PAUSE = 0.25
VOLL_TAGE = 35
PROBEN = 6
AB = "|".join(str(i) for i in range(300))


class _KeinUmleiten(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def sitzung():
    op = urllib.request.build_opener(_KeinUmleiten)
    try:
        op.open(urllib.request.Request(B + "/Abfallkalender", headers=UA), timeout=30)
    except urllib.error.HTTPError as e:
        m = re.search(r"\(S\([a-z0-9]+\)\)", e.headers.get("Location", ""))
        if m:
            return m.group(0)
    raise SystemExit("keine Sitzung von C-Trace")


S = None
ABRUFE = 0
# nur Termine ab einer Woche zurueck zaehlen: neue Objekte haben einen Kalender erst ab ihrem Einzug
# (Alleestrasse 6a ab 28.08.) - mit allen Terminen galten sie als "andere Abfuhr"
AB_TAG = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y%m%d")


def holen(url, acc=None, versuche=3):
    global ABRUFE
    h = dict(UA)
    if acc:
        h["Accept"] = acc
    for i in range(versuche):
        try:
            ABRUFE += 1
            time.sleep(PAUSE)
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40) as f:
                return f.read()
        except urllib.error.HTTPError as e:
            if e.code == 500:          # Objekt ohne Abfuhr (gibt es) - kein neuer Versuch
                return None
            if i == versuche - 1:
                raise
        except Exception:
            if i == versuche - 1:
                raise
        time.sleep(3 * (i + 1))


def odata(pfad, **q):
    u = B + "/" + S + "/OData.svc/" + pfad + ("?" + urllib.parse.urlencode(q) if q else "")
    d = json.loads(holen(u, "application/json"))["d"]
    return d.get("results", d) if isinstance(d, dict) else d


def q(s):
    return "'" + s.replace("'", "''") + "'"


def kalender(gem, ort, strasse, hnr):
    """Termine [(JJJJMMTT, Tonne)] einer Hausnummer, sortiert; None bei Fehler."""
    url = B + "/" + S + "/abfallkalender/cal?" + urllib.parse.urlencode(
        {"Ort": ort, "Gemeinde": gem, "Strasse": strasse, "Hausnr": hnr, "Abfall": AB})
    r = holen(url)
    if r is None:
        return None
    t = r.decode("utf-8-sig", "replace").replace("\r\n ", "").replace("\n ", "")
    ev = []
    for blk in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", t, re.S):
        d = re.search(r"DTSTART[^:\n]*:(\d{8})", blk)
        s = re.search(r"\nSUMMARY[^:\n]*:([^\r\n]*)", blk)
        if d and s:
            name = re.sub(r"^\s*Abfuhr:\s*", "", s.group(1)).strip()
            if d.group(1) >= AB_TAG:
                ev.append((d.group(1), name))
    return sorted(set(ev)) if ev else None


def hnr_text(o):
    return ((o.get("HausNr") or "") + (o.get("HausNrZus") or "")).strip()


def hnr_zahl(h):
    m = re.match(r"\s*(\d+)", h)
    return int(m.group(1)) if m else 10 ** 6


def strasse_lesen(gem, ort, strasse, cache):
    """-> ("all", kal) oder ("hn", [(hnr, kal), ...])"""
    objs = odata("AktuelleObjekte", gemeinde=q(gem), ort=q(ort), strasse=q(strasse))
    nums = []
    for o in objs:
        h = hnr_text(o)
        if h and h not in nums:
            nums.append(h)
    nums.sort(key=lambda h: (hnr_zahl(h), h))
    if not nums:
        return None

    def kal(h):
        if h not in cache:
            cache[h] = kalender(gem, ort, strasse, h)
        return cache[h]

    def gruppe(lst):
        """Halbieren, bis beide Enden gleich sind; liefert {hnr: kal}."""
        res = {}
        if not lst:
            return res
        a, z = kal(lst[0]), kal(lst[-1])
        if len(lst) <= 2 or (a == z and kal(lst[len(lst) // 2]) == a):
            for h in lst:
                res[h] = a if (a == z or h == lst[0]) else z
            return res
        m = len(lst) // 2
        res.update(gruppe(lst[:m]))
        res.update(gruppe(lst[m:]))
        return res

    ger = [h for h in nums if hnr_zahl(h) % 2 == 0]
    ung = [h for h in nums if hnr_zahl(h) % 2 == 1 or hnr_zahl(h) == 10 ** 6]
    alle = {}
    alle.update(gruppe(ger))
    alle.update(gruppe(ung))
    kals = {json.dumps(v) for v in alle.values() if v}
    if not kals:
        return None
    if len(kals) == 1:
        return ("all", json.loads(kals.pop()))
    return ("hn", [(h, alle[h]) for h in nums if alle.get(h)])


def lesen_alt():
    try:
        return json.load(open(DATEI, encoding="utf-8"))
    except Exception:
        return None


# Kalender kompakt: je Tonne (Index in "fr") ein Text "JJJJMMTT d d d ..." - erstes Datum voll, danach
# der Abstand in Tagen zum vorigen. Rund 200 Byte je Kalender statt 1 KB.
def kal_pack(kal, frs):
    je = {}
    for d, n in kal:
        if n not in frs:
            frs.append(n)
        je.setdefault(str(frs.index(n)), []).append(d)
    out = {}
    for f, ds in je.items():
        ds = sorted(set(ds))
        tage = [datetime.date(int(d[:4]), int(d[4:6]), int(d[6:])) for d in ds]
        out[f] = " ".join([ds[0]] + [str((b - a).days) for a, b in zip(tage, tage[1:])])
    return out


def kal_auf(t, frs):
    ev = []
    for f, txt in t.items():
        teile = txt.split()
        d = datetime.date(int(teile[0][:4]), int(teile[0][4:6]), int(teile[0][6:]))
        ev.append((d.strftime("%Y%m%d"), frs[int(f)]))
        for x in teile[1:]:
            d += datetime.timedelta(days=int(x))
            ev.append((d.strftime("%Y%m%d"), frs[int(f)]))
    return sorted(ev)


def alt_kalender(alt, gem, strasse, hnr=None):
    """Termine einer Strasse (bzw. Hausnummer) aus der alten Datei.
    Strasse = Kalender-Index, oder geteilt: [Standard, "h1|h2|...", {Hausnummer: Kalender}]."""
    try:
        e = alt["g"][gem]["s"][strasse]
        if isinstance(e, list):
            if hnr is None or hnr not in e[1].split("|"):
                return None
            e = e[2].get(hnr, e[0])
        return kal_auf(alt["t"][e], alt["fr"])
    except Exception:
        return None


def probe_noetig(alt, heute):
    """True, wenn ein voller Lauf faellig ist."""
    if not alt or "--voll" in sys.argv:
        return True
    try:
        st = datetime.date.fromisoformat(alt["voll"][:10])
    except Exception:
        return True
    if (heute - st).days >= VOLL_TAGE:
        return True
    ab = (heute - datetime.timedelta(days=1)).strftime("%Y%m%d")
    for gem, ort, _ in GEMEINDEN:
        st_alle = [k for k, v in alt["g"].get(gem, {}).get("s", {}).items() if not isinstance(v, list)]
        for k in st_alle[:: max(1, len(st_alle) // PROBEN)][:PROBEN]:
            objs = odata("AktuelleObjekte", gemeinde=q(gem), ort=q(ort), strasse=q(k))
            nums = sorted({hnr_text(o) for o in objs if hnr_text(o)}, key=lambda h: (hnr_zahl(h), h))
            if not nums:
                continue
            neu = [e for e in (kalender(gem, ort, k, nums[0]) or []) if e[0] >= ab]
            vor = [e for e in (alt_kalender(alt, gem, k) or []) if e[0] >= ab]
            if neu != vor:
                print("Probe", k, "weicht ab - voller Lauf")
                return True
    return False


def main():
    global S
    heute = datetime.date.today()
    S = sitzung()
    alt = lesen_alt()
    if not probe_noetig(alt, heute):
        print("Stichprobe unveraendert, letzter voller Lauf", alt.get("voll"), "- nichts zu tun;", ABRUFE, "Abrufe")
        return
    maxn = None
    if "--max" in sys.argv:
        maxn = int(sys.argv[sys.argv.index("--max") + 1])
    bleib = (heute - datetime.timedelta(days=7)).strftime("%Y%m%d")
    touren, tour_id, frs = [], {}, []
    g_out = {}
    t0 = time.time()

    def tour(kal):
        t = kal_pack(kal, frs)
        k = json.dumps(t, sort_keys=True)
        if k not in tour_id:
            tour_id[k] = len(touren)
            touren.append(t)
        return tour_id[k]

    def geteilt(paare):
        """[(hnr, tour)] -> [Standard, "h1|h2", {Abweichung}] - Standard = haeufigster Kalender."""
        zaehl = {}
        for _, t in paare:
            zaehl[t] = zaehl.get(t, 0) + 1
        std = max(zaehl, key=zaehl.get)
        return [std, "|".join(h for h, _ in paare), {h: t for h, t in paare if t != std}]

    def mit_alt(kal, gem, strasse, hnr=None):
        """vergangene Woche aus der alten Datei behalten (der neue Jahreskalender beginnt im Januar)."""
        if not alt:
            return kal
        da = set(kal)
        for e in alt_kalender(alt, gem, strasse, hnr) or []:
            if e[0] >= bleib and e[0] < (kal[0][0] if kal else "99999999") and e not in da:
                da.add(e)
        return sorted(da)

    for gem, ort, box in GEMEINDEN:
        strassen = odata("Strassen", **{"$filter": "Ort/Gebiet/Name eq " + q(gem) + " and Ort/Name eq " + q(ort)})
        namen = sorted({s_["Name"] for s_ in strassen})
        if maxn:
            namen = namen[:maxn]
        s_out, fehl = {}, 0
        for i, n in enumerate(namen):
            try:
                r = strasse_lesen(gem, ort, n, {})
            except Exception as e:
                print("Fehler", n, e)
                r = None
            if not r:
                fehl += 1
                # alte Daten behalten, sonst faellt die Strasse aus der Auswahl
                if alt and n in alt.get("g", {}).get(gem, {}).get("s", {}):
                    e = alt["g"][gem]["s"][n]
                    if isinstance(e, list):
                        s_out[n] = geteilt([(h, tour(alt_kalender(alt, gem, n, h))) for h in e[1].split("|")])
                    else:
                        s_out[n] = tour(alt_kalender(alt, gem, n))
                continue
            if r[0] == "all":
                s_out[n] = tour(mit_alt(r[1], gem, n))
            else:
                s_out[n] = geteilt([(h, tour(mit_alt(k, gem, n, h))) for h, k in r[1]])
            if i % 25 == 0:
                print(f"{gem}: {i + 1}/{len(namen)} Strassen, {len(touren)} Kalender, {ABRUFE} Abrufe, {time.time() - t0:.0f} s", flush=True)
        if fehl > len(namen) * 0.2:
            raise SystemExit(f"{gem}: {fehl} von {len(namen)} Strassen ohne Kalender - nichts geschrieben")
        g_out[gem] = {"o": ort, "b": box, "s": s_out}
    out = {
        "stand": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "voll": heute.isoformat(),
        "quelle": "Abfallwirtschaftsbetrieb Landkreis Aurich (C-Trace)",
        "fr": frs, "t": touren, "g": g_out,
    }
    json.dump(out, open(DATEI, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    geteilt = sum(1 for g in g_out.values() for v in g["s"].values() if isinstance(v, list))
    print(f"geschrieben: {sum(len(g['s']) for g in g_out.values())} Strassen ({geteilt} geteilt), "
          f"{len(touren)} Kalender, Tonnen {frs}, {ABRUFE} Abrufe, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
