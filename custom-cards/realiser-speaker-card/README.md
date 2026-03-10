# Realiser A16 Speaker Grid Custom Card

<p align="center">
  <img src="https://raw.githubusercontent.com/benzman/realiser-a16-ha/main/assets/logo-realiser-a16.svg" alt="Realiser A16 Logo" width="80"/>
</p>

Ein benutzerdefiniertes Home Assistant Lovelace Card zur Anzeige und Steuerung Ihrer Realiser A16 Lautsprecher in einer Grid-Ansicht, ähnlich wie die Beispiel-Weboberfläche.

## Features

- Visuelle Grid-Ansicht aller 52 möglichen Lautsprecherpositionen
- Farbcodierung nach Lautsprechertyp:
  - **Grün**: Floor (Standlautsprecher, Regallautsprecher)
  - **Orange**: Height (Höhenlautsprecher für Dolby Atmos)
  - **Violett**: Overhead (Deckenlautsprecher)
  - **Gelb**: Under (Unterhalb der Ohrhöhe)
  - **Rot**: LFE (Subwoofer)
- Anzeige des aktuellen Status (aktiv/muted) mit abgedunkelten Farben
- Klick auf jeden Lautsprecher zum Solo/Mute (abhängig vom Modus)
- "ALL" Button zum Umschalten zwischen SOLO und MUTE ALL Modi
- "Visibility" und "Refresh" Buttons für manuelle Datenaktualisierung
- Automatische Synchronisierung mit dem Realiser A16 Gerät

## Voraussetzungen

- Home Assistant Installation
- **Realiser A16 Integration v0.2.0 oder neuer** (für den refresh_speakers Service)
- Die Integration muss mit `enable_speaker_switches: true` konfiguriert sein, um individuelle Lautsprechersteuerung zu aktivieren

## Voraussetzungen

- Home Assistant Installation
- Realiser A16 Integration muss installiert und konfiguriert sein
- Die Integration muss mit `enable_speaker_switches: true` konfiguriert sein, um individuelle Lautsprechersteuerung zu aktivieren

## Installation

### Option 1: Über die `www` Verzeichnis (einfachste Methode)

1. Laden Sie die Datei `realiser-speaker-card.js` herunter und platzieren Sie sie im `www` Verzeichnis Ihrer Home Assistant Installation:

```bash
# In Ihrer Home Assistant Konfiguration:
cp realiser-speaker-card.js /homeassistant/www/
```

2. In Home Assistant gehen Sie zu **Lovelace Dashboards → Ressourcen** (oben rechts die drei Punkte → Ressourcen)

3. Fügen Sie eine neue Ressource hinzu:
   - Typ: `JavaScript Module`
   - URL: `/local/realiser-speaker-card.js?v=1`
   - Reihenfolge: `100` oder höher

4. Speichern und Ihre Custom Card ist verfügbar!

### Option 2: Über HACS (empfohlen für fortgeschrittene Benutzer)

1. HACS installieren (falls noch nicht geschehen)
2. In HACS → Frontend → "+" → "Repository"
3. Repository URL dieses Projekts hinzufügen
4. Die Custom Card herunterladen und installieren
5. Lovelace neu laden

## Konfiguration in Lovelace

Fügen Sie in Ihrem Dashboard eine neue Karte hinzu (über "Karte hinzufügen" → "Benutzerdefinierte Karte"):

```yaml
type: custom:realiser-speaker-card
entity: sensor.realiser_a16_speakers
```

### Optionale Konfiguration

```yaml
type: custom:realiser-speaker-card
entity: sensor.realiser_a16_speakers
title: "Speaker Grid"
```

## Wichtige Hinweise

- Die Karte erfordert, dass der `sensor.realiser_a16_speakers` Sensor existiert. Dieser wird automatisch von der Realiser A16 Integration erstellt.
- Für die Steuerung einzelner Lautsprecher müssen die Schalter (`switch.realiser_a16_speaker_*`) verfügbar sein. Dies wird durch `enable_speaker_switches: true` in der Integration-Konfiguration aktiviert.
- Der "ALL" Button steuert den `switch.realiser_a16_all_solo` Schalter zwischen SOLO und MUTE ALL Modi.
- Die Grid-Anordnung folgt einer typischen 9.1.6 (oder ähnlich) Lautsprecherkonfiguration. Nicht genutzte Positionen sind ausgegraut.
- Die Karte aktualisiert sich automatisch, wenn sich der Status der Lautsprecher oder der Modus ändert.

## Fehlerbehebung

### Karte zeigt "Configuration Error" oder lädt nicht
1. **Prüfe die Entity ID**: Stelle sicher, dass `sensor.realiser_a16_speakers` existiert ( Developer Tools → States suchen)
2. **Integration Version**: Du brauchst Realiser A16 Integration **v0.2.0 oder neuer** für den `refresh_speakers` Service
3. **Ressource prüfen**: Öffne im Browser `http://deine-ha-ip:8123/local/realiser-speaker-card.js` - müsste die JS-Datei anzeigen
4. **Browser Konsole**: Drücke F12 → Console, dort stehen oft genauere Fehlermeldungen

### "Service not found" Fehler in Konsole
- Die Integration ist zu alt (vor v0.2.0). Aktualisiere auf v0.2.0+
- Oder der Service ist nicht verfügbar, weil die Integration nicht geladen wurde

### Keine oder falsche Lautsprecher angezeigt
- Stelle sicher, dass `enable_speaker_switches: true` in der Integration aktiviert ist
- Prüfe, ob das Realiser A16 Gerät die Speaker-Daten liefert (0xAE und 0xAF Befehle)
- Nicht alle 52 Positionen sind bei jedem Setup belegt; nicht sichtbare Speaker sind ausgegraut

### Buttons reagieren nicht
- Die `switch.realiser_a16_speaker_*` Entitäten müssen existieren (nur mit `enable_speaker_switches: true`)
- Prüfe die Home Assistant Logs auf Fehler bei Service-Aufrufen

## Anpassung der Farben und Anordnung

Die JavaScript-Datei kann bei Bedarf angepasst werden:

- **Farben**: Ändern Sie die CSS-Variablen im `_injectStyles()` Methode
- **Layout**: Ändern Sie die `gridLayout` Arrays in der `_render()` Methode (die 7 Reihen)
- **Lautsprecher-Zuordnung**: Ändern Sie die `_getSpeakerColor()` Methode, um andere Speaker-IDs anderen Typen zuzuordnen

## Lizenz

Diese Custom Card wird im Rahmen der Realiser A16 Home Assistant Integration bereitgestellt. Überprüfen Sie die Lizenz der Hauptintegration für Details.

## Unterstützung

Bei Problemen oder Fragen erstellen Sie bitte ein Issue im GitHub Repository der Realiser A16 Integration.