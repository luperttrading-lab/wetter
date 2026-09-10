# Datenquellen, Lizenzen und Kosten

Stand 10.09.2026. Geprueft, als die Frage aufkam, ob die App verkauft oder
mit Abo betrieben werden koennte. Fuer den heutigen Betrieb (private Seite
auf GitHub Pages, ein Nutzer, keine Werbung) ist alles frei — die Spalte
"kommerziell" gilt nur fuer den hypothetischen Verkaufsfall.

| Quelle | Wofuer | heute | kommerziell |
|---|---|---|---|
| opendata.dwd.de | Sonnenscheindauer, Strahlung, RADOLAN, Solar-10-Minuten | frei | frei, Namensnennung |
| api.brightsky.dev | Wetterstationen in der App | frei | frei, nur DWD-Bedingungen |
| api.open-meteo.com, air-quality-api.open-meteo.com | Vorhersage, CAMS-UV, Wolkenschichten | frei | **kostenpflichtig** |
| nominatim.openstreetmap.org | Ortssuche | frei | eingeschraenkt |
| server.arcgisonline.com (World_Imagery) | Satellitenkacheln der Wolkenkarte | geduldet | **nicht erlaubt** |
| uvi.bfs.de | UV-Tagesgrafiken (Bildauswertung) | frei | ungeklaert |
| GitHub Actions und Pages | Rechnen, Ausliefern | frei (Repo oeffentlich) | frei, solange oeffentlich |

## Die drei Punkte, die im Verkaufsfall zu klaeren waeren

**Esri-Satellitenkacheln — der einzige harte Verstoss.** `WOLK_TILE` in
index.html holt die Kacheln ohne Schluessel direkt von Esris Servern. Das
ist geduldet, solange niemand damit Geld verdient. Ersatz gaebe es:
Sentinel-2 ueber EOX oder OpenStreetMap-Kacheln, beide frei. Das waere der
erste Handgriff, nicht der letzte.

**Open-Meteo.** Kostenlos nur "for non-commercial purposes"; ausgeschlossen
sind laut deren Bedingungen Seiten mit Werbung oder Abo und kommerzielle
Produkte. Grenzen der freien Stufe: 10.000 Aufrufe am Tag, 5.000 je Stunde,
600 je Minute, Lizenz CC-BY 4.0. Davon sind wir weit entfernt — die Action
fragt einmal am Tag rund 80-mal.
Die Preisseite nennt nur Kontingente (Standard 1 Mio. Aufrufe im Monat,
Professional 5 Mio. mit Historie, Enterprise ab 50 Mio.), **keine
Eurobetraege**; dafuer info@open-meteo.com anschreiben. Der Server steht
unter AGPLv3 und laesst sich selbst betreiben — die Daten kommen ohnehin
vom DWD und sind frei.
(Frueher stand hier von mir eine Zahl von 29 Euro im Monat. Die war
geraten, nicht nachgeschlagen, und ist geloescht.)

**Nominatim.** Kommerziell erlaubt, aber hoechstens 1 Anfrage je Sekunde,
und Dienste, deren *Hauptfunktion* Geocoding ist, muessen eine eigene
Instanz betreiben. Bei uns ist die Ortssuche Nebensache, das passt. Verboten
sind ausserdem Auto-Vervollstaendigung waehrend des Tippens und
systematisches Abfragen.

## Was tatsaechlich Geld kostet

Nicht die Daten, sondern Claude: die taegliche Routine um 10:00 Uhr morgens
rund 1 $ mit Sonnet 5, dazu die Entwicklungschats.

Ein Nebenpunkt: Der Solar-Laeufer alle 15 Minuten braucht etwa 100
Action-Minuten am Tag. Bei einem oeffentlichen Repo unbegrenzt frei. Wuerde
das Repo privat, griffe das Monatskontingent und es waere nach etwa drei
Wochen aufgebraucht. Also: Repo oeffentlich lassen.
