#!/usr/bin/env python3
"""Diagnose einer langen Claude-Code-Sitzung: prueft das Kostenmodell an echten Daten.

Liest NUR die Token-Zaehler des eigenen Sitzungsprotokolls (usage-Felder),
keine Nachrichteninhalte. Aufruf im Projektverzeichnis:  python3 kosten-diagnose.py
"""
import json, os, glob, datetime, collections, sys

base = os.path.expanduser('~/.claude/projects')
d = os.path.abspath(os.getcwd()); files = []
while not files:
    files = glob.glob(f"{base}/{d.replace('/', '-')}/*.jsonl")
    if os.path.dirname(d) == d: break
    d = os.path.dirname(d)
if not files:
    sys.exit('Kein Protokoll fuer ' + os.getcwd())
f = max(files, key=os.path.getmtime)

seen = {}
for line in open(f):
    try: dd = json.loads(line)
    except: continue
    m = dd.get('message') or {}
    if dd.get('type') == 'assistant' and isinstance(m, dict) and m.get('usage'):
        seen[m.get('id') or dd.get('uuid')] = (dd.get('timestamp', ''), m.get('model'), m['usage'])
rows = sorted(seen.values())
if not rows: sys.exit('Keine Nachrichten mit usage.')

P = {'claude-fable-5-1':(10,50,.025),'claude-mythos-5-1':(10,50,.025),'claude-fable-5':(10,50,.1),
     'claude-mythos-5':(10,50,.1),'claude-opus-5':(5,25,.1),'claude-opus-4-8':(5,25,.1),
     'claude-opus-4-7':(5,25,.1),'claude-opus-4-6':(5,25,.1),'claude-opus-4-5':(5,25,.1),
     'claude-opus-4-1':(15,75,.1),'claude-opus-4':(15,75,.1),'claude-sonnet-5':(2,10,.1),
     'claude-sonnet-4-6':(3,15,.1),'claude-sonnet-4-5':(3,15,.1),'claude-sonnet-4':(3,15,.1),
     'claude-haiku-4-5':(1,5,.1),'claude-haiku-3-5':(0.8,4,.1)}
def preis(mo, u):
    tr = [k for k in P if (mo or '').startswith(k)]
    p = P[max(tr, key=len)] if tr else (5, 25, .1)
    if u.get('speed') == 'fast' and (mo or '').startswith(('claude-opus-5', 'claude-opus-4-8')):
        p = (10, 50, .1)
    fk = 1.1 if u.get('inference_geo') == 'us' else 1.0
    return p[0]*fk, p[1]*fk, p[2]
def teile(u):
    cc = u.get('cache_creation') or {}
    w1 = cc.get('ephemeral_1h_input_tokens', 0) or 0
    w5 = cc.get('ephemeral_5m_input_tokens', 0) or 0
    if not (w1 or w5): w1 = u.get('cache_creation_input_tokens', 0) or 0
    return w1, w5
def kost(mo, u):
    pin, pout, fr = preis(mo, u); w1, w5 = teile(u)
    return (((u.get('input_tokens',0) or 0)*pin + (u.get('output_tokens',0) or 0)*pout
             + w1*2*pin + w5*1.25*pin
             + (u.get('cache_read_input_tokens',0) or 0)*fr*pin)/1e6
            + ((u.get('server_tool_use') or {}).get('web_search_requests',0) or 0)*0.01)

t = lambda s: datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
W1 = sum(teile(u)[0] for _, _, u in rows); W5 = sum(teile(u)[1] for _, _, u in rows)
KOST = [kost(mo, u) for _, mo, u in rows]
schreib = sum((teile(u)[0]*2 + teile(u)[1]*1.25)*preis(mo, u)[0] for _, mo, u in rows)/1e6

print(f'Datei      : {os.path.basename(f)}  ({len(files)} Sitzung(en) im Projekt)')
print(f'Nachrichten: {len(rows)}   {t(rows[0][0]):%d.%m. %H:%M} bis {t(rows[-1][0]):%d.%m. %H:%M} UTC')
print(f'Kosten     : {sum(KOST):.2f} $ gesamt, davon {schreib:.2f} $ Cache-Writes '
      f'({100*schreib/sum(KOST):.0f} %)')
print(f'Cache-TTL  : 1h-Writes {W1:,} Tok | 5min-Writes {W5:,} Tok')
mods = collections.Counter()
for _, mo, u in rows: mods[mo] += kost(mo, u)
print('Modelle    :', {m: round(c, 2) for m, c in mods.most_common()})
print('speed      :', dict(collections.Counter(u.get('speed', '-') for _, _, u in rows)),
      '| inference_geo:', dict(collections.Counter(u.get('inference_geo', '-') for _, _, u in rows)),
      '| Websuchen:', sum((u.get('server_tool_use') or {}).get('web_search_requests', 0) or 0
                          for _, _, u in rows))
tage = collections.Counter()
for ts, mo, u in rows: tage[(t(ts)+datetime.timedelta(hours=2)).strftime('%d.%m.')] += kost(mo, u)
print('Tage (MEZ+):', {d: round(c, 2) for d, c in sorted(tage.items())})

print('\nPause vor einer Nachricht  ->  wie viel Prozent des Verlaufs neu geschrieben wurde')
print('(Modell sagt: Pause > TTL  =>  Neuaufbau nahe 100 %; sonst wenige Prozent)')
lang = []
for (ts0, _, _), (ts1, mo, u) in zip(rows, rows[1:]):
    p = (t(ts1)-t(ts0)).total_seconds()
    w1, w5 = teile(u); verlauf = w1+w5+(u.get('cache_read_input_tokens', 0) or 0)
    if verlauf: lang.append((p, 100*(w1+w5)/verlauf, verlauf, t(ts1)))
for p, q, v, tt in sorted(lang, reverse=True)[:12]:
    print(f'  {tt:%d.%m. %H:%M}  Pause {p/60:8.1f} min  ->  {q:5.1f} % von {v:,} Tok neu')
kurz = [q for p, q, _, _ in lang if p <= 300]; weit = [q for p, q, _, _ in lang if p > 300]
med = lambda x: sorted(x)[len(x)//2] if x else float('nan')
print(f'\n  Pausen <= 5 min : {len(kurz):3d} Stueck, Median-Neuaufbau {med(kurz):5.1f} %')
print(f'  Pausen  > 5 min : {len(weit):3d} Stueck, Median-Neuaufbau {med(weit):5.1f} %')
