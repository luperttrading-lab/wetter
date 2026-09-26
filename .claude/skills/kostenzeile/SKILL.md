---
name: kostenzeile
description: Kostenzeile unter jede Antwort haengen - Datum, Dauer der Bearbeitung und API-Gegenwert (Frage, heute, gesamte Sitzung). Nutze diese Skill, wenn der Nutzer nach Kosten, Token-Verbrauch, Cache-Preisen oder der Dauer einer Antwort fragt, wenn die Kostenzeile fehlt oder falsch aussieht, wenn "tools/kosten.py" nicht vorhanden ist und angelegt werden muss, oder wenn eine KOSTENZEILE.md hochgeladen wird. Enthaelt das fertige Skript, die geprueften Preise und den Ablauf.
---

# Kostenzeile

## Ablauf, ohne Ausnahme

1. `python3 tools/kosten.py` ausfuehren.
2. Die Ausgabe **woertlich** als letzte Zeile der Antwort setzen.
3. Nichts dahinter, nicht umformatieren, nicht schaetzen.

So sieht sie aus:

```
<sub>26.09. 19:35 Uhr · Arbeit 4 min · Frage 4,26 · heute 4,26 · ges. 35,44 $</sub>
```

Bedeutung der Werte:

- **Uhrzeit** — Ortszeit (Europe/Berlin), nicht UTC.
- **Arbeit** — Spanne vom letzten echten Nutzerbeitrag bis jetzt. Unter einer
  Minute `<1 min`, ab 90 Minuten `1 h 34 min`; liegt der Beitrag mehr als
  36 Stunden zurueck, faellt das Feld weg.
- **Frage** — alle Antworten seit dem letzten echten Nutzerbeitrag, diese Sitzung.
- **heute** — Summe des lokalen Tages ueber **alle** Projekte.
- **ges.** — die gesamte laufende Sitzung.

## Wenn das Skript fehlt

`tools/kosten.py` liegt neben dieser Datei als `kosten.py`. Fehlt es im
Arbeitsverzeichnis, kopieren:

```bash
mkdir -p tools && cp "$CLAUDE_SKILL_DIR/kosten.py" tools/kosten.py
```

Steht `$CLAUDE_SKILL_DIR` nicht zur Verfuegung, die Datei aus dem Ordner dieser
SKILL.md nehmen.

## Wenn es nicht laeuft

Offen sagen statt eine Zahl erfinden. Die drei Ursachen:

1. **Kein Sitzungsprotokoll** unter `~/.claude/projects` — andere Umgebung, oder
   die normale Claude-App ohne Bash. Dann geht es grundsaetzlich nicht.
2. **Falsches Verzeichnis** — das Skript sucht den Projektpfad aufwaerts durch die
   Elternordner und warnt auf stderr, wenn es auf ein fremdes Projekt ausweicht.
3. **Nachfrage bei jedem Aufruf** — dann fehlt die Freigabe in
   `.claude/settings.json`:

```json
{ "permissions": { "allow": ["Bash(python3 tools/kosten.py)",
                             "Bash(python3 tools/kosten.py *)"] } }
```

## Preise

Geprueft am 08.09.2026 gegen <https://platform.claude.com/docs/en/about-claude/pricing>.
Das Skript haelt je Modell nur Eingabe- und Ausgabepreis; die Cachepreise leitet es
aus den dokumentierten Faktoren ab (5 min = 1,25x Eingabe, 1 h = 2x Eingabe,
Lesen = 0,1x Eingabe, bei Fable/Mythos 5.1 = 0,025x). Mitgerechnet werden Fast Mode,
US-Datenresidenz und Websuchen.

Es sind API-Listenpreise, keine Rechnung. Mit Abo zahlt man den Pauschalpreis.
