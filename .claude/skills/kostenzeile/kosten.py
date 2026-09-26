#!/usr/bin/env python3
"""Kostenzeile fuer Claude Code: liest das Sitzungsprotokoll und gibt eine kurze Zeile aus.

Aufruf:  python3 tools/kosten.py [-v] [--ttl5]
  -v      zusaetzlich Summen je Tag und je Modell
  --ttl5  nur Rueckfall fuer alte Protokolle ohne Cache-TTL-Aufteilung

Preise geprueft am 08.09.2026 gegen
https://platform.claude.com/docs/en/about-claude/pricing

Feinheiten, die leicht falsch gemacht werden:
 1. Jede Nachricht wird EINMAL gezaehlt (nach message.id entdoppeln) - sonst etwa das Dreifache.
 2. "Letzte Frage" = alle Antworten ab dem letzten ECHTEN Nutzerbeitrag; Werkzeugergebnisse
    stehen im Protokoll ebenfalls als `user`, zaehlen aber nicht als Frage.
 3. Modell-IDs im Protokoll tragen oft ein Datum ("claude-haiku-4-5-20251001").
    Deshalb laengster passender Praefix, nicht exakter Schluessel - sonst greift der
    Rueckfall auf Opus-Preise und Haiku waere um Faktor 5 zu teuer.
 4. Cache-Preise werden aus dem Basis-Eingabepreis abgeleitet (1,25x fuer 5 min,
    2x fuer 1 h, 0,1x fuer Lesen; 0,025x bei Fable/Mythos 5.1) - eine Zahl je Modell
    weniger, die veralten kann.
"""
import json, os, glob, collections, datetime, sys

# Modell-Praefix -> (Eingabe $/M, Ausgabe $/M, Faktor fuer Cache-Lesen)
PREISE = {
    'claude-fable-5-1':  (10,   50,  0.025),
    'claude-mythos-5-1': (10,   50,  0.025),
    'claude-fable-5':    (10,   50,  0.1),
    'claude-mythos-5':   (10,   50,  0.1),
    'claude-opus-5':     (5,    25,  0.1),
    'claude-opus-4-8':   (5,    25,  0.1),
    'claude-opus-4-7':   (5,    25,  0.1),
    'claude-opus-4-6':   (5,    25,  0.1),
    'claude-opus-4-5':   (5,    25,  0.1),
    'claude-opus-4-1':   (15,   75,  0.1),
    'claude-opus-4':     (15,   75,  0.1),
    'claude-sonnet-5':   (2,    10,  0.1),
    'claude-sonnet-4-6': (3,    15,  0.1),
    'claude-sonnet-4-5': (3,    15,  0.1),
    'claude-sonnet-4':   (3,    15,  0.1),
    'claude-haiku-4-5':  (1,     5,  0.1),
    'claude-haiku-3-5':  (0.8,   4,  0.1),
}
STD = (5, 25, 0.1)                              # Rueckfall fuer unbekannte Modelle: Opus 5
FAST = (10, 50, 0.1)                            # speed="fast", nur Opus 5 / Opus 4.8
WEB_SUCHE = 0.01                                # $ je Websuche (10 $ / 1000)
try:                                            # Zeitumstellung automatisch, kein Handgriff im Winter
    from zoneinfo import ZoneInfo
    ZONE = ZoneInfo('Europe/Berlin')
except Exception:
    ZONE = datetime.timezone(datetime.timedelta(hours=2))
TTL5 = '--ttl5' in sys.argv

base = os.path.expanduser('~/.claude/projects')

def protokolle():
    """Protokolle des aktuellen Projekts: cwd, sonst aufwaerts durch die Elternordner.

    Der Rueckfall auf *alle* Projekte bleibt, warnt aber auf stderr - sonst liefert
    ein Aufruf aus dem falschen Ordner stillschweigend die Zahlen eines fremden
    Projekts, und die Zeile sieht trotzdem richtig aus.
    """
    d = os.path.abspath(os.getcwd())
    while True:
        g = glob.glob(f"{base}/{d.replace('/', '-')}/*.jsonl")
        if g: return g
        eltern = os.path.dirname(d)
        if eltern == d: break
        d = eltern
    g = glob.glob(f'{base}/*/*.jsonl')
    if g:
        print(f'Warnung: kein Protokoll fuer {os.getcwd()}; nehme '
              f'{os.path.basename(os.path.dirname(max(g, key=os.path.getmtime)))}',
              file=sys.stderr)
    return g

files = protokolle()
if not files:
    sys.exit('Kein Sitzungsprotokoll gefunden - keine Kostenzeile.')
f = max(files, key=os.path.getmtime)

FRAGEN = []                                     # Zeitstempel aller echten Nutzerbeitraege

def lies(pfad, merken=False):
    """-> ({message_id: (timestamp, modell, usage)}, letzte echte Nutzerfrage)"""
    treffer, letzte = {}, None
    try: zeilen = open(pfad)
    except OSError: return treffer, letzte
    for line in zeilen:
        try: d = json.loads(line)
        except: continue
        t, m = d.get('type'), d.get('message', {})
        if not isinstance(m, dict): continue
        if t == 'user':                         # nur echte Nutzerfragen, keine Werkzeugergebnisse
            c = m.get('content')
            if isinstance(c, str) or (isinstance(c, list)
                    and any(b.get('type') == 'text' for b in c if isinstance(b, dict))
                    and not any(b.get('type') == 'tool_result' for b in c if isinstance(b, dict))):
                letzte = d.get('timestamp')
                if merken and letzte: FRAGEN.append(letzte)
        if t == 'assistant' and m.get('usage'): # je Nachricht nur die letzte Fassung zaehlen
            treffer[m.get('id') or d.get('uuid')] = (d.get('timestamp', ''), m.get('model'),
                                                     m['usage'])
    return treffer, letzte

seen, last_user = lies(f, merken=True)

def preis(model, u):
    """Basispreise fuer diese Nachricht: laengster Praefix, Fast-Mode, Datenresidenz."""
    mo = model or ''
    treffer = [k for k in PREISE if mo.startswith(k)]
    p = PREISE[max(treffer, key=len)] if treffer else STD
    if u.get('speed') == 'fast' and (mo.startswith('claude-opus-5')
                                     or mo.startswith('claude-opus-4-8')):
        p = FAST                                # doppelter Preis, Cache-Faktoren gelten darauf
    faktor = 1.1 if u.get('inference_geo') == 'us' else 1.0   # US-Datenresidenz
    return p[0] * faktor, p[1] * faktor, p[2]

def cost(model, u):
    pin, pout, fread = preis(model, u)
    # Das Protokoll nennt die Cache-TTL selbst (usage.cache_creation.ephemeral_*).
    cc = u.get('cache_creation') or {}
    w1 = cc.get('ephemeral_1h_input_tokens', 0) or 0
    w5 = cc.get('ephemeral_5m_input_tokens', 0) or 0
    if not (w1 or w5):                          # aeltere Protokolle ohne Aufteilung
        rest = u.get('cache_creation_input_tokens', 0) or 0
        w5, w1 = (rest, 0) if TTL5 else (0, rest)
    tok = ((u.get('input_tokens', 0) or 0) * pin
           + (u.get('output_tokens', 0) or 0) * pout
           + w1 * 2 * pin + w5 * 1.25 * pin
           + (u.get('cache_read_input_tokens', 0) or 0) * fread * pin) / 1e6
    such = ((u.get('server_tool_use') or {}).get('web_search_requests', 0) or 0) * WEB_SUCHE
    return tok + such

jetzt = datetime.datetime.now(ZONE)
heute_lokal = jetzt.strftime('%Y-%m-%d')
def zeit(ts):
    try: return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(ZONE)
    except: return None
def lokal(ts):
    t = zeit(ts)
    return t.strftime('%Y-%m-%d') if t else ''

# "heute" zaehlt ueber ALLE Projekte, nicht nur diese Sitzung - sonst waere die Zahl in
# einem eintaegigen Chat identisch mit "ges." und truege keine eigene Information.
# Dateien, die vor der lokalen Mitternacht zuletzt geschrieben wurden, koennen nichts
# von heute enthalten und werden gar nicht erst geoeffnet.
schwelle = jetzt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
alle, projekte = {}, set()
for p in glob.glob(f'{base}/*/*.jsonl'):
    try:
        if os.path.getmtime(p) < schwelle: continue
    except OSError: continue
    tr, _ = lies(p)
    if any(lokal(ts) == heute_lokal for ts, _, _ in tr.values()):
        projekte.add(os.path.basename(os.path.dirname(p)))
    alle.update(tr)                             # message.id ist global eindeutig
alle.update(seen)                               # eigene Sitzung sicher enthalten

tot   = sum(cost(mo, u) for _, mo, u in seen.values())
heute = sum(cost(mo, u) for ts, mo, u in alle.values() if lokal(ts) == heute_lokal)
frage = sum(cost(mo, u) for ts, mo, u in seen.values() if last_user and ts >= last_user)
# Dauer der laufenden Frage: vom letzten echten Nutzerbeitrag bis zur juengsten
# Antwort im Protokoll. Die Sekunden nach diesem Aufruf fehlen - wie beim Betrag.
def dauer_seit(ab):
    t0 = zeit(ab) if ab else None
    enden = [zeit(ts) for ts, _, _ in seen.values() if ts]
    enden = [t for t in enden if t and t0 and t >= t0]
    if not (t0 and enden): return '–'
    return spanne((max(enden) - t0).total_seconds())

def spanne(s):
    s = int(round(s))
    if s < 60:   return f'{s} s'
    if s < 3600: return f'{s//60}:{s%60:02d} min'
    return f'{s//3600}:{(s%3600)//60:02d} h'

frage_dauer = dauer_seit(last_user)
de = lambda x: f'{x:.2f}'.replace('.', ',')
print(f"<sub>{jetzt.strftime('%d.%m. %H:%M')} Uhr · {frage_dauer} · Frage {de(frage)} · "
      f"heute {de(heute)} · ges. {de(tot)} $</sub>")

if '-v' in sys.argv:
    days, mods = collections.Counter(), collections.Counter()
    for ts, mo, u in seen.values():
        days[lokal(ts)] += cost(mo, u); mods[mo] += cost(mo, u)
    print('Tage:   ', {d: round(c, 2) for d, c in sorted(days.items())})
    # Arbeitszeit = Summe der Fragedauern, nicht die Spanne vom ersten bis zum
    # letzten Zeitstempel - dazwischen liegen die Pausen des Nutzers.
    grenzen = sorted(set(FRAGEN)) + ['9999']
    antworten = sorted((ts, ) for ts, _, _ in seen.values() if ts)
    summe, gezaehlt = 0.0, 0
    for a, b in zip(grenzen, grenzen[1:]):
        im_fenster = [zeit(ts) for (ts,) in antworten if a <= ts < b]
        im_fenster = [t for t in im_fenster if t]
        if im_fenster and zeit(a):
            summe += (max(im_fenster) - zeit(a)).total_seconds(); gezaehlt += 1
    if gezaehlt:
        print(f'Dauer:   {spanne(summe)} Arbeitszeit ueber {gezaehlt} Fragen, '
              f'im Mittel {spanne(summe/gezaehlt)}')
    print('Modelle:', {m: round(c, 2) for m, c in mods.items()})
    print('Suchen: ', sum((u.get('server_tool_use') or {}).get('web_search_requests', 0) or 0
                          for _, _, u in seen.values()))
    stempel = sorted(ts for ts, _, _ in seen.values() if ts)
    print('Datei:  ', f, f'({len(seen)} Nachrichten,'
          f' {lokal(stempel[0])} bis {lokal(stempel[-1])})' if stempel else '')
    if len(files) > 1:
        print('Hinweis:', len(files), 'Sitzungen in diesem Projekt; "ges." zaehlt nur die'
              ' zuletzt geaenderte.')
    print('heute:  ', f'{len(projekte)} Projekt(e):', ', '.join(sorted(projekte)) or '-')
