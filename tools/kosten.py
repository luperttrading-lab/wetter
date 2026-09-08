#!/usr/bin/env python3
"""Kostenzeile fuer Claude Code: liest das Sitzungsprotokoll und gibt eine kurze Zeile aus.

Aufruf:  python3 tools/kosten.py [-v] [--ttl5]
  -v      zusaetzlich Summen je Tag und je Modell
  --ttl5  Cache-Schreibpreis fuer 5-Minuten-Cache statt 1 Stunde (siehe PREISE unten)

Zwei Feinheiten, die leicht falsch gemacht werden:
 1. Jede Nachricht wird EINMAL gezaehlt (nach message.id entdoppeln) - sonst etwa das Dreifache.
 2. "Letzte Frage" = alle Antworten ab dem letzten ECHTEN Nutzerbeitrag; Werkzeugergebnisse
    stehen im Protokoll ebenfalls als `user`, zaehlen aber nicht als Frage.
"""
import json, os, glob, collections, datetime, sys

# $ je Million Token: Eingabe, Ausgabe, Cache schreiben (1 h / 5 min), Cache lesen
PREISE = {
    'claude-fable-5-1': (10, 50, 20.0, 12.5, 0.25),
    'claude-opus-5':    (5,  25, 10.0,  6.25, 0.5),
    'claude-sonnet-5':  (2,  10,  4.0,  2.5,  0.2),
    'claude-haiku-4-5': (1,   5,  2.0,  1.25, 0.1),
}
STD = (5, 25, 10.0, 6.25, 0.5)                  # Rueckfall fuer unbekannte Modelle
TZ = 2                                          # Stunden Abstand zu UTC (Sommerzeit); im Winter 1
TTL5 = '--ttl5' in sys.argv                     # Standard: 1-Stunden-Cache, so laeuft diese Umgebung

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

def cost(model, u):
    p = PREISE.get(model, STD)
    cw = p[3] if TTL5 else p[2]
    return ((u.get('input_tokens', 0) or 0) * p[0]
            + (u.get('output_tokens', 0) or 0) * p[1]
            + (u.get('cache_creation_input_tokens', 0) or 0) * cw
            + (u.get('cache_read_input_tokens', 0) or 0) * p[4]) / 1e6

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
