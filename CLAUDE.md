# Wetter-App — Arbeitsregeln

## Versionierung (bei JEDER Aenderung)

Die App traegt ihre Version an genau einer Stelle in `index.html`:

```html
<span class="ver">v3.30</span>
```

Bei jeder Aenderung, die gepusht wird:

1. **Minor-Nummer um 1 erhoehen** (`v3.30` -> `v3.31`).
2. **`index.html` bleibt die aktive Datei** — sie wird bearbeitet, nicht umbenannt.
3. **Zusaetzlich eine Kopie mit Versionsnummer ablegen**, Schema
   `wetter-giessen-v<major>_<minor>.html`, also `wetter-giessen-v3_31.html`.
   Inhalt identisch zu `index.html` (`cp index.html wetter-giessen-v3_31.html`).
4. Beide Dateien im selben Commit.

### Zwei Fallstricke

- **Minor immer zweistellig schreiben** (`v3.30`, nicht `v3.3`). Die
  Update-Pruefung rechnet `major*1000 + minor`: `v3.3` ergibt 3003 und liegt
  damit *unter* `v3.29` (3029) — der Update-Hinweis bliebe aus.
- Nach `.99` auf die naechste Major wechseln (`v3.99` -> `v4.00`).

### version.json braucht keine Pflege

`checkUpdate()` fragt `version.json` (rund 20 Bytes) statt der ganzen
`index.html` (174 KB gzip) - die App prueft alle zehn Minuten, das waeren
sonst 16 MB am Tag. Die Datei schreibt der Workflow `version.yml` bei jedem
Push auf `main`, der `index.html` anfasst. Nicht von Hand aendern; wenn sie
fehlt oder veraltet ist, faellt die App auf den alten Weg zurueck und liest
die Versionsnummer aus der Seite selbst.

Der Workflow committet `version.json` auf `main`. Vor dem naechsten
`main`-Push also `git fetch origin main` - wie bei RADOLAN.

### Wozu die Kopie

`checkUpdate()` in `index.html` laedt die eigene URL neu und vergleicht die
Versionsnummer; steht online eine hoehere, erscheint der Balken „Neue Version
verfuegbar". Die Versionsdateien sind das Archiv daneben — eine alte Fassung
laesst sich direkt im Browser oeffnen, ohne Git.

## Veroeffentlichen (immer sofort)

GitHub Pages liefert den Branch `main` aus. Eine fertige Version wird
**sofort** veroeffentlicht, ohne Rueckfrage:

1. Auf dem Arbeitsbranch committen und pushen.
2. Nach `main` mergen (`git merge --no-ff`), `main` pushen.
3. Pruefen, dass die Live-URL die neue Versionsnummer liefert:
   `curl -s https://luperttrading-lab.github.io/wetter/ | grep -o 'class="ver">v[0-9.]*'`
   (Pages braucht 1-2 Minuten).

Die Versionierung oben gilt fuer Aenderungen an `index.html`. Reine
Pipeline- oder Doku-Aenderungen (Python-Skripte, Workflows, diese Datei)
brauchen keine neue Versionsnummer.

## Im Chat immer die Version nennen

Jede Antwort, die eine Aenderung abschliesst, endet mit der Versionsnummer,
die gerade live ist - sonst ist unklar, ob das Beschriebene schon beim Nutzer
angekommen ist. Sieht der Nutzer eine Aenderung nicht, ist die erste Frage:
welche Fassung hat er geladen? Der Update-Balken nennt die Version, die
ONLINE liegt, nicht die geladene.

## Datenpipelines

- RADOLAN, BfS-Achse, BfS-Stationen: Actions committen ihre JSON-Dateien
  auf `main` (kleine Dateien, seltene Laeufe).
- **Solar 10-Minuten** (`solar10.py`, alle 15 min, ~60 Stationen): schreibt
  nach Branch `daten` **ohne Historie** (jeder Lauf ersetzt den einzigen
  Commit per force-push). Die App liest
  `https://raw.githubusercontent.com/luperttrading-lab/wetter/daten/solar10/`.
  Nie `daten` nach `main` mergen und nie Daten dieser Pipeline auf `main`
  committen - sonst waechst das Repo um etwa 1 GB im Jahr.

## Pruefen vor dem Commit

`index.html` ist eine einzelne Datei mit zwei Inline-Scripts. Syntaxcheck:

```bash
python3 - <<'PY'
import io,re
s=io.open('index.html',encoding='utf-8').read()
b=re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>',s,re.S)
io.open('/tmp/app.js','w',encoding='utf-8').write("\n;\n".join(b))
PY
node --check /tmp/app.js
```

## Kostenzeile unter jeder Antwort

Jede Antwort im Chat endet mit einer Kostenzeile. Ablauf, ohne Ausnahme,
auch bei kurzen Antworten:

1. `python3 tools/kosten.py` ausfuehren.
2. Die Ausgabe **woertlich** als letzte Zeile der Antwort setzen.
3. Nichts dahinter, nicht umformatieren, nicht schaetzen.

Die Zeile sieht so aus:

```
<sub>08.09. 19:11 Uhr · Frage 0,25 · heute 18,85 · ges. 229,16 $</sub>
```

Laeuft das Skript nicht (kein Sitzungsprotokoll, anderes Werkzeug), das
offen sagen statt eine Zahl zu erfinden.

### Preisstand

Die Preistabelle wurde am **08.09.2026** gegen
<https://platform.claude.com/docs/en/about-claude/pricing> geprueft. Das Skript
haelt je Modell nur noch **Eingabe- und Ausgabepreis**; die Cachepreise leitet es
aus den dokumentierten Faktoren ab (5 min = 1,25x Eingabe, 1 h = 2x Eingabe,
Lesen = 0,1x Eingabe, bei Fable/Mythos 5.1 = 0,025x). Zwei Zahlen je Modell
statt fuenf, die veralten koennen.

Mitgerechnet werden ausserdem: **Fast Mode** (`speed: "fast"`, nur Opus 5 und
Opus 4.8, doppelter Preis 10/50 $ je Mio.), **US-Datenresidenz**
(`inference_geo: "us"`, Faktor 1,1 auf alles) und **Websuchen**
(0,01 $ je Suche). Alle drei stehen im Protokoll und wurden vorher stillschweigend
mit 0 bzw. dem Standardpreis bewertet.

Modell-IDs werden per **laengstem Praefix** aufgeloest, weil im Protokoll oft ein
Datum anhaengt (`claude-haiku-4-5-20251001`). Ohne das greift der Rueckfall auf
Opus-Preise und Haiku waere um Faktor 5 zu teuer.

### Was das Skript rechnet

Es liest das Sitzungsprotokoll `~/.claude/projects/<cwd mit - statt />/*.jsonl`
und bewertet jede Assistenz-Nachricht mit den API-Listenpreisen **ihres eigenen
Modells** (Modellwechsel mitten im Chat werden also korrekt getrennt).
`-v` gibt zusaetzlich Summen je Tag und je Modell aus. Die Cache-TTL wird nicht
geraten: das Protokoll nennt sie je Nachricht selbst
(`usage.cache_creation.ephemeral_1h_input_tokens` bzw. `..._5m_...`), danach wird
gerechnet. `--ttl5` greift nur noch bei alten Protokollen ohne diese Aufteilung.

Drei Stolpersteine, die im Skript bereits geloest sind:

- **Entdopplung nach `message.id`** — im Protokoll steht dieselbe Nachricht beim
  Streaming mehrfach; ohne das kommt etwa das Dreifache heraus.
- **„Letzte Frage" = ab dem letzten echten Nutzerbeitrag** — Werkzeugergebnisse
  stehen ebenfalls als `user` im Protokoll, zaehlen aber nicht als Frage.
- **Tagesgrenze in Ortszeit** — `TZ = 2` im Skript (Sommerzeit); im Winter auf `1`
  aendern, sonst ist zwischen 22 und 24 Uhr das „heute" falsch.

### Lange Sitzungen ueber mehrere Tage

Pausen aendern an der Abrechnung nichts: jede Nachricht traegt ihre eigenen,
gemessenen Token-Zahlen. Eine lange Pause laesst den Cache ablaufen, der naechste
Aufruf schreibt den ganzen Verlauf neu - das steht dann als grosser
`cache_creation_input_tokens`-Wert im Protokoll und wird zum Schreibpreis
bewertet. Genau richtig, ohne dass etwas geschaetzt werden muesste.

`-v` zeigt bei langen Sitzungen zusaetzlich die gelesene Datei, die Anzahl der
Nachrichten und die abgedeckte Zeitspanne - damit laesst sich pruefen, ob wirklich
die richtige Sitzung gezaehlt wurde.

Die Protokolldatei wird ueber den Pfad gesucht: erst das aktuelle Verzeichnis,
dann aufwaerts durch die Elternordner. Erst wenn das nichts findet, faellt das
Skript auf das zuletzt geaenderte Protokoll **irgendeines** Projekts zurueck und
warnt dabei auf stderr. Ohne diese Warnung liefert ein Aufruf aus dem falschen
Ordner eine plausible, aber fremde Zahl.

### Grenzen

- Die Zeile entsteht, **bevor** die Antwort geschrieben ist. Die Token der Antwort
  selbst fehlen und tauchen erst in der naechsten Zeile auf (bei „Frage" 10-50 Cent).
- Nur die eine Sitzung wird gezaehlt, andere Chats zum selben Projekt haben eigene
  Protokolle. Gezaehlt wird die zuletzt geaenderte; `-v` weist auf weitere hin.
- Winterzeit: `TZ = 2` im Skript auf `1` setzen. Faellt eine Zeitumstellung mitten in
  eine lange Sitzung, sind die Tagesgrenzen davor um eine Stunde verschoben.
- API-Listenpreise, keine Rechnung. Mit Abo zahlt man den Pauschalpreis.
- Der Cache-Schreibpreis ist die groesste Stellschraube: Nach jedem Modellwechsel und
  nach jeder Pause laenger als die Cache-Gueltigkeit kostet die naechste Frage 3-10 $,
  weil der ganze Verlauf neu in den Cache geschrieben wird. Sonst 10-30 Cent.
