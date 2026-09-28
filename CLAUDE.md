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
Zugeklappt ist die Voreinstellung; der Zustand steht je Abschnitt im Geraet
(`klapp_<name>`).

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
mit weg. Der Balken "Niederschlag 2 Std" nutzt eine eigene 1-km-Abfrage und
ist NICHT gefiltert - stuende ein Scheinecho genau ueber einem Ort, zeigte
er Regen.

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
366 Tage dominieren sie alles andere. Die vorhandene UV->=3-Rechnung in
`vitdJahr` braucht deshalb rund 210 ms, fast nur fuer diese Aufrufe - dort
waere noch viel zu holen.

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

### Offen: "Sonne durch eine Luecke" bleibt 8 % zu hoch

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
