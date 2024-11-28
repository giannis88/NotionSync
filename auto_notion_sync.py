from datetime import datetime, timedelta
import logging
import os
import random
import re
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List
import json

from dotenv import load_dotenv
from notion_client import Client

class DashboardValidator:
    def __init__(self):
        self.base_path = Path("notion_export")
        self.expected_sections = [
            "Master Dashboard",
            "Gesundheit",
            "Business",
            "Beziehung",
            "ARCHIV"
        ]
        self.min_word_count = 300
        self.setup_logging()

    def setup_logging(self):
        log_dir = self.base_path / "logs"
        log_dir.mkdir(exist_ok=True, parents=True)
        
        handler = RotatingFileHandler(
            log_dir / "validation.log",
            maxBytes=1024 * 1024,  # 1MB
            backupCount=3
        )
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[handler, logging.StreamHandler()]
        )

    def validate_file(self, filepath):
        """Validates a dashboard export file for completeness"""
        try:
            content = filepath.read_text(encoding='utf-8')
            missing_sections = []
            
            # Check for expected sections
            for section in self.expected_sections:
                if not re.search(rf"#\s*{section}", content, re.IGNORECASE):
                    missing_sections.append(section)
            
            # Check word count
            word_count = len(content.split())
            if word_count < self.min_word_count:
                logging.warning(f"File {filepath.name} seems unusually short ({word_count} words)")
            
            return {
                'filename': filepath.name,
                'complete': len(missing_sections) == 0,
                'missing_sections': missing_sections,
                'word_count': word_count,
                'file_size': filepath.stat().st_size
            }
            
        except Exception as e:
            logging.error(f"Error validating {filepath}: {str(e)}")
            return {
                'filename': filepath.name,
                'error': str(e)
            }

    def fix_truncation(self, source_file, reference_file):
        """Attempts to fix truncation by comparing with a reference file"""
        try:
            source_content = source_file.read_text(encoding='utf-8')
            reference_content = reference_file.read_text(encoding='utf-8')
            
            # Wenn die Quelldatei nur eine Warnung enthält, verwende die Referenzdatei
            if "⚠️ Warnung:" in source_content and len(source_content.split('\n')) < 5:
                fixed_content = reference_content
            else:
                # Teile beide Dateien in Abschnitte
                source_sections = self._split_into_sections(source_content)
                reference_sections = self._split_into_sections(reference_content)
                
                # Verwende Referenzabschnitte für fehlende Abschnitte
                for section in self.expected_sections:
                    if section not in source_sections and section in reference_sections:
                        source_sections[section] = reference_sections[section]
                
                # Stelle die richtige Reihenfolge wieder her
                fixed_content = []
                for section in self.expected_sections:
                    if section in source_sections:
                        fixed_content.append(source_sections[section])
                
                fixed_content = '\n'.join(fixed_content)
            
            # Speichere den fixierten Inhalt
            fixed_filename = source_file.stem + "_fixed.md"
            fixed_file = source_file.parent / fixed_filename
            fixed_file.write_text(fixed_content, encoding='utf-8')
            
            logging.info(f"Created fixed file: {fixed_filename}")
            return fixed_file
            
        except Exception as e:
            logging.error(f"Error fixing truncation: {str(e)}")
            return None

    def _split_into_sections(self, content):
        """Splits content into sections"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('# '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip() + '\n\n'
                current_section = line[2:].strip()
                current_content = [line]
            else:
                if current_section:
                    current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip() + '\n\n'
        
        return sections

class NotionSync:
    def __init__(self, token):
        self.notion = Client(auth=token)
        self.base_path = Path("notion_export")
        self.archive_path = self.base_path / "archive"
        self.base_path.mkdir(exist_ok=True)
        self.archive_path.mkdir(exist_ok=True)
        self.validator = DashboardValidator()
        self.max_retries = 3
        self.page_size = 250
        self.updates_path = self.base_path / "updates"
        self.updates_path.mkdir(exist_ok=True)
        
    def _process_rich_text(self, rich_text_list):
        """Processes rich text array and combines all text content"""
        if not rich_text_list:
            return ""
        return "".join(text['plain_text'] for text in rich_text_list)

    def archive_old_files(self):
        """Archives older export files"""
        try:
            current_files = list(self.base_path.glob("master_dashboard_*.md"))
            if len(current_files) > 5:  # Keep only the last 5 files
                sorted_files = sorted(current_files, key=lambda x: x.stat().st_mtime)
                for old_file in sorted_files[:-5]:
                    archive_file = self.archive_path / old_file.name
                    old_file.rename(archive_file)
                    logging.info(f"Archived old file: {old_file.name}")
        except Exception as e:
            logging.error(f"Error archiving old files: {str(e)}")

    def save_to_file(self, content, filename):
        """Saves content to a Markdown file"""
        try:
            filepath = self.base_path / f"{filename}.md"
            filepath.write_text(content, encoding='utf-8')
            logging.info(f"Saved: {filepath}")
        except Exception as e:
            logging.error(f"Error saving file: {str(e)}")
            raise

    def get_page_content(self, page_id, level=0, visited_pages=None, retry_count=0):
        """Gets the content of a page and all subpages with pagination and retry logic"""
        MAX_RETRIES = 3
        
        if retry_count >= MAX_RETRIES:
            logging.error(f"Failed to get complete content after {MAX_RETRIES} attempts")
            return "# Master Dashboard\n\n> ⚠️ Warnung: Unvollständiger Export\n\n"
        
        if visited_pages is None:
            visited_pages = set()
        
        if page_id in visited_pages:
            logging.warning(f"Circular reference detected for page {page_id}")
            return ""
        
        visited_pages.add(page_id)
        processed_blocks = {}  # Track Block-IDs und deren Inhalt
        
        try:
            # Hole alle Blöcke in einem Durchgang
            all_blocks = []
            has_more = True
            start_cursor = None
            
            while has_more:
                response = self._retry_request(
                    lambda: self.notion.blocks.children.list(
                        block_id=page_id,
                        page_size=100,
                        start_cursor=start_cursor
                    ),
                    retries=5
                )
                
                blocks = response.get('results', [])
                if not blocks:
                    break
                    
                # Dedupliziere Blöcke basierend auf Inhalt und ID
                for block in blocks:
                    block_id = block['id']
                    block_content = self._get_block_content(block)
                    
                    if block_id not in processed_blocks and block_content not in processed_blocks.values():
                        all_blocks.append(block)
                        processed_blocks[block_id] = block_content
                
                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')
                
                if has_more:
                    time.sleep(0.5)
            
            # Verarbeite Blöcke
            content = []
            if level == 0:
                content.append("# Master Dashboard\n")
            
            # Sortiere Blöcke nach ihrer Position
            all_blocks.sort(key=lambda x: x.get('created_time', ''))
            
            for block in all_blocks:
                try:
                    block_content = self._process_block(block, level, visited_pages)
                    if block_content:
                        content.append(block_content)
                except Exception as e:
                    logging.error(f"Error processing block: {str(e)}")
                    continue
            
            # Validiere und bereinige Content
            full_content = self._clean_section_content('\n'.join(content))
            
            if level == 0:
                sections = self._split_into_sections(full_content)
                ordered_content = []
                
                # Stelle sicher, dass jeder Abschnitt nur einmal vorkommt
                seen_sections = set()
                for section in self.validator.expected_sections:
                    if section in sections and section not in seen_sections:
                        ordered_content.append(sections[section])
                        seen_sections.add(section)
                
                full_content = '\n'.join(ordered_content)
                
                # Prüfe auf Vollständigkeit
                missing_sections = [
                    section for section in self.validator.expected_sections 
                    if section not in sections
                ]
                
                if missing_sections and retry_count < MAX_RETRIES:
                    logging.info(f"Retrying page fetch (attempt {retry_count + 1}/{MAX_RETRIES})...")
                    time.sleep(2)
                    return self.get_page_content(page_id, level, set(), retry_count + 1)
            
            return full_content
            
        except Exception as e:
            logging.error(f"Error getting page {page_id}: {str(e)}")
            if level == 0 and retry_count < MAX_RETRIES:
                time.sleep(2)
                return self.get_page_content(page_id, level, set(), retry_count + 1)
            return ""

    def _get_block_content(self, block):
        """Extrahiert den Inhalt eines Blocks für Deduplizierung"""
        try:
            block_type = block['type']
            if block_type in ['paragraph', 'heading_1', 'heading_2', 'heading_3']:
                return self._process_rich_text(block[block_type]['rich_text'])
            elif block_type == 'table':
                return f"table_{block['id']}"  # Unique ID für Tabellen
            else:
                return f"{block_type}_{block['id']}"
        except:
            return block['id']

    def _normalize_text(self, text):
        """Normalisiert Text und behandelt Umlaute"""
        try:
            # Ersetze problematische Zeichen
            replacements = {
                'ä': 'ae',
                'ö': 'oe',
                'ü': 'ue',
                'Ä': 'Ae',
                'Ö': 'Oe',
                'Ü': 'Ue',
                'ß': 'ss'
            }
            
            for char, replacement in replacements.items():
                text = text.replace(char, replacement)
                
            return text
        except Exception as e:
            logging.error(f"Error normalizing text: {str(e)}")
            return text

    def _retry_request(self, request_func, retries=None):
        """Retries a request with exponential backoff"""
        if retries is None:
            retries = self.max_retries
            
        api_logger = logging.getLogger('api')
        last_error = None
        
        for attempt in range(retries):
            try:
                response = request_func()
                # Log nur wichtige API-Details
                if api_logger.isEnabledFor(logging.DEBUG):
                    api_logger.debug(f"API Request successful: {str(request_func)}")
                return response
            except Exception as e:
                last_error = e
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                api_logger.warning(f"Request failed ({attempt + 1}/{retries}): {str(e)}")
                time.sleep(wait_time)
        
        api_logger.error(f"Request failed after {retries} attempts: {str(last_error)}")
        raise last_error

    def _process_block(self, block, level, visited_pages):
        """Processes a single block and returns its content"""
        block_type = block['type']
        
        try:
            # Spezielle Behandlung für leere Blöcke
            if block_type == 'paragraph' and not block['paragraph']['rich_text']:
                return "\n"
            
            # Mapping von Block-Typen zu Verarbeitungsfunktionen
            processors = {
                'paragraph': self._process_paragraph,
                'heading_1': lambda b: self._process_heading(b, 1, level),
                'heading_2': lambda b: self._process_heading(b, 2, level),
                'heading_3': lambda b: self._process_heading(b, 3, level),
                'bulleted_list_item': lambda b: self._process_list_item(b, bullet=True),
                'numbered_list_item': lambda b: self._process_list_item(b, bullet=False),
                'to_do': self._process_todo,
                'toggle': self._process_toggle,
                'table': lambda b: self._process_table(b['id']),
                'child_page': lambda b: self.get_page_content(b['id'], level + 1, visited_pages),
                'divider': lambda b: "---\n",
                'callout': self._process_callout,
                'quote': self._process_quote,
                'code': self._process_code,
                'column_list': self._process_column_list,
                'column': self._process_column,
                'synced_block': self._process_synced_block
            }
            
            # Verarbeite Block mit entsprechendem Processor
            if block_type in processors:
                content = processors[block_type](block)
                return self._clean_block_content(content) if content else ""
            else:
                logging.debug(f"Unhandled block type: {block_type}")
                return ""
                
        except Exception as e:
            logging.error(f"Error processing block {block['id']}: {str(e)}")
            return ""

    def _clean_block_content(self, content):
        """Bereinigt Block-Inhalt"""
        if not content:
            return ""
        
        # Entferne überflüssige Leerzeilen
        lines = content.split('\n')
        cleaned = []
        last_empty = False
        
        for line in lines:
            is_empty = not line.strip()
            if is_empty and last_empty:
                continue
            cleaned.append(line)
            last_empty = is_empty
        
        # Stelle sicher, dass Blöcke korrekt getrennt sind
        result = '\n'.join(cleaned)
        if not result.endswith('\n\n'):
            result += '\n\n'
        
        return result

    def _process_callout(self, block):
        """Verarbeitet Callout-Blöcke"""
        if not block['callout']['rich_text']:
            return ""
        icon = block['callout'].get('icon', {}).get('emoji', '💡')
        text = self._process_rich_text(block['callout']['rich_text'])
        return f"{icon} {text}\n\n"

    def _process_quote(self, block):
        """Verarbeitet Quote-Blöcke"""
        if not block['quote']['rich_text']:
            return ""
        text = self._process_rich_text(block['quote']['rich_text'])
        return f"> {text}\n\n"

    def _process_code(self, block):
        """Verarbeitet Code-Blöcke"""
        if not block['code']['rich_text']:
            return ""
        language = block['code'].get('language', '')
        code = self._process_rich_text(block['code']['rich_text'])
        return f"```{language}\n{code}\n```\n\n"

    def _process_paragraph(self, block):
        """Processes paragraph blocks with full rich text content"""
        if not block['paragraph']['rich_text']:
            return "\n"
        return self._process_rich_text(block['paragraph']['rich_text']) + "\n\n"

    def _process_heading(self, block, level, parent_level):
        if not block[f'heading_{level}']['rich_text']:
            return ""
        indent = "#" * (parent_level + level)
        text = self._process_rich_text(block[f'heading_{level}']['rich_text'])
        return f"{indent} {text}\n\n"

    def _process_list_item(self, block, bullet=True):
        block_type = 'bulleted_list_item' if bullet else 'numbered_list_item'
        if not block[block_type]['rich_text']:
            return ""
        prefix = "-" if bullet else "1."
        text = self._process_rich_text(block[block_type]['rich_text'])
        return f"{prefix} {text}\n"

    def _process_todo(self, block):
        if not block['to_do']['rich_text']:
            return ""
        checkbox = "✓" if block['to_do']['checked'] else "☐"
        text = self._process_rich_text(block['to_do']['rich_text'])
        return f"{checkbox} {text}\n"

    def _process_toggle(self, block):
        if not block['toggle']['rich_text']:
            return ""
        text = self._process_rich_text(block['toggle']['rich_text'])
        content = [f"- {text}"]
        
        # Process toggle children
        children = self._retry_request(
            lambda: self.notion.blocks.children.list(block_id=block['id'])
        )
        
        for child in children['results']:
            if child['type'] == 'paragraph' and child['paragraph']['rich_text']:
                child_text = self._process_rich_text(child['paragraph']['rich_text'])
                content.append(f"  {child_text}")
                
        return "\n".join(content) + "\n"

    def _process_table(self, table_id):
        """Processes tables into clean Markdown format"""
        try:
            all_rows = []
            has_more = True
            start_cursor = None
            
            # Get all rows with pagination
            while has_more:
                response = self._retry_request(
                    lambda: self.notion.blocks.children.list(
                        block_id=table_id,
                        page_size=self.page_size,
                        start_cursor=start_cursor
                    )
                )
                
                if not response.get('results'):
                    break
                    
                all_rows.extend(response['results'])
                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')
                
            if not all_rows:
                return ""
            
            # Process table rows
            markdown_table = []
            
            # Header row
            header_cells = all_rows[0].get('table_row', {}).get('cells', [])
            if not header_cells:
                return ""
            
            headers = []
            for cell in header_cells:
                cell_text = "".join(t.get('plain_text', '') for t in cell) if cell else " "
                headers.append(cell_text.strip() or " ")
            
            markdown_table.append("| " + " | ".join(headers) + " |")
            markdown_table.append("|" + "|".join(["---"] * len(headers)) + "|")
            
            # Data rows
            for row in all_rows[1:]:
                cells = []
                row_cells = row.get('table_row', {}).get('cells', [])
                
                for cell in row_cells:
                    cell_text = "".join(t.get('plain_text', '') for t in cell) if cell else " "
                    cells.append(cell_text.strip() or " ")
                    
                # Ensure all rows have same number of columns
                while len(cells) < len(headers):
                    cells.append(" ")
                    
                markdown_table.append("| " + " | ".join(cells) + " |")
            
            # Return table with minimal spacing
            return "\n".join(markdown_table) + "\n\n"
            
        except Exception as e:
            logging.error(f"Error processing table {table_id}: {str(e)}")
            return ""

    def find_recent_updates(self):
        """Finds updates by comparing the latest two dashboard files"""
        try:
            dashboard_files = sorted(
                list(self.base_path.glob("master_dashboard_*.md")),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if len(dashboard_files) < 2:
                logging.info("First run or not enough files to compare")
                # Bei erstem Lauf alles als neu behandeln
                if len(dashboard_files) == 1:
                    content = dashboard_files[0].read_text(encoding='utf-8')
                    sections = self._split_into_sections(content)
                    updates = []
                    for section, content in sections.items():
                        if content.strip():  # Nur nicht-leere Sektionen
                            updates.append({
                                "section": section,
                                "new_content": [content.strip()]
                            })
                    return updates
                return None
                
            current = dashboard_files[0].read_text(encoding='utf-8')
            previous = dashboard_files[1].read_text(encoding='utf-8')
            
            # Find new content by comparing files
            current_sections = self._split_into_sections(current)
            previous_sections = self._split_into_sections(previous)
            
            updates = []
            for section, content in current_sections.items():
                if section not in previous_sections or content != previous_sections[section]:
                    # Nur den neuen Text finden
                    new_lines = self._find_new_lines(
                        previous_sections.get(section, ""),
                        content
                    )
                    if new_lines:
                        logging.info(f"Found new content in section {section}:")
                        for line in new_lines:
                            logging.info(f"  {line}")
                        updates.append({
                            "section": section,
                            "new_content": new_lines
                        })
            
            if not updates:
                logging.info("No new content found")
            
            return updates
            
        except Exception as e:
            logging.error(f"Error finding updates: {str(e)}")
            return None

    def _split_into_sections(self, content):
        """Splits content into sections"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('# '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip() + '\n\n'
                current_section = line[2:].strip()
                current_content = [line]
            else:
                if current_section:
                    current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip() + '\n\n'
        
        return sections

    def _clean_section_content(self, content):
        """Bereinigt den Inhalt eines Abschnitts"""
        # Entferne aufeinanderfolgende Leerzeilen
        lines = content.split('\n')
        cleaned_lines = []
        last_line_empty = False
        
        for line in lines:
            is_empty = not line.strip()
            if is_empty and last_line_empty:
                continue
            cleaned_lines.append(line)
            last_line_empty = is_empty
        
        # Entferne Leerzeilen am Ende
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        
        # Füge eine Leerzeile am Ende hinzu
        cleaned_lines.append('')
        
        return '\n'.join(cleaned_lines)

    def _find_new_lines(self, old_content, new_content):
        """Finds new lines in new_content that aren't in old_content"""
        old_lines = set(old_content.split('\n'))
        new_lines = new_content.split('\n')
        return [line for line in new_lines if line and line not in old_lines]

    def save_updates_for_llm(self, updates):
        """Saves updates to a JSON file for LLM processing"""
        if not updates:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        update_file = self.updates_path / f"updates_{timestamp}.json"
        
        with open(update_file, 'w', encoding='utf-8') as f:
            json.dump(updates, f, indent=2)
            
        return update_file

    def update_notion_content(self, page_id, section_name, new_content):
        """Updates a specific section in Notion"""
        try:
            logging.info(f"Attempting to update section '{section_name}'")
            
            # Hole alle Blöcke der Seite
            blocks = self._retry_request(
                lambda: self.notion.blocks.children.list(
                    block_id=page_id,
                    page_size=100
                )
            )
            
            # Finde den Abschnitt und seine Position
            section_blocks = []
            in_section = False
            section_start = None
            section_end = None
            
            for i, block in enumerate(blocks['results']):
                if block['type'] in ['heading_1', 'heading_2']:
                    current_heading = self._process_rich_text(block[block['type']]['rich_text']).lower()
                    if current_heading == section_name.lower():
                        section_start = i
                        in_section = True
                    elif in_section:
                        section_end = i
                        break
                if in_section:
                    section_blocks.append(block)
            
            if section_end is None and in_section:
                section_end = len(blocks['results'])
            
            # Archiviere alte Blöcke
            if section_blocks:
                for block in section_blocks:
                    self._retry_request(
                        lambda: self.notion.blocks.update(
                            block_id=block['id'],
                            archived=True
                        )
                    )
                    logging.info(f"Archived block {block['id']}")
            
            # Erstelle neue Blöcke
            new_blocks = self._convert_markdown_to_blocks(new_content)
            
            # Füge neue Blöcke an der richtigen Position ein
            if not section_blocks:
                # Wenn Abschnitt nicht existiert, erstelle ihn am Ende
                self._retry_request(
                    lambda: self.notion.blocks.children.append(
                        block_id=page_id,
                        children=[{
                            "object": "block",
                            "type": "heading_1",
                            "heading_1": {
                                "rich_text": [{"type": "text", "text": {"content": section_name}}]
                            }
                        }]
                    )
                )
                logging.info(f"Created new section: {section_name}")
            
            # Füge Inhalt hinzu
            self._retry_request(
                lambda: self.notion.blocks.children.append(
                    block_id=page_id,
                    children=new_blocks
                )
            )
            logging.info(f"Added {len(new_blocks)} new blocks")
            
            return True
            
        except Exception as e:
            logging.error(f"Error updating section: {str(e)}")
            return False

    def _convert_markdown_to_blocks(self, markdown_content):
        """Konvertiert Markdown-Inhalt in Notion-Blöcke"""
        blocks = []
        lines = markdown_content.split('\n')
        in_table = False
        table_rows = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            if line.startswith('# '):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('## '):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    }
                })
            elif line.startswith('### '):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    }
                })
            elif line.startswith('- '):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('|'):
                # Tabellen-Verarbeitung
                cells = [cell.strip() for cell in line.strip('|').split('|')]
                if not line.replace('|', '').replace('-', '').strip():
                    continue  # Überspringe Trennzeilen
                if not in_table:
                    in_table = True
                    table_rows = []
                table_rows.append(cells)
            else:
                if in_table and table_rows:
                    # Ende der Tabelle - füge sie zu den Blöcken hinzu
                    blocks.append({
                        "object": "block",
                        "type": "table",
                        "table": {
                            "table_width": len(table_rows[0]),
                            "has_column_header": True,
                            "has_row_header": False,
                            "children": [
                                {
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [[{"type": "text", "text": {"content": cell}}] for cell in row]
                                    }
                                } for row in table_rows
                            ]
                        }
                    })
                    in_table = False
                    table_rows = []
                
                if line:  # Nicht-leere Zeile
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": line}}]
                        }
                    })
        
        return blocks

    def sync_dashboard(self, dashboard_id):
        """Synchronizes the entire dashboard"""
        logging.info("Starting synchronization...")
        
        try:
            content = self.get_page_content(dashboard_id)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"master_dashboard_{timestamp}"
            
            self.archive_old_files()
            self.save_to_file(content, filename)
            
            current_file = self.base_path / f"{filename}.md"
            validation_result = self.validator.validate_file(current_file)
            
            if not validation_result['complete'] or validation_result['word_count'] < 300:
                logging.warning("Export appears incomplete!")
                if validation_result['missing_sections']:
                    logging.warning(f"Missing sections: {', '.join(validation_result['missing_sections'])}")
                
                # Versuche die letzte gute Version zu finden
                previous_files = sorted(
                    [f for f in self.base_path.glob("master_dashboard_*.md") 
                     if f != current_file and not f.name.endswith('_fixed.md')],
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                
                if previous_files:
                    reference_file = previous_files[0]
                    ref_validation = self.validator.validate_file(reference_file)
                    
                    if ref_validation['complete'] and ref_validation['word_count'] >= 300:
                        fixed_file = self.validator.fix_truncation(current_file, reference_file)
                        if fixed_file:
                            logging.info("Created fixed version of truncated export")
                        else:
                            logging.error("Failed to fix truncated export")
                    else:
                        logging.warning("No valid reference file found for fixing")
                else:
                    logging.warning("No previous files found for reference")
            
            logging.info("Synchronization successfully completed!")
            return True
            
        except Exception as e:
            logging.error(f"Error during synchronization: {str(e)}")
            return False

    def optimize_section_content(self, page_id, section_name, bullet_points):
        """Optimiert bestimmte Bullet Points in einem Abschnitt"""
        try:
            # Hole aktuellen Inhalt
            blocks = self._retry_request(
                lambda: self.notion.blocks.children.list(page_id)
            )
            
            section_block = None
            section_content = []
            in_section = False
            
            # Finde Abschnitt und Inhalt
            for block in blocks['results']:
                if block['type'] == 'heading_1' and self._process_rich_text(block['heading_1']['rich_text']) == section_name:
                    section_block = block
                    in_section = True
                elif in_section and block['type'] == 'heading_1':
                    break
                elif in_section:
                    content = self._process_rich_text(block.get(block['type'], {}).get('rich_text', []))
                    if content.strip().startswith('-'):
                        section_content.append({
                            'id': block['id'],
                            'content': content.strip()
                        })
            
            # Optimiere ausgewählte Bullet Points
            for bullet in bullet_points:
                for content in section_content:
                    if bullet in content['content']:
                        self._retry_request(
                            lambda: self.notion.blocks.update(
                                block_id=content['id'],
                                archived=True
                            )
                        )
                        logging.info(f"Archivierter Bullet Point: {content['content']}")
            
            return True
            
        except Exception as e:
            logging.error(f"Fehler beim Optimieren des Inhalts: {str(e)}")
            return False

    def _process_column_list(self, block):
        """Verarbeitet Spalten-Listen"""
        try:
            columns = self._retry_request(
                lambda: self.notion.blocks.children.list(block_id=block['id'])
            )
            
            column_contents = []
            for column in columns.get('results', []):
                if column['type'] == 'column':
                    content = self._process_column(column)
                    if content:
                        column_contents.append(content)
            
            return "\n".join(column_contents) + "\n\n"
        except Exception as e:
            logging.error(f"Error processing column list: {str(e)}")
            return ""

    def _process_column(self, block):
        """Verarbeitet einzelne Spalten"""
        try:
            children = self._retry_request(
                lambda: self.notion.blocks.children.list(block_id=block['id'])
            )
            
            column_content = []
            for child in children.get('results', []):
                content = self._process_block(child, 0, set())
                if content:
                    column_content.append(content)
            
            return "\n".join(column_content)
        except Exception as e:
            logging.error(f"Error processing column: {str(e)}")
            return ""

    def _process_synced_block(self, block):
        """Verarbeitet synchronisierte Blöcke"""
        try:
            if block['synced_block'].get('synced_from'):
                # Hole Original-Block
                original_id = block['synced_block']['synced_from']['block_id']
                original = self._retry_request(
                    lambda: self.notion.blocks.retrieve(block_id=original_id)
                )
                return self._process_block(original, 0, set())
            else:
                # Verarbeite Kinder des Sync-Blocks
                children = self._retry_request(
                    lambda: self.notion.blocks.children.list(block_id=block['id'])
                )
                content = []
                for child in children.get('results', []):
                    child_content = self._process_block(child, 0, set())
                    if child_content:
                        content.append(child_content)
                return "\n".join(content)
        except Exception as e:
            logging.error(f"Error processing synced block: {str(e)}")
            return ""

def setup_logging():
    """Konfiguriert das Logging-System mit optimierter Struktur"""
    log_dir = Path("notion_export/logs")
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # Basis-Formatter für alle Logger
    base_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Detaillierter Formatter für API-Logs
    api_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s\n'
        'Request: %(http_method)s %(url)s\n'
        'Response: %(status_code)s\n',
        defaults={'http_method': '', 'url': '', 'status_code': ''}
    )
    
    # Logger-Konfigurationen
    loggers = {
        'sync': {
            'file': 'sync.log',
            'maxBytes': 500_000,
            'backupCount': 5,
            'level': logging.INFO,
            'formatter': base_formatter,
            'console': True
        },
        'api': {
            'file': 'api.log',
            'maxBytes': 200_000,
            'backupCount': 3,
            'level': logging.INFO,
            'formatter': api_formatter,
            'console': False
        },
        'validation': {
            'file': 'validation.log',
            'maxBytes': 200_000,
            'backupCount': 2,
            'level': logging.INFO,
            'formatter': base_formatter,
            'console': True
        }
    }
    
    # Logger erstellen und konfigurieren
    for name, config in loggers.items():
        logger = logging.getLogger(name)
        logger.setLevel(config['level'])
        logger.propagate = False
        
        # Datei-Handler
        file_handler = RotatingFileHandler(
            log_dir / config['file'],
            maxBytes=config['maxBytes'],
            backupCount=config['backupCount'],
            encoding='utf-8'
        )
        file_handler.setFormatter(config['formatter'])
        logger.addHandler(file_handler)
        
        # Optional: Konsolen-Handler
        if config['console']:
            console = logging.StreamHandler()
            console.setFormatter(config['formatter'])
            logger.addHandler(console)
        
        # Alte Log-Dateien archivieren
        archive_dir = log_dir / 'archive'
        archive_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / config['file']
        if log_file.exists() and log_file.stat().st_size > config['maxBytes']:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_file = archive_dir / f"{config['file']}.{timestamp}"
            log_file.rename(archive_file)

def main():
    setup_logging()
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Get configuration from .env
        NOTION_TOKEN = os.getenv('NOTION_TOKEN')
        DASHBOARD_ID = os.getenv('NOTION_DASHBOARD_ID')
        
        # Check if necessary environment variables are set
        if not NOTION_TOKEN:
            logging.error("No Notion API Token found in .env!")
            return
            
        if not DASHBOARD_ID:
            logging.error("No Dashboard ID found in .env!")
            return
            
        # Log start of synchronization with Dashboard ID
        logging.info(f"Starting sync for Dashboard: {DASHBOARD_ID}")
        
        # Initialize and start sync
        syncer = NotionSync(NOTION_TOKEN)
        success = syncer.sync_dashboard(DASHBOARD_ID)
        
        if not success:
            logging.error("Synchronization failed!")
        
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()