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
`index.html` (251 KB gzip, Stand v4.69; frueher 174 KB) - die App prueft alle
zehn Minuten, das waeren sonst rund 35 MB am Tag. Die Datei schreibt der Workflow `version.yml` bei jedem
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

## Bright Sky: "sunshine" ist die VORANGEGANGENE Stunde

Der Wert mit Stempel 14:00 beschreibt 13 bis 14 Uhr (ebenso `precipitation`
und `solar`). `cloud_cover` und `icon` dagegen sind Momentanwerte ZUM
Stempel. Wer beides nebeneinander zeigt oder verrechnet, muss den Sonnenwert
eine Stunde zurueckschieben. Das hat zweimal zugeschlagen: v3.32 bei der
UV-Treppe (Treppe eine Stunde versetzt), v4.29 in der Stundenleiste ("60 min
Sonne" neben "bewoelkt"). `sonnenMoeglich(t)` rechnet deshalb ebenfalls die
Stunde VOR t.

## Datenquellen und Lizenzen

Welche Quelle was liefert, was sie heute kostet (nichts) und was bei einer
kommerziellen Nutzung zu klaeren waere, steht in `LIZENZEN.md`. Kurzfassung:
Esri-Satellitenkacheln und Open-Meteo waeren die Knackpunkte, DWD und
Bright Sky sind auch kommerziell frei.

## Knifflige Einstellungen: nicht raten, waehlen lassen

Wenn ein Wert nur am Geraet zu beurteilen ist - Geschwindigkeiten, Abstaende,
Farben, Schwellen -, nicht schaetzen und auch nicht die App mehrfach umbauen.
Zwei Wege, beide haben sich bewaehrt:

1. **Regler in die App**, sichtbar nur dort, wo es gebraucht wird, mit
   Zahlenanzeige und Speicherung im Geraet. Der Nutzer stellt ein, nennt den
   Wert, der wird Voreinstellung. So entstand die Kachelbewegung (v3.97:
   Ausschlag und Dauer, gewaehlt 1,0 Grad / 0,6 s).
2. **Eine eigene HTML-Seite mit mehreren Varianten nebeneinander**, im Repo
   und ueber GitHub Pages erreichbar, zum Vergleichen am Telefon. So entstand
   `wackeltest.html` mit neun Wackelvarianten.

Der Umweg spart am Ende Zeit: Beim Wackeln kosteten fuenf Runden Raten
(v3.89 bis v3.93) mehr als der Regler, der die Frage in einem Zug geklaert hat.
Bei Bewegungen zusaetzlich immer pruefen, ob die Bedienungshilfe "Bewegung
reduzieren" aktiv ist - sie hat monatelang wie ein Programmierfehler ausgesehen
(siehe v3.94).

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
<sub>08.09. 19:11 Uhr · Arbeit 4 min · Frage 0,25 · heute 18,85 · ges. 229,16 $</sub>
```

**Nicht in einen Codeblock setzen.** Die Zeile geht roh in die Antwort, sonst
zeigt die App einen Kasten mit sichtbaren `<sub>`-Tags statt der kleinen Zeile -
und genau das ist mit "nicht umformatieren" gemeint. Passiert leicht, weil drei
Backticks im Fliesstext sonst ueberall richtig sind.

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

**Opus 5.5** (seit 29.09.2026 in der Tabelle) hat eigene Preise: 4 / 20 $ je Mio.,
Cache lesen **0,05x** Eingabe. `claude-opus-5` ist auch Praefix von `claude-opus-5-5` -
ohne eigenen Eintrag lief 5.5 zum Opus-5-Preis, bei diesem Nutzungsmuster 50 % zu hoch.
Fast Mode ist deshalb ebenfalls je Modell hinterlegt (Opus 5.5: 8 / 40 $).

**Gegenprobe gegen Claude Code selbst:** Das Protokoll enthaelt gelegentlich Zeilen
`"type": "cost-state"` mit Claude Codes eigener Rechnung (`modelUsage.costUSD`). Mit
unserer Formel auf dieselben Token nachgerechnet: 13,1567765 $ gegen 13,1567765 $ -
identisch auf sieben Stellen. Als Quelle fuer die Zeile taugt `cost-state` nicht: es
wird nur sporadisch geschrieben und zaehlt je Prozess, nach jedem Container-Neustart
von null.

Modell-IDs werden per **laengstem Praefix** aufgeloest, weil im Protokoll oft ein
Datum anhaengt (`claude-haiku-4-5-20251001`). Ohne das greift der Rueckfall auf
Opus-Preise und Haiku waere um Faktor 5 zu teuer.

### Was die Zahlen bedeuten

- **Arbeit** — Spanne vom letzten echten Nutzerbeitrag bis jetzt, also die reine
  Bearbeitungszeit. Dieselbe Grenze wie bei „Frage": Werkzeugergebnisse stehen im
  Protokoll ebenfalls als `user`, zaehlen hier aber nicht als Beginn. Unter einer
  Minute steht `<1 min`, ab 90 Minuten `1 h 34 min`. Ist der Beitrag laenger als
  36 Stunden her (Sitzung nach langer Pause fortgesetzt), faellt das Feld weg,
  statt eine sinnlose Zahl zu zeigen.
- **Frage** — alle Antworten seit dem letzten echten Nutzerbeitrag, diese Sitzung.
- **heute** — Summe des lokalen Tages ueber **alle Projekte**, nicht nur diese
  Sitzung. Sonst waere die Zahl in einem eintaegigen Chat identisch mit „ges."
  und truege keine eigene Information. `-v` nennt die beteiligten Projekte.
- **ges.** — die gesamte laufende Sitzung.

Ein Claude-Code-Protokoll haengt am **Arbeitsverzeichnis**, nicht am Repository:
der Ordner `~/.claude/projects/-home-user-wetter/` ist der cwd `/home/user/wetter`
mit `-` statt `/`. Zwei Clones desselben Repos an verschiedenen Pfaden ergeben also
zwei getrennte Protokollordner. Deshalb kann „ges." nie ueber Repos hinweg zaehlen,
„heute" dagegen schon.

### In der Cloud zaehlt jeder Chat nur sich selbst

Das gilt so nur auf einem Rechner, auf dem alle Sitzungen dasselbe
`~/.claude/` teilen. Claude Code im Browser gibt **jedem Chat einen eigenen
Container**; dessen `~/.claude/projects/` ist beim Start leer und enthaelt
danach genau ein Protokoll - das des laufenden Chats.

Folge: Ein zweiter Chat zum selben Repo faengt bei „ges. 0" an und zeigt
unter „heute" ebenfalls nur seine eigenen Kosten. Er kann die Zahlen des
ersten Chats nicht sehen, auch nicht die des gleichen Tages. Die Summe ueber
mehrere Chats muss von Hand gebildet werden.

Zum Vergleichen: Diese Sitzung stand am 22.09.2026 bei 840 $ ueber 20 Tage,
2078 Nachrichten in einem einzigen Protokoll. Ein neuer Chat daneben zeigt
davon nichts.

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
- **Tagesgrenze in Ortszeit** — ueber `zoneinfo("Europe/Berlin")`, die
  Zeitumstellung ist damit abgedeckt. Bis v4.30 stand dort ein festes `TZ = 2`,
  das ab dem 25.10.2026 Uhrzeit und Tagesgrenze um eine Stunde verschoben haette.

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
- Die Skill `.claude/skills/kostenzeile/` traegt Skript und Ablauf, damit beides in
  einer neuen Sitzung nicht fehlt. `.claude/settings.json` gibt den Aufruf frei,
  sonst fragt Claude Code bei jeder Antwort nach.
- API-Listenpreise, keine Rechnung. Mit Abo zahlt man den Pauschalpreis.
- Der Cache-Schreibpreis ist die groesste Stellschraube: Nach jedem Modellwechsel und
  nach jeder Pause laenger als die Cache-Gueltigkeit kostet die naechste Frage 3-10 $,
  weil der ganze Verlauf neu in den Cache geschrieben wird. Sonst 10-30 Cent.


Der Syntaxcheck allein genuegt nicht. Jede sichtbare Aenderung wird im
Browser mit echten Daten angesehen, bevor sie gepusht wird - Playwright und
Chromium sind da, `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`. Ein kleiner
lokaler Server (`python3 -m http.server 8899`) und ein Skript, das die Seite
laedt, das Ergebnis ausliest und einen Screenshot macht. Fast jeder Fehler
dieser Sitzung - verzerrte Diagramme, abgeschnittene Zeilen, unsichtbare
Elemente - ist so aufgefallen und nicht beim Lesen des Codes.

## Aufklappbare Abschnitte

Seit v4.18 ist jede Abschnittsueberschrift ein Schalter: Titel, eine feine
Linie bis zum Rand, dort ein runder Knopf. `klappBauen()` baut die Zeilen im
Code um - wer einen Abschnitt hinzufuegt, traegt ihn nur in `KLAPP_ABS` ein.
Seit v4.86 (Nutzer) ist OFFEN die Voreinstellung (v4.20-v4.85: zugeklappt);
zu bleibt nur, was von Hand zugeklappt wurde (`klapp_<name>` = "0"). Ueber
dem ersten Abschnitt stehen "Alle auf" / "Alle zu" (`#kAlle`, `klappAlle`),
beide werden gemerkt. Folge: beim Start wird alles gerechnet und das Radar
sofort geladen (vorher erst beim Aufklappen).

### Aufklappen per Kachel (v4.62)

Tippen auf eine Kachel oben klappt ihren Zielabschnitt auf (`sec._setzen(true,
false)` - NICHT gemerkt) und springt hin; der Abschnitt traegt dann
`_autoAuf`. Scrollt man danach ganz nach oben (scrollY <= 30, nachdem man
einmal ueber 250 war), klappen alle `_autoAuf`-Abschnitte wieder zu. Von
Hand geoeffnete bleiben offen; wer einen per Kachel geoeffneten von Hand
antippt, uebernimmt ihn. Das Ziel sucht `kzZiel(z,true)` auch in
zugeklappten Abschnitten.

### Fuenf Kacheln zum Ausprobieren (v4.63)

Im Pool, nicht in `KZ_STD`: `iss` (naechster SICHTBARER Ueberflug aus
`_issPasses`), `vitd` (`vitdTag` heute: "ab"/"bis"/"vorbei"), `luft`
(`_aqi.european_aqi`, `aqiCat`, `luftTreiber`), `himmel` (hellster Planet,
der bis zum naechsten Sonnenaufgang >= 10 Grad hoch steht und fuer den es
dunkel genug ist - `plDuskOf` wie im Bild), `regen24` (`_rainHourly`).
Teures laeuft ueber `kzMerk(k,ms,fn)` (Planeten 5 min, Vitamin D 10 min),
weil `kzRender` bei jeder Datenlieferung laeuft. Neue `kzRender()`-Aufrufe
nach `_aqi`, `renderIss` und `_rainHourly`. Beschriftungen kurz halten: die
Kachel ist ein Drittel breit, "11:38–14:50" oder "Luftqualitaet" werden
abgeschnitten.

v4.64 (Nutzer): ISS-Kachel ab 72 h bis zum naechsten sichtbaren Ueberflug
"keiner · naechster in X Tagen". `issWhen` ab 7 Tagen mit Datum ("Do 15.10.")
- vorher stand nur "Do", und die Kachel zeigte so "Do 06:27" fuer einen
Ueberflug 16 Tage spaeter. `issCountdown` ab 48 h in Tagen ("in 356 Std"
war unlesbar), ab morgen mit dem Tag davor.

v4.65 (Nutzer: "nichts hinschreiben, was man nicht lesen kann"): Kachelzeilen
schneiden nicht mehr mit "..." ab. `kzPassen(box)` nach jedem `kzRender` und
per ResizeObserver: zu breite Zeile erst bis 88 % verkleinern (darunter
unleserlich), sonst umbrechen. Gemessen mit einer Range, nicht scrollWidth -
das ist gerundet, ein halbes Pixel Ueberhang reichte fuer "...". Kacheln
einer Reihe gleich hoch (`.kz .k{display:flex}`). PV-Kachel heisst "PV heute"
("PHOTOVOLTAIK" passt in Grossbuchstaben in kein Drittel).

v4.66 (Nutzer: "Regen heute zu lang, zu viel Text, wir verlieren Platz"):
Texte so gekuerzt, dass bei 375/390/430 pt NICHTS mehr umbricht (Test misst
`style.whiteSpace==='normal'` nach `kzPassen`). Regel: Unterzeile <= ~13
Zeichen, Beschriftung <= 10. "Regen heute" -> "Tagesregen", Wert nur das
Gefallene, Unterzeile "bis X erwartet"; Heute "bisher 13–23" (ganze Grad);
UV jetzt "☀ bis 19:08"; Sonne "noch 6:14 h"; UV heute "jetzt 1,7";
"7 Tage" / "2 Regentage"; Regen "nächste 2 h", "jetzt / bis ~14:35",
"in 25 min / 30 min leicht". Neues Feld `kurz` je Kachel = Beschriftung,
solange Daten fehlen (vorher der lange Name aus dem Pool).

v4.67 (Nutzer, New York: noch immer dreizeilige Kacheln - je nach Zustand):
Die Grenze ist eng. Bei 375 pt ist `#kz` 305 px breit, eine Drittelkachel hat
rund 77 px Text: Unterzeile ~12 Zeichen, Wert ~8. Deshalb ALLE Zustaende
gekuerzt, nicht nur die gerade sichtbaren: ISS Tag in die Beschriftung ("ISS
MORGEN", Wert nur die Uhrzeit, Unterzeile "53° · 6 min"); Luft Wort nur bei
<= 5 Zeichen neben der Zahl, sonst in die Unterzeile; Morgen bei Regen die
Menge, "Gewitter"/Schnee/Glaette gehen vor, lange WMO-Woerter gekuerzt
(Griesel, Schnee, Glaette, Glatteis, Schauer); Regen 2 h "in X min" +
Staerke; Tagesregen "noch 2,4 mm"; Regen 24 h "~0,4 mm"; Frost "gem.
-12–-5"; Wind Boeen dreistellig ohne Punkt; Taupunkt "gesaettigt" bei 100 %.
Innenabstand der Kachel rechts 9 -> 7 px. `kzPassen` misst mit 1 px Reserve
(bei +0,2 px blieb "Boeen 125 N..." stehen).
Pruefung: `p467.py` im Scratchpad rendert ~30 Worst-Case-Texte als Kacheln
bei 375 und 390 pt und meldet Umbruch/Verkleinerung.

v4.68: UV-Werte als farbige Pille (`kzUvPille`, Farben `bfsBadgeCol` wie das
UV-Abzeichen) statt des Worts "niedrig". Kachel "Planet": der ZUERST sichtbare
Planet (Nutzer), bei gleicher Zeit der hellere. ISS-Hauptkarte zeigt "~" vor
der Uhrzeit, wenn der Ueberflug mehr als 3 Tage entfernt und nur grob
gerechnet ist - wie in der Liste.

v4.73 (Nutzer: B+C): Kachel "Sonne" zeigt kein "UV jetzt" mehr (steht in
"UV heute"). Stattdessen WECHSELT sie ruhig: "bis 19:06 / noch 8:06 h" <->
"☀ 2:40 h / bisher" (nach Sonnenuntergang "ab 07:23 / in 11:23 h" <->
"☀ 5:01 h / heute"). Sonnenstunden `kzSonneHeute()`: Summe `sd` der
10-Minuten-Station seit Mitternacht (Wert i endet bei t0+i*dt), sonst Bright
Sky `sunshine` stuendlich; am 29.09. beides 301 min. Allgemein: eine Kachel
darf `v2`/`s2` liefern, `kzZeile` legt beide Texte in dieselbe Grid-Zelle
(Breite = der laengere), `#kz.kzw2` schaltet um. Erst ausblenden, dann
einblenden (je halbe Blendzeit) - Ueberblenden liess beide Texte halb
uebereinander stehen. Laeuft auch bei "Bewegung reduzieren" (eine Blende ist
keine Bewegung). Regler unter dem Zahnrad: Haupttext / Zusatz / Blende,
Voreinstellung 6 / 3 / 0,8 s (`KZ_WE_STD`, gespeichert `kzWechsel`) - noch
nicht vom Nutzer gewaehlt. `kzPassen` misst Wechselzeilen je Text einzeln
(die Spans sind so breit wie die Zelle, die Range meldete sonst Ueberbreite).
"☀ 10:16 h bisher" passt in KEINE Unterzeile (375 pt) - darum wechselt der
Wert mit.
v4.75 (Nutzer: "sehe keine Aenderung"): Der Wechsel lief nur ab 1 Minute
Sonne - morgens ohne Sonne stand die Kachel still und sah kaputt aus. Jetzt
auch "☀ 0 min / bisher", sobald die Sonne auf ist und Daten da sind.
v4.91 (Nutzer, 03.10. Nebel): ERSTE SONNE. Solange heute < 10 min Sonne
gemessen sind und noch welche erwartet wird, zeigt die Kachel zuerst
"☀ ~11:30 / erste Sonne" (dann "bis 19:00 / noch" und "☀ 0 min / bisher").
`kzSonneErwartet()`: aus `chartRows` (Bright Sky = MOSMIX, NICHT `fullRows` -
das endet bei jetzt), erste Stunde mit >= 30 min erwarteter Sonne, Beginn =
Stempel minus Sonnenminuten, auf 15 min gerundet; "☀ bald" ab 15 min vorher.
MOSMIX-Sonnenminuten sind Erwartungswerte. Modelle streuten am 03.10. um 09 Uhr
von 08:00 (ECMWF) ueber 10:00 (ICON-EU) bis 11:30/11:45 (MOSMIX/ICON-D2) -
Nebelaufloesung ist schwer. Gegenprobe mit der 10-Minuten-Station steht aus.
Bearbeiten-Fuss: Hinweis in eigener Zeile, das Minus darin als grauer Kreis
wie auf den Kacheln (`.kzminI`); Zahnrad ist jetzt ein Knopf "⚙ Tempo"
LINKS, "Fertig" rechts (vorher 15-px-Zeichen direkt neben "Fertig" - Nutzer
traf "Fertig" statt Zahnrad).

v4.76 (Nutzer): Wechsel mit BELIEBIG vielen Varianten. Eine Kachel liefert
`alt:[{l?,v?,s?},...]` (oder weiter `v2`/`s2`); `kzVarianten(x)` macht daraus
eine Liste, `kzZeile(k,arr)` legt alle Texte in eine Zelle, sichtbar ist
`_kzWeC mod n` (Klasse `.an`). Alle Kacheln schalten im selben Takt: gerade
Takte dauern "Haupttext", ungerade "Zusatz" - bei 3 Planeten stehen die also
abwechselnd 6 und 4 s. Planet: ALLE Planeten, die ab jetzt bis zur
Morgendaemmerung sichtbar werden, in der Reihenfolge ihres Erscheinens,
Beschriftung "Planet 2/3"; untergegangene fallen raus (Suche beginnt jetzt).
Regen (wenn die 2 h trocken sind): Zusatz "ab 09:00 / morgen 28 %" aus
`_rainHourly` (`kzRegenDanach`, Suche ab +1,5 h). Open-Meteo `precipitation`
ist die Summe der Stunde VOR dem Stempel - Beginn = Stempel - 1 h; die Kachel
"Regen 24 h" zeigte deshalb bis v4.75 eine Stunde zu spaet. "morgen · 28 %"
brach um, "morgen 28 %" passt (auf 10,5 px), bei "morgen" und 100 % faellt
die Zahl weg.
v4.77 (Nutzer): Der Regen-Zusatz erscheint nur, wenn "Regen 24 h" NICHT
gewaehlt ist - sonst stand dieselbe Uhrzeit zweimal da.
v4.78 (Nutzer): Wechsel auch fuer Heute ("max 16 Uhr", `kzWaermsteStunde`
aus chartRows; "max um 15 Uhr" brach um), UV heute ("Spitze 13:25" = Zeit
des erwarteten bzw. gemessenen Tageshoechstwerts, auch "UV morgen") und
7 Tage (nasse Tage zusammengefasst "Do–Sa, Di", alle 7 "jeden Tag", laenger
als 12 Zeichen -> kein Zusatz). Regler-Ueberschrift "Wechsel der Kacheln".
v4.79 (Nutzer): Zahnrad als SVG (`KZ_GEAR`, 20 px bei "Tempo", 17 px bei
"Kacheln waehlen") - das Zeichen U+2699 war am iPhone kaum als Zahnrad zu
erkennen. Minus im Hinweis `vertical-align:middle; top:-1px` - Mitte auf
0,3 px mit der Textmitte (vorher sass es tiefer).
v4.80 (Nutzer: Variante A, "ruhig"): Wechselnde Kacheln tragen PUNKTE
(`.kzdots`, einer je Ansicht, der dunkle = aktuelle) - senkrecht im rechten
Innenrand, weil sie oben rechts "UV MORGEN" ueberdeckten (Abstand zum Text
jetzt >= 1,3 px). "Planet 1/3" entfaellt. EIN Takt fuer alle Ansichten
(`kzWe().takt`, Voreinstellung 5 s; alte Speicherung an/aus -> takt = an),
dazu Blende und "Faerbung" (leichtes Blau hinter wechselnden Kacheln,
`--kzwf` = Prozent x 0,16, Voreinstellung aus). Regler (`kzRegler`): 32 px
Flaeche, 26-px-Knopf, touch-action:none, Tippen auf die Bahn setzt den Wert,
Ziehen per Pointer-Capture - vorher reagierten sie am iPhone schwer.
v4.81 (Nutzer): Bearbeiten-Modus schliesst nur noch bei einem TIPPEN
ausserhalb (<= 10 px Bewegung, pointercancel = Scrollen bricht ab) und nie
auf Hoehe von Kacheln/Reglern/Fuss - vorher schloss ihn schon das Aufsetzen
zum Scrollen rechts neben den Werten. Ueberschriften "Wackeln beim
Sortieren", "Wechsel der Kacheln", "Faerbung wechselnder Kacheln" (Regler
dort heisst "Staerke").
v4.82 (Nutzer): Voreinstellung des Wechsels Takt 4 s / Blende 1,5 s /
Faerbung aus; neuer Speicherschluessel `kzWechsel2` (die Testwerte im alten
`kzWechsel` gelten nicht mehr). "Regen 24 h": liegt der Beginn morgen, wechselt
die Unterzeile "morgen" / Menge. DATENFRISCHE (`kzAlter`, `KZ_QUELLE`,
`KZ_ALT`, `_kzStand`): jede Quelle merkt ihren letzten Abruf (mess = Zeit der
letzten DWD-Messung 100 min, radar 25, om = Open-Meteo stuendlich 200, fc =
Tagesvorhersage 200, aqi 200); ist sie aelter, wird die Kachel blass
(`.kzalt`, Deckkraft .6) und wechselt zusaetzlich auf "Stand HH:MM". Ohne
Ausfall unsichtbar. Sonne/PV/Planet/ISS/Mond sind nicht erfasst (Rechnung).
v4.83 (Nutzer): WISCHEN statt Timer als Standard (`kzWe().modus`
"wischen"|"auto", gespeichert in `kzWechsel2`). Wischen: Kachel steht still,
Wisch nach links = naechste, nach rechts = vorherige Ansicht NUR dieser
Kachel (`kzWeSchritt`, `_kzWeI[id]`, an Ort und Stelle umgeschaltet - die
Blende laeuft). Waagrecht >= 28 px und > 1,6 x senkrecht; gemeint ist die
Kachel, auf der der Finger AUFSETZTE (`_kzP0.id`), nicht die beim Loslassen.
`.kz:not(.edit) .k{touch-action:pan-y}`. Tippen (<= 14 px) oeffnet weiter den
Abschnitt. Im Auto-Modus gilt der alte Takt (Wisch geht auch dort bis zum
naechsten Takt). Einstellungen: Umschalter "Wischen | Automatisch"; der
Regler "Takt" erscheint nur bei Automatisch (Blende und Faerbung in beiden).
Der Knopf heisst "Einstellungen" (nicht mehr "Tempo" - dort steht mehr als
Tempo). Nicht am iPhone geprueft (Mausereignisse im Browser).
v4.84 (Nutzer): Der Auto-Modus heisst "Auto + Wischen" - Wischen geht dort
auch, und ein Wisch startet den Takt NEU (`kzWeSchritt` ruft
`kzWechselLauf()`), sonst schaltete es gleich wieder von allein weiter. Der
Takt setzt die Ansichten nicht mehr auf den gemeinsamen Zaehler zurueck,
sondern rueckt jede Kachel von IHRER Ansicht eins weiter (`_kzWeI` gilt in
beiden Modi, `kzIdx` liest nur noch das). Der Neustart gilt fuer alle
Kacheln (ein Timer), nicht nur die gewischte.
v4.85 (Nutzer): "Auto + Wischen" ist VOREINSTELLUNG (`KZ_WE_STD.modus`
"auto"). Gespeichert wird jetzt mit `mv:2`; ein Modus ohne diese Marke (aus
v4.83/84, da war "wischen" nur Voreinstellung) gilt nicht mehr - Takt, Blende
und Faerbung bleiben erhalten. Dabei behoben: in der Ladezeile stand
`if(!o)return null;` HINTER einem `//`-Kommentar (lief nur dank try/catch).

### Die Falle: ein verstecktes Canvas ist null Pixel breit

Wer einen Abschnitt zuklappt, findet ihn beim naechsten Start zugeklappt vor
- und dort wird gezeichnet, waehrend das Canvas `display:none` hat. Es bleibt
dann auf seiner Standardbreite von 300 Pixeln stehen, und nach dem Aufklappen
steht ein verzerrtes Bild da. Das faellt nicht beim ersten Start auf, sondern
erst beim zweiten.

Darum traegt sich jeder Abschnitt mit Canvas in `KLAPP_NACH` ein und zeichnet
beim Aufklappen neu. Beim Jahresbild kommt ein `ResizeObserver` auf dem Canvas
dazu: Er faengt jede Ursache ab - Einhaengen, Aufklappen, Drehen des Geraets.
Betroffen waren `uvchart`, `bfsOvl`, `vitdCv`, `planetenCv`, `planetenSunCv`,
`pvCv`, `mjCv` und die Stundenleiste, deren Scrollposition sich im
Verborgenen ebenfalls nicht setzen laesst.

## Benachrichtigung und Dateien

Nutzerwunsch (30.09.2026): IMMER eine Nachricht aufs iPhone, wenn etwas fertig
ist - der Nutzer hat die Claude-App dann oft geschlossen. Das gilt nicht nur
fuer veroeffentlichte Versionen, sondern fuer jede abgeschlossene Aufgabe
(auch Analysen, Pipeline-Aenderungen, Antworten auf laengere Auftraege) und
fuer jede Rueckfrage, ohne die es nicht weitergeht. Das Werkzeug
`PushNotification` meldet nur "requested" - die Zustellung laesst sich nicht
pruefen; deshalb steht die Kernaussage im Text der Nachricht selbst, nicht
nur "fertig".

Ist eine Aufgabe fertig und veroeffentlicht, geht eine kurze
Push-Benachrichtigung aufs iPhone. Dateien, an denen gearbeitet wurde -
Screenshots, Vergleichsseiten -, gehen vor dem Ende der Antwort an den Nutzer.

## Kompass im Planetenbild (v4.39-v4.41)

Knopf "Richtung zeigen" unter der Planetenlegende, danach ein roter Strich
dort, wohin das Handy zeigt. iOS: `webkitCompassHeading` (MAGNETISCH Nord)
und `webkitCompassAccuracy` (+-Grad, -1 = unkalibriert), Erlaubnis nur nach
Tippen. Android: `deviceorientationabsolute`, 360 - alpha, ohne Genauigkeit.
Dazu die Missweisung (`plMissweisung`, gefittet an 30 NOAA-Punkten in
Deutschland, Rest <= 0,04 Grad, +0,14 Grad/Jahr) - Wettenberg +3,8 Grad.
Glaettung als Vektor mit 0,25 s Zeitkonstante. Am iPhone geprueft
(27.09.2026): "funktioniert sehr gut"; das angezeigte +-10 Grad ist die
Selbsteinschaetzung von iOS, keine Messung. Eine Eichung am Mond (Handy
draufhalten, tippen -> Versatz merken, dann +-2-3 Grad) hat der Nutzer
vorerst abgelehnt - "sieht so schon ganz gut aus".

v4.40: dazu die HOEHE als waagrechter Strich und ein Ring im Kreuzungspunkt.
Gezielt wird mit der OBERKANTE (Zeigestock, Bildschirm zum Betrachter) - die
Achse, auf die sich auch webkitCompassHeading bezieht. Hoehe = beta
(W3C: Hochkomponente der y-Achse ist sin beta, gamma spielt keine Rolle).
Nicht die Rueckkamera: das waere asin(-cos beta cos gamma), und dann passte
die Kompassrichtung nicht mehr zur selben Achse.

v4.41: Knopf "Ton" (nur bei laufendem Kompass): Parksensor-Piepen zum
naechstgelegenen sichtbaren Koerper (Planeten nur, wenn dunkel genug; Mond
immer; Positionen fuer JETZT, nicht fuer die gewaehlte Uhrzeit). Abstand ist
der Grosskreiswinkel, Pause waechst linear von 60 ms an der Schwelle bis 1 s
ab 40 Grad. Dauerton-Schwelle: bis v4.43 ein Regler, seit v4.44 fest 3 Grad. v4.42: zwei Bestaetigungspiepser beim Einschalten
(trennt "Ton kommt nicht durch" von "kein Ziel"); am Tag ohne Planet und
Mond ist die Sonne das Ziel. iOS-Stummschalter: `navigator.audioSession.type =
"playback"`, wo Safari es kennt.

v4.43: vier Klaenge zur Wahl (`pl_ton_klang`: hell 880 Hz, weich 520 Hz,
tief 330 Hz Dreieck, steigend 300-700 Hz nach Naehe), Voreinstellung "weich"
bis der Nutzer waehlt. Jeder Piepser blendet weich ein/aus
(setTargetAtTime) - hartes setValueAtTime knackte und klang schaerfer.

v4.44: Schalter statt Knopftext (Beschriftung fest, Schiebeschalter zeigt den
Zustand - "Ton aus" war nicht zu deuten: Zustand oder Aktion?). Dauerton fest
ab 3 Grad, vom Nutzer draussen gewaehlt; der Regler ist weg. Ziel waehlen:
Koerper im Bild (28 px Fangradius, `cv._plPkte`) oder in der Legende
antippen -> festes Ziel (`PL_TON.fix`), gestrichelter Ring; "automatisch"
hebt es auf. Nur bei laufendem Kompass. Festes Ziel braucht keine
Dunkelheit, nur den Horizont.

v4.58: EICHTEST (Nutzer, 28.09.2026 - mit Finsternisbrille an der Sonne).
Schalter "Eichtest" (nur bei laufendem Kompass). "Messpunkt": 0,4 s warten
(Tippen ruckelt), 1 s die geglaetteten ROHwerte mitteln (`PL_KOMP.hdRoh`,
`hochRoh`), mit der berechneten Position des Ziels vergleichen (gewaehltes
Ziel, sonst Sonne, sonst Mond). Gespeichert wird der rohe Versatz plus die
gerade geltende Eichung (`pl_eich_log`, hoechstens 200 Punkte). Bloecke je
Eichung: Mittel und Streuung des Rests. "Eichung uebernehmen" = Mittel des
laufenden Blocks, wirkt auf Strich, Ring und Ton (`pl_eich`), bis "Eichung
aus"; der Kompassknopf zeigt dann "geeicht". "Kopieren" legt die Tabelle
als Text in die Zwischenablage. Zweck: trennen, was eine Eichung wegnimmt
(fester Versatz) und was bleibt (Zittern), und pruefen, ob der Versatz nach
15-30 min noch gilt. Ergebnis steht noch aus.

v4.59 (Nutzer): Nur die Kompassrichtung wird geeicht, die Hoehe nicht (wird
weiter gemessen und in der Tabelle gezeigt). ERLEDIGT in v4.68 (siehe unten),
vorher galt: `altaz()` rechnet GEOZENTRISCH und ohne Refraktion - der
Mond steht vom Standort aus bis ~0,95 Grad tiefer (Parallaxe ~ 0,95 Grad x
cos Hoehe), die Luft hebt bei 10 Grad um 0,1, bei 2 Grad um 0,3 Grad. Eine
Hoeheneichung am Mond wuerde die Parallaxe als Geraetefehler lernen.
Tageslicht-Trick zum Anpeilen der Sonne: Schatten des Handys auf der Hand
am kleinsten = Oberkante zeigt zur Sonne (etwa 1-2 Grad).

v4.68: `altaz()` liefert jetzt die SCHEINBARE Hoehe: Mond minus 0,951 Grad x
cos h (mittlere Horizontalparallaxe, schwankt 0,90-1,01), dazu fuer alle
Koerper die Refraktion nach Saemundsson ab -1 Grad. Geprueft gegen PyEphem
(Wettenberg, 29./30.09.2026): Mondhoehe 7,80/27,63/53,88 gegen 7,70/27,56/
53,75 Grad - Rest 0,07-0,13 Grad (vorher rund 0,9). Das Azimut des Monds liegt
0,4-0,65 Grad neben PyEphem - das ist die verkuerzte Mondtheorie, unter der
Kompassgenauigkeit. `altaz()` wird nur im Planetenteil (und der Kachel
"Planet") benutzt; Auf-/Untergangszeiten anderswo rechnen eigene Formeln.

## Regenradar (v4.45)

Eigener Abschnitt `radarSec` (Klapp-Schluessel `radar`), laedt erst beim
Aufklappen, danach hoechstens alle 5 min. Bright Sky `/radar`, format=plain
(der Browser holt es gzip - trocken rund 1 KB, sonst einige hundert KB),
50 km um den Ort (+6 km Rand), eine Stunde zurueck bis zwei voraus, 5-min-Takt.
Entscheidungen des Nutzers (27.09.2026): Quelle Bright Sky statt DWD-WMS-Bild,
50 km, Film mit Schieber.

**Projektion:** Das Radarraster ist polar-stereographisch, die Esri-Kacheln
Mercator. `rkStereo(lat,lon)` rechnet nach dem proj-String der Bright-Sky-Doku
(lat_ts 60, lon_0 10, WGS84, x_0/y_0 aus der Doku); Pixelmitte Spalte c bei
x=1000c, Zeile r bei y=-1000r, Zeile 0 = Norden. Geprueft gegen die vier
Gitterecken der Doku, die Ecken der Antwort und `latlon_position`: 0,0 m.
Je Bildschirmpixel (halbe Aufloesung) wird die Zelle einmal nachgeschlagen
(`RK.karte`), jedes Bild ist dann nur ein Nachschlagen. Farbe nach
`radarBoden()` (geeicht), Regen ja/nein nach der rohen Rate (>= 0,1 mm/h).

**Scheinechos (v4.46, `rkEntstoeren`):** Anlass Norden, 27.09.2026 - ein
Fleck mit "31 mm/h" stand stundenlang an der Emsmuendung (Windparks
Eemshaven/Delfzijl, rund 8 km vor dem DWD-Radar Emden) und wanderte in der
Vorhersage als Regen weiter. Filter: (1) Maske = in der gemessenen Stunde in
>= der Haelfte der Bilder nass (3x3-Nachbarschaft) UND allein (11x11-Fenster
im Mittel <= 25 nasse Zellen), eine Zelle breiter; (2) in der Vorhersage
wandert die Maske mit (Versatz je Bild <= 3 Zellen, der die meisten nassen
Zellen deckt); (3) Einzelpunkte <= 2 Zellen fallen in allen Bildern weg.
Norden: Vorhersage 150 -> 15 nasse Zellen (erster Test), im Browser danach 0.
Grenze: ein echter Schauer, der eine Stunde auf demselben km2 steht, faellt
mit weg. Seit v4.68 ist auch der Balken "Niederschlag 2 Std" (und damit die
Kachel "Regen") gefiltert: `loadNowcast` holt 7 km Umkreis (15x15 Zellen)
und die letzte Stunde dazu, `renderNowcast` laesst `rkEntstoeren` darueber
laufen und liest danach die Mittelzelle (`_nowStoer` = Zahl der Stellen).
Vorher: 1 km, nur ab jetzt, ungefiltert - an der Kueste "Regen jetzt" durch
ein Windpark-Echo, das die Karte schon ausblendete.

v4.88 (Nutzer-Vergleich mit WetterOnline, 01.10.2026 07:04): ZWEI Fehler.
(1) Der Filter loeschte echten Regen. Im 15x15-Fenster des Balkens galt
Niesel der letzten Stunde als "fest und allein" (das Fenster ist zu klein, um
Nachbarschaft zu sehen), und in der Vorhersage suchte sich die mitwandernde
Maske (+-3 Zellen je Bild, kumulativ) genau den ankommenden Regen: Balken
07:45-09:00 trocken, roh durchgehend 0,12-0,72 mm/h. Auch auf der Karte
(70 km) verschwanden rund 1 % der nassen Vorhersagezellen, im 7-km-Fenster
28 %. Jetzt loescht `nulle` je Bild nur, wenn ein Ring von 3 Zellen um die
(verschobene) Maske hoechstens 25 % nass ist (ab 8 Ringzellen). Ein
Windpark ueber trockenem Meer faellt weiter weg; steckt er in echtem Regen,
bleibt er stehen. Den Fall Norden (27.09.) konnte ich nicht nachspielen -
Bright Sky liefert nur die letzten Stunden; am 01.10. regnete es dort
flaechig, alter und neuer Filter liessen fast alles stehen.
(2) Ueberschrift "Regen in 5 Min · ~5 Min lang" beschrieb einen einzelnen
Balken und verschwieg 85 min Regen danach. `nowEreignisse()`: nasse Schritte
zu Ereignissen, Luecken bis 15 min ueberbrueckt; regnet es jetzt, zaehlt das
Jetzt-Ereignis (mit "in X Min maessig", wenn danach ein groesseres kommt),
sonst das GROESSTE (Summe der Bodenrate). Ueberschrift, Staerke und Kachel
"Regen" nutzen dieselben Ereignisse; "haelt ueber 2 Std an", wenn es bis
zum Ende reicht. Balken "jetzt" ist blass (`.bar.blass`), wenn er ueber 0,1,
aber unter der Jetzt-Schwelle (0,25 bei trockener Station) liegt - vorher
blau, ohne mitzuzaehlen.

**Grenzen (v4.89, Nutzer: "zur Orientierung, haben die anderen Karten auch"):**
Staats- und Landesgrenzen in Radar- UND Wolkenkarte (`grenzenZeichnen`, vor
den Orten, ueber dem Regen; v4.90 (Nutzer): SCHWARZ 1,4 px, Staat 1,9 px,
auf hellem Saum 40 % - v4.89 war weiss auf dunklem Saum). Daten `grenzen.json` (136 KB, gzip 54 KB), gebaut von `tools/grenzen.py`
aus BKG VG250, Ebene LI, AGZ 1+2, Douglas-Peucker 100 m, Koordinaten in
1e-4 Grad als Differenzen. Geladen beim ersten Zeichnen, danach zeichnen
beide Karten neu; nur Linien, deren Rahmen das Fenster schneidet (3,8 ms je
Radarbild im Test). NICHT VG2500: lag um Wettenberg bis 1,8 km neben VG250
(90 % unter 581 m), auf der 130-km-Karte bis 5 px. Quellvermerk "Grenzen ©
GeoBasis-DE / BKG (2026)" steht unter beiden Karten (Pflicht nach
dl-de/by-2-0, siehe LIZENZEN.md). Nebenbei: Ortsnamen bekamen
`lineJoin="round"` - die schwarze Kontur zog an M, N, W, A Gehrungsspitzen
("Marburg", "Nidda", "Weilburg"). Ausland zeigt nur die deutsche
Staatsgrenze; Grenzen zwischen Nachbarlaendern fehlen.

**Zugpfeil (v4.47, `rkZug`/`rkZugZeichnen`):** Das Radarbild von vor 30 min
wird bis 30 Zellen verschoben, bis es die nassen Zellen von jetzt am besten
deckt (>= 30 Zellen, Deckung >= 30 %); sonst jetzt -> +30 min aus der
Vorhersage; ohne Regen der Wind in 700 hPa (Open-Meteo, `rkWindZug`). Laeuft
NACH dem Scheinecho-Filter - ein stehender Windpark taeuschte sonst 0 km/h
vor. Gitternord weicht um (Laenge - 10) Grad ab, die Nordrichtung am Ort
kommt aus `rkStereo`. Pfeil durch den Standort, Striche stromauf: "was dort
ist, erreicht dich nach dieser Zeit". Stunden, solange zwei Striche ins
Bild passen, sonst 30 bzw. 15 min; hoechstens vier Striche. Geprueft nur an
einem echten Schauer (Giessen 27.09. 17 Uhr: Radar 55 km/h nach 82 Grad,
700 hPa 47 km/h nach 61 Grad) und kuenstlichen Bewegungen.

v4.48: Messung aus ALLEN 10-Minuten-Paaren der gemessenen Stunde (Versatz
bis 12 Zellen, Deckung >= 30 %), Median der Komponenten; Rueckfall die
Vorhersage jetzt -> +30 min, dann 700 hPa. Anlass: kurzlebige Schauer bei
Giessen (225 -> 31 Zellen in 30 min) - der 30-min-Vergleich fand nur 10 %
Deckung, die App schrieb "kein Regen im Bild", obwohl der Film Regen zeigte.
10-min-Paare: 40-46 km/h nach 63-67 Grad, App 43 km/h nach 64 Grad,
700 hPa 46 km/h nach 65 Grad. Andere Radar-App zum selben Zeitpunkt:
Richtung rund 70 Grad. Der Hinweis unterscheidet jetzt "kein Regen im Bild"
von "zu wenig Regen fuer eine Messung".

v4.49 (Wunsch des Nutzers): Ausschnitt = Wolkenkarte (`WOLK`, rund
130 x 110 km, `rkFenster`), Abfrage-Radius `rkAbfrageKm()` deckt das Fenster
plus 8 km; rund 1,6-mal mehr Daten als bei 50 km. Die Ortsbeschriftung ist
jetzt `wolkOrteZeichnen()` und wird von beiden Karten benutzt - gleiche Orte
an gleicher Stelle. Am Pfeil nur noch die Zeitstriche (nur solche, die im
Bild liegen); Richtung und Tempo stehen in der Zeile unter der Karte. Kein
25-km-Ring mehr. Zeitkaestchen oben rechts (links oben steht Kreuztal).

v4.50 (Wunsch des Nutzers): EINE Karte "Wolken & Regen" mit Umschalter
Wolken | Regen | Beides (`karteModus()`, gemerkt als `karte_modus`,
Voreinstellung Regen). Der Block `wolkenSec` liegt jetzt IM Abschnitt
`radarSec` und ist kein eigener Klapp-Abschnitt mehr (aus `KLAPP_ABS`
entfernt); sein Titel ist ausgeblendet, `renderWolken` schreibt aber weiter
die Standzeit hinein (die Radarzeile liest sie dort). Sichtbarkeit per CSS
ueber `#radarSec[data-modus]`. "Beides": `wolkEbene()` (die weisse Ebene
der Wolkenkarte, genau das WOLK-Fenster) wird im Radar unter die
Regenfarben gelegt; die Wolkenregler bleiben sichtbar und zeichnen ueber
`drawWolken()` auch das Radar neu. In "Wolken" wird kein Radar geladen. v4.51: Radarkarte mit
demselben Innenabstand (Standard-`.nowcard`) und Radius wie die Wolkenkarte
und ohne Abdunkeln des Satellitenbilds - vorher war sie breiter (andere Orte
fielen weg) und dunkler. Beide jetzt 350 x 326 px im Test.

v4.52 (Nutzer: Variante B): In "Beides" bewegen sich die Wolken im Film mit.
Die Wolkenabfrage (`wolkenURL`) holt zusaetzlich `hourly` mit
`past_hours=2&forecast_hours=3` - in DERSELBEN Abfrage, kein weiterer Abruf;
Cache-Schluessel deshalb `wolkCache5`. `renderWolken` baut `_wolkStunden`
(Zeiten ueber `utc_offset_seconds` in echte Zeitpunkte). `wolkEbene(zeit)`
blendet zwischen den beiden umgebenden Stunden und verschiebt jede mit dem
Zugpfeil bis zum Bildzeitpunkt; am Rand wird der Randwert fortgesetzt. Die
reine Wolkenansicht nutzt weiter die aktuellen Werte (`wolkEbene()` ohne
Zeit). Getestet nur mit nachgebauter Open-Meteo-Antwort, weil der
Prueframer an dem Tag ins Tageslimit von Open-Meteo lief (HTTP 429) - am
Geraet mit echten Daten noch ansehen.

v4.61 (Nutzer, 29.09.2026): "Beides" wieder entfernt - "bringt nicht so viel".
Nur noch Wolken | Regen; gespeichertes "beides" wird zu "regen". Der Code
(`wolkEbene(zeit)`, `_wolkStunden`, hourly in `wolkenURL`) ruht und laesst
sich zuruecknehmen, indem der Knopf wieder ins HTML kommt und `karteModus()`
"beides" wieder zulaesst. v4.69: der ruhende Code ist ENTFERNT (Stundenwerte in
`wolkenURL`, `_wolkStunden`, Zeit-Zweig in `wolkEbene`, Beides-Zweige in
Radar, Hinweis und CSS); Cache-Schluessel jetzt `wolkCache6`. Zurueckholen
aus `wetter-giessen-v4_68.html`.

v4.53: Orte unter dem Zugpfeil fallen weg (Nutzer: "Herborn kann man unter
dem Pfeil nicht lesen"). `rkZugZeichnen(...,true)` zeichnet nichts und
liefert die belegten Flaechen (Linie +-8 px, Striche, Zeitbeschriftungen);
`wolkOrteZeichnen(x,P,W,H,sperr)` laesst jeden Ort weg, dessen Punkt
hoechstens 8 px daneben liegt, und legt keine Beschriftung darauf.

v4.54: Zeitkasten oben rechts immer gleich breit (Nutzer). Ein unsichtbarer
Platzhalter "00:00 in 188 min · Vorhersage" liegt per CSS-Grid in derselben
Zelle wie der echte Text; `el('rkZeit').textContent` enthaelt deshalb beide.
v4.55: Text linksbuendig - die Uhrzeit steht immer an derselben Stelle (Nutzer).

v4.57 (Nutzer, Norden 28.09.2026): Pfeil zeigte 6 km/h nach O, der Wind in
3 km Hoehe blies mit 72 km/h nach NO (Wind-App des Nutzers: 70 km/h). Die
Radarechos lagen schwach ueber der Nordsee (Windparks/Meeresechos), wuchsen
und schrumpften an Ort und Stelle; auch ohne die fest stehenden Zellen kamen
nur rund 25 km/h heraus. Zwei Aenderungen: (1) Gegenprobe `rkZugPruefen()`:
der 700-hPa-Wind wird jetzt IMMER geholt (je Ort 30 min zwischengespeichert);
ab 20 km/h Hoehenwind gilt der Wind, wenn das Radartempo unter einem Drittel
liegt oder die Richtung um mehr als 90 Grad abweicht (`RK.zug.verworfen`,
der Hinweis nennt das verworfene Radartempo). (2) Suchbereich 20 statt 12
Zellen je 10 min (bis 120 km/h); ueber 800 nassen Zellen eine gleichmaessige
Stichprobe, damit grosse Regenflaechen nicht bremsen (Norden: 36 ms).

v4.60 (Nutzer, Norden 29.09.2026, Vergleich mit anderer Radar-App ~50 km/h
nach NNO): App zeigte 22 km/h NO aus dem Radar. Ursache: breites Regenband
mit 3400 nassen Zellen - verschoben oder nicht deckte es sich fast gleich gut
(82 % gegen 80 %), der Median fiel auf 13-22 km/h. Neu: ueber 600 nassen
Zellen werden nur die KERNE verfolgt (Schwelle = 600. staerkster Wert in
Bild A, dieselbe fuer B). Alle 11 Paare dann (-7,5) Zellen je 10 min =
52 km/h nach 33 Grad; 700 hPa 44 km/h nach 28 Grad. Unter 600 nassen Zellen
unveraendert 0,1 mm/h. Stichprobe jetzt bis 1500 Kernzellen; 88 ms.

## Sonnenkarte im UV-Abschnitt (v4.56)

Die Karte "Sonne" (Bogen, Auf-/Untergang, Sonnenstunden) stand als letzte
Karte in "Details". Seit v4.56 steht sie ganz oben im Abschnitt, der jetzt
"Sonne, UV & Vitamin D" heisst (Klapp-Schluessel weiter `uvvitd`), VOR dem
Schalter Gestern|Heute - sie zeigt nur heute. Eigenes Gitter `gridSonne`,
gefuellt beim Bau des Hauptgitters; `gridUv` entsteht getrennt mit den
UV-Daten. Das Hauptgitter nimmt `uvSec` das `hidden` ab, damit die Sonne
auch ohne UV-Daten erscheint.

## Das UV-Modell: wo die Zahlen herkommen

Die Herleitungen stehen ausfuehrlich als Kommentare in `index.html`. Hier nur,
was ein neuer Chat wissen muss, bevor er etwas daran aendert.

Zwei Kurven, zwei ganz verschiedene Wege:

- **Schwarze Glocke ("max. moeglich")** = CAMS-Klarhimmel von Open-Meteo,
  korrigiert mit `uvCamsFaktor()`: Geo-Korrektur nach Breite und Hoehe
  (`0,9506 + 0,0128*(Breite-50) + 0,0538*Hoehe[km]`, seit v4.31 gefittet gegen
  MESSUNG/CAMS an 28 BfS-Stationen) mal dem **Stationsfaktor** aus
  `uv-station.json`. Fuer Wettenberg: 0,969 x 1,078 = 1,045.
  **Dieselbe Formel steht in `uv_klarcheck.py` (`cams_faktor`)** - beide
  muessen gleich bleiben, sonst misst der Stationsfaktor die Differenz der
  Formeln statt der Geraete.
- **Bunte Saeulen** = Glocke x Durchlass^`UV_K_EXP`. Der Durchlass ist
  gemessen: DWD-Globalstrahlung im 10-Minuten-Takt (`solar10`) geteilt durch
  die Klarhimmel-Globalstrahlung. **Nichts davon kommt vom BfS** - dass die
  Saeulen und das amtliche Bild darunter dieselben Zacken zeigen, sind zwei
  unabhaengige Messgeraete an derselben Station unter denselben Wolken.

### v4.70: Prognosesaeulen im UV-Bild

Rechts von der Messung (ab Ende der 10-Minuten-Werte, sonst ab jetzt) blasse
Saeulen (`UV_PROG_ALPHA` 0,3, gestrichelte Oberkante, keine Punkte) fuer den
Rest des Tages. Durchlass = Bright Sky `solar` (MOSMIX, Stunde VOR dem
Stempel) / Mittel von `gClear` ueber dieselbe Stunde, zwischen den
Stundenmitten linear, dann `uvKurveD` wie bei der Messung (`uvProgStd()`, aus
`chartRows`). Ergebnis in `window._uvProg` ({max, t, ab}). Ausserhalb
Deutschlands kein `solar` -> keine Prognose. Anlass: Open-Meteos `uv_index`
(CAMS, "mit Wolken") lag am 30.09. bei 3,35 gegen 3,4 klar - die Wolken
wirken darin kaum, die Kachel "UV heute" zeigte so faktisch den Klarwert.
v4.71: Kachel "UV heute" (`kzUvHeute`), vom Nutzer gewaehlt (30.09.2026):
vor Aufgang und vormittags bei UV < 0,5 "3,1 erw." / "klar 3,5"; tagsueber
"1,6 jetzt" / "erw. 3,1" (v4.72, vorher "max ~3,1"), sobald die Prognose fuer den
Rest unter dem Gemessenen liegt "max 3,2" ohne Tilde; nachmittags UV < 0,5
"3,3 gem." / "Tagesmax"; nach Sonnenuntergang "UV MORGEN" "3,1 erw." /
"klar 3,6" (`kzUvMorgen`: Stundenklarwert x `uvKurveD(uvProgK(t))`, dafuer
Luftabfrage `forecast_days=2`). Erwartet = max(gemessen, Prognose Rest).
Die Tageswerte rechnet seit v4.74 `uvTagRechnen()` SELBST (Glocke
`makeSunBell`, Messung `solar10Werte`, Prognose `uvProgK`, 5-min-Schritt;
gegen drawUV auf 0,01 gleich). Bis v4.73 las die Kachel `window._uvHeute`
aus `drawUV` - lief sie vor dem ersten Zeichnen, stand "3,6 max / maessig"
(Klarwert) statt "3,2 erw." da (Nutzer, 30.09. 07:55). `drawUV` schreibt
`_uvHeute` weiter und ruft `kzRender`, wenn sich eine Zahl aendert. Ohne
Prognose steht jetzt "3,6 klar" statt "3,6 max". `kzUvJetzt()` nimmt jetzt die letzte
10-Minuten-Messung (wie das Abzeichen), Open-Meteo nur noch als Rueckfall -
das gilt auch fuer die Kachel "Sonne / UV". "klar" = `uv_index_clear_sky`.
Geprueft mit verstellter Uhr am 29.09.: 06:30 3,1 erw.; 10:30 1,5 jetzt /
max ~3,1; 13:15 2,5 jetzt / max 3,2; 15:30 1,4 / max 3,3; 18:15 3,3 gem.;
20:00 UV morgen 3,1 / klar 3,6. Ohne Prognose (Ausland) wie bisher der
Klarwert.
v4.87 (Nutzer): Nach Sonnenuntergang bis MITTERNACHT zuerst noch "UV heute"
"3,3 gem." / "Spitze 13:15" (gemessenes Tagesmaximum), im Wechsel "UV morgen"
"1,9 erw." / "klar 3,5". Ab Mitternacht gilt der Morgenzweig des neuen Tages
("erw." / "klar", Zusatz "Spitze"). Ohne Messung (Ausland) wie bisher nur
"UV morgen". Geprueft 30.09. 20:45 mit echten Daten und Uhr 01.10. 00:30.

### Prognose gegen Messung (uv_prognose.py, ab 30.09.2026)

Stimmt "erw." in der Kachel "UV heute"? Am 30.09. sagte die App morgens 3,1,
gemessen wurden 3,3 - ein Tag, kein Beleg. `uv_prognose.py` (Workflow
`uv-prognose.yml`, 07:20 und 22:05 Ortszeit) oeffnet die LIVE-APP in headless
Chromium und liest `uvTagRechnen()` / `kzUvMorgen()` aus - genau der
Rechenweg, den der Nutzer sieht, kein zweites Modell in Python. Morgens:
erwartetes Tagesmaximum (`erw_tag`), Klarwert; abends: gemessenes Maximum und
die Erwartung fuer MORGEN (wird beim naechsten Tag als `vortag` verbucht - so
zeigt sie die Kachel ab Sonnenuntergang). Log `uv_prognose_log.json`, darin
`_auswertung` (Bias, Streuung, mittlerer Fehler, Bias in %; `--auswerten`
lokal). Unter etwa 10 Tagen unbelastbar. Grenzen: (1) Ein Handstart des
Workflows nach Sonnenaufgang erfasst nur den Rest des Tages (`erw_tag` nimmt
das schon Gemessene hinzu). (2) Antwortet Open-Meteo dem geteilten Runner mit
429, bricht der Lauf nach zwei Versuchen ab - dann fehlt der Tag, es wird
nichts Falsches eingetragen. Lokal getestet mit eingespielter Luftabfrage
(die eigene Abfrage der App scheitert im Pruefstand).

### Erledigt (v4.33): Vitamin D - zweite Flaeche fuer Sonne >= 45 Grad

Das Jahresbild zeigt jetzt zwei Flaechen: hellgruen UV >= 3 bei klarem Himmel,
dunkelgruen Sonne >= 45 Grad (Schattenregel). Beide Regeln sind Naeherungen und
irren in entgegengesetzte Richtungen: UV >= 3 ist bei flacher Sonne zu
grosszuegig (das Verhaeltnis Vitamin-D- zu Sonnenbrand-Wirkung ist nur ueber
UV-Index ~5,5 annaehernd konstant), 45 Grad ist zu streng (Webb/Kline/Holick
1988: in Edmonton, 52 Grad Nord, endet die Bildung erst im Oktober - Ende
September, bei rund 37 Grad Hoechststand, bildete sich noch Previtamin D).
Wettenberg: UV >= 3 an rund 205 Tagen, Sonne >= 45 Grad an 157 (4. April bis
7. September).

Das 45-Grad-Fenster wird GESCHLOSSEN berechnet (cos H0 = (sin 45 - sin phi sin
delta)/(cos phi cos delta)), nicht gesucht - 1,3 ms statt 125 ms fuers Jahr,
Abweichung zur Suche hoechstens 18 s.

**Die Falle dabei: `ortsMs()` und `std()`/`ortsStundeDez()` gehen durch die
Intl-Zeitzonenrechnung und kosten je Aufruf rund 0,2 ms.** In Schleifen ueber
366 Tage dominieren sie alles andere. Erledigt in v4.69: `vitdTag(d,K,off)`
nimmt den Tagesversatz aus `vitdJahr` mit und rechnet ohne `ortsMs`,
Beginn/Ende ueber `stdOff` statt `ortsStundeDez`. 267 -> rund 90 ms
(Chromium, Mittel aus 3), Ergebnis in Berlin und New York hoechstens 1 s
anders. Der Rest: `tzVersatzMin` je Tag (rund 30 ms) und die UV-Suche.

### Erledigt (v4.31): Breitenkorrektur neu, mit Waechter

Die alte Geo-Formel (`0,939 - 0,0199*(Breite-50) + ...`) war gegen die
DWD-*Prognose* gefittet, und die faellt nach Norden zu steil ab. Die
Stationsfaktoren haben den Fehler geschluckt: Stuttgart 0,930, Giessen 1,120,
Norderney 1,175, Cuxhaven 1,227 - einzeln plausibel, zusammen ein Trend von
+0,033 je Grad bei t = 3,6. An Orten ohne Station in der Naehe stand der Fehler
offen da: Kueste rund 15 % zu wenig UV, Alpen 7 % zu viel.

Neu gefittet gegen Messung/CAMS: a = 0,9506, b = +0,0128 +- 0,0081 je Grad,
c = +0,0538 +- 0,029 je km. **Sicher ist nur, dass -0,0199 falsch war** (vier
Standardfehler); die neue Breitensteigung ist nicht sicher von null
verschieden. `uv_klarlog.json` wurde dabei umgerechnet (verh x alt/neu,
schwarz x neu/alt), damit alte und neue Eintraege dieselbe Formel meinen.

**Der Waechter** in `uv_station.py` regressiert bei jedem Lauf die
Stationsmediane gegen Breite und Hoehe und setzt in `uv-station.json`
`"waechter": {"alarm": true}`, sobald |t| >= 3. Gegen das Protokoll von vorher
schlaegt er an (t = +3,6), gegen das umgerechnete nicht (t = -0,9 / -0,4). Steht
dort ein Alarm, gehoert die Geo-Formel neu gefittet - nicht die Faktoren
vergroessert.

### Erledigt (v4.38): die Saeulen lernen aus der Messung

Saeule = Glocke x f(Durchlass). f ist keine Formel mehr (`min(1,k)^p` mit
Deckel), sondern die **gelernte Kurve** aus `uv-durchlass.json`, Feld
`kurve.kurve` = Liste `[Durchlass, f, n]`. `uv_durchlass.py` bildet sie bei
jedem Klarcheck-Lauf (taeglich) neu: Median je 5-%-Band ab 30 Paaren, danach
monoton gemacht, gedeckelt bei 1,0. Die App (`uvKurveD`) interpoliert linear;
fehlt die Kurve oder ist sie unplausibel, gilt wieder die Potenz.

**Bezug wie in der App:** Jedes q wird vorher durch Geo-Korrektur x
Stationsfaktor x Tagesgang geteilt (`_korrigiert`). Stationen ohne Faktor
zaehlen mit 1, wie in der App. Damit ist der alte offene Punkt "rechnet gegen
das rohe CAMS" fuer die Kurve erledigt; `p_gesamt` rechnet weiter roh, wird
aber nur noch als Rueckfall gebraucht.

Stand 17 Tage, 15 326 Paare: bei voller Sonne f = 0,96, nicht 1,0 - darum
klebten die Saeulen an Sonnentagen an der Glocke. Guete, jeder Tag aus den
anderen vorhergesagt (steht im Klarcheck-Log, die 10-Uhr-Routine sieht sie):
Tagesbias Median alt -2,6 %, neu -0,6 %; typischer Fehler je 10 min 14,9 ->
14,3 %. Der Gewinn ist klein und sitzt bei Sonne; die Streuung von Tag zu Tag
(-10 bis +7 %) bleibt - die kommt von Ozon und Dunst, die die
Globalstrahlung nicht sieht.

Der Testregler "Saeulen stauchen" (v4.32) ist entfernt, ein gespeicherter
Wert `saeuleF` wird beim Start geloescht.

### Frueher offen: uv_durchlass.py rechnet gegen das ROHE CAMS

`q = Messung / Glocke` mit `glocke = cs_max * (mu/mu_max)^2,42` - ohne
Geo-Korrektur und ohne Stationsfaktor. Der Kommentar dort sagt "der kuerzt
sich", das stimmt aber nur fuer das Verhaeltnis innerhalb einer Station, nicht
fuer die Regression durch den Ursprung ueber alle Stationen. Die Aussagen aus
v4.28 ("gemessen nie ueber 1,0", "Luecke 8 % zu hoch") beziehen sich auf diese
rohe Glocke. Die Richtung bleibt, die genauen Prozente koennen sich um einige
Punkte verschieben.

### Erledigt (v4.26): der Exponent kommt jetzt aus der Datei

`UV_K_EXP` startet auf 0,669, aber `uvDurchlassLaden()` holt alle sechs
Stunden `uv-durchlass.json` und nimmt das Feld **`p_gesamt`** - EIN Exponent
ueber alle Sonnenschein-Klassen (Stand 14 Tage: 0,685 aus 10 741 Paaren,
r2 0,75). Die Klassentrennung bringt nichts, "volle Sonne" bleibt mit r2 0,21
unbrauchbar. Faellt die Datei aus oder liegt der Wert ausserhalb 0,35-0,95,
bleibt 0,669 stehen.

Wichtiger als der Wert ist, was dabei herauskam: Sagt man jeden Tag einzeln
mit dem Exponenten der anderen 13 vorher, schwankt der Bias zwischen -17 %
und +8 %. Der Wechsel von 0,669 auf 0,685 verschiebt ihn um 0,8
Prozentpunkte. **Am Exponenten ist nichts mehr zu holen.** Wer die UV-Saeulen
besser machen will, muss am Tag ansetzen, nicht an p.

`uv_durchlass.py --nur-auswerten` bewertet das Protokoll neu, ohne einen Tag
zu holen - der Sammellauf zieht rund 20 Stationsbilder und dauert Minuten.

### Erledigt (v4.26): der Stationsfaktor nimmt eine zweite Sonnenklasse

`MIN_SONNE` bleibt bei 0,90. Neu ist eine zweite Klasse 70-90 %, die **je
Station** zugelassen wird, wenn sie mindestens `MIN_TAGE_2 = 3` Tage hat und
ihre Streuung hoechstens `MAX_STREU_2 = 0,06` betraegt.

Die Mindestanzahl ist die halbe Regel, nicht Beiwerk: Ein einzelner Tag hat
Streuung 0,000 und saehe damit am vertrauenswuerdigsten aus. Schneefernerhaus
ist genau dieser Fall und liegt 17,5 % neben seinen sieben Klartagen. An den
24 Stationen mit beiden Klassen:

    ohne Mindestanzahl, SD<=0,06   18 zugelassen  Median 2,1 %  MAX 17,5 %
    ab 3 Tagen,         SD<=0,06    6 zugelassen  Median 0,8 %  max  3,4 %

Wettenberg steht damit auf 1,113 aus 7 Tagen statt 1,094 aus 1, und nicht
mehr vorlaeufig. Sonst betroffen: Andernach (1,097), Zingst (neu, 1,080).

### Erledigt (v4.25): der Tagesgang der Truebung

Die Klarhimmelglocke ist nicht mehr symmetrisch um den Sonnenhoechststand:
Faktor `1 + b*(Stunden seit Hoechststand)` mit `b = -0,0075/h`, geklemmt auf
+-6 %, angewandt in `uvCamsAnwenden`, `makeSunBell` und `physUvAt`.

**Nicht** der Wert aus `uv-durchlass.json` (-0,0094 +- 0,001): dessen Fehler
behandelt 2619 Punkte als unabhaengig, obwohl Punkte derselben Station am
selben Tag es nicht sind. Geclustert nach Tagen -0,0080 (SD 0,0125), nach
Stationen -0,0069 (SD 0,0086); 11 von 14 Tagen und 17 von 21 Stationen
negativ. Die Richtung steht, die Groesse nicht - das 95-%-Band der
Sechs-Stunden-Spanne reicht von -0,8 % bis -8,5 %.

Die Glocke braucht den Faktor extra: `makeSunBell` fittet A*mu^k an die
Stundenwerte, und mu ist symmetrisch um den Hoechststand - eine schiefe
Kippung kann diese Regression gar nicht abbilden.

### Erledigt (v4.28): die Saeule darf die Glocke nicht ueberragen

`UV_K_MAX` stand auf 1,40 und liess eine Saeule 25 % ueber der
Klarhimmelglocke zu. Am 22.09.2026 war das den ganzen Mittag zu sehen:
"Wolkendurchlass 106 %", Saeulen ueber der schwarzen Kurve, die amtliche
BfS-Messung daneben unter ihr.

**Ursache:** Wolkenraender verstaerken die *Globalstrahlung*, aber kaum das
*UV*. Der Pyranometer sieht bei Sonne durch eine Luecke die direkte Strahlung
plus Reflexion von den Wolkenflanken; das UV ist schon zur Haelfte diffus und
wird vom umstehenden Wolkenfeld zugleich beschnitten. Dazu wandte die App den
Exponenten bis 1,40 an, obwohl `uv_durchlass.py` ihn nur auf
`dl in (0,08 ; 0,97)` fittet.

Gemessen, 12 771 Paare aus 22 Stationen, Median Messung/Glocke:

    Durchlass   0,60-0,80  0,80-0,90  0,90-0,97  0,97-1,00  >1,00
    gemessen        0,757      0,851      0,894      0,920  0,938
    Modell alt      0,782      0,896      0,960      0,989  1,015

In **keinem** Band liegt der gemessene Median ueber 1,0.

### Geprueft (v4.68): "Sonne durch eine Luecke" - Korrektur lohnt nicht mehr

Nachgerechnet am 29.09.2026 gegen die GELERNTE Kurve (v4.38), 22 Tage,
Messung / Kurve, Durchlass ab 0,97:

    wirklich klar (alle Schichten <15 %)   n=1786  1,009
    Luecke (eine Schicht >= 15 %)          n=2504  0,985
    Luecke mit tiefen Wolken >= 15 %       n=1226  0,971

Die Kurve hat den Unterschied weitgehend geschluckt: aus 8 % sind 2,4 %
(klar gegen Luecke) geworden. Die Tagesmediane streuen im Lueckenfall von
0,88 bis 1,03 - ein Faktor fuer 2-3 % ginge im Rauschen unter und braeuchte
dazu Wolkenschichten je 10 Minuten in der App. Nicht eingebaut. Neu pruefen,
wenn die Tage deutlich mehr werden.

Frueher (v4.28, gegen die rohe Glocke):

Der Deckel nimmt die Spitze, nicht die Ursache. Bei Durchlass ab 0,97
trennen sich die beiden Faelle klar:

    wirklich klar (alle Schichten <15 %)   n=559   q = 0,971
    Sonne durch eine Luecke                n=1229  q = 0,918

Gegen ein Modell von 1,00 ist der zweite Fall 8,4 % zu hoch, der erste nur
3 %. Die Zutaten zur Unterscheidung liegen bereit: Sonnenminuten je zehn
Minuten aus `solar10`, Bewoelkung je Schicht von Open-Meteo (`wl`/`wm`/`wh`
stehen im Durchlassprotokoll schon drin). Ein Daempfungsfaktor nur fuer den
Lueckenfall waere der naechste Schritt.

### Erledigt (v4.27): die Radar-Eichung ist angeschlossen

`regenRadarLaden()` holt `regen-radar.json`, `radarBoden(mmh)` rechnet die
Radarrate in eine geschaetzte Bodenrate um. Drei Punkte, die jeder nachlesen
sollte, der daran arbeitet - ausfuehrlich im Kommentar bei
`radarSchwelleJetzt()`:

1. **Die Stufenfaktoren sind nicht monoton.** niesel 2,95, leicht 0,83, hart
   an der Grenze 0,5: Radar 0,49 ergaebe 1,45 mm/h, Radar 0,51 nur 0,42. Ein
   staerkeres Echo waere weniger Regen. Stattdessen eine stetige Potenzkurve
   durch zwei Anker, flach ausserhalb; die Bodenrate geht mit r^0,53. Der
   Lader prueft `1+b > 0` und verwirft die Eichung, wenn das Protokoll
   spaeter eine fallende Kurve liefert.

2. **Anker ist NICHT das Feld `faktor`.** Das ist der Median der Quotienten,
   und der ist nicht der Quotient der Mediane (niesel 2,95 gegen 1,90; leicht
   0,83 gegen 0,85). Er gehoert auch nicht an den Klassenmedian, weil der
   Quotient bei kleinem r am groessten ist. Genommen wird
   `mess_median / radar_median`.

3. **Der Faktor gilt nur, WENN es unten regnet.** `regen_radar.py` zaehlt nur
   Stunden mit >= 0,2 mm an der Station. Wie oft das Gegenteil eintritt,
   steht in derselben Datei unter `_boden_trocken`: bei Radar 0,10-0,25
   bleibt der Boden in 66 % der Stunden trocken. Darum bleibt die
   **Erkennung** auf den rohen Radarwerten (`radarSchwelleJetzt`,
   `NOWCAST_TH`, jeder Vergleich, der entscheidet OB es regnet), und geeicht
   wird nur, was als **Menge** dasteht.

Ohne geladene Datei ist `radarBoden()` die Identitaet.

### Offen: die Klasse "regen" hat erst 4 Paare

Oberhalb von 1,17 mm/h gilt flach der Faktor der Klasse "leicht" (0,85).
Sobald `regen` 30 Paare hat, gehoert ein dritter Anker in `regenRadarLaden()`.
Der Nieselanker ist mit Standardfehler 0,60 (n=34) ebenfalls noch grob.
