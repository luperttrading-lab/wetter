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
TZ = 2                                          # Stunden Abstand zu UTC (Sommerzeit); im Winter 1
TTL5 = '--ttl5' in sys.argv

base = os.path.expanduser('~/.claude/projects')
slug = os.getcwd().replace('/', '-')
files = glob.glob(f'{base}/{slug}/*.jsonl') or glob.glob(f'{base}/*/*.jsonl')
if not files:
    sys.exit('Kein Sitzungsprotokoll gefunden - keine Kostenzeile.')
f = max(files, key=os.path.getmtime)

seen, last_user = {}, None
for line in open(f):
    try: d = json.loads(line)
    except: continue
    t, m = d.get('type'), d.get('message', {})
    if t == 'user':                             # nur echte Nutzerfragen, keine Werkzeugergebnisse
        c = m.get('content')
        if isinstance(c, str) or (isinstance(c, list)
                and any(b.get('type') == 'text' for b in c if isinstance(b, dict))
                and not any(b.get('type') == 'tool_result' for b in c if isinstance(b, dict))):
            last_user = d.get('timestamp')
    if t == 'assistant' and m.get('usage'):     # je Nachricht nur die letzte Fassung zaehlen
        seen[m.get('id') or d.get('uuid')] = (d.get('timestamp', ''), m.get('model'), m['usage'])

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

jetzt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=TZ)
heute_lokal = jetzt.strftime('%Y-%m-%d')
def lokal(ts):
    try: return (datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                 + datetime.timedelta(hours=TZ)).strftime('%Y-%m-%d')
    except: return ''

tot   = sum(cost(mo, u) for _, mo, u in seen.values())
heute = sum(cost(mo, u) for ts, mo, u in seen.values() if lokal(ts) == heute_lokal)
frage = sum(cost(mo, u) for ts, mo, u in seen.values() if last_user and ts >= last_user)
de = lambda x: f'{x:.2f}'.replace('.', ',')
print(f"<sub>{jetzt.strftime('%d.%m. %H:%M')} Uhr · Frage {de(frage)} · heute {de(heute)} · ges. {de(tot)} $</sub>")

if '-v' in sys.argv:
    days, mods = collections.Counter(), collections.Counter()
    for ts, mo, u in seen.values():
        days[lokal(ts)] += cost(mo, u); mods[mo] += cost(mo, u)
    print('Tage:   ', {d: round(c, 2) for d, c in sorted(days.items())})
    print('Modelle:', {m: round(c, 2) for m, c in mods.items()})
    print('Suchen: ', sum((u.get('server_tool_use') or {}).get('web_search_requests', 0) or 0
                          for _, _, u in seen.values()))
