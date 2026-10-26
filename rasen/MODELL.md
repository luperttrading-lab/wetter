# Wachstumsmodell der Rasen-App – `rasen/modell.js`

Fassung 1.2 (nach dritter Prüfung, Abschnitt 13), Stand 26.10.2026. Verbindlich für `RasenModell` nach `vertrag.md`.
Höhen in **mm**, Wachstum in **mm/Tag**, Temperaturen °C, Regen und ET0 mm/Tag,
Strahlung MJ/m²/Tag, Sonne s/Tag, Datum `"YYYY-MM-DD"` in der Ortszeit der Fläche.
`null` = Wert fehlt. Das Modul ist rein: kein DOM, kein fetch, kein `Date.now()`;
`heute` und alle Daten werden übergeben. Nach außen nie `NaN`, nie negatives Wachstum.

> **Wie diese Fassung entstand.** Zwei unabhängige Entwürfe lagen vor (ein dritter kam
> nicht an): einer aus agrarmeteorologischer Sicht (PACE-Turf-Wachstumspotenzial,
> FAO-56-Wasserbilanz, Licht- und Stickstofffaktor), einer aus statistischer Sicht
> (Trapez-Temperatur, einfacher Eimer, aber eine saubere Eichung als Kalman-Filter im
> Logarithmus mit Mess- und Modellfehler). **Gewonnen hat das agrarmeteorologische
> Gerüst** für Tagesschritt, Wasser, Licht und Stickstoff – seine Faktoren sind
> belegt oder wenigstens an Literatur verankert. **Übernommen aus dem statistischen
> Entwurf** sind Eichung, Unsicherheitsband, Rückfallketten für fehlende Werte,
> die Konsistenzprüfung gegen die Wetter-App (60 Gradtage ≙ 20 mm in 7 Tagen bei
> 15 °C), das halbe Wachstum am Mähtag und das 3-Tage-Mittel der Strahlung.
> Angepasst wurden Topt/σ der Temperaturkurve (siehe 3.1) und Gmax, damit die
> Praxiswerte getroffen werden. Fassung 1.1 arbeitet sieben Prüfpunkte ein (Abschnitt 13):
> σ 6 → 7 und Rsat 10 → 6, Bodenart `ton` gestrichen, Band bei G = 0, Trockenhinweis mit
> Schwelle, Düngung ohne Sprung, Terminsuche vollständig, Plausibilitätsschwellen angeglichen.

---

## 1. Übersicht

Rasen wächst mit einer Höchstrate `Gmax` (mm/Tag), die nur erreicht wird, wenn
Temperatur, Wasser, Licht und Stickstoff zugleich günstig sind. Jeder Tag bekommt
vier Faktoren zwischen 0 und 1 (Stickstoff bis 1,15), die multipliziert werden.
Ein Eichfaktor `k` je Fläche verschiebt das Ganze und wird aus den Mähbeobachtungen
des Nutzers gelernt (Höhe vor dem Mähen). Die Höhe ist die Summe der Tageszuwächse
ab der Schnitthöhe des letzten Mähens.

```
Höhe(t+1)   = min( hoeheMax , Höhe(t) + Wachstum(t) )
Wachstum(t) = Gmax · typ · k · f_T(t) · f_W(t) · f_L(t) · f_N(t)      [mm/Tag, >= 0]
```

Der Nutzer liefert je Mähintervall genau EINE Zahl mit rund ±5 mm Messfehler, 5–15
Mal im Jahr. Daraus ist nur EINE Größe lernbar: `k`. Alle anderen Faktoren sind fest
(Quelle oder Schätzwert) und bestimmen nur die Form des Verlaufs innerhalb eines
Intervalls sowie den Startwert vor der ersten Eichung. Das Modell sagt das in der
Erklärung offen: *„Die App lernt aus deinen Messungen nur, wie schnell dein Rasen
insgesamt wächst – nicht, woran es liegt.“*

**Genauigkeit, ehrlich:** Ohne Eichung kann die Höhe um ±50 % danebenliegen; mit
3–5 Eichungen bleiben rund ±25 % für die laufende Woche. Zuwachsraten in mm/Tag sind
für Hausrasen nirgends sauber publiziert – `Gmax` ist ein Schätzwert, der auf die
Praxisbereiche (Frühjahr 3–6, Sommer 2–4, Herbst 1–3, Winter < 0,5 mm/Tag) abgestimmt ist.

---

## 2. Eingaben

### Tag (`tag`)
| Feld | Einheit | Rolle |
|---|---|---|
| `datum` | `"YYYY-MM-DD"` | Tag in Ortszeit |
| `tmean` | °C | Haupttreiber f_T |
| `tmin`, `tmax` | °C | Drei-Punkt-Tagesgang von f_T; Rückfall für tmean |
| `regen` | mm/Tag | Wasserbilanz |
| `et0` | mm/Tag | Wasserbilanz (FAO-56-Referenzverdunstung) |
| `strahlung` | MJ/m²/Tag | Lichtfaktor (3-Tage-Mittel) |
| `sonne` | s/Tag | NUR Rückfall für `strahlung` (Ångström), sonst unbenutzt |
| `quelle` | `"gemessen"`/`"prognose"`/`"fehlt"` | Markierung im Verlauf, Unsicherheitsband |

### Einstellungen (`einst`, Form von `STD`)
`schnitt` (mm), `max` (mm Zielhöhe), `drittel` (bool), `typ` ∈ {gebrauch, sport,
schatten, zier}, `boden` ∈ {sand, lehm} (`ton` aus Fassung 1.0 gilt als lehm), `wasser` ∈ {nie, trocken, regelmaessig},
`duenger` ∈ {keine, wenig, normal, viel}, `letzteDuengung` (Datum|null),
`licht` ∈ {sonne, halbschatten, schatten}. Unbekannter Wert → `STD`-Wert
(gebrauch / lehm / nie / normal / sonne).

```js
RasenModell.STD = {schnitt:40, max:60, drittel:true, typ:"gebrauch", boden:"lehm",
                   wasser:"nie", duenger:"normal", letzteDuengung:null, licht:"sonne"}
```

### Zustand und Eichung
`zustand = {wasser}` (pflanzenverfügbares Bodenwasser mm, 0…TAW; null → Startwert).
`kal = {k, n, log, p, stand}` – `p` und `stand` sind dokumentierte Erweiterungen gegenüber
dem Vertrag (`{k,n,log}`); fehlen sie (alter Speicher), gilt `p = σ0²/(1+n)`, `stand = null`.

---

## 3. Tagesschritt – `tagesWachstum(tag, einst, zustand, kal)`

Reihenfolge bindend (Reproduzierbarkeit):

1. Fehlende Eingaben ersetzen (Abschnitt 9): T-Werte, regen, et0, strahlung3.
2. `f_T` aus tmin/tmean/tmax (3.1); `f_N` aus duenger, letzteDuengung, datum (3.4).
3. `W_anfang = zustand.wasser` (null → W0; `regelmaessig` → TAW). `f_W = Ks(W_anfang)` (3.2).
4. `f_L` aus strahlung3 und licht (3.3).
5. `k = clamp(kal.k, 0,4, 2,5)` (null → 1).
6. `mm = max(0, Gmax · typ · k · f_T · f_W · f_L · f_N)`, auf 0,01 mm gerundet.
7. Wasserbilanz fortschreiben → `W_ende` (3.2), Bewässerungsregel anwenden.
8. Rückgabe `{mm, faktoren:{T, W, L, N, k}, zustand:{wasser: W_ende}}`.

Ist ein Faktor `NaN` (Programmierfehler), gilt für ihn 1 (f_T: 0, wenn nach allen
Rückfällen keine Temperatur vorliegt), und `simulieren` setzt den Hinweis
„Rechenfehler in Faktor X“. Die Kappung an `hoeheMax` und das halbe Wachstum am Mähtag
macht `simulieren`, weil `tagesWachstum` die Höhe nicht kennt.

### 3.1 Temperatur `f_T` – Wachstumspotenzial (Gauß-Kurve)

Form nach dem PACE-Turf-„Growth Potential“ (Gelernter & Stowell; Woods):

```
GP(T) = exp( −0,5 · ((T − Topt) / σ)² )          Topt = 19 °C,  σ = 7 °C
```

PACE/Woods nennen für kühle C3-Gräser Topt 20 °C, σ 5,5 °C – geeicht an
amerikanischen Golfgrüns. Damit läge der April in Mittelhessen (Tagesmittel 9,5 °C)
bei nur ~1,1 mm/Tag und 15 °C ergäben in 7 Tagen 28 mm statt der 20 mm, die die
Wetter-App mit 60 Gradtagen meint. **Topt 19 / σ 7 ist deshalb eine angepasste
Konstante (Schätzwert)**; Topt liegt in der Mitte von Beards Optimum des Sprosswachstums
kühler Gräser (15–24 °C). Fassung 1.0 hatte σ 6; die Prüfung (Abschnitt 13, Punkt 7)
zeigte April/Mai/Oktober UNTER dem Praxisbereich. σ 7 hebt die Flanken: Mai 2,8 statt 2,5,
Oktober 1,8 statt 0,9 mm/Tag (mit Rsat 6, siehe 3.3), und trifft den Anker der Wetter-App
genauer (10/15/20 °C → 20,3 statt 18,9 mm in 7 Tagen). Unter 2 °C bleibt die Kurve klein
(GP(2) = 0,052), über 33 °C ebenfalls (0,135) – zusammen mit dem Drei-Punkt-Tagesgang und dem
Lichtfaktor im Winter (Januar 0,08 mm/Tag) braucht es keine eigene Frost- oder Hitzeregel.

Stützwerte (σ 7): GP(5) = 0,135 · GP(10) = 0,44 · GP(15) = 0,85 · GP(19) = 1 · GP(25) = 0,69 · GP(30) = 0,29.

**Drei-Punkt-Tagesgang** (Pflicht, wenn tmin und tmax vorliegen): GP ist nicht linear,
die Funktion des Tagesmittels ist nicht das Mittel der Funktion (Jensen-Effekt wie bei der
UV-Prognose in CLAUDE.md).

```
f_T = 0,25·GP(tmin) + 0,50·GP(tmean) + 0,25·GP(tmax)
```

Beispiel 10/15/20 °C → 0,781 statt GP(15) = 0,85; Hitzetag 18/25/32 → 0,64 statt 0,69.
Gewichte 1/4-1/2-1/4 sind ein Schätzwert (Simpson-Form). Nur `tmean` → `f_T = GP(tmean)`.
Nur tmin/tmax → tmean = (tmin+tmax)/2.

### 3.2 Wasser `f_W` – FAO-56-Wasserbilanz für den Wurzelraum

**Speicher.** Wurzelraum `Zr = 0,25 m` (Schätzwert für Hausrasen auf oft verdichtetem
Boden; FAO-56 Tab. 22 nennt 0,5–1,0 m für bewässerte, tief wurzelnde Bestände).
Nutzbare Feldkapazität `nFK` je Bodenart aus FAO-56 Tab. 19 (Spannenmitten, auf 5 mm/m
aufgerundet: 85 → 90, 150 → 155):

| `einst.boden` | θFC − θWP (FAO-56 Tab. 19) | nFK mm/m | TAW = nFK·Zr |
|---|---|---|---|
| `sand` | 0,05–0,12 | 90 | **22 mm** |
| `lehm` (Voreinstellung) | 0,11–0,19 | 155 | **39 mm** |

Nur zwei Bodenarten. Fassung 1.0 hatte `ton` (0,12–0,20 → 160 mm/m → TAW 40 mm), das
ist 2,5 % neben Lehm und für den Nutzer wirkungslos (Prüfung, Abschnitt 13, Punkt 4) –
gestrichen; ein gespeichertes `boden:"ton"` gilt als `lehm`. Was den Rasen bei Trockenheit
wirklich länger durchhalten lässt, ist die Wurzeltiefe `Zr`, nicht die Bodenart; sie ist
fest 0,25 m (Grenze 3).

Entleerungsfaktor `p = 0,45` (fest; FAO-56 Tab. 22 gibt 0,40 für kühle Rasengräser bei
ETc 5 mm/Tag und korrigiert +0,04 je mm weniger – bei typischen 2–4 mm/Tag ≈ 0,44–0,52;
der feste Mittelwert spart eine Rückkopplung, die unter dem Messfehler liegt).
`RAW = p·TAW` (leicht verfügbares Wasser). Pflanzenkoeffizient `Kc = 0,90`
(FAO-56 Tab. 12: Turf grass cool season 0,90/0,95/0,95 für 6–8 cm Schnitthöhe, Fußnote:
−0,10 bei sparsamer Bewirtschaftung; 0,90 für den 4-cm-Hausrasen ist ein Schätzwert
dazwischen).

**Bilanz je Tag** (W = pflanzenverfügbares Wasser am Tagesanfang, Dr = TAW − W):

```
Ks     = Dr <= RAW ? 1 : clamp( (TAW − Dr) / ((1 − p)·TAW) , 0, 1 )     FAO-56 Gl. 84
f_W    = Ks                                      // Wachstum DIESES Tages, vor Regen
ETc    = Ks · Kc · ET0                           // FAO-56 Gl. 81
W_ende = clamp( W + regen − ETc , 0, TAW )       // Überschuss versickert
```

`f_W` kommt aus dem Wasser am TAGESANFANG – ein Abendgewitter „rettet“ den Tag nicht,
es wirkt ab morgen. Regen zählt voll bis zur Kapazität (keine Interzeption; der Fehler
ist klein gegen den Messfehler und wird von k geschluckt).

**Startwert** `W0 = 0,75·TAW` (Schätzwert). Enthält `tage` Einträge VOR `start.datum`
(erlaubt, bis zu 14), läuft die Bilanz ab dem ersten Eintrag ohne Höhe mit („Einschwingen“) –
der Speicher von 22–39 mm vergisst seinen Start bei 2–4 mm/Tag binnen ~10 Tagen. Hinweis
„Bodenfeuchte am Start geschätzt“, wenn weniger als 7 Tage zwischen `start.datum` und `heute`
liegen und kein Vorlauf da ist.

**Bewässerung (`einst.wasser`):**

| Wert | Regel |
|---|---|
| `nie` (Voreinstellung) | reine Bilanz |
| `trocken` („wenn er trocken aussieht“) | ist `Ks` dieses Tages ≤ 0,5, wird am Abend gegossen: `W_ende = TAW`. `f_W` des Tages bleibt der gerechnete Ks – der Nutzer gießt zu spät. f_W pendelt so 0,5–1, Mittel ~0,85. Schwelle 0,5 Schätzwert |
| `regelmaessig` (Beregnung) | `W = TAW` immer, `f_W = 1` |

Grenzfälle: W fällt in der Dürre EXPONENTIELL (`W_ende = W·(1 − Kc·ET0/((1−p)·TAW))`,
Faktor 0,83 je Tag bei Lehm und ET0 4) und erreicht 0 nie exakt, solange ET0 unter
(1−p)·TAW/Kc = 13,4 mm/Tag (Sand) liegt – also nie. Deshalb gibt es KEINE Bedingung
„Dr = TAW“ oder „W = 0“; Trockenstress ist eine Schwelle: **`Ks < 0,1`** (≙ W < 5,5 % von
TAW). Hinweis „Boden trocken seit N Tagen – Wachstum ruht“, wenn Ks an ≥ 3 Tagen in Folge
bis heute unter 0,1 lag (N = Tage seit dem ersten; Abschnitt 5.7). Bei `wasser:"trocken"`
wird ab Ks ≤ 0,5 gegossen – der Hinweis kommt dort nie. Im Winter (ET0 ≤ 0,5) füllt sich
der Speicher, f_W → 1 und f_T entscheidet. TAW ≥ 22 > 0, nie Division durch 0.

Zahlenbeispiel Lehm (TAW 39, RAW 17,6), W0 29,3, zehn Tage ET0 4,0 ohne Regen, Kc 0,90:
Tag 1–3 Ks = 1 (W 25,7 → 22,1 → 18,5), Tag 4 0,86, Tag 5 0,72, Tag 6 0,60, Tag 7 0,50,
Tag 8 0,41, Tag 10 ≈ 0,29, Tag 16 0,095 (erstmals unter 0,1), Hinweis ab Tag 18. Rasen
bremst nach knapp einer Woche Sommertrockenheit und steht nach rund zwei Wochen fast –
entspricht der Beobachtung. Sand (TAW 22, W0 16,5), ET0 5: Ks 1 / 0,99 / 0,62 / 0,39 /
0,25 / 0,15 / **0,097** (Tag 7) / 0,061 / 0,038 → Hinweis ab Tag 9.

### 3.3 Licht `f_L` – Standort und Tagesstrahlung

```
strahlung3 = Mittel der Strahlung von heute und den zwei Vortagen (so viele vorhanden)
f_L = min( 1 , τ(licht) · strahlung3 / Rsat )           Rsat = 6 MJ/m²/Tag
```

- `Rsat = 6` (Schätzwert): Lichtsättigung des HÖHENzuwachses eines 4-cm-Rasens bei
  knapp einem Drittel eines sonnigen Sommertags (~20 MJ). Fassung 1.0 hatte 10 MJ mit dem
  Anker „30 mol PAR/m²/Tag ≈ 14,5 MJ für Agrostis-Grüns (Arkansas)“ – das ist aber das
  Minimum für die QUALITÄT eines 3-mm-Golfgrüns, nicht die Sättigung der Blattstreckung
  eines hoch gemähten Rasens. Mit 10 MJ zählte der Herbst doppelt: f_T und f_L fallen
  beide mit der Jahreszeit und sind in Tagesdaten hoch korreliert (kalt = trüb), die
  Praxisbereiche enthalten den Herbst schon über die Temperatur; Oktober stand so bei
  0,9 mm/Tag (Praxis 1–3), und drei trübe Julitage (3-Tage-Mittel 5 MJ) halbierten das
  Wachstum. Mit 6 MJ ist Licht in der Sonne von März bis Oktober nicht begrenzend
  (Oktober R 6 → 1,0), November 0,5, Dezember 0,33, Januar 0,42, Februar 0,75; drei trübe
  Sommertage mit 5 MJ → 0,83. Licht ist damit nur noch eine Dämpfung für wirklich dunkle
  Tage und für Schattenlagen.
- Das **3-Tage-Mittel** bildet den Reservestoff-Puffer ab (LINGRA: der Reservepool trägt
  die Blattstreckung über trübe Tage) und verhindert, dass ein einzelner Regentag im Juli
  das Wachstum drückt. `simulieren` rechnet `strahlung3` und übergibt es als
  `tag.strahlung3`; `tagesWachstum` nimmt `tag.strahlung3`, sonst `tag.strahlung`.
- Durchlass `τ`: `sonne` 1,00 (Voreinstellung) · `halbschatten` 0,75 · `schatten` 0,50
  (Schätzwerte; bewusst milder als die Lichtmenge, weil Blätter im Schatten länger werden –
  Etiolement – und die HÖHE weniger sinkt als die Masse. UC Riverside: Rasenqualität fällt
  ab ~73 % Schatten deutlich; unter dichten Kronen mit bis 98 % Abschirmung wächst kein Rasen,
  dafür steht 0,50 nicht). Mit Rsat 6 kostet Halbschatten von April bis September nichts
  (0,75·13,5/6 > 1), im Oktober 25 % (0,75·6/6), im November die Hälfte; Schatten bremst ab
  Oktober auf 0,5 und im Sommer nicht – gewollt (Sättigung).

### 3.4 Stickstoff `f_N` – Düngestufe mit Abklingen

Belegt ist nur Richtung und Größenordnung: Schnittgutertrag steigt mit der N-Gabe
(Nebraska-Kammerversuch bei Poa pratensis stärker als bei Lolium perenne; Rutgers 0/2/4 lb N
je 1000 ft²). Ungedüngt gegen gut gedüngt etwa Faktor 1,5 – Schätzwert für die Stufen:

| `einst.duenger` | f_stufe |
|---|---|
| `keine` | 0,65 |
| `wenig` (1 Gabe/Jahr) | 0,85 |
| `normal` (2–3 Gaben, Voreinstellung) | 1,00 |
| `viel` (4+ Gaben) | 1,15 (Deckel – mehr N bringt Krankheiten, nicht mehr Höhe) |

Mit Datum `letzteDuengung`, `d` = Tage seit der Düngung am Tag t:

```
w(d) = d < 0 ? 0 : d <= 42 ? 1 : d >= 90 ? 0 : (90 − d) / 48      // wirkt 6 Wochen voll, klingt bis 90 Tage ab
f_N  = 0,65 + (f_stufe − 0,65) · w(d)
```

Die Gabe ist ein PULS: vor dem Datum (d < 0) und ab 90 Tagen danach gilt der Rasen als
ungedüngt (0,65), egal wie alt das Datum ist – auch bei d > 365. Fassung 1.0 hatte für
d > 365 wieder `w = 1`; damit wirkte eine Düngung vor 366 Tagen stärker (1,15) als eine vor
364 Tagen (0,65) – ein unbegründeter Sprung um Faktor 1,8 (Prüfung, Abschnitt 13, Punkt 3).
Erwogen und verworfen: nach 90 Tagen auf die Stufe zurückfallen (w = 1) – dann hätte das
Datum nur eine Delle zwischen Tag 42 und 90 erzeugt und sonst nichts bewirkt.

Die Stufe setzt also nur die HÖHE des Pulses; WANN er wirkt, sagt das Datum. **Ohne Datum**
(`letzteDuengung` null) gilt `w = 1` konstant – die Stufe beschreibt dann die übliche Praxis
übers Jahr. Wer ein Datum pflegt, muss es bei jeder Gabe nachtragen; sonst sagt der Hinweis
„Letzte Düngung über 90 Tage her – gerechnet wie ungedüngt. Trage die nächste Gabe ein oder
lösche das Datum, dann gilt wieder deine Düngestufe“ (wenn ein Datum vorliegt und w(heute) = 0).
Liegt das Datum NACH `heute`: Hinweis „Düngedatum liegt in der Zukunft“, bis dahin w = 0.
Bei `keine` ist das Datum egal (f_stufe = 0,65 → f_N = 0,65 für jedes w).
Wirkdauer 42/90 Tage: Schätzwert aus Herstellerangaben (Mineraldünger 6–8 Wochen,
Langzeitdünger 2–3 Monate). Beispiele `viel`: d 20 → 1,15; d 66 → 0,90; d 364 → 0,65;
d 366 → 0,65; ohne Datum → 1,15.

### 3.5 Gmax und Rasentyp

`Gmax = 4,0 mm/Tag` (Schätzwert) × Typfaktor: `gebrauch` 1,00 · `sport` 1,10 ·
`schatten` 0,85 · `zier` 0,80 (Schätzwerte: Lolium-betonter Sportrasen RSM 3.1 streckt am
schnellsten – Peacock 1975; Festuca-/Poa-supina-Mischungen RSM 1.1/2.2 langsamer).

**Plausibilitätsprüfung** mit Monatswerten Mittelhessen (tmin/tmean/tmax), f_N = 1, k = 1,
Wasser nicht begrenzend, Licht nach Klimatabelle:

| Monat | T min/mean/max | f_T | f_L | Wachstum mm/Tag | Praxis |
|---|---|---|---|---|---|
| März | 1 / 4,6 / 10 | 0,18 | 1 | 0,7 | Winter/Start < 1 ✓ |
| April | 4 / 9,5 / 15 | 0,44 | 1 | 1,8 | Frühjahr 3–6 gilt für den Höhepunkt Mai/Juni; Anfang April (Monatsmittel 9,5 °C) wächst kein Rasen 3 mm/Tag – **unter dem Bereich, bewusst** (Grenze 2) |
| Mai | 8 / 13,5 / 19 | 0,69 | 1 | 2,8 | 3–6 (knapp unter dem unteren Rand; warme Maitage 12/18/24 → 3,5) |
| Juni | 11 / 17 / 23 | 0,82 | 1 | 3,3 | 3–6 ✓ |
| Juli | 13 / 19 / 25 | 0,85 | 1 | 3,4 · f_W (0,5–0,8) ≈ 1,7–2,7 | Sommer 2–4 ✓ |
| August | 12,5 / 18,5 / 25 | 0,83 | 1 | 3,3 · f_W | 2–4 ✓ |
| September | 9 / 14,5 / 20 | 0,74 | 1 | 3,0 | Herbst 1–3 ✓ |
| Oktober | 6 / 10 / 14 | 0,46 | 1 | 1,8 | 1–3 ✓ (Fassung 1.0: 0,9) |
| November | 2 / 5 / 8 | 0,15 | 0,5 | 0,3 | Winter < 0,5 ✓ |
| Dez–Feb | −2…6 | 0,05–0,07 | 0,33–0,75 | 0,07–0,2 | ✓ (Januar −1/2/5, R 2,5 → 0,08) |

Nachgerechnet mit σ 7 und Rsat 6 (Skript, 25.10.2026). Hitzesommer 18/27/34 → f_T 0,53.

**Konsistenz mit der Wetter-App:** dort gilt „60 Gradtage über 5 °C“ ≙ 7 Tage bei 15 °C
als Mähabstand (`RZ_STD.gd`). Hier: 10/15/20 °C → f_T 0,781 → 3,13 mm/Tag → in 7 Tagen
(halber Mähtag + 6 Tage) 20,3 mm ≈ der Weg von Schnitthöhe 40 auf die Ein-Drittel-Marke
60 mm. Beide Apps meinen denselben Rasen. Mit `duenger:"viel"` (1,15) liegt der Juni bei
3,8 mm/Tag; k deckt den Rest (0,4–2,5).

---

## 4. Parametertabelle (`RasenModell.PARAM`)

Jeder Eintrag als `{wert, einheit, quelle}`, damit die Erklärung „So rechnet die App“ ihn
direkt anzeigen kann. „Schätzwert“ heißt: keine belastbare Quelle, auf Plausibilität gesetzt.

| Name | Wert | Einheit | Herkunft |
|---|---|---|---|
| `gmax` | 4,0 | mm/Tag | Schätzwert; Praxis 2–3 cm/Woche Mai/Juni; konsistent mit Wetter-App gd = 60 |
| `typ` gebrauch/sport/schatten/zier | 1,00 / 1,10 / 0,85 / 0,80 | – | Schätzwert (Lolium streckt am schnellsten, Peacock 1975) |
| `topt` | 19 | °C | PACE-Turf-Form (dort 20 °C); auf Mitteleuropa angepasst – Schätzwert; Beard: Optimum 15–24 °C |
| `sigma` | 7 | °C | PACE/Woods 5,5 °C; angepasst – Schätzwert (Fassung 1.0: 6; siehe 3.1 und Abschnitt 13) |
| `gewichte3` tmin/tmean/tmax | 0,25 / 0,50 / 0,25 | – | Schätzwert (Simpson-Form gegen Jensen-Effekt) |
| `zr` Wurzelraum | 0,25 | m | Schätzwert (FAO-56 Tab. 22: 0,5–1,0 m für bewässerten Rasen) |
| `nfk` sand/lehm | 90 / 155 | mm/m | FAO-56 Tab. 19, Spannenmitten auf 5 aufgerundet (85 / 150) |
| `taw` sand/lehm | 22 / 39 | mm | abgeleitet nfk·zr; `ton` (40) gestrichen, gilt als lehm |
| `ksTrocken` | 0,1 | – | Schätzwert: Schwelle „Wachstum ruht“ (W < 5,5 % TAW), ≥ 3 Tage in Folge |
| `p` Entleerungsfaktor | 0,45 | – | FAO-56 Tab. 22 (0,40 bei ETc 5) + Kap. 8 Anpassung; fester Mittelwert |
| `kc` | 0,90 | – | FAO-56 Tab. 12 Turf cool season (0,90/0,95/0,95; −0,10 sparsam), Zwischenwert |
| `w0` Startfüllung | 0,75·TAW | mm | Schätzwert |
| `giessSchwelle` (wasser „trocken“) | Ks ≤ 0,5 → TAW | – | Schätzwert |
| `rsat` | 6 | MJ/m²/Tag | Schätzwert (Fassung 1.0: 10; der Anker 30 mol PAR/m²/d ≈ 14,5 MJ für Bentgrass-Grüns war ein Qualitätsminimum, keine Sättigung – siehe 3.3) |
| `strahlungTage` | 3 | Tage | Schätzwert (Reservepool, LINGRA) |
| `tau` sonne/halbschatten/schatten | 1,00 / 0,75 / 0,50 | – | Schätzwert (UC Riverside, MSU; Etiolement) |
| `fN` keine/wenig/normal/viel | 0,65 / 0,85 / 1,00 / 1,15 | – | Schätzwert; Richtung belegt (Nebraska, Rutgers) |
| `duengerVoll` / `duengerEnde` | 42 / 90 | Tage | Schätzwert (Hersteller 6–12 Wochen); Puls, danach 0,65 ohne Ausnahme für d > 365 |
| `hoeheMax` | 150 | mm | Schätzwert (ungemähter Gebrauchsrasen legt sich bei 15–20 cm) |
| `hoeheWarnung` | 120 | mm | Schätzwert (Hinweis „in zwei Schritten mähen“) |
| `kMin` / `kMax` | 0,4 / 2,5 | – | Vorgabe des Auftrags (≈ e^±0,9 ≈ 2,6 σ0) |
| `sigma0` Prior ln k | 0,35 | – | Schätzwert: Streuung zwischen Gärten ~Faktor 1,4 |
| `sigmaMess` | 5 | mm | Schätzwert: Lineal im Gras, Laie |
| `sigmaModell(L)` | clamp(0,25·√(7/L), 0,12, 0,5) | relativ | Schätzwert |
| `q` Prozessrauschen | 0,15² je Jahr | – | Schätzwert (Verfilzung, Düngegewohnheit ändern sich) |
| `huber` Stutzung | ln 1,6 | – | Standard-Huber-Schwelle ~1,5 σ |
| `verhMin` / `verhMax` | 0,35 / 2,8 | – | Schätzwert (≈ 3 σ eines typischen Intervalls) |
| `minIntervall` / `maxIntervall` | 2 / 120 | Tage | Schätzwert |
| `minZuwachs` | 5 | mm | Schätzwert (Messfehler) |
| `bandFaktor` | 1,28 | – | 80-%-Band (Normalverteilung) |
| `sigmaVorhersage(d)` | min(0,35, 0,03 + 0,025·d) | relativ | Schätzwert (Open-Meteo-Erfahrung: ab ~2 Wochen Klimaniveau) |
| `stufen` Sicherheit | ≤ 0,30 hoch, ≤ 0,45 mittel | relativ | Schätzwert |
| `drittelFaktor` | 1,5 | – | Ein-Drittel-Regel (Beard 1973; Gartenbau-Konsens); mit STD (40/60) fällt die Marke mit `max` zusammen |
| `maxMinFaktor` | 1,25 | – | Einstellungen: `max >= 1,25·schnitt` (Abschnitt 10) |
| `klima` Monatstabellen | Abschnitt 9 | gemischt | Schätzwert in DWD-Größenordnung (50° N) |
| `angstrom` a/b | 0,25 / 0,50 | – | FAO-56 Gl. 35 |
| `makkink` | 0,65 · s · Rs / 2,45 | – | Makkink 1957; s linear an FAO-Tabellen gefittet |

---

## 5. `simulieren({tage, start, einst, kal, heute, tageVoraus, klima?})`

1. `tageVoraus` fehlt → 14; Grenzen 1…120. Horizontende `H = heute + tageVoraus`.
2. Tagesliste von `start.datum` bis `H` aufbauen: vorhandene `tage` nach Datum; fehlende
   Daten (Lücke oder hinter dem Vorhersageende) als `{quelle:"fehlt"}` mit Klimaersatz
   (Abschnitt 9). Tage VOR `start.datum` laufen nur durch den Wasserspeicher (ohne Höhe).
   `strahlung3` je Tag bilden.
3. `Höhe = start.hoehe` (null → `einst.schnitt`). Tag für Tag `tagesWachstum`; **am Mähtag
   zählt das halbe Wachstum** (gemäht irgendwann am Tag; Fehler ≤ 2 mm); Kappung
   `mm = min(mm, hoeheMax − Höhe)`; `verlauf.push({datum, hoehe, mm, faktoren, quelle, lo, hi})`.
   `verlauf[d].hoehe` = Höhe am ENDE des Tages d.
4. `heute = {hoehe: Höhe_Anfang(heute) + 0,5·mm(heute), lo, hi}` („Mitte des Tages“ – so
   misst der Nutzer; keine Uhrzeit nötig). Liegt `heute` vor `start.datum` → `hoehe = start.hoehe`,
   Verlauf nur der Starttag, Hinweis „Mähdatum liegt in der Zukunft“.
5. `rate = {jetzt: mm(heute), naechste7: Mittel mm(heute+1 … heute+7)}`, beide ≥ 0, auf 0,1 gerundet.
   `rate` ist die TAGESRATE: ohne die Mähtag-Halbierung (am Mähtag = heute steht im Verlauf
   das halbe Wachstum, in `rate.jetzt` die volle Rate), aber gedeckelt auf das, was bis
   `hoeheMax` noch Platz hat – am Deckel 150 mm ist `rate` 0, nicht 3,5 (bis Fassung 1.0
   meldete sie dort weiter das ungekappte Potenzial, während die Höhe stand).
6. `start.datum` null → Hinweis „Letztes Mähen unbekannt“, Simulation ab `heute − 14` mit
   Starthöhe `einst.schnitt`. `heute` fehlt oder ist kein Datum → KEINE Ausnahme (Vertrag), sondern
   `{verlauf:[], heute:{hoehe:start.hoehe, lo, hi}, rate:{0,0}, hinweise:["Datum unbekannt – keine
   Rechnung möglich"]}`; `termine` liefert dazu einen Text ohne Termin.
7. `hinweise` (Du-Form, jeder höchstens einmal):
   „N Tage ohne Wetterdaten – mit Klimawerten gerechnet“ · „Boden trocken seit N Tagen –
   Wachstum ruht“ (f_W = Ks < 0,1 an ≥ 3 Tagen in Folge bis heute; N = Tage seit dem ersten
   solchen Tag – NICHT „W = 0“, das tritt nie ein, siehe 3.2) · „Zu kalt – dein Rasen wächst zurzeit kaum“
   (f_T < 0,1 an ≥ 5 der letzten 7 Tage) · „Noch keine Mähbeobachtung – die Schätzung kann um
   ±50 % abweichen“ (kal.n = 0) · „Sehr hoch – mähe in zwei Schritten (Ein-Drittel-Regel)“
   (Höhe heute > 120 mm) · „Höhe hat die Modellgrenze von 15 cm erreicht“ · „Letzte Düngung
   über 90 Tage her …“ / „Düngedatum liegt in der Zukunft“ (3.4) · „Regen fehlt an N Tagen –
   Boden evtl. feuchter als gerechnet“.

Die Modellhöhe sinkt nur durch Mähen (neuer `start`). Blattsterben im Winter wird nicht
modelliert; Hinweis „Winter – die Modellhöhe bleibt stehen, real sinkt der Rasen etwas“, wenn
f_T an ≥ 30 Tagen in Folge < 0,05.

---

## 6. Eichung – `kalibrieren(kal, beobachtung)`

`beobachtung = {von, bis, hoeheStart, hoeheGemessen, hoeheProg}`. `hoeheProg` ist stets die
Modellhöhe „Mitte des Tages `bis`“ mit dem bisherigen k, also
`simulieren({start:{datum:von, hoehe:hoeheStart}, heute:bis, kal, …}).heute.hoehe`.

### 6.1 Was gelernt wird – und was nicht
`verh = (hoeheGemessen − hoeheStart) / (hoeheProg − hoeheStart)` = beobachtetes /
vorhergesagtes Wachstum. Weil Wachstum ∝ k, ist `k_beob = k_alt · verh`. Mehr steckt in der Zahl
nicht: konstante Faktoren (typ, licht, duenger-Niveau, boden, Gmax) sind mit k perfekt kollinear
und aus Höhen nie trennbar; tagesveränderliche Faktoren (f_T-Form, f_W, Rsat) bräuchten bei
20–30 % Rauschen je Beobachtung 30–50 Intervalle unter kontrastreichen Bedingungen – Jahre.
Deshalb **genau ein Parameter k**, alles andere fest. Einstellungen sollen VOR den ersten
Messungen gesetzt werden; wer sie nach n ≥ 2 Eichungen ändert, entwertet die Eichung
(Oberfläche: Hinweis „Einstellungen geändert – Eichung ggf. zurücksetzen“).

### 6.2 Rauschmodell – bestimmt das Gewicht
Gerechnet wird in ln k (Verhältnisse sind log-normal, Grenzen symmetrisch um 1).

```
Δobs     = hoeheGemessen − hoeheStart            beobachtetes Wachstum
Δprog    = hoeheProg − hoeheStart                vorhergesagtes Wachstum
L        = tageZw(von, bis)
σ_m      = 5 mm                                  Messfehler einer Höhenmessung
σ_mod(L) = clamp( 0,25 · sqrt(7 / L) , 0,12 , 0,5 )   Modellfehler des Intervalls (relativ)
z        = clamp( ln verh , −ln 1,6 , +ln 1,6 )   (6.3 Regel 6)
w0       = p_prior / ( p_prior + (σ_m / Δprog)² + σ_mod(L)² )
Δ_est    = Δprog · exp( w0 · z )                 Zuwachs nach einem ersten Schritt (Prior und Messung gewichtet)
R        = (σ_m / Δ_est)² + σ_mod(L)²            Varianz von ln(verh)
```

Daraus folgen die gewünschten Eigenschaften von selbst: **längeres Intervall → kleineres
σ_mod → mehr Gewicht; größerer Zuwachs → kleinerer Messanteil → mehr Gewicht.** Ein
Intervall mit Δ ≈ 8 mm hat R ≈ 0,39 + 0,06 und zählt kaum; 25 mm in 14 Tagen hat
R ≈ 0,04 + 0,03. Der Boden 0,12 steht für systematische Anteile (falsches TAW, falscher
Düngezeitpunkt), die sich nicht herausmitteln.

**Warum nicht Δobs im Nenner** (so stand es bis Fassung 1.1): dann bestimmt das Rauschen einer
Messung ihr eigenes Gewicht – eine zu hohe Messung (großes Δobs) bekommt ein kleines R und viel
Gewicht, eine zu niedrige wenig. Prognose 55 mm (Δprog 15), Messung 60 → w 0,54, Messung 50 →
w 0,29; der Schritt nach oben war fast doppelt so groß wie nach unten. Monte Carlo (300 Gärten,
20 Intervalle à 10 Tage, wahres k = 1, Messrauschen σ_m = 5 mm): k im Mittel 1,11 bei Δ 15 mm,
1,25 bei Δ 10 mm, bei wahrem k 0,7 sogar +30 % – gerade langsam wachsende Flächen (Schatten,
Herbst) wurden zu früh und zu hoch gerechnet. Reines Δprog wäre unverzerrt (−1 % / +4 %), lernt
aber bei grob falschem Gmax kaum: wahres k 3,5 → nach 8 Mähungen erst 1,24, weil der kleine
erwartete Zuwachs die Messung immer als „ungenau“ einstuft. Δ_est ist der Kompromiss: Bias
0 % / +6 % (Δ 15 / 10 mm, k 1), +11 % bei k 0,7 (der Rest kommt von den Ausreißergrenzen, die
unten bei verh 0,25 bzw. 0,35 abschneiden); wahres k 3,5 → 2,33 nach 8 Mähungen, 2,5 nach 9.
Mit Δprog 15: Messung 60 → w 0,49, Messung 50 → w 0,38, Schritte +0,140 / −0,153 in ln k.

### 6.3 Verwerfen (Ausreißer) – erster zutreffender Grund steht im Log (`uebernommen:false`)
1. Eingaben fehlen / nicht endlich / `bis <= von` → „unvollständig“.
2. L < 2 → „zu kurz nach dem Mähen“; L > 120 → „Intervall zu lang (Winter?)“.
3. Δprog < 5 mm → „Modell erwartet kaum Wachstum (kalt/trocken) – kein Signal“;
   Δobs ≤ 0 → „gemessene Höhe nicht über der Schnitthöhe“ (ln verh wäre nicht definiert).
   Ein KLEINER positiver Δobs wird nicht mehr eigens verworfen (bis Fassung 1.1: Δobs < 5 mm
   → „kaum über Schnitthöhe“): das traf nur die zu NIEDRIGEN Messungen – bei Δ 10 mm rund 16 %
   aller Beobachtungen – und zog k zusätzlich nach oben. Zu kleine Verhältnisse fängt Regel 5
   symmetrisch (verh 0,08 bei 42 mm gegen Prognose 64 → „Ausreißer“).
4. `hoeheProg >= hoeheMax − 1` oder `hoeheGemessen > 200` → „Deckel erreicht / Höhe unplausibel“.
5. verh < 0,35 oder verh > 2,8 → „Ausreißer: Verhältnis außerhalb 0,35–2,8“
   (≈ ±1,0 in ln k ≈ 3 σ; eine korrekte Messung liegt so weit praktisch nie, ein Tippfehler
   – 18 statt 8 cm – sofort). **Gilt erst ab n ≥ 2** (`verhNeuBis`). Ungeeicht (n < 2) sind
   die Grenzen 1/4–4 (`verhAblehnen`, dieselben wie die Eingabeprüfung in Abschnitt 10):
   ein geschätztes Gmax kann für einen Garten um Faktor 3 danebenliegen (Grenze 1: ±50 %
   ohne Eichung, falsche Einstellungen wie schatten·keine = 0,325), und mit der festen
   Grenze galt dann JEDE Mähbeobachtung als Ausreißer – k blieb für immer 1,0, n = 0, die
   Oberfläche meldete dauerhaft „Noch keine Mähbeobachtung“. Jetzt zieht die Huber-Stutzung
   k in zwei Schritten auf ~1,6–1,9; danach liegt verh (relativ zur aktuellen Vorhersage)
   wieder innerhalb 0,35–2,8. Test: wahres k 3,5 → nach 8 Beobachtungen k > 2,4, alle übernommen.
   `verhGrenzen(n)` liefert die geltenden Grenzen (für `pruefeHoehe` mit `kontext.n`).
6. **Robuste Stutzung (Huber):** `z = clamp(ln verh, −ln 1,6, +ln 1,6)`. Gestutzte Fälle
   stehen im Log mit `uebernommen:true, grund:"gestutzt auf ×1,6"`.

### 6.4 Aktualisierung – exponentielle Glättung mit adaptivem Gewicht (Kalman in ln k)
```
Δt       = tageZw(kal.stand, bis)   (stand null → 0; negativ → 0)
p_prior  = kal.p + q · Δt / 365               q = 0,15²
w        = p_prior / (p_prior + R)            Gewicht 0…1
ln k_neu = ln k_alt + w · z
k_neu    = clamp( exp(ln k_neu) , 0,4 , 2,5 )
p_neu    = (1 − w) · p_prior
n_neu    = n + 1 ;  stand = max(stand, bis)
```
`stand` ist das JÜNGSTE verbuchte Datum: trägt der Nutzer eine ältere Mähung nach (Historie
ergänzt, Eichung neu durchgespielt), rechnet sie mit Δt = 0 und dreht `stand` nicht zurück –
sonst zählte die nächste Beobachtung das Prozessrauschen q für die ganze Lücke noch einmal
(Nachtrag 11.5. nach 11.6.: die Beobachtung am 21.6. rechnete Δt = 41 statt 10 Tage).
Startzustand `{k:1, n:0, log:[], p:σ0² = 0,1225, stand:null}`. Zahlenbeispiel (14 Tage,
Δprog 24 mm, Δobs 30 mm, verh 1,25: w0 = 0,621, Δ_est 27,7 mm, R = 0,064): 1. Beobachtung
w = 0,656 → k 1,158, p 0,042; 2. gleichartige 14 Tage später w = 0,39 → k 1,262; Dauerzustand
bei einer Beobachtung je Monat w∞ ≈ 0,2. (Fassung 1.1 mit Δobs im Nenner: R 0,059, w 0,675,
k 1,163 / 1,273.)
Eine einzelne Beobachtung kann k höchstens um Faktor 1,6^0,68 ≈ 1,37 verschieben.
q sorgt dafür, dass w nicht gegen null geht – ohne q wäre k nach 20 Beobachtungen eingefroren.
Hinweis „Eichung am Rand (k = 2,5): prüfe Rasentyp, Licht und Düngung“, wenn geklemmt.

**Randfall (geklemmt):** wird k_neu auf 0,4 bzw. 2,5 geklemmt, sinkt p nur um den Schritt, der
wirklich gegangen wurde: `w_eff = (ln k_neu − ln k_alt) / z` (0 ≤ w_eff ≤ w), `p_neu = (1 − w_eff) · p_prior`.
Steht k schon am Rand und die Beobachtung zeigt weiter hinaus, ist w_eff = 0 und p bleibt p_prior
(wächst mit q). Vorher lief die Aktualisierung voll durch: nach 15 Beobachtungen mit verh 2,8
stand p = 0,0071 – identisch mit 15 ungeklemmten –, obwohl k sich seit der 6. nicht bewegt hatte;
der Rückweg zum wahren k = 1 (verh 0,4) brauchte 34 Mähungen bis k < 1,2. Jetzt p = 0,019 und
14 Mähungen (Δprog 20, Δobs 8 mm; mit Δobs im Nenner, Fassung 1.1, waren es bei diesem kleinen
gemessenen Zuwachs 37 – die Zahl 14 galt dort nur für Δobs 20); schneller geht es nicht, weil die
Huber-Stutzung jeden Schritt auf ×1,6^w begrenzt (vom frischen Start aus: 4 Schritte bis k < 0,5,
weil p dort 0,1225 ist). Wer die Einstellungen
nach einer Eichung am Rand korrigiert, setzt die Eichung besser zurück (Einstellungen).

Log-Eintrag `{von, bis, verh, uebernommen, grund, w, kVor, kNach}` (w/kVor/kNach dokumentierte
Erweiterung), höchstens 50 Einträge. `kalibrieren` ist rein: index.html kann nach dem Löschen
eines Historieneintrags die Eichung aus dem Startzustand neu durchspielen – `hoeheProg` je
Intervall dann mit dem DAMALS gültigen k neu simulieren.

---

## 7. Unsicherheitsband (`lo`/`hi`, `sicherheit`)

Relativ zum kumulierten Wachstum G seit dem Mähen – die Schnitthöhe selbst ist sicher.

```
σ_f(d)   = d <= 0 ? 0 : min( 0,35 , 0,03 + 0,025·d )     Vorhersagefehler, d = Tage nach heute
G <= 0  →  lo = hi = start.hoehe                          (Mähtag, Starttag, Winter ohne Zuwachs)
sonst:
σ_fehlt  = 0,5 · G_fehlt / G                              G_fehlt = Wachstum an Tagen mit quelle "fehlt"
σ_vor    = σ_f(d) · G_voraus / G                          Vorhersageanteil
b(t)     = 1,28 · sqrt( p + σ_mod(L_t)² + σ_fehlt² + σ_vor² )
lo       = max( start.hoehe , start.hoehe + G·(1 − b) )
hi       = min( hoeheMax , start.hoehe + G·(1 + b) )
```
**G = 0 ist kein Sonderfall der Anzeige, aber der Rechnung:** am Mähtag vor dem halben
Tageswachstum, bei `heute == start.datum` und in Winterwochen, in denen `mm` auf 0,01 gerundet
0,00 ergibt (Januar, `zier` im Schatten), wären σ_fehlt und σ_vor 0/0. Die Fallunterscheidung
oben ist Pflicht (Vertrag: nie NaN nach außen); das Band ist dann die Schnitthöhe selbst.
Zwei weitere Nenner sind unkritisch: σ_fehlt ≤ 0,5 und σ_vor ≤ σ_f, weil G_fehlt ≤ G und
G_voraus ≤ G.
`L_t` = Tage seit `start.datum` (≥ 1), `G_voraus` = Anteil von G nach `heute`. 1,28 σ = 80-%-Band
(ein 95-%-Band wäre bei Laienmessungen so breit, dass es nichts mehr sagt). **p sinkt mit n,
σ_mod und σ_f bleiben – das Band wird nie schmaler als der Vorhersagefehler.**
Beispiele: n = 0, Tag 14 nach dem Mähen, G = 20 mm → b ≈ 0,50 → 50–70 mm; n = 4 (p ≈ 0,015)
→ b ≈ 0,28; dazu 7 Tage voraus (σ_f 0,205 auf den Prognoseanteil) → b ≈ 0,35–0,40.

`sicherheit(kal, tageVoraus)`:
```
band  = min( 1 , 1,28 · sqrt( p + σ_mod(14)² + σ_f(tageVoraus)² ) )
stufe = band <= 0,30 ? "hoch" : band <= 0,45 ? "mittel" : "gering"
```
Beispiele: n = 0 → 0,50 „gering“ (jeder Horizont); n = 2, 1 Tag → 0,32 „mittel“; n = 5, 1 Tag →
0,28 „hoch“; n = 5, 7 Tage → 0,40 „mittel“; n = 5, 14 Tage → 0,55 „gering“. „Hoch“ heißt also
±30 % – ehrlicher ist es nicht. `text` z. B. „Noch ohne Eichung – die Höhe kann um ±50 %
abweichen“, „3 Mähungen geeicht – ±32 %“, „in 7 Tagen ±40 % (Wettervorhersage)“.

---

## 8. Termine – `termine({sim, einst, heute})`

Drei Dinge, die die Oberfläche auseinanderhalten muss:

1. **Biologisch sinnvoller Termin – Ein-Drittel-Regel** (`drittel`): erster Tag d ≥ heute im
   `verlauf` mit `hoehe >= 1,5 · einst.schnitt` (dann wird höchstens ein Drittel der
   Blattlänge entfernt – Beard 1973, Standardregel der Rasenpflege; DIN 18919 nennt für
   Gebrauchsrasen 3,5–5 cm Schnitthöhe). Ist `heute.hoehe` schon ≥ 1,5·schnitt →
   `drittel.datum = heute`. `einst.drittel = false` → `null`.
2. **Zielhöhe erreicht** (`max`): erster Tag mit `hoehe >= einst.max`; `tageBisMax =
   tageZw(heute, max.datum)`; `ueberfaellig = heute.hoehe >= einst.max`. Im Horizont nicht
   erreicht → `max: null, tageBisMax: null`, Text nennt `rate.naechste7` und sagt das auch
   („wächst in den nächsten 7 Tagen im Mittel 0,8 mm/Tag – Zielhöhe nicht in den nächsten 14
   Tagen“; bis Fassung 1.1 „wächst zurzeit“, was neben der Kachel „Wachstum jetzt“ = `rate.jetzt`
   wie ein Widerspruch las; bei `naechste7 < 0,3`: „Dein Rasen wächst kaum – kein Mähtermin in Sicht“).
3. **Wetterbedingt geeigneter Termin:** NICHT Sache von modell.js. `RasenPlaner.tagesFenster`
   liefert je Tag einen Wetterwert 0–100. Regel für index.html, mit `T1 = drittel.datum`,
   `T2 = max.datum` (je null möglich) und `H` = Horizontende – alle Fälle:

   | Fall | Suchfenster | Art, wenn empfohlen = … |
   |---|---|---|
   | T1 und T2 null | kein Termin; Text aus `rate.naechste7` (Punkt 2) | – |
   | T1 null (Regel aus oder nicht erreicht), T2 gesetzt | `[max(heute, T2 − 3) … T2 + 1]` | T2 „Zielhöhe“, sonst „Wetter“ |
   | T1 gesetzt, T2 null (Zielhöhe im Horizont nicht erreicht) | `[max(heute, T1 − 2) … H]` | T1 „Ein-Drittel“, sonst „Wetter“ |
   | T1 ≥ T2 (Drittel-Marke ≥ Zielhöhe, **auch STD 40/60: beide fallen zusammen**) | `[max(heute, T2 − 3) … T2 + 1]` | T2 „Zielhöhe“, sonst „Wetter“ – „Ein-Drittel“ kommt hier nicht vor |
   | T1 < T2 | `[max(heute, T1 − 2) … T2]` | T1 „Ein-Drittel“, T2 „Zielhöhe“, sonst „Wetter“ |

   Das Fenster ist nie leer (Ende ≥ Anfang ≥ heute; `T2 + 1` wird an `H` gekappt). Empfohlen =
   Tag mit dem höchsten Wetterwert ≥ 50 im Fenster, bei Gleichstand (≤ 3 Punkte) der früheste –
   dieselbe Regel wie v5.69/v5.73 der Wetter-App. Keiner ≥ 50 → erster Tag ≥ 30 NACH dem
   Fensterende (bis H); auch keiner → erster Tag mit irgendeinem Fenster nach dem Fensterende;
   sonst `null` mit Text „kein passendes Wetter im Vorhersagezeitraum“. `ueberfaellig` → erster
   Tag ab heute mit irgendeinem Fenster. Fällt der Termin auf Sonntag, Feiertag oder einen
   abgewählten Tag, gilt der letzte Mähtag davor, aber nicht vor heute – sonst der nächste danach
   (wie `rzFrist`). Mit der Voreinstellung (schnitt 40, max 60) ist die Ein-Drittel-Marke
   1,5·40 = 60 = max: beide Termine sind IMMER derselbe Tag, die Art heißt dann „Zielhöhe“.
   Das ist gewollt – wer die Zielhöhe über 1,5·Schnitt legt, lässt bewusst mehr als ein Drittel
   stehen; dann trennt sich der Drittel-Termin (früher) von der Zielhöhe.

`text` deutsch, Du-Form, mit Spanne aus dem Band (erster Tag, an dem `hi` bzw. `lo` die
Schwelle erreicht): „Ein-Drittel-Höhe 6,0 cm voraussichtlich Do 29.10. (in 4 Tagen, zwischen Mi und Sa) –
Zielhöhe 7 cm am Mo 2.11. (in 8 Tagen)“ – Abstand und Spanne stehen in EINER Klammer (bis
Fassung 1.0 zwei Klammern hintereinander: „(in 4 Tagen) (zwischen Mi und Sa)“); überfällig: „Dein Rasen ist über der Zielhöhe –
mähe, sobald das Wetter passt“. Plausibilität: `einst.max < 1,25·schnitt` → Zusatz „Zielhöhe
liegt zu nah an der Schnitthöhe“; Drittel-Marke ≥ max (T1 ≥ T2, auch STD) → Text nennt nur die
Zielhöhe; T2 null und T1 gesetzt → „Ein-Drittel-Höhe 6,0 cm voraussichtlich Do 29.10. – Zielhöhe
7 cm nicht in den nächsten 14 Tagen“.

---

## 9. Fehlende Werte

Reihenfolge je Feld: (1) Wert des Tages, (2) Ableitung aus anderen Feldern, (3) Vortag
(höchstens 1 Tag weit), (4) Klimaersatz. Klimatabellen gelten für Monatsmitten (15.) und
werden linear nach Tag im Jahr interpoliert – keine Sprünge am Monatswechsel.

| Monat | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T_klima °C | 0,9 | 1,5 | 4,6 | 9,0 | 13,1 | 16,4 | 18,3 | 18,0 | 14,0 | 9,4 | 4,9 | 1,9 |
| Tmin_klima | −2 | −2 | 1 | 4 | 8 | 11 | 13 | 12,5 | 9 | 6 | 2 | −1 |
| Tmax_klima | 4 | 6 | 10 | 15 | 19 | 23 | 25 | 25 | 20 | 14 | 8 | 4 |
| Rs_klima MJ/m²/d | 2,5 | 4,5 | 8,5 | 13,5 | 17,5 | 19,0 | 18,5 | 16,0 | 11,0 | 6,0 | 3,0 | 2,0 |
| ET0_klima mm/d | 0,3 | 0,6 | 1,3 | 2,3 | 3,3 | 3,8 | 3,9 | 3,3 | 2,0 | 1,0 | 0,4 | 0,3 |
| Regen_klima mm/d | 2,0 | 1,7 | 1,8 | 1,5 | 2,2 | 2,3 | 2,6 | 2,3 | 2,0 | 1,9 | 2,0 | 2,2 |
| Ra (50° N) MJ/m²/d | 8,4 | 13,0 | 20,1 | 28,1 | 34,5 | 37,4 | 36,0 | 31,0 | 23,4 | 15,6 | 9,9 | 7,1 |
| N Tageslänge h | 8,5 | 10,0 | 11,8 | 13,8 | 15,5 | 16,4 | 16,0 | 14,5 | 12,6 | 10,7 | 9,0 | 8,0 |

Schätzwerte in DWD-Größenordnung für Mittelhessen (Jahresmittel ~9,4 °C, ET0 ≈ 690 mm,
Strahlung ≈ 3800 MJ/m²). Optional nimmt `simulieren` ein `klima = {"MM-DD": tmean}` wie
`rzKlima` der Wetter-App entgegen; es ersetzt dann T_klima.

- `tmean` null → (tmin+tmax)/2 → Vortag → T_klima. `tmin`/`tmax` null → Drei-Punkt entfällt,
  `f_T = GP(tmean)`. Liegt nur EIN Randwert vor (tmin ohne tmax oder umgekehrt), ist das keine
  Schätzung des Tagesmittels: er wird verworfen, es gilt Vortag → T_klima (bis Fassung 1.1
  `tmean = tmin` bzw. `tmax`, einseitig zu kalt bzw. zu warm – nur tmin 10 im Juli ergab f_T 0,44
  statt 0,84).
- `strahlung` null → Ångström aus `sonne`: `Rs = (0,25 + 0,5 · (sonne/3600) / N) · Ra` → Vortag → Rs_klima.
  `Ra` je Monat aus FAO-56 Gl. 21–25 für 50,65° N (8,5 / 13,8 / 22,5 / 31,6 / 38,7 / 41,7 / 40,0 /
  33,9 / 25,3 / 16,2 / 9,8 / 7,1 MJ/m²/Tag; die Tabelle der Fassung 1.0 lag März–September 8–11 %
  darunter, der Strahlungsersatz aus der Sonnenscheindauer und der Makkink-ET0-Rückfall damit
  ~10 % zu klein). Für andere Breiten gilt die Tabelle näherungsweise (±10 % zwischen 47° und 54° N).
- `et0` null → Makkink aus Rs und T: `ET0 = 0,65 · s · Rs / 2,45`, `s = clamp(0,41 + 0,014·T, 0,40, 0,75)`
  (s ≈ Δ/(Δ+γ), Fehler < 0,02 gegen FAO-Tabellen 0–30 °C) → ET0_klima. Ergebnis ≥ 0.
- `regen` null bei vorhandenem Tag → 0 mm + Hinweis (Open-Meteo liefert 0, nicht null, bei
  Trockenheit; ein Loch soll den Speicher nicht künstlich füllen); ganz fehlender Tag → Regen_klima.
- Ganz fehlender Tag (Lücke oder hinter der Vorhersage): alle Felder aus den Klimatabellen,
  `quelle:"fehlt"`, zählt in σ_fehlt. Hinweis mit Anzahl.
- `einst`-Felder null/unbekannt → `STD`. `kal` null → Startzustand. `zustand` null → `{wasser: W0}`.

---

## 10. Plausibilitätsprüfung – `pruefeHoehe(hoehe, einst, {schnitt, hoeheProg, tage})`

| Bedingung | Ergebnis |
|---|---|
| `hoehe <= schnitt` | `ok:false` „Die Höhe vor dem Mähen muss über der Schnitthöhe liegen“ |
| `hoehe > 200` | `ok:false` „Über 20 cm – bitte prüfen“ |
| `hoehe > hoeheMax` (150) | `ok:true`, Warnung „Sehr hoch – über der Modellgrenze von 15 cm“ |
| `tage < 2` | `ok:true`, Warnung „So kurz nach dem Mähen misst man kaum Zuwachs“ |
| `hoeheProg` vorhanden, Δprog ≥ 5 und Δobs/Δprog > 4 | `ok:false` „Mehr als das Vierfache der Vorhersage – stimmt die Zahl?“ |
| `hoeheProg` vorhanden, Δprog < 5 | `ok:true`, Warnung „Das Modell erwartete kaum Wachstum (X cm) – die Messung wird gespeichert, aber nicht zur Eichung genutzt“ – dieselbe Entscheidung wie 6.3 Regel 3 (vorher: `ok:true` ohne Warnung, obwohl `kalibrieren` verwarf) |
| Δobs/Δprog > 2,8 oder < 0,35 (Δprog ≥ 5, `kontext.n` ≥ 2) | `ok:true`, Warnung „Weicht sehr stark von der Vorhersage (etwa X cm) ab – wird NICHT zur Eichung genutzt (Ausreißer)“ – dieselben Grenzen wie `verhMin`/`verhMax` in 6.3 Regel 5; ungeeicht (`n` < 2 oder fehlt) gilt 1/4–4, dazwischen „gestutzt“ |
| Δobs/Δprog > 1,6 oder < 0,625 (= 1/1,6; Δprog ≥ 5) | `ok:true`, Warnung „Weicht stark von der Vorhersage (etwa X cm) ab – geht gestutzt in die Eichung ein“ – dieselbe Grenze wie die Huber-Stutzung 6.3 Regel 6 |
| sonst | `ok:true, warnung:""` |

Die drei Schwellen 1,6 / 2,8 / 4 sind bewusst identisch mit `kalibrieren`: Fassung 1.0 warnte
erst ab 2 bzw. unter 0,4 und versprach „wird zur Eichung genutzt“ auch für 2,8–4, wo
`kalibrieren` verwirft (Prüfung, Abschnitt 13, Punkt 6). `ok:false` bleibt erst ab dem
Vierfachen – zwischen 2,8 und 4 kann die Messung stimmen (Düngestoß, Regen nach Dürre),
sie wird gespeichert, nur nicht zum Lernen benutzt.

Einstellungen: `max >= 1,25·schnitt` erzwingen (STD: 40 → mindestens 50; Fassung 1.0 sagte
„schnitt + 10, sonst fällt der Drittel-Termin mit max zusammen“ – falsch begründet: ob beide
zusammenfallen, hängt an `max = 1,5·schnitt`, und das ist bei STD der Fall, siehe 8.3).

---

## 11. Grenzen des Modells

1. **Gmax ist geschätzt.** Zuwachsraten in mm/Tag für Hausrasen sind nicht publiziert
   (Forschung misst Trockenmasse, Praxis sagt „wöchentlich mähen“). Ohne Eichung ±50 %; die
   Oberfläche MUSS das Band zeigen und zur Eingabe der Höhe vor dem Mähen ermuntern.
2. **Frühjahr am unteren Rand.** Topt 19/σ 7 liefert im April (Monatsmittel 9,5 °C) 1,8 und
   im Mai 2,8 mm/Tag; die Praxis nennt 3–6 – gemeint ist der Höhepunkt Mai/Juni. April auf
   3 mm/Tag zu heben, verlangte f_T ≈ 0,75 bei 9,5 °C Tagesmittel, also eine Kurve mit
   Optimum um 12 °C, die den Sommer falsch macht; das ist mit keiner reinen Temperaturkurve
   zu haben. Peacock 1975 fand, dass Lolium im Frühjahr bei gleicher Temperatur schneller
   wächst als im Herbst (Reservestoffe, Tageslänge) – nicht modelliert. Nach 1–2 Saisons
   Eichdaten prüfen, ob ein Frühjahrszuschlag nachzuziehen ist; k fängt den Rest je Fläche.
   **Herbstmaximum:** In der Jahressimulation mit den eigenen Klimatabellen (Wettenberg, STD,
   k = 1, 52 cm/Jahr) ist der September mit 2,7 mm/Tag der schnellste Monat (Mai 2,2, Juni 2,2,
   Juli 2,4, August 2,6): die Wasserbilanz (Ks Juni ≈ 0,7) bremst den Sommer, die
   Temperaturkurve ist symmetrisch, und der feuchte Herbst bei 14 °C läuft ungebremst. Die
   Praxis (Frühjahr 3–6, Herbst 1–3) und Peacock 1975 sagen das Gegenteil. Folge für die
   Terminprognose, bis k nachgeeicht ist: im Frühjahr eher zu späte, im Herbst eher zu frühe
   Termine – und k kann die Jahresform nicht korrigieren. Ein saisonaler Faktor am
   Tageslängen-Trend (Frühjahr +, Herbst −, ±15 %) ist der Kandidat, wird aber erst nach der
   ersten Saison an den Eichlogs (verh je Monat) geprüft, nicht vorher geraten.
3. **Wasser ist die größte Fehlerquelle im Sommer.** Zr 0,25 m und TAW 22–39 mm lassen den
   Rasen nach ~1–2 Wochen ohne Regen stehen; alte, tief wurzelnde Rasen halten länger – das
   steckt in der Wurzeltiefe Zr, und die ist NICHT einstellbar (eine Option „alter Rasen“ mit
   Zr 0,40 m wäre der nächste Schritt, wenn Nutzer das vermissen; der Vertrag kennt das Feld
   nicht). Die Bodenart hilft dabei nicht: Fassung 1.0 empfahl hier „ton wählen“, aber Ton
   (TAW 40) lag 2,5 % neben Lehm (39) und verschob den Dürrebeginn um weniger als einen Tag –
   gestrichen. Open-Meteo-Regen und -ET0 sind Gitterwerte: ein lokaler Schauer oder das
   Gießen des Nachbarn fehlen.
4. **Licht und Stickstoff sind Schätzwerte**, die k mitschluckt – wer „Schatten“ oder die
   Düngestufe nachträglich ändert, entwertet die alte Eichung.
5. **Nur k wird gelernt.** Das Modell kann nicht sagen, WARUM ein Rasen schneller wächst.
6. **Messung.** ±5 mm bei 20 mm Zuwachs sind 25 % – darum Mindestzuwachs 5 mm und Glättung.
   Gemessen wird mit dem Lineal am Halm, nicht am Ohr des Mähers.
7. **Kein Blattsterben, keine Verfilzung, keine Krankheit.** Die Modellhöhe sinkt nur durch Mähen.
8. **Zwei Modelle nebeneinander:** Die Wetter-App rechnet weiter mit der Wärmesumme (`gd`).
   Beide sind bei 15 °C auf 20 mm in 7 Tagen abgestimmt, weichen aber bei Trockenheit, Schatten
   und im Frühjahr ab. Die Rasen-App soll beim Import aus `rasen`/`rasenTest` den `gd`-Wert nicht
   übernehmen, sondern Schnitt- und Zielhöhe abfragen.
9. **Sommerzeit** (CLAUDE.md v5.38) betrifft modell.js nicht (Tagesdaten mit `timezone=tz`),
   wohl aber die Stundenwerte in `wetter.js`.

---

## 12. Rechenbeispiele für `test_modell.js` (Mindestumfang)

1. `GP(19) = 1`, `GP(15) ≈ 0,849`, `GP(10) ≈ 0,438`; Drei-Punkt 10/15/20 ≈ 0,781; 18/25/32 ≈ 0,64.
2. Lehm, normal ohne Datum, Sonne, k = 1, W = 30: Tag {tmin 10, tmean 15, tmax 20, strahlung 12,
   regen 0, et0 2,5} → f_T 0,781, f_W 1, f_L 1, f_N 1, **mm ≈ 3,13**, wasser 27,75 (30 − 0,90·2,5).
   Nur tmean 15 → mm ≈ 3,40. Strahlung 3 → f_L 0,5; Strahlung 6 → f_L 1; `boden:"ton"` → wie lehm (TAW 39).
3. 10 Tage {tmin 15, tmean 20, tmax 25}, ET0 4, Regen 0, lehm, `nie`: f_W Tag 1–3 = 1, Tag 4 ≈ 0,86,
   Tag 7 ≈ 0,50, Tag 10 < 0,35 (≈ 0,29 – also KEIN Trockenhinweis); `wasser` nie < 0 oder > 39.
   `regelmaessig` → f_W = 1 an allen Tagen; `trocken` → min f_W ≥ 0,45 und W nach Gießtag = 39.
   **Trockenhinweis:** Sand, ET0 5, 14 Tage ohne Regen → Ks Tag 7 ≈ 0,097 < 0,1, Hinweis „Boden
   trocken seit N Tagen – Wachstum ruht“ ab Tag 9 (N = 3), an Tag 14 N = 8; Lehm, ET0 4 → ab Tag 18;
   `trocken` → nie.
4. tmean 2 → f_T ≈ 0,052, mm ≤ 0,21. Alle Eingaben null für 30 Tage → kein NaN, Höhe steigt nach
   Klimaersatz, Hinweis „30 Tage ohne Wetterdaten“ vorhanden, alle `quelle:"fehlt"`.
5. 40 mm Start, 7 Tage wie Beispiel 2 → Höhe ≈ 40 + 0,5·3,13 + 6·3,13 ≈ 60,3 (Konsistenz gd = 60).
   Monatsprüfung (Tabelle 3.5, Klimawerte, Wasser voll): April 1,7–1,9, Oktober 1,7–1,9, November
   0,2–0,4, Januar < 0,15 mm/Tag.
6. Höhe nie > 150; bei 125 mm Hinweis „in zwei Schritten“.
7. Eichung: Start-kal, {von 1.5., bis 15.5., hoeheStart 40, hoeheGemessen 70, hoeheProg 64} → verh 1,25,
   R ≈ 0,064, w ≈ 0,656, k ≈ 1,158, p ≈ 0,042, n 1; zweite gleiche Beobachtung 14 Tage später → k ≈ 1,262.
   Symmetrie: Prognose 55, Messung 60 und 50 → Schritte in ln k gleich groß auf 12 %; Monte Carlo
   (wahres k 1, σ_m 5, Δ 15 / 10 mm) → Mittel von k innerhalb 4 % / 10 % von 1; Nachtrag einer älteren
   Beobachtung lässt `stand` stehen.
8. Verwerfen: verh 3,0 → „Ausreißer“, k und n unverändert; hoeheGemessen 42 bei Start 40 →
   „Ausreißer“ (verh 0,08); 40 oder 35 → „nicht über der Schnitthöhe“; hoeheProg 150 → „Deckel“;
   L = 1 → „zu kurz“.
9. Stutzung: verh 2,0 wird als ln 1,6 verrechnet (k nach erster Beobachtung ≤ 1,6^w).
   50 Beobachtungen verh 2,8 → k ≤ 2,5; verh 0,4 wiederholt → k ≥ 0,4.
10. Band: n = 0, Tag 14, G = 20 → b ≈ 0,50 → lo 50, hi 70; hi nie > 150, lo nie < start.hoehe.
    **Band am Mähtag und bei 0 mm Wachstum endlich:** `start.datum == heute` → heute.lo = heute.hi =
    start.hoehe, keine NaN im Verlauf; 30 Januar-Tage (−1/2/5 °C, R 2,5) mit `typ:"zier"`,
    `licht:"schatten"` → mm je Tag 0,00–0,02, G darf 0 sein, lo/hi überall endlich (`Number.isFinite`),
    lo ≥ start.hoehe, hi ≥ lo.
11. `sicherheit`: (n 0, 14 Tage) → „gering“; (n 5 mit p ≈ 0,011, 1 Tag) → „hoch“; (n 5, 14 Tage) → „gering“.
12. `termine`: schnitt 40, max 60, 5 mm/Tag konstant ab Mähtag (halber erster Tag) → drittel und max
    am 4. Tag nach dem Mähen (42,5 → 47,5 → 52,5 → 57,5 → 62,5), **derselbe Tag (STD)** – Art „Zielhöhe“;
    `drittel:false` → drittel null; schnitt 40, max 50 → max am 2. Tag, drittel (60) am 4. Tag, T1 > T2 →
    Text nennt nur die Zielhöhe, Suchfenster `[max(heute, T2 − 3) … T2 + 1]` nicht leer; schnitt 40, max 80 →
    T1 (Tag 4) < T2 (Tag 8), Fenster `[T1 − 2 … T2]`; 0,9 mm/Tag, 14 Tage, max 60 → max null, drittel null,
    tageBisMax null, Text „Zielhöhe nicht in den nächsten 14 Tagen“; 0,2 mm/Tag → „wächst kaum“.
    Düngung (3.4): `viel`, Datum heute − 20 → f_N 1,15; − 66 → 0,90; − 364 → 0,65; − 366 → 0,65 (kein
    Sprung); ohne Datum → 1,15; Datum heute + 5 → 0,65 und Hinweis „Düngedatum liegt in der Zukunft“.
13. `pruefeHoehe(35, …, {schnitt:40})` → ok false; `(210)` → ok false; `(90, {schnitt 40, hoeheProg 50,
    tage 7})` → ok false (Δ 50 gegen 10 = 5,0 > 4); `(75, {schnitt 40, hoeheProg 50})` → Δ 35/10 = 3,5 →
    ok TRUE mit „NICHT zur Eichung genutzt“, und `kalibrieren` mit derselben Beobachtung → `uebernommen:false`,
    Grund „Ausreißer“; `(60, …)` → 2,0 → ok true „gestutzt“; `(43,5, …)` → 0,35 → ok true, Warnung
    „NICHT … Ausreißer“ – nicht leer; `(55, …)` → 1,5 → ok true, warnung "".

---

## 13. Geprüft – Prüfpunkte vom 25.10.2026 und ihr Verbleib

Sieben Punkte aus der Durchsicht der Fassung 1.0. „Behoben“ heißt: Text, Formel, Parameter
und Testfall in dieser Fassung geändert; „zurückgewiesen“ steht mit Grund.

| Nr. | Punkt | Verbleib |
|---|---|---|
| 1 | Band teilt durch G = 0 → NaN (Mähtag, Winter) | **Behoben** (Abschnitt 7: `G <= 0 → lo = hi = start.hoehe`; Test 10 erweitert). |
| 2 | Hinweise „W = 0“ / „Dr = TAW“ feuern nie | **Behoben** (3.2, 5.7: Schwelle Ks < 0,1 an ≥ 3 Tagen in Folge; Parameter `ksTrocken`). Zurückgewiesen ist nur der Testvorschlag „Beispiel 3, Tag 10 muss den Hinweis setzen“: dort steht Ks bei 0,29 – Lehm fällt erst an Tag 16 unter 0,1; der neue Test nimmt Sand mit ET0 5 (Hinweis ab Tag 9). |
| 3 | Düngung: Sprung von 0,65 auf f_stufe bei d > 365 | **Behoben**, Variante (a): die Gabe ist ein Puls, ab 90 Tagen und für jedes ältere Datum 0,65, Hinweis fordert zum Nachtragen oder Löschen des Datums auf. Variante (b) (nach 90 Tagen zurück auf die Stufe) verworfen: dann hätte das Datum nur eine Delle 42–90 erzeugt und sonst nichts bewirkt. Nebenbei den Widerspruch „Datum in der Zukunft → w = 1“ gegen die Formel `d < 0 → 0` beseitigt (jetzt 0 mit Hinweis). |
| 4 | Bodenart `ton` wirkungslos (TAW 39 gegen 40) | **Behoben**: `ton` gestrichen (gilt als `lehm`), Grenze 3 umgeschrieben (Wurzeltiefe, nicht Bodenart), nFK als „Spannenmitten auf 5 aufgerundet (85 / 150)“ ausgewiesen; die Zahlen 90/155 und TAW 22/39 bleiben, damit alle Beispiele stehen. Eine Wurzeltiefen-Option ist NICHT eingeführt – der Vertrag kennt das Feld nicht; als nächster Schritt notiert. |
| 5 | Termine: Drittel = max bei STD; Suchfenster undefiniert bei max null / Drittel > max | **Behoben** (8.3 als Fallunterscheidung mit fünf Fällen, Fenster nie leer; 10: `max >= 1,25·schnitt`, falsche Begründung „+10“ ersetzt). Dass bei STD beide Termine zusammenfallen, ist dokumentiert und gewollt (Art „Zielhöhe“) – die Vertragsvorgabe STD 40/60 bleibt. Test 12 erweitert. |
| 6 | `pruefeHoehe` sagt „wird zur Eichung genutzt“, `kalibrieren` verwirft ab 2,8 | **Behoben** (Abschnitt 10: Schwellen 1,6 / 2,8 / 4 und 0,625 / 0,35 identisch mit 6.3; Test 13 prüft beide Funktionen gegeneinander). |
| 7 | Frühjahr und Herbst unter dem Praxisbereich; Licht und Temperatur zählen die Jahreszeit doppelt | **Teils behoben**: Rsat 10 → 6 (Oktober f_L 1, drei trübe Sommertage 0,83 statt 0,5; Licht nur noch Dämpfung Nov–Feb und im Schatten), σ 6 → 7 (Mai 2,8, Oktober 1,8 mm/Tag, Anker der Wetter-App 20,3 statt 18,9 mm). **Zurückgewiesen**: „April–Mai mindestens 3 mm/Tag“ – April mit 9,5 °C Monatsmittel bräuchte f_T ≈ 0,75, also ein Optimum um 12 °C, das den Sommer falsch macht; auch σ 7 (vom Prüfer selbst genannt) ergibt im April 1,75. Der Praxisbereich 3–6 beschreibt den Höhepunkt Mai/Juni, nicht den Monatsmittel-April (Grenze 2). Das Trapez nach Peacock ist nicht eingeführt, weil die Gauß-Form mit σ 7 die Prüfwerte trifft und die Konsistenzprüfung gegen die Wetter-App bestanden ist. Tabelle 3.5 und Tests 1/2/4/5 neu gerechnet. |

Zweite Durchsicht (Fassung 1.1, 26.10.2026): Randfall der Eichung (6.4, w_eff), Ausreißergrenze
ungeeicht 1/4–4 (6.3 Regel 5, `verhNeuBis`), Ra-Tabelle nach FAO-56 (9), `pruefeHoehe` warnt bei
Δprog < 5 und kennt `kontext.n` (10), `rate` am Deckel 0 (5.5), Termintext mit einer Klammer (8),
Herbstmaximum als Grenze 2 dokumentiert (11) – nicht modelliert, weil ein saisonaler Faktor ohne
Eichdaten geraten wäre. Tests 13, 18, 18b ergänzt.

Dritte Durchsicht (Fassung 1.2, 26.10.2026): Messvarianz der Eichung an Δ_est statt am gemessenen
Zuwachs (6.2 – Bias +11…+30 % beseitigt, Rückweg vom Rand bei kleinem Δobs 37 → 14), Regel 3 ohne
„Δobs < 5“ (6.3), `stand = max(stand, bis)` (6.4), einzelner Randwert tmin/tmax verworfen (9),
`simulieren` ohne `heute` liefert ein leeres Ergebnis statt einer Ausnahme (5.6), Termintext nennt
„nächste 7 Tage im Mittel“ (8.2). Tests 13, 18c, 18d.

Nicht beanstandet, aber beim Nachrechnen mitgezogen: Test 4 („tmean 2 → f_T < 0,02“) gilt mit
σ 7 nicht mehr (0,052) – Grenze auf ≈ 0,052 / mm ≤ 0,21 gesetzt.

---

## 14. Quellen

- Allen, Pereira, Raes, Smith (1998): *FAO Irrigation and Drainage Paper 56 – Crop
  evapotranspiration.* Kap. 6 Tab. 12 (Kc Turf grass cool season), Kap. 8 Tab. 19 (θFC, θWP),
  Tab. 22 (Zr, p für Turf), Gl. 35 (Ångström), Gl. 81/84 (Ks).
  https://www.fao.org/4/x0490e/x0490e0b.htm · https://www.fao.org/4/x0490e/x0490e0e.htm
- Gelernter, W. & Stowell, L. (PACE Turf): *Turf Growth Potential.*
  https://www.paceturf.org/reference/Turf_growth_potential
- Woods, M. (Asian Turfgrass Center): *Calculating GP* – GP = exp(−0,5((t−to)/var)²), to 20 °C C3,
  var 5,5. https://asianturfgrass.com/post/calculating-gp
- BIGGA Greenkeeper International, Mai 2007: Growth Potential, variance 10 °F cool season.
  https://archive.lib.msu.edu/tic/bigga/gki/article/2007may34.pdf
- Beard, J. B. (1973): *Turfgrass: Science and Culture.* Optimum Sprosswachstum kühler Gräser
  60–75 °F; Ein-Drittel-Regel.
- Peacock, J. M. (1975): *Temperature and leaf growth in Lolium perenne I–III.* J. Appl. Ecol. 12.
  https://britishecologicalsociety.org/applied-ecology-resources/document/19750733310
- Frontiers in Plant Science 2019: *Phenotyping leaf growth of perennial ryegrass under
  water-limiting conditions.* https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6440318/
- Schapendonk et al. (1998): LINGRA – Grasland-Wachstumsmodell (Reservepool, Lichtnutzung).
- Univ. of Arkansas / Sportsfield Management: minimale DLI 30 mol/m²/d für Agrostis-Grüns.
  https://sportsfieldmanagementonline.com/?p=8055
- UC Riverside Turfgrass: Lichtwerte und Schatten. https://turfgrass.ucr.edu/media/329/download
- MSU Turfgrass Information Center: Nebraska-Kammerversuch Schnittgutertrag vs. N-Rate.
  https://archive.lib.msu.edu/tic/mitgc/article/198917a.pdf
- Rutgers Soil Profile v09: Kentucky bluegrass 0/2/4 lb N je 1000 ft²·Jahr.
  https://njaes.rutgers.edu/soil-profile/pdfs/sp-v09.pdf
- Makkink, G. F. (1957): *Testing the Penman formula by means of lysimeters.* J. Inst. Water Eng. 11.
- Husqvarna Mähkalender (Praxis: Drittel-Regel, saisonale Schnitthäufigkeit).
  https://www.husqvarna.com/de/lernen-und-entdecken/maehkalender-saisonal-maehen/
- Wetter-App `index.html` Zeilen 5300–5495 (`rzFaellig`, Wärmesumme über 5 °C, `rzKlimaLaden`
  ERA5-Mittel 2018–2025) – Bestand, zu dem dieses Modell konsistent gehalten ist.
- Praxisbereiche Frühjahr 3–6 / Sommer 2–4 / Herbst 1–3 / Winter < 0,5 mm/Tag: Aufgabenvorgabe
  und Erfahrung, keine wissenschaftliche Quelle – als Prüfbereich verwendet, nicht als Beleg.
