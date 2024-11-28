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
    def __init__(self, model_name="dashboard-llama", api_base="http://localhost:11434"):
        self.model_name = model_name
        self.api_base = api_base
        self.session = requests.Session()
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
        """Optimiert einen Abschnitt mit LLM"""
        llm_logger = logging.getLogger('llm')
        
        if not content.strip():
            llm_logger.warning(f"Empty content received for section: {section_name}")
            return content
        
        for attempt in range(retries):
            try:
                prompt = f"""Du bist ein präziser Assistent für die Optimierung von Dashboard-Inhalten.
Aufgabe: Optimiere den folgenden {section_name}-Abschnitt, behalte dabei ALLE wichtigen Informationen bei.

Aktueller Inhalt:
{content}

Formatierungsregeln:
1. Verwende exakt diese Struktur:
   # {section_name}
   ### Übersicht & Status
   ### Aktuelle Situation
   ### Nächste Schritte
   ### Tracking & Notizen

2. Formatiere Tabellen einheitlich:
   | Bereich | Status | Priorität | Nächste Aktion |
   |---|---|---|---|

3. Verwende diese Status-Emojis:
   - ✅ für erledigt/gut
   - ⚠️ für Warnung/in Arbeit
   - ❌ für kritisch/nicht erledigt

4. Spezifische Regeln für {section_name}:
   - Gesundheit: Priorisiere Laborwerte und Medikation
   - Business: Fokussiere auf konkrete Projekte und Deadlines
   - Beziehung: Betone Grenzen und Kommunikationsziele
   - ARCHIV: Behalte nur relevante Hintergrundinformationen

5. Wichtig:
   - Behalte ALLE medizinischen Details bei
   - Setze konkrete Termine wo möglich
   - Maximal 3 Kernpunkte pro Abschnitt
   - Klare, actionable Formulierungen

Gib NUR den formatierten Inhalt zurück."""

                llm_logger.info(f"Optimiere Abschnitt: {section_name}")
                
                response = self.session.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "top_p": 0.9,
                            "num_ctx": 2048,
                            "repeat_penalty": 1.1,
                            "stop": ["<|im_start|>", "<|im_end|>"]
                        }
                    },
                    timeout=65
                )
                
                response.raise_for_status()
                result = response.json()
                llm_logger.info(f"Successfully optimized section: {section_name}")
                return result['response']
                
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    llm_logger.error(f"Failed to optimize section after {retries} attempts: {str(e)}")
                    return content
                llm_logger.warning(f"Attempt {attempt + 1} failed, retrying...")
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