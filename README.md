# Notion Dashboard Sync

Ein Tool zur Synchronisierung und KI-gestützten Optimierung von Notion Dashboards.

## Setup

1. Python-Umgebung einrichten:
   ```bash
   python -m venv notion_sync_env
   notion_sync_env\Scripts\activate
   pip install -r requirements.txt
   ```

2. `.env` Datei erstellen:
   ```
   NOTION_TOKEN=your_token_here
   NOTION_DASHBOARD_ID=your_dashboard_id
   ```

3. Ollama Server starten (für KI-Optimierung)

## Verwendung

- Nur Sync: `run_notion_sync.bat`
- Sync mit KI-Optimierung: `run_notion_sync_with_llm.bat`

## Struktur

- `auto_notion_sync.py`: Hauptsynchronisierungslogik
- `process_updates.py`: KI-gestützte Optimierung
- `config.py`: Konfigurationseinstellungen
- `notion_export/`: Exportierte Dashboard-Dateien 