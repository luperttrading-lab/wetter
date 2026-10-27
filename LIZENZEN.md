# Datenquellen, Lizenzen und Kosten

Stand 27.10.2026 (erste Fassung 10.09.2026). Anlass beider Fassungen: die Frage, ob die App
verkauft, mit Abo/Werbung betrieben oder im App Store veroeffentlicht werden koennte. Fuer den
heutigen Betrieb (private Seite auf GitHub Pages, keine Werbung, kein Geld) ist alles frei - die
Spalte "kommerziell" gilt fuer den Fall, dass Geld fliesst (Kaufpreis, Abo, Werbung).

Markierung wie im Chat: [Sicher] = auf der Seite des Anbieters gelesen, [Wahrscheinlich] = aus
Drittquellen oder abgeleitet, [Vermutung] = nicht belegt.

| Quelle | Wofuer | heute | kommerziell |
|---|---|---|---|
| opendata.dwd.de | Sonnenschein, Strahlung, RADOLAN, Solar-10-Minuten, Pollen | frei | frei, CC BY 4.0, Quelle nennen [Sicher] |
| api.brightsky.dev | Messung, Radar, Warnungen, MOSMIX | frei | "free-to-use for all purposes", DWD-Bedingungen gelten, keine Ratenbegrenzung veroeffentlicht, selbst betreibbar [Sicher] |
| api / air-quality-api / archive-api / geocoding-api .open-meteo.com | Vorhersage, CAMS-UV/Luft/Pollen, Wolkenkarte, Rasen (Stunden, Klima), Ortssuche Rasen-App | frei (nicht kommerziell) | **Abo noetig** [Sicher], siehe unten |
| nominatim.openstreetmap.org | Ortssuche Wetter-App | frei | erlaubt mit Grenzen (1 Anfrage/s, kein Tippen-Vervollstaendigen) |
| server.arcgisonline.com (World_Imagery), services.arcgisonline.com (World_Hillshade) | Satellit in Wolken- und Regenkarte, Untergrund "Relief" | geduldet | **nicht gedeckt** ohne Esri-Konto, siehe unten |
| uvi.bfs.de, bfs.de | UV-Tagesgrafiken (Bildauswertung) | frei | ungeklaert |
| api.wheretheiss.at | ISS-Bahndaten (TLE) | frei | nicht geprueft |
| ntfy.sh | Erinnerung der Rasen-App | frei | nicht geprueft; im App Store ersetzt durch echte iPhone-Nachrichten (APNs) |
| daten.gdz.bkg.bund.de (VG250) | Grenzen in den Karten (`grenzen.json`) | frei | frei, "© GeoBasis-DE / BKG (Jahr)" (dl-de/by-2-0) |
| Mondfoto (`MOON_IMG`, eingebettet in index.html) | Mondanzeige | - | **Herkunft unbekannt** - vor jeder Veroeffentlichung klaeren |
| GitHub Pages und Actions | Ausliefern, Datenlaeufe | frei (Repo oeffentlich) | Pages **nicht** fuer Geschaeft/SaaS [Sicher], siehe unten |

## Esri - der haerteste Punkt

[Sicher] World Imagery steht unter dem Esri Master License Agreement (Angabe im Datensatz selbst,
`arcgis.com/sharing/rest/content/items/10df2279f9684e4a9f6a7f08febac2a9?f=json`), Quellvermerk
"Esri, Vantor, Earthstar Geographics, and the GIS User Community". [Wahrscheinlich] Ohne Esri-Konto
und -Schluessel ist die Nutzung in einer fremden App nicht gedeckt - auch nicht in einer Gratis-App
im Store. Betroffen: `WOLK_TILE` (Wolkenkarte, Regenkarte "Satellit") und `RK_GRUND` "Relief"
(World_Hillshade). Wege:
- Regenkarte: "Grau" (v5.39) braucht keine Kacheln.
- ArcGIS Location Platform mit Schluessel: 2 Mio. Basiskarten-Kacheln im Monat frei, danach 0,15 $
  je 1000 [Sicher, Preisseite]; ob das kommerziell erlaubt ist, steht dort nicht.
- Sentinel-2 (EOX) oder OSM-Kacheln - Lizenzen je Jahrgang/Anbieter vorher pruefen.

## Open-Meteo

[Sicher] Freie Stufe nur nicht kommerziell, 600 Abrufe/min, 5000/h, 10.000/Tag, 300.000/Monat; die
Preisseite nennt sie "fuer Ausprobieren und Prototypen". Nicht kommerziell sind laut Bedingungen u. a.
"private or non-profit websites or apps that do not have subscriptions or advertising"; kommerziell
sind Seiten/Apps mit Abo oder Werbung und kommerzielle Produkte. Daten unter CC BY 4.0 (Namensnennung
Pflicht, auch kommerziell). App-Store-Verteilung erwaehnen die Bedingungen nicht - fuer eine Gratis-App
ohne Werbung bei info@open-meteo.com schriftlich bestaetigen lassen.

Abos: Standard 1 Mio. Abrufe/Monat, Professional 5 Mio. (mit Historical/Climate/Ensemble),
Enterprise ab 50 Mio. [Sicher]. Die offizielle Seite nennt KEINE Preise. [Wahrscheinlich] Standard
29 im Monat (Waehrung je Quelle $ oder EUR), Professional 99 - nur aus Drittquellen (apio.sh,
ein GitHub-Issue mit Dashboard-Angabe 29 EUR). Unser `archive-api` (Klima der Rasenplanung, `rzKlimaLaden`)
ist Historical Weather -> laut Preis-FAQ erst ab Professional; Ausweg: Klimamittel einmal vorrechnen
und als Datei ausliefern.

Zaehlweise: mehr als 10 Variablen oder mehr als 2 Wochen je Ort zaehlen anteilig mehrfach (15
Variablen x 2 Wochen = 1,5 Abrufe) [Sicher]. Wie eine Abfrage mit mehreren Orten zaehlt, steht
nirgends; der Blog nennt sie "wie eine Schleife ueber Einzelabrufe" [Vermutung: zaehlt je Ort].

GEMESSEN 27.10.2026 (Playwright, App-Start, 25 s): je Start 4-6 Anfragen an api.open-meteo.com
(neue Nutzer 4, alles offen 6), dazu 1 air-quality, bei offenem Rasen 1 archive; EINE davon ist die
Wolkenkarte mit 100 Orten (`wolkenURL`, 10 x 10). Solange die App offen ist, laedt sie alle 30 min
komplett neu (`REFRESH_FULL_MS`). Hochrechnung je Nutzer und Tag (3-5 Starts): 15-30 Abrufe, wenn die
Wolkenkarte als einer zaehlt -> Standard reicht fuer ~1000-2000 taegliche Nutzer; 300-500, wenn sie
als 100 zaehlt -> nur ~70-110. EMPFEHLUNG fuer jeden Ausbau: Wolkenkarte (und alles, was nicht vom
genauen Ort abhaengt) einmal zentral auf einem eigenen Server holen und allen ausliefern - dann haengt
die Rechnung nicht mehr an der Nutzerzahl.

Selbst betreiben geht (Server unter AGPLv3), die Modelldaten selbst sind frei.

## GitHub

[Sicher] Pages ist "not intended for or allowed to be used as a free web-hosting service to run your
online business ... or providing commercial software as a service"; weiche Grenze 100 GB Datenverkehr im
Monat. Fuer den heutigen privaten Betrieb passt das. Bei Preis/Abo/Werbung: Seite und Datenlaeufe
(RADOLAN, Solar-10, Pollen, UV) auf einen eigenen Server [Vermutung: einige Euro im Monat].
Actions sind bei oeffentlichem Repo unbegrenzt frei; wuerde das Repo privat, waere das Monatskontingent
nach etwa drei Wochen aufgebraucht (Solar-Laeufer allein ~100 min/Tag). Also: Repo oeffentlich lassen.

## App Store (geprueft 27.10.2026)

- Apple-Entwicklerprogramm 99 $ im Jahr [Sicher, developer.apple.com/programs]; in Deutschland
  laut aelteren Berichten 99 EUR [Wahrscheinlich].
- Provision 15 % auf Verkaeufe und In-App-Kaeufe bis 1 Mio. $ Erloes im Jahr (Small Business Program),
  bei EU-Alternativbedingungen 10 % [Sicher]. Gratis-App: keine Provision.
- EU-Plattformgesetz (DSA): Wer mit einer App Geld verdient (auch Werbung), ist "Haendler" - Name,
  Anschrift, Telefon, E-Mail stehen im Store. Nur ganz kostenlose Apps ohne Werbung sind ausgenommen.
  Apps ohne Angabe wurden im Februar 2025 aus dem EU-Store genommen [Sicher, heise].
- Regel 4.2: mehr als eine "repackaged website" [Sicher]. Hochladen geht nur als iOS-App (Huelle um die
  Seite, z. B. Capacitor/WKWebView, gebaut mit Xcode auf einem Mac oder Cloud-Mac). Echte iPhone-
  Nachrichten statt ntfy und ein ordentlicher Offline-Zustand machen die Pruefung sicherer [Wahrscheinlich].
- Regel 2.5.2: kein nachgeladener Code, der Funktionen aendert [Sicher]. Folge: entweder jede Aenderung
  durch Apples Pruefung (Release-Takt Wochen statt Stunden, Update-Balken `checkUpdate` entfaellt) oder die
  Seite live laden (technisch moeglich, gegen den Wortlaut).
- Regel 5.1.1: Datenschutzerklaerung Pflicht, im Store und in der App [Sicher]. Sie muss nennen, dass der
  Standort an Open-Meteo, Bright Sky, Esri, Nominatim und wheretheiss.at geht; dazu die Datenschutz-Angaben
  in App Store Connect. Quellenvermerke: Fuss der Wetter-App nennt DWD/Bright Sky und Open-Meteo/CAMS,
  ein Hinweis auf CC BY 4.0 fehlt; Rasen-App pruefen.
- Gewerbe, Steuer, Impressum bei Verkauf: Steuerberater - nicht geprueft.

## Was tatsaechlich Geld kostet

Heute nicht die Daten, sondern die Entwicklung mit Claude (dieser Chat vom 21. bis 27.10.2026 rund
298 $). Im App-Store-Fall kaemen dazu: 99 $/Jahr Apple; bei Preis/Abo/Werbung 15 %
Provision, Open-Meteo-Abo (je nach Nutzerzahl und Zaehlweise Standard oder Professional) und ein
eigener Server.

## Quellen (27.10.2026)

developer.apple.com/programs, /app-store/review/guidelines, /app-store/small-business-program;
heise.de/-9838371 und heise.de/en/news/...-10247298 (DSA); open-meteo.com/en/pricing, /en/terms,
openmeteo.substack.com/p/weather-data-for-multiple-locations, apio.sh/apis/open-meteo;
location.arcgis.com/pricing; arcgis.com Datensatz 10df2279f9684e4a9f6a7f08febac2a9; brightsky.dev;
opendata.dwd.de/climate_environment/CDC/Nutzungsbedingungen_German.pdf;
docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits.
