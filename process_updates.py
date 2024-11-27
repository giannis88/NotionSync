import json
import logging
from pathlib import Path
from datetime import datetime
from auto_notion_sync import NotionSync, setup_logging
from dotenv import load_dotenv
import os
import requests

class OllamaProcessor:
    def __init__(self):
        self.model_name = "qwen2.5-coder-extra-ctx:7b"
        self.api_base = "http://localhost:11434"
        logging.info(f"Using Ollama model: {self.model_name}")

    def optimize_section(self, content, section_name):
        """Optimiert einen bestimmten Abschnitt des Dashboards"""
        try:
            prompt = f"""Du bist ein KI-Assistent, der einen Dashboard-Abschnitt optimiert.
Hier ist der aktuelle Inhalt des {section_name}-Abschnitts:

{content}

Bitte:
1. Behalte die grundlegende Struktur bei
2. Verbessere die Formulierungen
3. Ergänze fehlende wichtige Informationen
4. Mache den Text präziser und aktionsorientierter
5. Behalte alle wichtigen Informationen bei

Gib den optimierten Text im gleichen Format zurück.
Behalte die Markdown-Formatierung bei.
Füge keine Meta-Kommentare hinzu."""

            logging.info(f"Optimiere Abschnitt: {section_name}")
            
            response = requests.post(
                f"{self.api_base}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logging.info(f"Successfully optimized section: {section_name}")
                return result['response']
            else:
                raise Exception(f"Ollama API returned status code {response.status_code}")
            
        except Exception as e:
            logging.error(f"Error optimizing section: {str(e)}")
            return content  # Return original content if optimization fails

def main():
    setup_logging()
    load_dotenv()
    
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    DASHBOARD_ID = os.getenv('NOTION_DASHBOARD_ID')
    
    if not all([NOTION_TOKEN, DASHBOARD_ID]):
        logging.error("Missing required environment variables")
        return
    
    syncer = NotionSync(NOTION_TOKEN)
    
    # Get latest dashboard file
    dashboard_files = sorted(
        list(Path("notion_export").glob("master_dashboard_*.md")),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not dashboard_files:
        logging.error("No dashboard files found")
        return
        
    # Read latest dashboard content
    content = dashboard_files[0].read_text(encoding='utf-8')
    
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