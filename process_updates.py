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
        self.api_base = "http://localhost:11434"  # Standard Ollama API endpoint
        logging.info(f"Using Ollama model: {self.model_name}")

    def process_text(self, text, section):
        try:
            prompt = f"""Analyze this note from my personal dashboard (section: {section}):

{text}

Please provide a detailed analysis with:

1. Brief Summary
- What is the key message?
- What is the context?

2. Key Insights
- What are the main takeaways?
- What implications does this have?
- What opportunities or challenges are indicated?

3. Suggested Actions
- What specific steps should be taken?
- What resources might be needed?
- What timeline would be appropriate?

4. Patterns & Connections
- How does this relate to previous notes/events?
- What trends or patterns might be emerging?
- What broader implications exist?

5. Additional Thoughts
- What other considerations are important?
- What potential risks or opportunities should be monitored?
- What follow-up questions should be asked?

Format your response using markdown headings (###) and bullet points. Be specific and actionable in your analysis."""

            logging.info(f"Processing text for section {section}")
            
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
                logging.info("Successfully processed text with Ollama")
                return result['response']
            else:
                raise Exception(f"Ollama API returned status code {response.status_code}")
            
        except Exception as e:
            logging.error(f"Error processing with Ollama: {str(e)}")
            return f"Error processing note: {str(e)}"

def process_updates_with_llm(updates_file):
    """Process updates using Ollama LLM"""
    try:
        with open(updates_file, 'r', encoding='utf-8') as f:
            updates = json.load(f)
        
        processor = OllamaProcessor()
        processed_updates = []
        
        for update in updates:
            section = update['section']
            content = "\n".join(update['new_content'])
            
            logging.info(f"Processing update for section: {section}")
            processed_content = processor.process_text(content, section)
            
            final_content = f"\n### AI Analysis ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"
            final_content += processed_content
            final_content += f"\n\n### Original Note\n{content}"
            
            processed_updates.append({
                "section": section,
                "content": final_content
            })
        
        return processed_updates
        
    except Exception as e:
        logging.error(f"Error processing with LLM: {str(e)}")
        return None

def main():
    setup_logging()
    load_dotenv()
    
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    DASHBOARD_ID = os.getenv('NOTION_DASHBOARD_ID')
    
    if not all([NOTION_TOKEN, DASHBOARD_ID]):
        logging.error("Missing required environment variables")
        return
    
    syncer = NotionSync(NOTION_TOKEN)
    
    # Find recent updates
    updates = syncer.find_recent_updates()
    if not updates:
        logging.info("No new updates found")
        return
    
    # Save updates for LLM processing
    updates_file = syncer.save_updates_for_llm(updates)
    if not updates_file:
        logging.error("Failed to save updates")
        return
    
    # Process updates with LLM
    processed_updates = process_updates_with_llm(updates_file)
    
    # Update Notion with processed content
    if processed_updates:
        for update in processed_updates:
            success = syncer.update_notion_content(
                DASHBOARD_ID,
                update['section'],
                update['content']
            )
            if success:
                logging.info(f"Successfully updated section: {update['section']}")
            else:
                logging.error(f"Failed to update section: {update['section']}")
    else:
        logging.error("No updates were processed")

if __name__ == "__main__":
    main() 