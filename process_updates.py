import json
import logging
from pathlib import Path
from datetime import datetime
from auto_notion_sync import NotionSync, setup_logging
from dotenv import load_dotenv
import os
import requests
import time
import sys

class OllamaProcessor:
    def __init__(self, model_name="qwen2.5-coder-extra-ctx:7b", api_base="http://localhost:11434"):
        self.model_name = model_name
        self.api_base = api_base
        self.session = requests.Session()  # Wiederverwendbare Session
        try:
            self._validate_connection()
        except Exception as e:
            logging.error(f"Failed to initialize OllamaProcessor: {str(e)}")
            raise
    
    def _validate_connection(self):
        """Überprüft die Verbindung zum Ollama-Server"""
        try:
            response = self.session.get(f"{self.api_base}/api/version")
            if response.status_code != 200:
                raise ConnectionError(f"Ollama server not responding correctly: {response.status_code}")
            logging.info(f"Successfully connected to Ollama server")
        except Exception as e:
            logging.error(f"Failed to connect to Ollama server: {str(e)}")
            raise

    def optimize_section(self, content, section_name, retries=3):
        if not content.strip():
            logging.warning(f"Empty content received for section: {section_name}")
            return content
        
        for attempt in range(retries):
            try:
                prompt = f"""Du bist ein KI-Assistent, der einen Dashboard-Abschnitt für {section_name} optimiert.
Hier ist der aktuelle Inhalt:

{content}

Formatiere den Inhalt EXAKT nach diesem Schema:

# {section_name}

### Übersicht & Status
| Bereich | Status | Priorität | Nächste Aktion |
| --- | --- | --- | --- |
[Bestehende Tabelle mit Emojis für Status: ✅ ⚠️ ❌]

### Aktuelle Situation
- Maximal 3 wichtigste Kernpunkte
- Fokus auf aktuelle Herausforderungen
- Klare, actionable Aussagen

### Nächste Schritte
1. [Konkrete Aktion] bis [Datum]
2. [Konkrete Aktion] bis [Datum]
3. [Konkrete Aktion] bis [Datum]

### Tracking & Notizen
- Messbare Erfolge/KPIs
- Blockaden & Lösungen
- Wichtige Erkenntnisse

Spezielle Regeln für {section_name}:
- Gesundheit: Laborwerte und Medikation priorisieren
- Business: Fokus auf konkrete Projekte und Deadlines
- Beziehung: Klare Grenzen und Kommunikationsziele
- ARCHIV: Nur relevante Hintergrundinformationen

Wichtig:
1. Behalte alle wichtigen Informationen bei
2. Nutze klare, actionable Formulierungen
3. Setze konkrete Termine
4. Priorisiere nach Dringlichkeit
5. Behalte medizinische Details bei

Gib NUR den formatierten Inhalt zurück."""

                logging.info(f"Optimiere Abschnitt: {section_name}")
                
                response = self.session.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "top_p": 0.9,
                            "timeout": 30
                        }
                    },
                    timeout=35
                )
                
                response.raise_for_status()
                result = response.json()
                logging.info(f"Successfully optimized section: {section_name}")
                return result['response']
                
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    logging.error(f"Failed to optimize section after {retries} attempts: {str(e)}")
                    return content
                logging.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(2 ** attempt)

def main():
    setup_logging()
    load_dotenv()
    
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    DASHBOARD_ID = os.getenv('NOTION_DASHBOARD_ID')
    
    if not all([NOTION_TOKEN, DASHBOARD_ID]):
        logging.error("Missing required environment variables")
        sys.exit(1)
    
    try:
        syncer = NotionSync(NOTION_TOKEN)
    except Exception as e:
        logging.error(f"Failed to initialize NotionSync: {str(e)}")
        sys.exit(1)
    
    # Get latest dashboard file
    dashboard_files = sorted(
        list(Path("notion_export").glob("master_dashboard_*.md")),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not dashboard_files:
        logging.error("No dashboard files found in notion_export directory")
        sys.exit(1)
    
    try:
        content = dashboard_files[0].read_text(encoding='utf-8')
    except Exception as e:
        logging.error(f"Failed to read dashboard file: {str(e)}")
        sys.exit(1)
        
    # Split content into sections
    sections = {}
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        if line.startswith('# '):
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = line[2:].strip()
            current_content = [line]
        else:
            if current_section:
                current_content.append(line)
    
    if current_section:
        sections[current_section] = '\n'.join(current_content)
    
    # Process each section
    processor = OllamaProcessor()
    success = False
    
    for section_name, section_content in sections.items():
        try:
            # Optimize section content
            optimized_content = processor.optimize_section(section_content, section_name)
            
            # Update in Notion
            success = syncer.update_notion_content(
                DASHBOARD_ID,
                section_name,
                optimized_content
            )
            
            if success:
                logging.info(f"Successfully updated section: {section_name}")
            else:
                logging.error(f"Failed to update section: {section_name}")
                
        except Exception as e:
            logging.error(f"Error processing section {section_name}: {str(e)}")
    
    if not success:
        logging.error("Failed to update any sections")

if __name__ == "__main__":
    main() 