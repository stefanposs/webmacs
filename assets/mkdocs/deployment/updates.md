---
title: System-Updates (One-Click)
---

## Übersicht

Dieses Kapitel beschreibt die neuen systemweiten Update-Funktionen: eine API, mit der die WebGUI installierte/ verfügbare Versionen anzeigt, sowie ein One-Click-Update-Trigger, der direkt Docker-Images zieht und den Stack neu startet.

## API-Endpunkte

- `GET /api/v1/system/versions` — Liefert die installierten Versionen der Dienste (`backend`, `frontend`, `controller`).
- `POST /api/v1/system/trigger` — Akzeptiert JSON mit optionalen Feldern `backend_image`, `frontend_image`, `controller_image` oder `version`. Startet im Hintergrund `docker pull` für die angegebenen Images und versucht anschließend, den Compose-Stack neu zu starten. Nur Administratoren dürfen diesen Endpunkt aufrufen.

Beispiel: Trigger per Version

```json
POST /api/v1/system/trigger
{
  "version": "2.3.1"
}
```

## Verhalten des Updaters

- Beim Anwenden von OTA-Bundles erstellt der Updater standardmäßig ein `pg_dump`-Backup vor dem Einspielen. Wenn das Backup fehlschlägt, bricht der Updater den Vorgang ab.
- Falls gewünscht, kann dieses Verhalten mit der Umgebungsvariablen `WEBMACS_UPDATER_ALLOW_NO_BACKUP=1` überschrieben werden — dadurch läuft das Update auch ohne erfolgreiches DB-Backup weiter (unsicher, nur für Experten).

## WebGUI

- Die WebGUI zeigt jetzt verfügbare GitHub-Releases (falls konfiguriert) und bietet im OTA-View einen `One-Click Update`-Button, der `POST /api/v1/system/trigger` mit der Ziel-Version aufruft.

## Sicherheitshinweis

- Der `trigger`-Endpunkt führt `docker pull` und `docker compose up` auf dem Host aus. Stelle sicher, dass nur vertrauenswürdige Administratoren Zugriff haben und dass der Docker-Socket nicht für unautorisierte Prozesse freigegeben ist.
