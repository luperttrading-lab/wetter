# Rasen – Mähplaner (separate App)

Schätzt aus dem Wetter, wie hoch dein Rasen seit dem letzten Mähen gewachsen ist, und
schlägt den nächsten Mähtermin vor – biologisch (Ein-Drittel-Regel), nach Zielhöhe und
nach Wetter (trockenes Fenster in deiner Mähzeit). Läuft als eigene Web-App unter
`https://luperttrading-lab.github.io/wetter/rasen/` (Home-Bildschirm: Teilen → „Zum
Home-Bildschirm“), unabhängig von der Wetter-App. Daten bleiben im Gerät.

## Dateien

| Datei | Aufgabe |
|---|---|
| `index.html` | Oberfläche, Speicher (`localStorage.rasenApp`), mehrere Flächen, Diagramm, Dialoge, Benachrichtigung. Version `r1.xx` oben rechts, die Skripte werden mit `?v=` geladen (Cache). |
| `modell.js` | Wachstumsmodell – rein (kein DOM, kein Netz, keine Uhr): `tagesWachstum`, `simulieren`, `termine`, `kalibrieren`, `sicherheit`, `pruefeHoehe`, `STD`, `PARAM`. |
| `wetter.js` | Wetterdienst: Open-Meteo Tages- und Stundenwerte, Archiv-Rückfall, Cache 30 min, Fehler auf Deutsch. |
| `planer.js` | Stundenregeln „wann ist Mähen möglich“ – Port aus der Wetter-App (Abtrocknen, Tau, Boden weich, Mähzeit, Pause, Sonn-/Feiertage, Tageslicht), Fenster und Wetterwert 0–100. |
| `MODELL.md` | Vollständige Modellbeschreibung: Formeln, Parameter mit Herkunft, Eichung, Band, Grenzen, Quellen. |
| `test_modell.js` | `node rasen/test_modell.js` – 228 Prüfungen, Exit 1 bei Fehler. |
| `test_app.py` | Playwright-Integrationstest der Oberfläche (`python3 rasen/test_app.py stub` mit nachgebautem Open-Meteo, `… echt` mit Netz). |
| `manifest.webmanifest`, `icon.png`, `icon-180.png` | Home-Bildschirm. |

## Was die Oberfläche zeigt

- **Status**: geschätzte Höhe heute in cm mit 80-%-Band („wahrscheinlich 5,0–7,2 cm“), Wachstum jetzt und
  Mittel der nächsten 7 Tage in mm/Tag, zuletzt gemäht, nächster Mähtermin mit Art (Ein-Drittel / Zielhöhe /
  Wetter) und Fenster, Prognosesicherheit (gering/mittel/hoch, Zahl der Eichungen, ± am Mähtermin).
- **Diagramm**: Höhe seit dem letzten Mähen (kräftig), Prognose 14 Tage (blass, mit Band), Zielhöhe,
  Ein-Drittel-Linie, heute, empfohlener Termin. Jede Zahl im Status ist antippbar → Erklärung.
- **Wann mähen – 14 Tage**: je Tag bestes trockenes Fenster, Regenrisiko, Wetterwert im Kreis
  (empfohlener Tag grün), Sonntag/Feiertag/abgewählter Tag als Balken, zweite Woche hinter gestrichelter Linie.
- **Heute/Zuletzt gemäht**: Datum, Schnitthöhe, optional Höhe vorher (Eichung), Plausibilitätsprüfung;
  Verlauf mit Löschen. **Einstellungen**: Schnitt-/Zielhöhe, Ein-Drittel-Regel, Rasentyp, Boden,
  Bewässerung, Düngung, Licht, Mähzeit/Pause/Tage/Dauer/Regenrisiko, Benachrichtigung, Flächen (neu,
  umbenennen, Ort per Suche/GPS/Hand, löschen).

## Modell in Kürze

Höhe(t+1) = Höhe(t) + Wachstum(t), Wachstum = Gmax · k · f_T · f_W · f_L · f_N, nie negativ,
Deckel 150 mm (darüber „nicht mehr gerechnet – bitte mähen“). Details und alle 45 Parameter in `MODELL.md`.

| Parameter | Wert | Herkunft |
|---|---|---|
| Gmax | 4,0 mm/Tag | Schätzwert (Praxis 2–3 cm/Woche Mai/Juni; wie Wetter-App gd = 60) |
| f_T: Gauß, Topt / σ | 19 °C / 7 °C | PACE-Turf-Form (Gelernter & Stowell; dort 20 / 5,5), angepasst – Schätzwert |
| f_W: FAO-56-Bilanz, nFK Sand/Lehm, Wurzelraum, p, Kc | 90 / 155 mm/m, 0,25 m, 0,45, 0,90 | FAO-56 Tab. 12/19/22; Wurzelraum Schätzwert |
| f_L: Sättigung Rsat, Schatten | 6 MJ/m²/Tag; 1 / 0,75 / 0,5 | Schätzwert |
| f_N: Düngestufe | 0,65 / 0,85 / 1,00 / 1,15, Puls 42/90 Tage | Schätzwert, Richtung belegt |
| Eichfaktor k | 0,4–2,5 | Vorgabe |
| Ein-Drittel-Regel | mähen ab 1,5 × Schnitthöhe | Beard 1973 |
| Band | 80 %, ±50 % ungeeicht, ≥ ±30 % bei ≥ 5 Eichungen | Schätzwert |

## Eichung

Gelernt wird nur der Gesamtfaktor k je Fläche (aus Höhenmessungen lassen sich Temperatur-, Wasser- und
Düngewirkung nicht trennen). Trägst du beim Mähen die Höhe vorher ein, vergleicht die App den gemessenen
mit dem vorhergesagten Zuwachs des Intervalls: Kalman-Filter in ln k, Messfehler 5 mm, Modellfehler je nach
Intervalllänge, Huber-Stutzung (ein Eintrag ändert k höchstens um Faktor 1,6), Ausreißer werden verworfen
(Verhältnis außerhalb 0,35–2,8; bei weniger als 2 Eichungen 1/4–4), Prozessrauschen lässt alte Eichungen
langsam verblassen. Löschen oder Ändern eines Eintrags rechnet die Eichung aus der Liste neu.

## Daten

Je Öffnen (höchstens alle 30 min, sonst Cache) zwei Abrufe bei Open-Meteo: Tageswerte (Mittel/Min/Max,
Regen, Strahlung, ET0, Sonne, Auf-/Untergang; bis 92 Tage zurück, 16 voraus) und Stundenwerte (3 zurück,
16 voraus). Liegt das letzte Mähen länger als 92 Tage zurück, einmal zusätzlich das Open-Meteo-Archiv.
Ohne Netz: alter Cache mit Hinweis; ohne Cache: Klimawerte, Hinweis, Knopf „Erneut versuchen“.
Ortssuche: Open-Meteo Geocoding. Keine Daten verlassen das Gerät außer Koordinaten an Open-Meteo und,
wenn eingeschaltet, Nachrichten an ntfy.sh.

## Speicher

`localStorage.rasenApp = {v:1, aktiv, flaechen:[{id, name, lat, lon, tz, einst, historie:[{datum, schnitt,
hoeheVorher, hoeheProg}], kal:{k, n, p, stand, log}, benachrichtigung:{an, topic, geplant, letzt}}]}`.
Beim ersten Start wird der Ort der Wetter-App (`locProfile`) übernommen, sonst Wettenberg.

## Benachrichtigung (aus, bis eingeschaltet)

ntfy.sh mit eigenem geheimen Topic (ntfy-App installieren, Topic abonnieren). Die App plant beim Öffnen
zeitversetzte Nachrichten (bis 3 Tage): „Zielhöhe in N Tagen“, „morgen günstiger Mähtermin, danach Regen“.
Grenzen: nur wenn die App geöffnet wird; einmal geplante Nachrichten lassen sich nicht zurücknehmen;
wer das Topic kennt, kann mitlesen.

## Tests

`node rasen/test_modell.js` (Winterruhe, Trockenheit, Starkregen, Frühjahr, fehlende Werte, unplausible
Höhen, wechselnde Schnitthöhen, zwei Flächen, Konvergenz der Eichung, Termine, Band).
`python3 rasen/test_app.py stub` braucht Playwright-Chromium und `python3 -m http.server 8899` in der Repo-Wurzel.

## Einschränkungen (ehrlich)

- Ohne Eichung ist die Höhe eine Schätzung mit Faktor-2-Unsicherheit; Sorte, Boden, Düngung, Verfilzung
  gehen nur grob ein. Die ersten 2–3 Mähvorgänge mit gemessener Höhe sind die eigentliche Eichung.
- Die zweite Vorhersagewoche ist grob; der Wettertermin gilt bis ~5 Tage voraus verlässlich.
- Open-Meteo-Zeiten mit festem Versatz: um die Zeitumstellung sind Stunden bis zu 1 h verschoben.
- Modellgrenze 15 cm; darüber keine Rechnung. Bewässerung wird nicht gemessen, nur als Stufe angenommen.
