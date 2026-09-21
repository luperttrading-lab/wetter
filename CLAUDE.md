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

### Was die drei Zahlen bedeuten

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

## Das UV-Modell: wo die Zahlen herkommen

Die Herleitungen stehen ausfuehrlich als Kommentare in `index.html`. Hier nur,
was ein neuer Chat wissen muss, bevor er etwas daran aendert.

Zwei Kurven, zwei ganz verschiedene Wege:

- **Schwarze Glocke ("max. moeglich")** = CAMS-Klarhimmel von Open-Meteo,
  korrigiert mit `uvCamsFaktor()`: Geo-Korrektur nach Breite und Hoehe
  (`0,939 - 0,0199*(Breite-50) + 0,0561*Hoehe[km]`, gefittet an 16 BfS-Bilder
  mit DWD-Kurve) mal dem **Stationsfaktor** aus `uv-station.json`.
  Fuer Wettenberg: 0,937 x 1,094 = 1,025 - die beiden Korrekturen heben sich
  fast auf, was Zufall ist und nicht Absicht.
- **Bunte Saeulen** = Glocke x Durchlass^`UV_K_EXP`. Der Durchlass ist
  gemessen: DWD-Globalstrahlung im 10-Minuten-Takt (`solar10`) geteilt durch
  die Klarhimmel-Globalstrahlung. **Nichts davon kommt vom BfS** - dass die
  Saeulen und das amtliche Bild darunter dieselben Zacken zeigen, sind zwei
  unabhaengige Messgeraete an derselben Station unter denselben Wolken.

### Offen: der Exponent steht fest, die Daten sind weiter

`UV_K_EXP = 0.669` ist fest eingebaut (Stand v3.87, 1488 Paare).
`uv-durchlass.json` hat inzwischen 14 Tage und sagt 0,679 +- 0,011 (teils
Sonne, r2 0,52) und 0,682 +- 0,004 (keine Sonne, r2 0,81) - also 1,5 % hoeher
und ueber die Klassen hinweg gleich. Die Klasse "volle Sonne" bleibt
unbrauchbar (r2 0,21), weil dort kaum Variation im Durchlass steckt.
Die App liest die Datei **nicht**; wer den Wert nachzieht, aendert die
Konstante in `index.html` von Hand.

### Offen: der Stationsfaktor und die 90-Prozent-Schwelle

`uv_station.py` nimmt einen Tag nur bei **`MIN_SONNE = 0,90`** (Sonnenanteil
11-15 Uhr). Der Grund steht im Skript und ist gut belegt: ueber 102
Stationstage ist die Klasse 50-70 % Sonne der Wolkenrand-Ausreisser-Bereich
(Median 1,209, 9 von 16 Tagen ueber 1,15).

Fuer Wettenberg ist die Schwelle trotzdem zu streng. Aus `uv_klarlog.json`,
15 Tage:

    >= 90 % Sonne    1 Tag    1,134
    70 bis 90 %      6 Tage   Median 1,118   Std 0,049
    alle >= 70 %     7 Tage   Median 1,120   Std 0,045

Der einzelne Klartag und die sechs Teilsonnentage sagen dasselbe (1,134 gegen
1,127 im Mittel, 0,6 % auseinander). Der Faktor steht also auf `tage: 1`
und `vorlaeufig`, obwohl sieben Tage ihn stuetzen; die Daempfung
`n/(n+0,43)` zieht ihn deshalb auf 1,094 statt 1,113.

Nicht einfach die Schwelle senken - die 102-Stationstage-Statistik dagegen
gilt weiter. Der saubere Weg waere, Tage mit 70-90 % Sonne mitzuzaehlen,
**wenn ihre Streuung klein ist** (bei Wettenberg 0,049), sonst zu verwerfen.
Vorher am Protokoll `uv-station-protokoll.json` gegenpruefen.

### Der Tagesgang der Truebung liegt noch brach

`uv-durchlass.json` misst ihn: Steigung -0,0094 ueber 2619 Punkte von 22
Stationen, vormittags 1,023, nachmittags 0,967 - also rund 5,6 % Unterschied
zwischen Vor- und Nachmittag. Das r2 ist mit 0,034 winzig, der Effekt aber
systematisch. Noch nicht eingebaut.
