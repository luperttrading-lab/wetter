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
- **GitHub-Zeitplaene sind unzuverlaessig** (gemessen: solar10 03.09. 2 von 68
  Terminen; RADOLAN 19./20.10. 6 von 48; UV-Prognose 3-5 h zu spaet). Was
  regelmaessig laufen MUSS, laeuft als SCHLEIFE in einem Job (5,5 h) und
  startet am Ende seinen Nachfolger per workflow_dispatch (`actions: write`,
  concurrency mit cancel-in-progress, Nachfolger nur bei success): so
  `solar10.yml` (seit 05.09.) und `radolan.yml` (seit 20.10., Abruf :07/:37,
  Rueckfall-Cron alle 4 h). Laeufe, die nur einmal am Tag zaehlen, pruefen
  stattdessen ihr Zeitfenster selbst (`uv_prognose.py`).
- **Solar 10-Minuten** (`solar10.py`, alle 15 min, ~60 Stationen): schreibt
  nach Branch `daten` **ohne Historie** (jeder Lauf ersetzt den einzigen
  Commit per force-push). Die App liest
  `https://raw.githubusercontent.com/luperttrading-lab/wetter/daten/solar10/`.
  Nie `daten` nach `main` mergen und nie Daten dieser Pipeline auf `main`
  committen - sonst waechst das Repo um etwa 1 GB im Jahr.

### ICON-D2-RUC-Vergleich (seit 21.10.2026)

Nutzer: "erst messen, dann in die App" - RUC kommt nur in index.html, wenn es
an der Station Giessen/Wettenberg (01639) messbar gewinnt. `ruc.py` (Workflow
`ruc.yml`, Schleife, Abruf stuendlich um :42 UTC; ein RUC-Lauf ist ~37 min
nach der vollen Stunde vollstaendig) holt den neuesten Lauf vom DWD
(`opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/<VAR>/r/<Lauf>/s/PT0hhH00M.grib2`,
TOT_PREC und T_2M fuer +1..+14 h, ~17 MB je Lauf) und schreibt zum SELBEN
Zeitpunkt die Vergleichsvorhersagen mit: Open-Meteo best_match (= was die App
zeigt) und icon_d2, MOSMIX ueber Bright Sky. Nachholen geht nicht - Open-Meteo
liefert nur den neuesten Lauf. Daten: Branch `ruc-daten` (mit Historie, NICHT
nach main mergen), `ruc/JJJJ-MM-TT.jsonl` je UTC-Tag, `ruc/stand.json`,
`ruc/gitter.json`. FALLE: "r" ist beim DWD das NATIVE ICON-Dreiecksgitter
(542 040 Zellen, CCSDS-gepackt), kein Laenge/Breite-Raster - eccodes noetig,
Zellmitten aus CLAT/CLON; naechste Zelle 0,4 km neben der Station, 16 Zellen
bis 5 km (gespeichert: Zelle, Mittel und Max der 5 km). TOT_PREC ist ab
Laufbeginn aufsummiert -> Stundenwert = Differenz, Stempel = Stundenende.
`ruc_auswertung.py` (einmal je Workflow-Lauf) holt die Stationsmessung von
Bright Sky und schreibt `ruc/auswertung.md` / `.json`: je Vorlauf (Stunden
nach dem Abruf) POD/FAR/CSI ab 0,1 und 0,5 mm/h, Regen-MAE, Temperatur
MAE/Bias - nur auf der GEMEINSAMEN Stichprobe aller Modelle. Dazu ein
Tagesvergleich RUC gegen App mit Vorzeichentest (Stunden sind abhaengig).
Erste Auswertung sinnvoll nach ~2 Wochen mit mehreren Regentagen.

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

**Unteragenten** (Stand 08.10.2026, mit einem Haiku-Agenten nachgewiesen) schreiben
ein EIGENES Protokoll: `<sitzung>.jsonl` und daneben `<sitzung>/subagents/agent-<id>.jsonl`.
Bis dahin fehlten ihre Kosten in der Zeile vollstaendig. Das Skript liest die Dateien jetzt
mit; ihre `user`-Zeilen (Auftraege des Haupt-Claude) verschieben die Fragegrenze nicht.
`-v` nennt Zahl und Kosten der Unteragenten.

**Haiku 5.5** ist nach Laenge der Anfrage gestaffelt: bis 100.000 Token 0,10 / 0,50 $,
darueber 0,50 / 2,50 $ (`STAFFEL` im Skript). **Sonnet 5.5** liest den Cache seit Oktober
zu 0,05x (0,10 $/M), am 29.09. stand dort noch 0,1x.

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

### Erster Start und Geheimknopf (v5.08)

Nutzer: "beim Start weniger Einblendungen" + Geheimknopf, um das zu sehen.
NEUE Nutzer finden `KLAPP_ZU_NEU` zugeklappt (umkreis, bilanz, pv, mond,
planeten, iss, meteore, ereignisse) und die Kacheln `KZ_STD` ohne Pollen.
BESTANDSNUTZER behalten "alles offen": das erste Script prueft als
Allererstes, ob schon Eintraege ausser Zwischenspeichern (/cache/i) da sind,
und setzt dann `klappBestand` (einmalig, Marke `klappStd2`). Wer neue Teile
hinzufuegt, die nur Kenner brauchen: in `KLAPP_ZU_NEU` eintragen.
GEHEIMKNOPF: 3 s auf die Versionsnummer (`.ver`) -> `erstStartUmschalten()`
legt alle Eintraege ausser /cache/i in EINEN Eintrag `erstStartSicherung`,
loescht sie und laedt neu = Ansicht eines neuen Nutzers, mit dunklem Balken
unten "So sieht die App beim ersten Start aus" + Knopf "Zurueck zu meinen
Einstellungen" (oder nochmal 3 s). Zurueck stellt alles exakt wieder her;
was in der Vorschau eingestellt wurde, verfaellt. Geprueft (Playwright):
Bestand A -> Vorschau -> zurueck, Eintraege identisch, Cache bleibt.

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

v5.03 (Nutzer, 05.10. 10:19 Nebel: Kachel "☀ ~11:30", Stundenleiste 10-11 Uhr
schon 28 min, draussen spitzte die Sonne durch): `kzSonneErwartet()` nimmt die
erste Stunde mit >= 10 statt >= 30 erwarteten Sonnenminuten. Zusaetzlich
verschwindet "erste Sonne", sobald die Station in den letzten 30 min >= 2 min
Sonne gemessen hat (`kzSonneHeute().zuletzt`). Geprueft mit eingespielten
Stunden: 0/28/35 -> "☀ bald" (10:30), 9/21/32 -> 10:45, 0/0/5/40 -> 12:15.
Die 10-min-Station liefert mit rund 30-40 min Verzug (05.10. 10:19: letzte
Werte 09:50) - die ersten Strahlen sieht man draussen frueher als die App.
v5.04: Auch die gerade abgelaufene Stunde zaehlt mit (Stempel bis 60 min alt;
fuer vergangene Stempel liefert Bright Sky die BEOBACHTETE Sonnenscheindauer).
Vorher sprang "bald" zum Stundenwechsel zurueck (11:01: Stempel 11 Uhr fiel
raus, 12 Uhr mit 35 min ergab "~11:30"). Geprueft 0/28/35/45: 09:30 und 10:10
"~10:30", 10:19 bis 12:05 durchgehend "bald".

v5.05 (Nutzer: "Pollenflug-Kachel"): Kachel `pollen` (einmalig per
`kzPollenNeu` ans Ende der eigenen Auswahl gehaengt). Quelle in Deutschland
der amtliche DWD-Pollenflug-Gefahrenindex (`s31fg.json`, acht Arten inkl.
Hasel und Esche, Stufen 0 / 0-1 / ... / 3, Ausgabe gegen 11 Uhr fuer
heute/morgen/uebermorgen). Die DWD-Datei hat KEINEN CORS-Kopf - darum holt
`pollen.py` (Workflow `pollen.yml`, 09:35 und 10:35 UTC) sie nach
`pollen.json` auf `main` (rund 6 KB, nur bei Aenderung). Region: naechster
Stuetzpunkt in `POL_PUNKTE` (mehrere je Teilregion, von Hand; Gießen/Wetzlar/
Marburg/Kassel -> 91, Frankfurt/Wiesbaden/Darmstadt -> 92, an 40 Staedten
geprueft), ab 45 km Abstand Ausland -> CAMS (`_pollenCams`, nur Graeser,
Birke, Erle, Beifuss, Ambrosia - CAMS kennt weder Hasel noch Esche).
Grenznah (Luxemburg) gilt die deutsche Nachbarregion. Vor 11 Uhr ist der
Stand von gestern - `polTage` verschiebt dann um einen Tag; aelter als
gestern -> nichts. Kachel: staerkste Art + farbige Pille (Stufe), Wechsel
zweitstaerkste Art und "POLLEN DI" (Wochentag morgen) - "morgen" + Pille
braucht 91-108 px, die Drittelkachel hat 78. Die grosse Kachel "Pollenflug"
unten (`pollenSubBauen`) zeigt ebenfalls zuerst DWD mit Regionsname.
Im Oktober steht ueberall 0 - die Kachel zeigt dann "keine".

v5.06 (Nutzer, 09.10.: ISS "keiner / in 6 Tagen" unverstaendlich - las sich
als "keiner in 6 Tagen"): ab 72 h jetzt "ISS / in 6 Tagen / Do ~19:31", ab 7
Tagen Unterzeile "So 18.10." (mit Uhrzeit brach sie um); gar keiner im
Rechenfenster "keiner / bis 29.10.". WOLKEN bei Planet und ISS (Nutzer:
"erkennen, ob die Planeten sichtbar sind oder Wolken"): `kzWolke(t)` nimmt
`issCloudAt` (Open-Meteo cloud_cover stuendlich, 7 Tage) und die Stufen von
`issAmpel` (<= 33 klar, <= 66 diesig, darueber bedeckt). Klar: nichts; diesig:
blasse Wolke hinter dem Wert; bedeckt: dunkle Wolke und der Wert blass
(`kzBlass`). Hinter dem WERT, nicht der Beschriftung - "ISS MORGEN" fuellt
die Beschriftung schon (10 px). Planet: Zeit = Erscheinen des Planeten
("jetzt im" = jetzt); Wolken ausserhalb `kzMerk`, weil sie nach der Rechnung
kommen. ISS ab 72 h ohne Wolke (Vorhersage zu unsicher).

v5.07 (Nutzer: Textpruefung aller Kachelzustaende, jede Kachel als Satz
gelesen wie beim ISS-Fall). Geaendert: ISS "53° · 6 min" -> "ab SW · 6 min"
(Grad las sich als Temperatur; ab 10 min "SW · 12 min"); Planet "ab 03:33 O"
-> "03:33 im O" (einzelnes O wie Null; "ab 03:33 im SO" 94 px zu breit);
Morgen "2,5 mm" -> Tropfen + "2,5 mm" (`KZ_TROPFEN`; "2,5 mm Regen" braucht
89 px, Platz 78 - das Wort fiel deshalb IMMER weg); Pollen "keine / DWD-Index"
-> "keine / heute", morgen "keine / erwartet". Gemessen bei 375 pt
(`p507m.py`: Text in eine Kachel, Breite gegen Platz). NICHT geaendert, weil
vom Nutzer gewaehlt oder zu breit: UV "klar 3,5" / "erw." / "gem."
("wolkenlos 3,5" passt nur auf 88 %), Wind "Boeen 35 · S" (Richtung = woher;
"aus SW" passt dreistellig nicht).

v5.09 (Nutzer-Screenshot 20.10.: Kachel "Regen 24 h" "ab 16:00 ~2,1 mm",
Abschnitt "Regen ab 17 Uhr ~1,7 mm gesamt"): zwei Fehler. (1) Der Abschnitt
`renderRainHours` nannte den STEMPEL statt des Stundenbeginns (precipitation =
Stunde VOR dem Stempel) - jetzt `hLbl` = Stempel - 1 h, auch an der Achse.
(2) Die Kachel nahm bis zu 25 Stunden (Fenster now-30 min bis now+24,5 h),
der Abschnitt 24 - jetzt beide `slice(0,24)`. Geprueft mit eingespieltem
Regen nur im Stempel 17 Uhr: beide "ab 16", beide 0,4 mm.
VARIANTENSEITE `regentest.html` (Nutzer: Tagesregen mit Stundenbalken 0-24
Uhr, evtl. morgen): A Drittelkachel nur heute, B Drittelkachel heute <->
morgen im Wechsel, C doppelt breit mit 48 Balken. Echte Daten (gefallen:
Bright Sky, nur vergangene Stempel; erwartet: Open-Meteo, Rueckfall MOSMIX)
oder "Beispiel: Schauertag". Balken 16 px hoch, volle Hoehe ab 1 mm/h,
dunkelblau gefallen, hellblau erwartet, roter Strich jetzt. Wahl steht aus.

v5.10 (Nutzer nach regentest.html: nicht doppelt breit, nicht 0-24 Uhr,
sondern ab JETZT 24 Stunden; Tag/Nacht eingefaerbt; Grafik als ZWEITE
ANSICHT statt darunter, damit die Kachel nicht hoeher wird): Kachel
"Regen 24 h" wechselt Text <-> Stundenbalken (`kzRegenGrafik(H)`, dieselben
24 Stunden wie Text und Abschnitt). Nacht = Sonnenuntergang bis -aufgang
(`sunMoment`, gestern bis uebermorgen) leicht dunkler, Mitternacht als
Strich mit Wochentag ("Mi"), volle Hoehe ab 1 mm/h. Die Grafik liegt
ABSOLUT in der Kachel (`.kzbal`, top 25 px, Rechts 13 px frei fuer die
Punkte) - im Fluss der Wertzeile machte sie die Zeile hoeher bzw. wurde vom
overflow:hidden der Zeile beschnitten. Kachelhoehe gleich den Nachbarn
(61 px). Nur Tests mit eingespielten Stundenwerten (Open-Meteo aus dem
Pruefstand nicht erreichbar). `regentest.html` bleibt als Archiv.

v5.11 (Nutzer, Variante 1 aus `regentest2.html`): "Tagesregen" und "Regen 24 h"
in EINER Kachel (`regenHeute`, Name "Regen bis 24 Uhr + 24 Std"). Ansicht 1
"BIS 24 UHR" (Nutzer: bis 24 Uhr sind nicht 24 Stunden): Wert = ganzer Tag
(gefallen + erwartet), Unterzeile "erwartet" / "1,2 gefallen" / "gefallen".
Ansicht 2: Stundenbalken (`kzRegenGrafik`) mit Ueberschrift "24 h 2,6 mm",
nur wenn in 24 h Regen kommt. Das WANN steht wieder als Zusatz in der Kachel
"Regen" (`kzRegenDanach`, laeuft, solange `regen24` nicht gewaehlt ist).
Einmalig (`kzRegenZus`): beide gewaehlt -> regen24 raus, nur regen24 -> wird
regenHeute. `regen24` bleibt im Pool. `kzRegen24H()` liefert die 24 Stunden
fuer beide Kacheln. MESSUNG statt Mockup: "Regen heute" 89 px und
"24 h · ~2,6 mm" 99 px passen NICHT in 78 px - das Mockup war rund 7 px
breiter als die App. "Bis 24 Uhr" 73 px, "24 h 2,6 mm" 81 px (auf 88 %).

v5.12 (Nutzer, Variante D aus `nachttest.html`; Sonne = TAGESLICHT, nicht
Sonnenschein): Stundenbalken mit Tag hellgelb (`.kzbd`) und Nacht blaugrau
(`.kzbn`), dazu `KZ_SONNE` / `KZ_MOND` in der Mitte jedes Abschnitts ab 14 %
Breite (`.kzbs`). Sperrzone um den Mitternachtsstrich 28 % (Wochentag ~15 px +
halbes Zeichen auf ~73 px Grafik), auf der Seite des Wochentags (rechts, ab
78 % links vom Strich); bei 14 % stand der Mond noch direkt am "Mi". Geprueft
09:00/14:00/20:30/23:30/03:00/06:30. Wochentag aus dem exakten Zeitpunkt
(`mnMs`), nicht aus Prozent zurueckgerechnet (23:59:59 ergaebe den Vortag).

v5.13 (Nutzer, 20.10. 16:04: Kachel "Regen in 5 min", Abschnitt "Regen ab 18
Uhr" - "nicht konsistent"): Radar und Modell wurden nie abgeglichen. Jetzt
`regenIntervall(a,b,mmStd)`: Teil von [a,b), den der Nowcast abdeckt
(`regenRadarTeil`, Schritt i = [t_i, t_i+5 min), nass ab roher Schwelle TH,
Menge = geeichte Bodenrate), Rest anteilig aus dem Modell. Gilt fuer
`kzRegen24H` (Kachel/Balken), `renderRainHours` (Abschnitt, Zusatz "erste 2 Std
aus dem Radar"), `bilanzRest` ("bis 24 Uhr") und `kzRegenDanach` (Zusatz der
Kachel "Regen"). `_kz.nowcast.zeit` neu; nach jedem Nowcast zeichnet
`renderRainHours(_rainHrD)` neu. Dabei behoben: `bilanzRest` behandelte den
Stempel als STUNDENBEGINN (precipitation = Stunde VOR dem Stempel) - die
laufende Stunde fehlte, 23-24 Uhr ebenso. Geprueft: Modell Regen ab 17 Uhr,
Radar 16:10-16:40 leicht und danach trocken -> Abschnitt "ab 16 Uhr", 17-18
Uhr trocken, "bis 24 Uhr" = 24 h = 1,1 mm, Zusatz "ab 18:00".

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

v4.93 (Nutzer, 03.10.: "man trifft den Eichknopf nicht"): Bei laufendem
Kompass UND Eichtest ist ein TIPP IRGENDWO (<= 10 px, <= 700 ms; nicht auf
Knoepfen/Links/Legende/Drehraedern - `closest(...)` in der pointerup-Pruefung)
ein Eichpunkt (`plEichTipp`): Messung wie "Messpunkt", danach SOFORT Eichung
= Mittel aller Punkte seit dem Einschalten des Eichtests (`PL_EICH.sitz`).
Bestaetigung: Dreiklang 659/831/988 Hz (`plEichKlang`, AudioContext wird schon
beim Tipp angelegt - iOS), Einblendung "Geeicht: Kompass 4,7 Grad zu weit
rechts" 3,5 s, im Kasten eine Skala -15..+15 Grad mit Punkt. Im Eichtest
waehlt ein Tipp aufs Bild KEIN Ziel mehr (Ziel ueber die Legende).
Getestet nur mit Mausklicks und gesetzten Kompasswerten, nicht am iPhone.
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

v4.94 (Nutzer, 03.10.: "am Himmel von oben beleuchtet, im Bild von der Seite"):
Die Lage der Mondsichel im Planetenbild kam aus BILDkoordinaten
(atan2(Y(sonne)-y, X(sonne)-x)) - das Bild zieht 360 Grad Azimut ueber die
Breite und staucht die Hoehe, eine Gerade darin ist kein Grosskreis. Jetzt
Anfangsrichtung des Grosskreises Mond -> Sonne in alt/az, gemessen vom Zenit
zu wachsendem Azimut (= rechts im Bild). Geprueft gegen PyEphem (chi - q,
Positionswinkel des hellen Randes minus parallaktischer Winkel) an vier
Zeitpunkten: Betrag auf 0,1 Grad gleich (03.10. 11:55: 48 Grad links von
oben, vorher im Bild fast waagrecht). Das Mondfoto selbst wird nicht
gedreht (Krater stehen also nicht exakt), nur der Schatten.
v4.95 (Nutzer): dasselbe fuer die Kachel "Mond" und die Mondkarte
(`moonSvg(mo,dreh)`, `mondHellDreh(frac)`): Grundzeichnung Lichtseite rechts
(zunehmend) bzw. links (abnehmend), Schattenmaske gedreht um (Winkel am Himmel
- (+-90)). Nur solange der Mond ueber dem Horizont steht, sonst Grundzeichnung.
Geprueft: 03.10. 11:05 48 Grad links von oben, 04.10. 06:00 132,6 Grad
(PyEphem 132,7).

v4.96 (Nutzer, 03.10.: "Anzeige direkt ueber dem Mond"): Im Bild "Mond im
Jahr" sass das Kaestchen mit den beiden Dauern mittig oben auf der
heute-Senkrechten - bei langem Mondbogen (17 h 55 min) genau auf dem Ring.
Jetzt 10 px NEBEN der Senkrechten, Seite und Hoehe nach der kleinsten
Ueberdeckung (Kurvenpunkt 1, Voll-/Neumond 6, Ring 1000; Gleichstand: oben,
rechts). Geprueft an sechs Tagen (Jan, Maerz, Juni, Aug, Okt, Dez): kein Ring
verdeckt. Dabei nachgeprueft: der Mondschatten im Planetenbild DREHT sich mit
der gewaehlten Uhrzeit (03.10.: 06:00 114 Grad, 07:30 82, 09:30 54, 13:00 52) -
zwischen Vormittag und Nachmittag aendert er sich wirklich kaum (PyEphem
09:05 48, 12:30 56, 13:40 63 Grad).

v4.97 (Nutzer: "kann das falsch aussehen, weil die Sonne von hinten kommt?"):
LICHTWEG im Planetenbild - der Grosskreis Sonne -> Mond als gestrichelte
gelbe Linie mit Pfeilspitze am Mond. Gerechnet als Slerp der Einheitsvektoren
(Ost, Nord, Oben) in 1-Grad-Schritten, Azimut stetig fortgesetzt; gezeichnet
nur im Fenster, ueber dem Horizont und bis 76 Grad, nur wenn der Mond oben
ist. Liegt auf dem Overlay (`planetenSunCv`) wie die Sonne, damit der Pfeil
nicht unter "Jetzt" verschwindet. Zeigt, warum die helle Seite nicht auf die
Sonne IM BILD zeigt: 03.10. 08:20 Mond 62 Grad SW, Sonne 7 Grad OSO (94 Grad
auseinander) - der Bogen verlaesst den Mond nach links oben.

v4.98 (Nutzer: "unverzerrte Darstellung zum Anklicken", Lichtweg "mit
Einschaltung und Erklaerung"): Umschalter "Panorama | Himmelskarte" ueber dem
Planetenbild (`pl_ansicht`, Voreinstellung Panorama) und Schalter "Lichtweg"
(`pl_lichtweg`, Voreinstellung AUS) mit Erklaerzeile `#plInfo` (`plLwNote`).
HIMMELSKARTE (`plKarteZeichnen`): stereographisch, Zenit Mitte, Horizont Rand,
N oben, O LINKS (Blick nach oben), r = R tan(z/2). Winkeltreu - die Sichel
wird aus der Karte gerichtet (0,5 Grad entlang des Grosskreises Mond -> Sonne,
projiziert, atan2), Lichtweg und helle Seite passen exakt. Geprueft gegen
PyEphem: Winkel der hellen Seite zum Zenit -65,7/-58,8/-119,2 gegen
-66,0/-58,9/-119,5 Grad (03.10. 08:20, 15:00; 04.10. 07:00). Hoehe
`PL_KARTE_TOP` + 2R + 26 (Raeder und "Jetzt" liegen darueber). `plTexF`
(Planetenportraets) ist jetzt top-level; der Fuss von drawPlaneten (Raeder,
Legende) ist die innere Funktion `plTail()`, die Karte ruft sie auch. Kompass
in der Karte: Speiche in Blickrichtung, Ring auf der Hoehe. Am iPhone nicht
geprueft.

v4.99 (Nutzer): dritte Ansicht BLICK ("durchs Handy", `plBlickZeichnen`,
`pl_ansicht`="blick"). Gnomonisch wie ein Kamerabild, 60 Grad breit
(`PL_BLICK_FOV`), Mitte = Kompassrichtung + Hoehe der Oberkante (Eichung gilt),
oben = zum Zenit; die Drehung des Handys um die eigene Achse (gamma) wird
nicht ausgewertet. Grosskreise = Geraden (Horizont waagrecht, Lichtweg gerade),
nichts gespiegelt - die Sichel steht wie am Himmel. Ohne Kompass steht die
Mitte auf dem gewaehlten Ziel, sonst Mond, Sonne, hellster Planet, sonst S 20
Grad (`plBlickMitte`, Hoehe 12-80 Grad). Mond, Sonne, gewaehltes Ziel ausserhalb:
Pfeil am Rand mit Winkelabstand. Zeile "Handy zeigt SSO 160 Grad - Hoehe 35"
steht in `#plInfo` (im Bild ueberdeckte sie die Richtungsbeschriftung).
Lichtweg-Erklaerung sagt jetzt "Mond unter dem Horizont", wenn er unten ist.
Getestet nur mit gesetzten Kompasswerten im Browser, nicht am iPhone.

v5.00 (Nutzer: "als laege das Handy auf dem Tisch", Blick von unten ins Handy
"unintuitiv"): Himmelskarte jetzt von OBEN gesehen - N oben, O RECHTS wie eine
Landkarte (`plKartePkt`: x = cx + r sin(az - rot)). Mit laufendem Kompass
dreht sie mit (`o.rot` = Blickrichtung, oben = vorn; gegen die Richtung
geprueft: Blick W -> S links, N rechts). Der Mond ist dadurch seitenverkehrt
zum Himmel (die Karte ist das Spiegelbild); die Sichel wird weiter aus der
Karte gerichtet und passt zum Lichtweg. Die Erklaerzeile sagt das und
verweist fuer den echten Anblick auf "Blick". Nach v4.99 kam laut Regel v5.00.

v5.01 (Nutzer, 04.10. 07:40: "den Ortungskreis sieht man hinter dem Schild
nicht"): Im Panorama liegen Kompass-Strich, Hoehenlinie, Ring und
Beschriftungen jetzt auf dem Overlay (`planetenSunCv`, VOR Raedern und
"Jetzt"), Ring Radius 16 statt 9 (der Mond hat 12,5 und deckte ihn ganz zu).
Liegt die Hoehe in der oberen Zone, steht "Hoehe 64 Grad" direkt neben dem
Ring statt am Rand unter dem Zeitrad.

v5.02 (Nutzer, 04.10. 12:27, Handy flach auf dem Buergersteig der
Weiherstrasse, OSM-Richtung 177,5 Grad): iOS-Kompass 178 Grad, App 188 Grad
"geeicht". Ursache: eine gespeicherte Eichung (`pl_eich`, rund -10 Grad aus
frueheren Tipps im Eichtest) - sie bleibt, bis "Eichung aus" gedrueckt wird;
"Loeschen" nahm nur die Messpunkte weg. Jetzt: "Loeschen" nimmt Punkte UND
Eichung weg (Rueckfrage nennt beides), der Kompassknopf zeigt die Groesse
("geeicht 10 Grad"). Kalibrierhilfe ohne Himmel: Handy flach an einer
geraden Strasse anlegen, deren Richtung bekannt ist (Weiherstrasse 177,5 /
357,5 Grad geografisch, aus OSM-Weg 4910338, 94 m gerade).

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

**Kein Pfeil (v4.92, Nutzer: "sieht aus wie eine Ortsangabe"):** Unter 3 km/h
statt weisser Beschriftung ein dunkler Kasten wie die Zeitanzeige: "Kein Pfeil
– Regen zieht kaum" unter dem Standort; die Zeile unter der Karte sagt dann
"Kein Pfeil: der Regen bewegt sich kaum (unter 3 km/h ...)" statt "Zug nach S,
0 km/h". Anlass 03.10. 09:20 Nebel: 40-216 Zellen mit 0,1-0,2 mm/h standen
eine Stunde still (Niesel aus dem Nebel, Wind 6 km/h) - 0 km/h war richtig
gemessen, sah aber nach Fehler aus.

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

v5.43 (Nutzer, Bildschirmfilm 24.10. 21:56: "Macht der Pfeil Sinn, so wie die Wolken
ziehen?"): Pfeil "nach NO, 28 km/h aus dem Radar", im Film rueckte ein Nord-Sued-Band von
WESTEN heran (Ostkante ~40 km/h nach O, nachgemessen je Zeile). ZWEI Fehler der Messung:
(1) Sie zaehlt nur, wie viele nasse Zellen aus A in B landen. Schiebt sich ein Band von
aussen ins Bild, waechst die nasse Flaeche und A landet bei JEDER kleinen Verschiebung ganz
in B - Gleichstand, 0 gewinnt (22:20: "0 km/h", verworfen, Hoehenwind 59 km/h NO). (2) In
der Stunde davor stand nur schwaches Gekruemel im Bild, das mit dem Wind nach NO zog.
Jetzt ZUERST `rkZugVorhersage(fr)`: die DWD-Vorhersage verschiebt das Feld selbst (= der
Film ab jetzt), gemessen wird nur der Versatz - normierte Korrelation von log(1+10 mm/h),
15-min-Schritte ab dem Bild "jetzt" (bis 7), grob auf 3-km-Bloecken +-10 (bis 120 km/h),
fein +-3 Zellen, je Schritt Korrelation >= 0,5, Median ab 2 Schritten. Messung der
gemessenen Stunde und der alte 30-min-Rueckfall bleiben dahinter, die Gegenprobe mit dem
Hoehenwind (v4.57) bleibt. Geprueft 24.10. 22:20 an 15 Orten (Bright Sky direkt):
Korrelation 0,82-0,99, gleich der vollen Suche (Wettenberg 40/83 Grad gegen 40/86, Koeln
40/93 gegen 44/92, Freiburg 20/99 gegen 20/99); alte Messung dort 0 km/h (Wettenberg,
Freiburg), 69 statt 44 (Koeln). Live Wettenberg 44 km/h nach O, im Film erreicht die Kante
am "1 h"-Strich den Ort nach ~1 h. 36-88 ms je Aufruf (Chromium). Bei langen Baendern
zeigt der Pfeil die Bewegung QUER zum Band - Zellen IM Band ziehen oft mit dem Wind
schraeg (hier NO), fuer "wann kommt der Regen" zaehlt nur die Querbewegung.

**Bewusst NICHT gemacht (04.10.2026, Nutzer):** Zugpfeil in der Wolkenkarte.
Wolken ziehen je Hoehe verschieden (tief 850 hPa, mittel 700, Cirrus 300 hPa -
oft doppelt so schnell und 30-90 Grad anders), ein zweiter Pfeil neben dem
Radarpfeil haette mehr verwirrt als geholfen. Grundsatz des Nutzers: Auftraege
ueberdenken und Dinge, die den Laien verwirren, lieber nicht bauen.

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

**20.10.2026: Laufzeiten repariert, Befund systematisch.** GitHub startete die
geplanten Laeufe 3-5 h zu spaet (07:20 -> 12:11, 22:05 -> 01:28 am Folgetag),
und die Rolle hing an der Uhrzeit: der verspaetete Morgenlauf verbuchte als
"gemessenes Maximum" den Stand VOR der Tagesspitze (20.10.: 1,46 statt ~2,1).
Jetzt entscheidet der SONNENSTAND (`fenster()`, Auf-/Untergang aus der App):
morgens bis 2 h nach Aufgang und solange gemessen < 0,5, abends ab 1 h vor
Untergang bis Mitternacht; ausserhalb wird nichts eingetragen. Je drei
Cron-Laeufe pro Fenster (:37/:43, nicht :00/:05). Neue Eintraege tragen
`gueltig`; alte Abendlaeufe vor 13:00 gelten als ungueltig (`_gilt`).
Ergebnis mit 12 gueltigen Tagen: Morgenprognose an ALLEN 12 Tagen unter dem
gemessenen Maximum (Vorzeichentest p ~ 0,0005), Bias -0,28 UV (-14 %), klare
Tage 1-5 %, Tage mit Wolkenluecken 25-40 %. Vermutete Ursache: Jensen - MOSMIX
`solar` ist ein Stundenmittel (Erwartungswert ueber Sonne und Wolke), die
Tagesspitze ein Maximum ueber 10-Minuten-Werten; E[max] >= max E. Naechster
Schritt (Nutzer zugestimmt, steht aus): Spitze aus Stunden mit erwarteter
Sonne (MOSMIX `sunshine` >= ~10 min) mit Klar-Durchlass rechnen, nur fuer die
Zahl "erw.", nicht fuer die Saeulen - dann 2-3 Wochen vorwaerts vergleichen.

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

## Zuletzt verwendete Orte (v5.14)

Nutzer: "die letzten gesuchten Orte speichern". Im Standort-Dialog unter den
festen Orten eine Zeile "Zuletzt verwendet:" (`#locZulWrap`, `#locZul`),
Knoepfe wechseln direkt wie die festen, das x rechts entfernt nur den
Eintrag. Speicher `locZuletzt` (hoechstens 6, neuester zuerst), geschrieben
in `saveGo` -> `fertig` per `locZulMerken(neu, LOC)`: der NEUE und der
VERLASSENE Ort - so ist der vorige Ort immer einen Tipp entfernt, auch wenn
er vor v5.14 eingestellt wurde. Feste Orte (`LOC_FEST`) und der aktuelle Ort
erscheinen nicht; gleich = 0,01 Grad. Geprueft (Playwright): New York ->
Neustadt -> Muenchen, Liste und Wechsel stimmen, x loescht ohne Wechsel.
v5.15 (Nutzer): die fuenf festen Orte (Wettenberg, Huettenberg, Norden,
Muenchen, Kiel; Knoepfe `locWtb` usw. und die Konstanten ausser
`LOC_WETTENBERG`, das Vorgabeort bleibt) sind ENTFERNT - es gibt nur noch die
Liste, Kopf "Zuletzt verwendet – direkt wechseln:", hoechstens 8. Leer: Hinweis
`#locZulLeer`. Das x fragt nach (`confirm("„Ort“ aus der Liste loeschen?")`).
Folge fuer Bestandsnutzer: die Liste beginnt leer; ein Ort steht erst drin,
wenn man ihn einmal uebernommen bzw. von ihm weggewechselt hat.
v5.16 (Nutzer: "Logikfehler - wir haben gar keinen Ort eingegeben"): Im
Hauptschritt steht "Uebernehmen" nur, wenn Breite/Laenge/Name vom aktuellen
Ort abweichen (`apStand()`, bei `schritt("haupt")`, am Ende von `show()` und
bei jeder Eingabe); sonst nur ein breiter Knopf "Schliessen". Suche, GPS und
Einfuegen haben ihren eigenen Knopf im Bestaetigungsschritt. Ortsknoepfe
(`.loc-go`) etwas blauer: hell #dcebf9 / Rand #9fc5ea, dunkel #1d3550 / #3a5f88.

## Kachel "7 Tage" mit Tagessaeulen (v5.17)

Nutzer: statt "jeden Tag" / "Do–Sa" Saeulen, dazu die unsicheren Folgetage.
Zweite Ansicht `kzTageGrafik(W)`: bis 16 Tage aus `_fcTage` (Open-Meteo
`precipitation_sum`, forecast_days=16), Beschriftung "16 Tage". Je Tag eine
Spalte (`.kzbw b`), Wochenende hinterlegt (`.we`), ab Tag 8 blass (`.un`,
Deckkraft .4) mit Trennstrich (`.ab`) und "unsicher" rechtsbuendig (8 px;
Platz ~41 px, Wort ~39 px - nur ab 14 Tagen). Feste Skala: volle Hoehe ab
10 mm/Tag, darueber gedeckelt. Ansicht 1 unveraendert (Summe 7 Tage, Regentage).
IPHONE-FEHLER dabei behoben (Nutzer-Screenshot 20.10. 22:23): Die Stundenbalken
der Kachel "24 h" fehlten, der Streifen war halb so hoch - WebKit schnitt die
absolut liegende `.kzbal` am overflow:hidden der Wertzeile `.v` bzw. der
Wechselzelle ab, genau dort stehen die Balken. Chromium tut das nicht, darum
fiel es im Test nie auf. Jetzt `.v:has(.kzbal)` und `.kzwe>span:has(.kzbal)`
mit overflow:visible. Am iPhone noch nicht bestaetigt (kein WebKit im Pruefstand).
Pruefstand: Chromium kommt nicht selbst ins Netz; `netz.py` im Scratchpad leitet
alle Abrufe per `page.route` ueber Python (Proxy + CA-Bundle) - so laeuft die
App mit ECHTEN Daten.
v5.18 (Nutzer: "grauen Hintergrund verstehe ich nicht" -> "mini klein Sa und So"):
unter den hinterlegten Wochenend-Spalten steht "Sa So" (`.kzbwt`, 7 px, wie
eine Achse; einzeln "Sa"/"So" am Rand), mittig unter der Gruppe, per CSS
`clamp()` im Streifen gehalten. Gemessen: "Sa So" 22 px, "Sa" 10 px - die Schrift
ist breiter als die beiden Spalten (~9 px), steht also mittig darunter.
UNTEN statt oben (Nutzer schlug oben vor): 9 Folgetage enthalten immer ein
Wochenende, oben stiesse es jedes Mal an "unsicher". Saeulen dafuer 20 statt
27 px hoch (8 px Schriftzeile). Geprueft mit Beginn Di/Fr/Sa/So, hell und dunkel.
v5.19 (Nutzer): "unsicher" in der Grafik entfernt (blass genuegt; die 16-Tage-Liste
blendet dieselben Tage ab, `.fc-row.far`). VARIANTENSEITE `wochenendtest.html`
fuer die Markierung des Wochenendes (Nutzer: grau unverstaendlich, Sa/So sehr klein,
evtl. Rot + Legende): A grau + "Sa So" 7 px (= App), B 6 px, C rot hinterlegt +
Legende "Sa/So" oben rechts, D roter Strich an der Grundlinie + Legende, E rot +
rotes "Sa So", F ohne Wochenende. Echte Daten (Open-Meteo 16 Tage) oder Beispiel.
Wahl steht aus. Langes Druecken auf eine Kachel ist schon belegt (450 ms =
Bearbeiten/Sortieren) - eine Vergroesserung per Druecken ginge nur ueber eine
andere Geste.
v5.20 (Nutzer, statt der Varianten A-F): ROTER PUNKT unter Samstag und Sonntag
(`.kzbwp`, 3 px - bei 4 px beruehrten sich Sa und So, Spaltenabstand 4,5 px),
mittig unter der Spalte per calc((1+i) px + (100% - (n+1) px) * (i+0,5)/n),
geprueft auf 0,1 px gegen die Spaltenmitten. Kein grauer Hintergrund, kein
"Sa So" mehr. Saeulen 21 px, darunter 6 px Punktzeile. ERKLAERUNG per Tipp:
`kzPunktTipp(tile,e)` im Tipp-Zweig von `ende` - landet ein Tipp in der
untersten ~12 px der SICHTBAREN Grafik, erscheint 2,8 s die Blase `#kzTipp`
"Roter Punkt = Wochenende (Sa/So)" ueber der Kachel, statt zum Abschnitt zu
springen; weiter oben springt der Tipp wie immer. Geprueft mit Mausklicks
(Punktzeile: Blase, kein Sprung; oben: Sprung), nicht am iPhone.
`wochenendtest.html` bleibt als Archiv.
v5.21 (Nutzer: "Punkte kaum zu sehen und kaum zu druecken - auf Druck die Kachel
groesser machen"): GROSSANSICHT. Eine Kachel darf `gross()` liefern (HTML); dann
oeffnet ein Tipp `kzGrossZeigen(html,ziel)` statt zu springen - Fenster im Stil
des Standort-Dialogs (`loc-ovl`/`loc-box`), Knoepfe "Vorhersage" (springt zu
`ziel`) und "Schliessen", Tipp daneben oder Esc schliesst. Klicks auf den
Hintergrund in den ersten 450 ms zaehlen nicht (iOS schickt den Klick des
oeffnenden Tipps erst nach pointerup). Bisher nur `regen7`: `kzTageGross(W)`,
16 Spalten (~17 px) mit mm-Wert, Wochentag (Sa/So rot), Datum; Kopf "7 Tage |
unsicher"; Summen 7 Tage und Tag 8-16; Skala volle Hoehe = max(10 mm, Hoechstwert).
Ziel der Kachel jetzt `fcSec` (16-Tage-Liste) statt `bilanzSec`. In der Kachel
statt zweier 3-px-Punkte EIN roter Strich je Wochenende (`.kzbwp`, 3 px hoch,
von Spaltenbeginn a bis Spaltenende b - auf 0,1 px gegen die Spalten geprueft).
`kzPunktTipp` und `#kzTipp` sind entfernt. Kandidat fuer dieselbe Grossansicht:
die 24-h-Stundenbalken von `regenHeute`.

v5.22 (Nutzer: "Heute bisher brauchen wir in der ersten Kachel nicht, steht oben
drueber"): Kachel "Heute" zeigt nur noch "max 15 Uhr" (waermste Stunde), kein
"bisher 4–11" mehr und damit keinen Wechsel. Nebenbei verschwindet ein
Widerspruch: die Zeile darueber zeigt 3,5°, die Kachel rundete auf "bisher 4".
v5.23 (Nutzer: "auf die 24-Stunden-Prognose gedrueckt kommt die Regenbilanz der
letzten 30 Tage - da muss das kleine Fenster aufgehen"): `regenHeute.gross()`
oeffnet `kzStundenGross(H,gef,rest)` - dieselben 24 Stunden wie Kachel und
Abschnitt (`kzRegen24H`), 24 Saeulen auf Tag/Nacht-Hintergrund mit Sonne/Mond
(nicht auf dem Mitternachtsstrich), Skala links (volle Hoehe 1/2/gerade mm je
Stunde), Uhrzeiten alle 3 Stunden (Stundenbeginn), an Mitternacht der Wochentag;
Text: Summe 24 h, staerkste Stunde, "Heute bis 24 Uhr" (gleiche Zahlen wie die
Kachel, `regenHeute.zahlen()`), Hinweis Radar fuer die ersten 2 h. Knopf
"Regen je Stunde" -> `rainHrSec`. `gross()` darf jetzt {html,ziel,knopf}
liefern (regen7 weiter nur HTML, Knopf "Vorhersage"). Tag/Nacht gemeinsam in
`kzTagNacht(W0,W1)`. Geprueft mit eingespielter Open-Meteo-Antwort (Pruefstand
holt sie per curl; Chromium kommt zu langsam durchs Netz), hell und dunkel.
v5.24 (Nutzer: "bei der 2-Stunden-Kachel die Grafik, damit man sieht, ob es 2 Stunden
durchregnet oder nur 5 Minuten"): Kachel "Regen" bekommt, sobald in den 2 h Regen
kommt, die zweite Ansicht "Regen 2 h" (`kzNowGrafik(_kz.nowcast)`): die 25
Radarschritte als Balken, gleiche Regeln wie der Abschnitt `nowcastSec` (nass ab
roher TH, Hoehe = geeichte Bodenrate / max(Spitze, 0,5), erster Balken blass
unter der Jetzt-Schwelle), Strich und "1 h" bei +1 Stunde (mit hellem Saum, sonst
bei Dauerregen unlesbar). Bei "Trocken" bleibt es beim Zusatz `kzRegenDanach`.
Tipp springt weiter zum Abschnitt (der zeigt dieselben Balken gross).
v5.25 (Nutzer, Vorbild andere App: "Farbe der Balken nach der Regenmenge, mit
sinnvollen Stufen"): `regenFarbe(mm,tag)` / `regenLegende(tag)`, Farben
`REGEN_FARB` = die acht Stufen der Radarkarte (RK_STUFEN, deckend). STUNDEN
(Radar-Rate, Modell je Stunde): Schwellen wie die Karte 0,1/0,5/1/2/5/10/20/50
mm/h - Rot ab 20 liegt in DWD-Starkregen "markant" (15-25 l/m2 in 1 h), Violett
ab 50 ueber "extrem" (> 40). TAGE: eigene Schwellen 0,1/1/3/5/10/20/30/50 mm in
denselben Farben - Rot ab 30, Violett ab 50 = DWD-Dauerregen markant (30-50 l/m2
in 24 h) bzw. Unwetter. DWD-Schwellen per Websuche geprueft (nur Portale, nicht
dwd.de selbst; Stufe 2 dort einheitlich). Gefaerbt: Kacheln Regen 2 h, 24 h,
16 Tage; Abschnitte 2 h und 24 h (mit Legende); beide Grossansichten (mit
Legende). NICHT die Regenbilanz - dort heisst dunkel/hell gefallen/erwartet.
Unsichere Tage 8-16 blasser (.55 Kachel, .6 gross) - bei .4 waren Rot/Orange/
Violett nicht mehr zu trennen. Legende 16 Tage: "Rote Wochentage = Wochenende",
weil Rot jetzt auch 30 mm heisst. RK_STUFEN und REGEN_FARB gemeinsam aendern.
VARIANTENSEITE `farbtest.html` (Nutzer, 21.10.: "nicht so bunt, eher Farbverlauf,
ohne Gelb und Orange", Vorbild Screenshot einer anderen App - Balken Hellgruen ->
Gruen -> Stahlblau -> Blau -> Indigo -> Violett, Farbe an die Hoehe gekoppelt, Achse
Null/Gering/Mittel/Stark; welche App, liess sich per Websuche nicht klaeren). Sechs
Paletten mit je 8 Stufen an den Schwellen REGEN_STD/REGEN_TAG: A jetzt, B wie die
andere App (Farben aus dem Screenshot gemessen), C nur Blau, D Blau -> Violett,
E Tuerkis -> Blau -> Violett, F Blau mit Rot/Violett erst ab 20 mm/h bzw. 30 mm/Tag.
Umschalter Hell/Dunkel und Stufen/Fliessend (Fliessend = in log(mm) zwischen den
Stufen interpoliert), je Palette L* der Stufen. Beispieldaten, keine echten. Wahl
steht aus; mit ihr klaeren, ob die Radarkarte (RK_STUFEN) mitzieht.
v5.27 (Nutzer: "B, D, E in der echten App ansehen, zum Auswaehlen, spaeter eins
fest"): FARBTEST in der App. `REGEN_PAL` {A (= REGEN_FARB), B, D, E} mit den Farben
aus farbtest.html; unter JEDER Regenlegende (`regenLegende`: Abschnitte 2 h/24 h,
alle drei Grossansichten) die Zeile "Farbtest A B D E" mit Mini-Verlauf, gemerkt als
`regenPalette`. `regenFarbe` liefert `var(--rf0..7, Fallback A)`, `regenPalSetzen`
setzt die acht Variablen auf <html> - ein Tipp faerbt alles sofort um, auch die
offene Grossansicht, ohne neu zu zeichnen. Radarkarte bleibt A (RK_STUFEN
unveraendert); "wie auf der Radarkarte" (`.rpal-karte`) ist bei B/D/E per
`html[data-rpal]` ausgeblendet. Geprueft (Playwright, eingespielte Daten): Wechsel
in der Grossansicht, Fenster bleibt offen, Kacheln/Abschnitte folgen, Wahl ueberlebt
Neuladen, hell und dunkel. AUFRAEUMEN nach der Wahl: Gewinner in REGEN_FARB, `.rpal`,
`REGEN_PAL`, `regenPal*`, den Klick-Listener und die CSS-Regeln entfernen.
VORBILD-APP ENTSCHLUESSELT (21.10. 16:08, Nutzer-Screenshot Erlental/Wettenberg,
Reiter Wahrscheinlichkeit|Intensitaet|Regenradar|Wind - vermutlich "RegenVorschau"):
15-min-Balken, 2 h, Achse Null/Schwach/Mittel/Stark in Dritteln. Bright Sky
(radar_erl.json, 16:11 geholt) hat denselben Verlauf: 16:00-17:15 0,12 mm/h (kleinste
Radarstufe) -> dort Balken GENAU auf "Schwach" (1/3); 17:45 ~0,44 (15-min-Mittel) ->
0,427; 18:00 ~1,0 -> 0,567. Hoehenskala damit noch offen (log: Mittel ~2,4, Stark
~50 mm/h; linear: Mittel ~1,4) - braucht einen Screenshot mit >= 3 mm/h. FARBE ist
exakt eine Funktion der Hoehe, linear gemischt zwischen Ankern auf den Achslinien:
Schwach = teal (0,128,128), Mittel = blau (0,0,255) - gemessen auf 1 Einheit genau
(h 0,357/0,427/0,567 -> (0,119,136)/(0,92,163)/(0,38,217)); darueber Richtung Rot
~(212,34,43) bei Stark (aus dem Froendenberg-Bild, 2 Punkte) - die Violetttoene sind
Blau-Rot-Mischungen. Unter Schwach Gruen (nur JPEG, unsicher). Niesel 0,12 mm/h steht
dort auf 1/3 Hoehe, bei uns (Grossansicht, Skala 2) auf 6 %.
v5.28 (Nutzer: "eher E"): Palette E (Tuerkis -> Blau -> Violett) fest in
`REGEN_FARB`; Farbtest-Zeile, `REGEN_PAL`, `regenPal*`, CSS-Variablen `--rf*` und
`.rpal*` entfernt, ein gespeichertes `regenPalette` wird beim Start geloescht. Die
RADARKARTE behaelt ihre bunten Farben (RK_STUFEN): Tuerkis/Blau gingen auf dem
Satellitenbild (Wald, Wasser) unter - Balken und Karte haben seitdem verschiedene
Farben bei gleichen Schwellen, der Satz "wie auf der Radarkarte" ist weg. Kein
Gruen (Nutzer fragte): in der Vorbild-App steht Hellgruen fuer Werte UNTER der
kleinsten Radarstufe, bei uns ist das trocken. Offen: feste (log) Hoehe und
fliessende Farbe wie die Vorbild-App - Nutzer hat noch nicht entschieden.
ZWEITER SCREENSHOT (Frankfurt 16:26, Radar 16:29 geholt, radar_ffm.json): FARBE
an allen 9 Balken bestaetigt (teal -> blau bis Mittel, darueber blau -> rot, Rest
<= 2 Einheiten). HOEHE: von 5 Zuordnungen (Punkt, 15 min vor/um/nach, Max) passt
das Mittel der 15 min AB Balkenzeit am besten (Auswahl nach Guete - Vorsicht).
Gemeinsam mit Erlental (n=8, ohne Plateau): h = 0,551 + 0,321*log10(R), r2 0,88,
rmse 0,038 (linear r2 0,77, setzte "Stark" auf 4,7 mm/h - unplausibel). Damit
Schwach ~0,2 / Mittel ~2,3 / Stark ~25 mm/h, rund eine Dekade je Drittel (95 %:
Faktor 6-46). Dazu ein BODEN: 4 Frankfurter Balken mit 0,24-0,44 mm/h stehen genau
auf "Schwach" - erkannter Regen steht dort mindestens auf 1/3. Welcher Punkt
"Frankfurt" ist, weiss ich nicht (Zentrum 50,111/8,682 angenommen).
DRITTE RUNDE (21.10. 17:06, Ausgewertet erst 17:34 - Vorhersagelauf der App da
schon ersetzt): Die App heisst auf dem Home-Bildschirm "Regen?" (Pro) = RegenVorschau
Pro von CH-Software (App Store id327754661; Reiter Wahrscheinlichkeit, Intensitaet,
Regenradar mit Zugpfeil +1h/+2h, Wind). Beschreibung sagt nichts zur Berechnung.
WAHRSCHEINLICHKEIT (Kurve Huettenberg): ist NICHT der Anteil nasser Radarzellen im
Umkreis - gegen Radien 0,5-25 km und Schwellen 0,12-0,36 mm/h stets ~+20 Punkte
daneben (Radar 95-100 % nass, App 67-79 %). Form: ~98 % bis +15 min, Absturz auf
~67 % bei +25-30 min, dann flach 70-79 % -> vermutlich Vorlaufzeit-Vertrauen, nicht
Flaechenanteil. Ob sie in die BALKEN eingeht: nicht pruefbar, weil Kurve
(Huettenberg) und Balken (Frankfurt) verschiedene Orte sind. Dagegen spricht: die
Balken kleben 45-75 min EXAKT auf "Schwach", waehrend die Kurve 67-99 % durchlaeuft.
Naechster Test: beide Reiter fuer DENSELBEN Ort zur selben Minute. Auf ihrer KARTE
ist Gruen die schwaechste Regenstufe; in den Balken liegt dieselbe Stufe auf Tuerkis
("Schwach"), Gruen nur darunter.
VIERTE RUNDE (21.10. 18:09, beide Reiter fuer Frankfurt UND Erlental, Radar 18:10
geholt - radar_ffm3/erl3.json): Wahrscheinlichkeit P und Balkenhoehe h sind eine
FESTE Funktion voneinander: P = 25 + 135*h bis "Schwach", darueber 70 + 82*(h-1/3);
16 Paare an beiden Orten, Rest <= 1,8 Punkte (Null = 25 %, Schwach = 70 %, Mittel
~97 %). Beide Reiter zeigen also DIESELBE Groesse in zwei Skalen; P saettigt bei
100 %, die Balken gehen darueber hinaus (Froendenberg 0,83). Und die Balken sind
KEINE reine mm/h-Skala: Bright Sky ~0,7 mm/h ergab in Erlental "Mittel", in
Frankfurt "Schwach"; Erlental 18:50 Einbruch auf Schwach bei 0,96 mm/h im Radar.
Die log-Eichung oben (Schwach 0,2 / Mittel 2,3 / Stark 25) ist damit HINFAELLIG.
Unter Schwach wird gemischt Gruen (0,255,0) bei Null -> teal; gemessen (0,157,98)
bei h 0,257 und (0,222,33) bei 0,087. Unter Schwach liegen Balken nur am Rand eines
Regengebiets (P < 70 %). Nicht weiter verfolgen, solange wir nichts uebernehmen.
FUENFTE RUNDE (21.10. 20:26, beide Reiter fuer Frankfurt, Erlental, Huettenberg):
die Formel von 18:09 gilt NICHT fest - P lag 3-14 Punkte darunter. Linear bis
"Schwach": 18:09 P = 24,5 + 134*h (rmse 0,7), 20:26 P = 15,0 + 147*h (rmse 2,6,
je Ort 12,9 / 15,3 / 16,1 Grundwert). Die STEIGUNG bleibt (~45-50 Punkte je
Drittel), der GRUNDWERT wandert mit der Lage (flaechiger Regen 25 %, ausklingende
Schauer ~15 %) und ist innerhalb eines Laufs an allen drei Orten gleich. Trockene
Balken (h = 0) haben 12-16 %, nicht 25 %. Also: P = Grundwert der Lage + Anteil aus
demselben Wert wie der Balken; der Balken selbst kennt den Grundwert nicht.
Herkunft des Grundwerts unbekannt (Vermutung: Modell- oder Flaechenwert).
v5.29 (Nutzer-Screenshot 20:28: "0,1 auf grau (Nacht) kann man kaum erkennen"):
gemessen (WCAG-Kontrast) hellste Stufe (160,230,220) auf hellem Nachtgrund 1,07:1,
auf Weiss 1,41, Tag 1,30. Dunklere Stufen allein brachten nur ~1,4 (Nachtgrund und
Tuerkis sind fast gleich hell). Jetzt im HELLEN Modus eine feine Kontur um jeden
Regenbalken und die Legendenfelder (inset 1px rgba(0,60,80,.22); .kzs-bb, .kzg-a,
Kachelbalken, .nowcard .bar, .rleg i), Farben E unveraendert. Varianten verglichen
(kontrast_varianten.png: A jetzt, B dunklere Hellstufen, C Kontur, D beides) - C
gewaehlt, weil es die vom Nutzer gewaehlten Farben laesst. Dunkler Modus ohne Kontur
(hellste Stufe dort 9:1); dort sind eher die violetten Stufen schwach (1,7-2,0:1).
v5.30 (Nutzer: "alle Kombinationen selbst kontrollieren", 16 Tage "Regenmenge
obendrueber zu eng - links daneben", "in den Grafikfenstern nur Schliessen"):
(1) KONTRASTPRUEFUNG aller 8 Stufen gegen 12 Hintergruende (Grossansicht hell/dunkel
x weiss/Tag/Nacht, Kachel hell/dunkel x Nacht, Abschnitt, unsicher .6): schwach waren
hell die Stufen 0-1 (1,04-1,5:1, seit v5.29 Kontur) und DUNKEL die Stufen 4-7 auf
Nachtgrund 1,5-2,1:1, unsicher .6 1,5-1,7:1 -> im dunklen Modus jetzt helle Kontur
(inset 1px rgba(255,255,255,.22)). Nachbarstufen 4/5/6 sind gleich hell (1,08-1,2:1),
unterscheiden sich nur im Farbton. Visuell geprueft: alle Stufen in 2 h, 24 h (Tag und
Nacht), 16 Tage (sicher und unsicher), Kacheln, hell und dunkel.
(2) `kzTageGross`: Skala links (Hilfslinien halbe/volle Hoehe, 10 mm, sonst naechste
Zehnerstufe; `.kzg-pl` 24 px Rand, `.kzg-gr` im Saeulenbereich) statt Zahlen ueber den
Saeulen; Wochentag 9,5 px (<= 350 px Breite 8 px) - bei 375 pt sonst 0,8 px zu breit,
gemessen per Range: 320/375/430 pt passen jetzt.
(3) `kzGrossZeigen(html)`: nur noch "Schliessen" (volle Breite); ziel/knopf aus gross()
werden nicht mehr benutzt.
(4) 24-h-Grossansicht: Skala glatt 1/2/5/10/20... wie bei 2 h (vorher ceil(mx/2)*2 =
"56 / 28"), 2,5 nicht mehr als "3".
v5.31 (Nutzer: "zwei Kacheln Regen bis 24 Uhr und Regen naechste 24 Stunden -
brauchen wir nur eine?"): `regen24` ist ENTFERNT (Pool, KZ_DEF, KZ_QUELLE). Neben
`regenHeute` brachte es nichts Eigenes: dieselben 24 Stundenbalken, dieselbe 24-h-
Summe ("~2,6 mm" = Ueberschrift "24 h 2,6 mm"), und der Beginn "ab 16:00" steht als
Zusatz in der Kachel "Regen" (`kzRegenDanach`) - den schaltete regen24 sogar AB,
solange es gewaehlt war. Dazu tippte regen24 zum Abschnitt statt die Grossansicht zu
oeffnen. Migration bei jedem Start (ohne Marke): beide gewaehlt -> regen24 raus, nur
regen24 -> an seine Stelle regenHeute. `kzRegenDanach` laeuft jetzt immer. Geprueft
(Playwright): drei gespeicherte Auswahlen, Pool ohne "Regen · naechste 24 Std",
Kachel "Regen" Trocken <-> "ab 13:00 / heute 70 %". Zurueckholen aus
`wetter-giessen-v5_30.html`.
v5.32 (Nutzer: "Regen in 24 Stunden macht mehr Sinn, weil die Grafik auch 24 Stunden
zeigt und nicht bis 24 Uhr"): v5.31 UMGEKEHRT - `regen24` ist wieder DIE 24-h-Kachel
(in `KZ_STD`), `regenHeute` ("Bis 24 Uhr") ist entfernt. Der Kalendertag ("Heute bis 24
Uhr X mm, davon Y gefallen") steht nur noch in der Grossansicht, die jetzt `regen24`
oeffnet (`kzRegenTagZahlen()`). Im Vergleichsbild sprach dafuer: "Bis 24 Uhr 0,4 mm
gefallen" neben Balken, die nur morgen Regen zeigen. `kzRegenDanach` ist wieder aus,
solange regen24 gewaehlt ist (v4.77). Migration bei jedem Start: regenHeute -> regen24
an derselben Stelle; beide gewaehlt -> Platz von regenHeute frei.
FREIE PLAETZE (Nutzer: "Kacheln irgendwo hin, und sie muessen dort bleiben, wo ich sie
hinsetze"): `_kzWahl` ist eine Liste von Plaetzen, `null` = frei (`kzSlots()`: unbekannte
Kacheln -> null, freie Plaetze am Ende weg). Minus laesst den Platz frei, "+" setzt in den
ersten freien Platz, Ziehen auf einen freien Platz verschiebt, auf eine Kachel TAUSCHT.
Ausgefuehrt wird erst beim LOSLASSEN (`_kzDrag.ziel`, Markierung `.kzziel`) - ein Tausch
bei jedem Ueberfahren haette die Kacheln entlang des Fingerwegs verschoben. Im
Bearbeiten gestrichelte freie Plaetze (`.kzleer`) bis Reihenende, bei voller Reihe eine
neue Reihe. Ausserhalb unsichtbar, eine Luecke bleibt als Luecke stehen.
PAUSE (Nutzer: "die Grafiken kurz laenger angucken"): Knopf rechts in der Fusszeile neben
"Kacheln waehlen", nur bei "Auto + Wischen" und wechselnden Kacheln. `_kzPause` haelt
den Takt an (Wischen geht weiter), angehalten dunkler Knopf "Weiter". Nicht gespeichert -
nach Neuladen laeuft der Takt wieder. Symbole als SVG (U+23F8 wird am iPhone ein Emoji).
Geprueft (Playwright, Maus): Migration, Entfernen, Verschieben in freien Platz, Tausch,
"+" in die Luecke, Pause 9 s ohne Wechsel, hell und dunkel. Am iPhone nicht geprueft.
v5.33 (Nutzer-Screenshot 09:44: "beim ersten Mal koennte man erwarten, die Grafik geht
von 0 bis 24 Uhr - umstellen oder 'jetzt' mit Pfeil an den Start"): Pfeil, NICHT 0-24 Uhr -
Kachel, Summe und Abschnitt rechnen ab jetzt, und abends zeigte eine 0-24-Grafik fast nur
Vergangenheit. Beide Grossansichten (24 h und 2 h) beschriften den Start mit "jetzt ->"
(`.kzs-jz`, fett, linksbuendig wie `.kzs-x0`); der Abschnitt "Regen je Stunde" hatte
"jetzt" schon. `kzAchseFrei(root)` blendet danach jede Achsbeschriftung aus, die an die
vorige stoesst (gemessen per getBoundingClientRect, NACH dem Einblenden - im verborgenen
Fenster ist alles 0 breit). Stoesst der Wochentag an "jetzt ->", faellt zuerst der Pfeil
(21:40: "jetzt  Fr" ab 375 pt), reicht das nicht (23:20, Mitternacht in Spalte 2), bleibt
der Pfeil und der Wochentag faellt weg - der Mitternachtsstrich bleibt. Geprueft 09:44 /
21:40 / 23:20 bei 320 / 375 / 430 pt (Playwright mit verstellter Uhr).
v5.34 (Nutzer: "der Pfeil soll auf jetzt ZEIGEN, nicht nach rechts - von oben auf die
Achse bzw. auf die Saeule; vielleicht hast du eine bessere Idee"): "jetzt ->" ist weg.
TEST in beiden Grossansichten (24 h und 2 h), Zeile "Test jetzt: A B C" unter der
Legende, gemerkt als `kzJetztStil` (Voreinstellung A): A Dreieck + "jetzt" von oben auf
die Saeule der laufenden Stunde bzw. auf die Achse (Nutzervorschlag), B roter Strich
durchs Bild mit Dreieck + "jetzt" ueber dem Bild, C Dreieck von unten an der Achse mit
"jetzt" daneben. x = GENAUE Uhrzeit (09:44 = 73 % der ersten Stunde), nicht der
Spaltenbeginn. Alle drei stehen im HTML (`kzJetztMarke(x,h)`), CSS zeigt die gewaehlte
(`#kzGrossIn[data-jz]`), Umschalten ohne Neuzeichnen (`kzJzSetzen`, misst die Achse neu).
Farbe Rot #d23a3a (Rot kommt in Palette E nicht vor). Grafik 20 px tiefer gesetzt
(Platz fuer A/B oben). Befund im Test: A legt "jetzt" ueber die Nachbarsaeulen, wenn es
regnet, und springt mit der Saeulenhoehe; B und C stoeren nicht. AUFRAEUMEN nach der
Wahl: `kzJzStil`, `kzJzSetzen`, die beiden anderen Varianten, `.kzjzw`, Klick-Listener
in `kzGrossZeigen` und die CSS-Regeln.
v5.35 (Nutzer waehlt B: "den jetzigen Zeitpunkt haben wir schon oft mit Strichen
markiert"): in beiden Grossansichten nur noch der rote Strich an der genauen Uhrzeit
(`.kzjzl`) mit Dreieck + "jetzt" ueber dem Bild (`.kzjz`, `kzJetztMarke(x)`). A, C,
Testzeile, `kzJzStil`/`kzJzSetzen` und CSS entfernt, gespeichertes `kzJetztStil` wird
beim Start geloescht. Nebenbei: "staerkste Stunde" nennt den Wochentag, wenn sie nicht
heute liegt (10:05: "Fr 07-08 Uhr" - vorher las sich "08-09 Uhr" wie die vergangene
Stunde von heute); "~0,2 mm" bricht nicht mehr zwischen Zahl und Einheit um.
Beobachtung aus dem Nutzer-Screenshot 10:05: die erste 24-h-Spalte ist die gerade
ABGELAUFENE Stunde (09-10, Fenster ab jetzt - 30 min, v5.09) - der Strich steht deshalb
am Anfang der ZWEITEN Spalte. Genau dafuer ist er gut.
v5.36 (Nutzer-Screenshots 23.10. 16:29: "nicht synchron - einmal kommt der staerkere
Regen, einmal ist er schon vorbei"): Das 24-h-Fenster begann seit v5.09 bei jetzt - 30 min.
Von :00 bis :30 war die erste Saeule damit die ABGELAUFENE Stunde - mit dem MODELLwert:
16:29 "staerkste Stunde 15-16 Uhr (1,0 mm)", das Radar zeigte den Regen erst ab 16:50
(Modell eine Stunde zu frueh). Und "24 Stunden ab jetzt" zaehlte diese Vergangenheit mit.
Jetzt `regen24Stunden(h)` fuer Kachel, Grossansicht UND Abschnitt "Regen je Stunde":
Stempel > jetzt (erste Saeule = laufende Stunde), die laufende Stunde zaehlt erst ab
jetzt (`regenIntervall(max(Beginn,jetzt), Ende, Modell)`). `regenBeginn(H,fr)`: genauer
Beginn = erster nasser Radarschritt; Radar dort trocken -> Ende des Radarfensters; sonst
Stundenbeginn. Kachel "ab 16:45" statt "jetzt" fuer die ganze laufende Stunde, Abschnitt
"Regen ab 16:45 Uhr" statt "Regen aktuell". Grossansicht: "Ab jetzt bis Sa 16 Uhr 2,7 mm"
(das Fenster endet mit der vollen Stunde, also 23-24 h), Legende "erste Saeule: Rest der
laufenden Stunde", links vom jetzt-Strich grau = schon vorbei (`.kzjzv`). 2-h-Text:
Zahl und Einheit mit festem Leerzeichen ("1,5 mm/h"). Geprueft 16:29 und 16:05 mit
nachgebautem Fall (Modell 15-16 Uhr 1,0 mm, Radar trocken bis 16:45).
v5.37 (Nutzer, 16:38: "grauer Balken bei der aktuellen Zeit - wozu?"): das Grau
"schon vorbei" links vom jetzt-Strich (`.kzjzv`, v5.36) ist wieder entfernt. Es war
ein dritter Hintergrundton neben Tag gelb / Nacht blau ohne eigene Legende und sah
nach Daten aus; der rote Strich und "erste Saeule: Rest der laufenden Stunde"
genuegen. Bekannte Kante: Ein einzelner nasser Radarschritt am Ende der laufenden
Stunde (16:55, 0,03 mm) bleibt unter der 0,1-mm-Stundenschwelle - die Kachel sagt dann
"ab 17:00", die 2-h-Kachel "in 20 min".
v5.38 (Nutzer: "nichts weniger stark zeichnen in den 24 Stunden - aber weitere 24
Stunden zum Rueberscrollen, blass, ob ueberhaupt Regen kommt"; Mond hinter der Saeule
beheben): Grossansicht von "Regen 24 h" zeigt 48 Stunden (`regen24Stunden(h,48)`,
Stundenabfrage jetzt `forecast_days=3`), sichtbar 24,4 Stunden, Rest per Wischen
(`.kzs-sr` overflow-x, Inhalt `.kzs-in` N/24,4 breit). Skala links fest (`.kzs-yl`
ausserhalb des Scrollbereichs). Stunde 25-48 blass (`.kzs-bb i.un`, .5), gestrichelte
Grenze `.kzs-ab` mit "unsicherer" darueber. Skala ueber ALLE 48 Stunden (Hoehen beim
Scrollen vergleichbar; Folge: kommt danach mehr Regen, werden die ersten 24 flacher).
Text: zusaetzlich "Danach bis So 17 Uhr ~5,7 mm (unsicherer)" bzw. "trocken"; Legende
"nach links wischen: die 24 Stunden danach". Mitternachtsstriche jetzt alle (vorher nur
der erste), `kzTagNacht` rechnet Sonnenzeiten bis +3 Tage. Sonne/Mond liegen VOR den
Saeulen (`.kzs-s`, Kachel `.kzbs`: z-index 3) - in Norden 23.10. 18:44 steckte der Mond
hinter einer 2-mm-Saeule. Kachel und Abschnitt bleiben bei 24 Stunden.
SOMMERZEIT-FALLE (dabei gefunden): Open-Meteo liefert die Zeiten mit EINEM festen
Versatz (`utc_offset_seconds`) fuer die ganze Antwort - am 23.10. 96 Stunden fuer
23.-26.10., obwohl der 25.10. 25 Stunden hat, keine doppelte 2-Uhr-Stunde. Der Browser
las "2026-10-25T03:00" als MEZ: alles nach der Umstellung eine Stunde zu spaet.
`omZeitenAbsolut(d)` haengt den Versatz an ("...T03:00:00+02:00"), bisher NUR fuer die
Stundenabfrage Regen/Wolken (Kachel 24 h, Abschnitt, Grossansicht, bilanzRest,
kzRegenDanach, Wolkenschichten). Andere Open-Meteo-Abfragen (Luft/UV, Wolkenkarte,
ISS-Wolken ...) haben dasselbe Muster und sind zweimal im Jahr fuer bis zu ~2 Tage
eine Stunde versetzt - offen. Geprueft mit Uhr 23.10. 18:44 und Zeiten im Open-Meteo-
Format (+02:00): 48 Stunden enden "So 17 Uhr" (die Nacht hat 25 Stunden), 320/375 pt,
hell und dunkel, gescrollt.
v5.39 (Nutzer: "die anderen Regenradare haben grauen Untergrund, bei uns ist der
schwaechste Regen blaugrau auf gruen" -> "bau den Umschalter zum Ausprobieren"): TEST
"Untergrund (Test): Satellit | Relief | Grau" unter der Regenkarte (`#rkGrund`, gemerkt
`rk_grund`, Voreinstellung Satellit). `RK_GRUND`: Satellit = WOLK_TILE wie bisher;
Relief = Esri World_Hillshade (`services.arcgisonline.com/.../Elevation/World_Hillshade`),
in der Ebene fast weiss, darum je Kachel per `multiply` mit #d3d7dc grau getoent (wie
WetterOnline); Grau = keine Kacheln, Flaeche #cdd2d8, nur Grenzen und Orte (wie "Regen?",
ohne Esri - der Lizenzpunkt in LIZENZEN.md fiele fuer die Regenkarte weg). Auf Grau sind
die Regenfarben deckend (Alpha >= .92), Legende ebenso (`leg.dataset.grau`); auf dem
Satelliten wie bisher durchscheinend. Hintergrund-Cache-Schluessel enthaelt den Untergrund.
Quellvermerk "Untergrund: Esri" nur bei Satellit/Relief. Wolkenkarte unveraendert
(Satellit). Geprueft mit ECHTEN Daten (Bright-Sky-Radar und Esri-Kacheln ueber
`netz.py` im Scratchpad, 23.10. 20:05), hell und dunkel. AUFRAEUMEN nach der Wahl:
Gewinner fest, `rkGrund`, `.rk-grund`, Klick-Listener, Test-Zeile.
v5.40 (Nutzer, Vergleich 20:45 mit WetterOnline und "Regen?": "das Grau ist bei den
anderen dunkler, wir haben mehr Wolken, deren Farben sind besser zu erkennen"). GEMESSEN
in den Bildschirmfotos: WetterOnline Grau ~190, schwaechste Stufe Cyan (170,254,255);
"Regen?" Grund (193,202,210), Gruen (0,255,0); unser Relief-Grau ~(208,212,215) und
Hellblau (150,205,255) - das Hellblau hat fast dieselbe Helligkeit wie ein Grau um 190
(L* ~80 gegen ~77), darum verschwand es. Flaechenanteil "Regen" im Bild: wir 50 %,
WetterOnline (Mitte) 27 %. Bright Sky 20:50, 120x120 km: 62 % nass, davon 51
Prozentpunkte roh 1 = 0,12 mm/h (kleinste Radarstufe), ab 0,24 mm/h nur 11 %.
Aenderungen: Grau dunkler (Relief multiply #bcc0c5, flach #bfc4ca, ~190), auf Grau eigene
Palette `RK_GRAU_RGBA` (0,1 helles Cyan 165,248,255 - HELLER als der Grund; 0,5 80,175,250;
Rest wie gehabt, deckend), Legende folgt. Zweite Testzeile "Kleinste Stufe: zeigen |
blass | aus" (`rk_schwach`, roh < 0,2 = roh 1; blass = Deckkraft .4) - NUR die Karte,
Balken/Kachel "Regen 2 h" bleiben bei 0,1. Satellit unveraendert. Geprueft mit echten
Daten (20:50), 375 pt einzeilig, 320 pt bricht die erste Zeile um.
v5.41 (Nutzer: "auf jeden Fall blass oder aus, nicht mit Gelb/Gruen, eher die andere
Farbskala, zum Umschalten - ich teste die naechsten Tage"): dritte Testzeile "Farben:
Verlauf | Bunt" (`rk_farbe`, `rkFarbe()`, `rkPalette(grau)`), Voreinstellung VERLAUF =
Palette E der Balken (`REGEN_FARB` -> `RK_E_RGBA`, gleiche Schwellen wie RK_STUFEN), auf
Grau deckend, auf dem Satelliten 85 %. "Bunt" = bisher (RK_RGBA / RK_GRAU_RGBA). Kleinste
Stufe nur noch "blass | aus", Voreinstellung blass; ein gespeichertes "zeigen" gilt als
blass. Drei Zeilen (Untergrund / Farben / Kleinste Stufe) - in zwei brach "aus" bei 390 pt
um. Legende folgt Untergrund UND Farbe. Gemessen: E 0,1 (160,230,220) L* 87 und E 0,5
L* 75 liegen nahe am Grau (L* 79, Kontrast 1,24 bzw. 1,14) - sie heben sich ueber den
Farbton ab, nicht ueber die Helligkeit; das Cyan von "Bunt" hat 1,46. Geprueft mit echten
Daten (21:15, Bright Sky + Eichung), Grau/Relief/Satellit. AUFRAEUMEN nach der Wahl:
Verlierer-Palette, `rk_farbe`-Zeile, ggf. `rk_schwach`/`rk_grund`.
v5.42 (Nutzer, Screenshot "Regen?" 18:07: "Pfeil in der Mitte des Punkts enden lassen
statt dahinter"): Die Spitze des Zugpfeils endet AM Standort - die weisse Spitze reicht bis
an den weissen Ring des Punkts (`R0` = 8 px vor der Mitte), die dunkle Kontur darunter;
vorher lief der Pfeil durch den Punkt und endete 27 px dahinter. Nicht exakt in der Mitte:
der Punkt liegt obenauf und haette die Spitze verdeckt. Reihenfolge jetzt Hof (rot, 22 %) ->
Pfeil -> Punkt, damit der Hof die Spitze nicht rosa toent. Zeitstriche unter 42 px vor der
Mitte (stiessen an die Spitze, 8-26 px) und keine 24 px hinter dem vorigen (Beschriftungen
ueberlappten, z. B. 6 km/h "1 h 2 h 3 h 4 h") entfallen - nur bei langsamem Zug. Ohne Strich
ist der Pfeil mindestens 48 px lang. Freiflaechen fuer die Orte folgen der neuen Lage (der
Ort hinter dem Punkt, z. B. "Giessen", erscheint wieder). Geprueft mit echtem Zug (44 km/h
nach 73 Grad, 24.10. 18:10) und gesetzten 6/25/57/110 km/h. BEWUSST SO GELASSEN (Nutzer:
"macht nichts, wenn es drunter steht - besser als drueber"): kommt der Regen aus N/NO, kann
eine Strichbeschriftung unter dem Zeitkasten oben rechts liegen. Nicht "reparieren".
v5.44 RASEN-PLANER (Nutzer 25.10.: Erinnerung zum Rasenmaehen; "erst mal integrieren", Kachel
mit dem Wichtigsten, Tipp oeffnet ein Fenster, Einstellungen separat). Vorlauf: Testseite
`rasentest.html` (bleibt, mit Beispiel-Lagen und simulierten Nachrichten). In der App: Kachel
`rasen` ("Rasen maehen", NICHT in KZ_STD; Bestandsnutzer einmalig per `kzRasenNeu` angehaengt),
Ansicht 1 "RASEN trocken/nass/weich/Tau + seit/bis", Ansicht 2 "MAEHEN heute|morgen|Mi 28. +
09-17 Uhr", Ansicht 3 "DANACH nass bis Sa", wenn danach >= 2 Tage kein Fenster kommt. Tipp ->
`rzGross()` (kzGrossZeigen + neues Feld `nach` = Knoepfe verdrahten): Gras jetzt, Empfehlung,
"Heute gemaeht", "Einstellungen" (Regler zeichnen erst beim Loslassen neu), Stundenleiste
gestern..+6 Tage (Kaestchen antippen = Werte). Code-Block `RASEN`/`rz*` vor KZ_DEF, CSS `.rz-*`.
Speicher `rasen` (beim ersten Mal aus `rasenTest` der Testseite uebernommen).
DATEN (eigene Abrufe, nur wenn die Kachel gewaehlt ist, alle 30 min bzw. bei Ortswechsel):
Open-Meteo stuendlich past_days=14/forecast_days=8/timeformat=unixtime (Rueckfall: Bright Sky
MOSMIX, Luftfeuchte aus Taupunkt); Messungen der naechsten DWD-Station 74 h (Bright Sky
/weather, nur observation_type != forecast) ueberschreiben die Modellstunden; Radar am Ort
(Bright Sky /radar 3 km, Mittelzelle) fuellt die Stunden seit der letzten Messung und 2 h
voraus. Anlass: 25.10. MOSMIX meldete fuer 13-14 Uhr 2 mm, Station und Radar blieben trocken.
REGELN (geschaetzt, nicht belegt - am Garten nachpruefen): Regen >= 0,1 mm/h nass; Abtrocknen
2/3/5/8 h nach <0,5/<2/<5/mehr mm in 6 h, Sonne/Wind >= 15 km/h doppelt, Luftfeuchte ueber der
Tau-Grenze halb so schnell; nach >= 10 mm in 24 h Boden 18 h weich (>= 25 mm: 24 h); Tau ab 90 %
Luftfeuchte; zu kalt unter 4 Grad. Erlaubt Mo-Sa in der Maehzeit (Voreinstellung 9-19),
nur bei Tageslicht (Sonnenzeiten Open-Meteo bzw. eigene Formel, gegen PyEphem 1 min), nie an
Sonn- und Feiertagen (bundesweit + Fronleichnam; 32. BImSchV laut Ratgebern Mo-Sa 7-20 Uhr).
Fenster = zusammenhaengende gute Stunden >= Dauer, Sicherheit 1 - max. Regenrisiko. Empfehlung
= hoechste Sicherheit vor der Frist mit 5 % Abschlag je Tag Vorlauf (Optimal Stopping: gut heute
schlaegt besser in 4 Tagen); "Gras ist schon hoch" oder unbekanntes Datum = erste gute
Gelegenheit, hohes Gras trocknet 50 % langsamer und ist 5 % frueher taunass. Faellig nach Tagen
oder nach Wuchs (Gradtage ueber 5 Grad). OFFEN: Erinnerung aufs Handy - Kanal nicht gewaehlt
(ntfy: App plant beim Oeffnen zeitversetzte Nachrichten, bis 3 Tage, ersetzbar; oder Web-Push mit
Service Worker); zweite Stufe waere eine GitHub-Schleife, die bei Vorhersageaenderung korrigiert.
Geprueft (Playwright, 25.10. 14:4x): Bestandsauswahl bekommt "rasen", Bright-Sky-Rueckfall und
Open-Meteo-Weg (nachgebaute Antwort), Kachel nass/bis 17 Uhr <-> morgen 9-17 Uhr, Fenster,
Regler speichert, Heute gemaeht setzt die Frist neu, hell und dunkel, 390 pt.
v5.45 (Nutzer: "eventuell noch eine Mittagspause einplanen"): MITTAGSPAUSE einstellbar
(`pause`, `pVon`, `pBis`), Voreinstellung AN 13-15 Uhr; ersetzt den festen Schalter `mittag`
(Mittagsruhe 13-15, Voreinstellung aus) aus v5.44, ein gespeichertes `mittag` wird verworfen.
Rechtslage: in Hessen KEINE Pflicht - die Laermschutzverordnung des Landes ist seit 01.01.2005
aufgehoben; "aus Ruecksicht auf die Nachbarn" sollen 13-15 Uhr moeglichst nur unaufschiebbare
Arbeiten laufen (Infoblatt Laermschutz der Stadt Neu-Anspach, gelesen); eine eigene Satzung von
Wettenberg fand die Websuche nicht. Pausenstunden zaehlen als "nicht deine Zeit", ein Fenster
wird dort geteilt (9-13 und 15-17). Dabei behoben (seit v5.44): im Fenster (.loc-box) griff
`.loc-box input` (volle Breite, appearance:none, Feldrahmen) - Haekchen waren unsichtbar,
Regler dicke Kaesten; jetzt `.loc-box .rz input[type=...]` mit normalen Bedienelementen.
v5.46 (Nutzer-Screenshot v5.44: "Regler kaum zu erkennen und viel zu hoch"; "Gradtage ist ein
komischer Begriff"): Regler im Rasen-Fenster jetzt EIGENE flache Form (`.loc-box .rz
input[type=range]`): 28 px Flaeche, 5-px-Bahn mit blauer Fuellung bis zum Knopf (CSS-Variable `--p`,
gesetzt in `rzEinstHtml` und in `oninput` per `rzP`), weisser 24-px-Knopf mit Schatten, hell und
dunkel - nicht mehr die System-Regler (v5.45), deren Aussehen am iPhone nicht pruefbar war.
"Gradtage" ist weg: im Wuchs-Modus stellt man den "Abstand bei 15 Grad" in ganzen Tagen ein
(intern weiter `gd` = Tage x 10, Waermesumme der Tagesmittel ueber 5 Grad; gespeicherte Werte auf
Zehner gerundet), darunter "bei 10 Grad 12 Tage, bei 20 Grad 4 Tage". Im Fenster "seither gewachsen:
48 %" statt "34 von 60 Gradtagen"; nicht faellig in der Vorhersage -> Kachel "Maehen / spaeter /
waechst kaum" statt "kein Fenster". Testseite rasentest.html gleich umbenannt.
v5.47 (Nutzer: bei "Heute gemaeht" erkennen, ob man getippt hat, und ein kleines X zum Loeschen):
nach dem Tipp steht statt des Knopfs ein gruenes Feld "Heute gemaeht" mit rundem x (`.rz-ok`,
`data-rzk="zurueck"`); x stellt Datum UND "Gras ist schon hoch" von davor wieder her (gemerkt in
`E.vor`; ohne Vorwert: Datum unbekannt). Erkennbar bleibt es, solange "zuletzt gemaeht" = heute.
Bei 320 pt bricht "Einstellungen" in eine eigene Zeile um (`.rz .loc-row` flex-wrap). Dabei:
Abtrocknungs-Etappen brechen bei neuem Regen ab ("... wieder Regen ab 16 Uhr.") statt "Regen
vorbei ab 11 Uhr - wieder Regen ab 12 Uhr" zu reihen (Nutzer-Screenshot v5.44), kein "...." mehr.
v5.48 (Nutzer, So 25.10. 15:00, Kachel "RASEN nass bis 17 Uhr": "irrelevant, heute ist
Sonntag, sowieso kein Maehen erlaubt"): `rzHeuteFrei()` liefert "" solange heute noch eine
ERLAUBTE Stunde kommt (`c.erlaubt`, Ende > jetzt + 15 min), sonst den Grund ("Sonntag",
Feiertagsname, "kein Maehtag", "vorbei"). Ist er gesetzt, zeigt die Kachel nur die naechste
Gelegenheit ("MAEHEN morgen 9-13 Uhr", ggf. im Wechsel "Danach nass") - den Zustand des
Grases nicht. Das Fenster sagt unter "Maehen" "Heute kein Maehen - Sonntag." bzw. "Fuer heute
ist die Maehzeit vorbei."; der Abschnitt "Gras jetzt" bleibt (fuer morgen nuetzlich).
Geprueft So 15:06 echt sowie Mo 10:00 (Zustand + Maehen heute), Mo 16:50 ("vorbei", Sonne
17:13), Di 07:00 (Tau bis 9 Uhr + heute 9-13).
v5.49 (Nutzer-Screenshots 25.10. 15:03, Norden: "Heute gemaeht" an/aus laesst die Anzeige springen, beide
Ansichten passen nicht aufs Display): Rasen-Fenster umgebaut. (1) Knoepfe "Heute gemaeht" / "Einstellungen"
DIREKT unter der Ueberschrift "Maehen" - darueber aendert sich beim Tippen nichts, der Knopf bleibt unter dem
Finger (vorher 17 px Sprung). Darunter immer drei Zeilen (`rzMaehHtml`: Stand / Termin / Begruendung);
`rzMaehAlt()` rechnet beim Oeffnen den ANDEREN Zustand mit, `rzGrossBinden` setzt `.rz-m` auf die groessere
Hoehe (`RASEN.mMin`, beim Oeffnen 0) - Leiste und Quelle stehen in allen Zustaenden auf demselben Pixel
(gemessen 320/375/393 pt). Knopfreihe als Grid 1,12fr/1fr (beide Zustaende gleich breit), unter 360 pt
untereinander. (2) Kompakter: Kopf "Rasen" + Ort/Stand in einer Zeile, "Heute kein Maehen - Sonntag" als Zusatz
in der Ueberschrift, "Naechster Regen" entfaellt, wenn die Etappen schon mit "wieder Regen" enden, Hinweis
"Kaestchen antippen = Werte" in der Leistenueberschrift, die Werte erscheinen als Blase UEBER der Zeile (statt im
Fluss - die schob Legende und Quelle), Leistenzeilen fest 18 px, Quelle kuerzer ("geschaetzt" statt "gerechnet").
393 x 779 (= iPhone 15/16 Pro nach Statusleiste): 874-894 px Inhalt -> 728-743, sichtbar 759. (3) ALLE Fenster
(`.loc-ovl`, auch Standort-Dialog): Abstand oben = Statusleiste + 8 px (env(safe-area-inset-top)) - wegen
viewport-fit=cover lag der obere Rand des Fensters unter der Statusleiste, "Rasen" war dort verdeckt. Unten
Home-Balken - 8 px. Am iPhone nicht geprueft (Chromium kennt die Raender nicht, gerechnet mit 59/34 pt).
v5.26 (Nutzer: "auf Regen jetzt tippen soll das Diagramm oben aufgehen, nicht nach
unten verweisen"): `regen.gross()` -> `kzNowGross(_kz.nowcast)`: die 25 Radarschritte
gross, FESTE Skala 1/2/5/10... mm/h (nicht relativ zur Spitze wie in Kachel und
Abschnitt - gross ist Platz fuer eine Achse), Farben `regenFarbe`, Uhrzeiten alle
30 min ("jetzt" linksbuendig), Tag/Nacht-Hintergrund, Text = Ueberschrift und Zeile
des Abschnitts (`_kz.nowcast.summary/detail`, neu mitgegeben) plus "In den 2 Stunden
40 min Regen, zusammen ~1,1 mm" bzw. "Durchgehend Regen". Knopf "Radarkarte" ->
`radarSec`. Auch bei "Trocken" geht das Fenster auf (flache Linie, Text "Kein Regen").
