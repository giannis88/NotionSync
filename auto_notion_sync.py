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
            
            # Check for potential truncation
            last_section = self.expected_sections[-1]
            if last_section not in missing_sections:
                archiv_content = re.split(r"#\s*ARCHIV", content, flags=re.IGNORECASE)[-1]
                if len(archiv_content.strip()) < 100:
                    logging.warning(f"ARCHIV section in {filepath.name} appears truncated")
                    missing_sections.append(f"{last_section} (truncated)")
            
            # Additional checks
            word_count = len(content.split())
            if word_count < 1000:
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
            
            # Find the last complete section in source
            sections = re.split(r'(?=# )', source_content)
            reference_sections = re.split(r'(?=# )', reference_content)
            
            # Compare sections and identify truncation point
            complete_content = []
            for i, section in enumerate(sections):
                if section.strip():
                    complete_content.append(section)
                    
                    # Check if this section is truncated
                    matching_ref_section = next(
                        (s for s in reference_sections if s.startswith(section.split('\n')[0])),
                        None
                    )
                    if matching_ref_section and len(section) < len(matching_ref_section) * 0.8:
                        # Section appears truncated, use reference content
                        complete_content[-1] = matching_ref_section
            
            # Save fixed content
            fixed_filename = source_file.stem + "_fixed.md"
            fixed_file = source_file.parent / fixed_filename
            fixed_file.write_text('\n'.join(complete_content), encoding='utf-8')
            
            logging.info(f"Created fixed file: {fixed_filename}")
            return fixed_file
            
        except Exception as e:
            logging.error(f"Error fixing truncation: {str(e)}")
            return None

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

    def get_page_content(self, page_id, level=0, visited_pages=None):
        """Gets the content of a page and all subpages with pagination and retry logic"""
        if visited_pages is None:
            visited_pages = set()
            
        if page_id in visited_pages:
            logging.warning(f"Circular reference detected for page {page_id}")
            return ""
            
        visited_pages.add(page_id)
        
        try:
            page = self._retry_request(lambda: self.notion.pages.retrieve(page_id=page_id))
            content = []
            indent = "#" * (level + 1)
            
            # Add page title
            if level == 0:
                content.append("# Master Dashboard\n")
            else:
                title = self._process_rich_text(page['properties']['title']['title'])
                content.append(f"{indent} {title}\n")
            
            # Get all blocks with pagination
            has_more = True
            start_cursor = None
            
            while has_more:
                blocks_response = self._retry_request(
                    lambda: self.notion.blocks.children.list(
                        block_id=page_id,
                        page_size=self.page_size,
                        start_cursor=start_cursor
                    )
                )
                
                for block in blocks_response['results']:
                    block_content = self._process_block(block, level, visited_pages)
                    if block_content:
                        content.append(block_content)
                
                has_more = blocks_response.get('has_more', False)
                start_cursor = blocks_response.get('next_cursor')
            
            return "\n".join(content)
            
        except Exception as e:
            logging.error(f"Error getting page {page_id}: {str(e)}")
            return ""

    def _retry_request(self, request_func, retries=None):
        """Retries a request with exponential backoff"""
        if retries is None:
            retries = self.max_retries
            
        last_error = None
        for attempt in range(retries):
            try:
                return request_func()
            except Exception as e:
                last_error = e
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logging.warning(f"Request failed, retrying in {wait_time:.2f}s... ({attempt + 1}/{retries})")
                time.sleep(wait_time)
                
        logging.error(f"Request failed after {retries} attempts: {str(last_error)}")
        raise last_error

    def _process_block(self, block, level, visited_pages):
        """Processes a single block and returns its content"""
        block_type = block['type']
        
        try:
            if block_type == 'paragraph':
                return self._process_paragraph(block)
            elif block_type == 'heading_1':
                return self._process_heading(block, 1, level)
            elif block_type == 'heading_2':
                return self._process_heading(block, 2, level)
            elif block_type == 'heading_3':
                return self._process_heading(block, 3, level)
            elif block_type == 'bulleted_list_item':
                return self._process_list_item(block, bullet=True)
            elif block_type == 'numbered_list_item':
                return self._process_list_item(block, bullet=False)
            elif block_type == 'to_do':
                return self._process_todo(block)
            elif block_type == 'toggle':
                return self._process_toggle(block)
            elif block_type == 'table':
                return self.process_table(block['id'])
            elif block_type == 'child_page':
                return self.get_page_content(block['id'], level + 1, visited_pages)
            elif block_type == 'divider':
                return "---\n"
            else:
                logging.debug(f"Unhandled block type: {block_type}")
                return ""
                
        except Exception as e:
            logging.error(f"Error processing block {block['id']}: {str(e)}")
            return ""

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

    def process_table(self, table_id):
        """Processes tables into Markdown format with retry logic and pagination"""
        try:
            all_rows = []
            has_more = True
            start_cursor = None
            
            # Get all rows with pagination
            while has_more:
                try:
                    response = self._retry_request(
                        lambda: self.notion.blocks.children.list(
                            block_id=table_id,
                            page_size=self.page_size,
                            start_cursor=start_cursor
                        )
                    )
                    
                    if not response.get('results'):
                        logging.warning(f"No results returned for table {table_id}")
                        break
                        
                    all_rows.extend(response['results'])
                    has_more = response.get('has_more', False)
                    start_cursor = response.get('next_cursor')
                    
                except Exception as e:
                    logging.error(f"Error fetching table rows: {str(e)}")
                    break
            
            if not all_rows:
                logging.warning(f"No rows found for table {table_id}")
                return ""
            
            # Process table rows
            markdown_table = []
            
            # Safely get header row
            header_row = all_rows[0].get('table_row', {}).get('cells', [])
            if not header_row:
                logging.warning(f"No header row found for table {table_id}")
                return ""
            
            headers = []
            for cell in header_row:
                cell_text = "".join(t.get('plain_text', '') for t in cell) if cell else ""
                headers.append(cell_text or " ")  # Use space for empty cells
            
            markdown_table.append("| " + " | ".join(headers) + " |")
            markdown_table.append("| " + " | ".join(["---"] * len(headers)) + " |")
            
            # Process data rows
            for row in all_rows[1:]:
                cells = []
                row_cells = row.get('table_row', {}).get('cells', [])
                
                for cell in row_cells:
                    cell_text = "".join(t.get('plain_text', '') for t in cell) if cell else ""
                    cells.append(cell_text or " ")  # Use space for empty cells
                    
                # Ensure all rows have same number of columns as header
                while len(cells) < len(headers):
                    cells.append(" ")
                    
                markdown_table.append("| " + " | ".join(cells) + " |")
            
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
        """Splits dashboard content into sections"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('# '):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line[2:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)
                
        if current_section:
            sections[current_section] = '\n'.join(current_content)
            
        return sections

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
            logging.info(f"Attempting to update section '{section_name}' with content:")
            logging.info(new_content)
            
            # First find the section block
            blocks = self._retry_request(
                lambda: self.notion.blocks.children.list(page_id)
            )
            
            section_block = None
            section_content_blocks = []
            in_section = False
            
            # Find section and its content blocks
            for block in blocks['results']:
                if block['type'] == 'heading_1' and self._process_rich_text(block['heading_1']['rich_text']) == section_name:
                    section_block = block
                    in_section = True
                elif in_section and block['type'] == 'heading_1':
                    in_section = False
                elif in_section:
                    section_content_blocks.append(block)
            
            if not section_block:
                logging.error(f"Section {section_name} not found")
                return False
            
            logging.info(f"Found section block: {section_block['id']}")
            
            # Archive old blocks
            for block in section_content_blocks:
                self._retry_request(
                    lambda: self.notion.blocks.update(
                        block_id=block['id'],
                        archived=True
                    )
                )
                logging.info(f"Archived block {block['id']}")
            
            # Convert markdown to Notion blocks
            new_blocks = []
            in_table = False
            table_rows = []
            
            for line in new_content.split('\n'):
                line = line.rstrip()
                
                if line.startswith('# ') and not line[2:].strip() == section_name:
                    new_blocks.append({
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                        }
                    })
                elif line.startswith('## '):
                    new_blocks.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                        }
                    })
                elif line.startswith('### '):
                    new_blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                        }
                    })
                elif line.startswith('- '):
                    new_blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                        }
                    })
                elif line.startswith('|'):
                    # Handle table rows
                    cells = [cell.strip() for cell in line.strip('|').split('|')]
                    if len(cells) > 1:  # Valid table row
                        if not line.replace('|', '').replace('-', '').strip():
                            continue  # Skip separator lines
                        if not in_table:
                            in_table = True
                            table_rows = []
                        table_rows.append(cells)
                else:
                    if in_table and table_rows:
                        # End of table - add it to blocks
                        new_blocks.append({
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
                    
                    if line:  # Non-empty line
                        new_blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": line}}]
                            }
                        })
                    else:  # Empty line
                        if new_blocks and new_blocks[-1]['type'] != 'paragraph':
                            new_blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": []
                                }
                            })
            
            # Add new blocks in chunks
            for i in range(0, len(new_blocks), 100):  # Notion API limit
                chunk = new_blocks[i:i+100]
                self._retry_request(
                    lambda: self.notion.blocks.children.append(
                        block_id=page_id,
                        children=chunk
                    )
                )
                logging.info(f"Added {len(chunk)} new blocks")
            
            return True
            
        except Exception as e:
            logging.error(f"Error updating Notion content: {str(e)}")
            return False

    def sync_dashboard(self, dashboard_id):
        """Synchronizes the entire dashboard"""
        logging.info("Starting synchronization...")
        
        try:
            content = self.get_page_content(dashboard_id)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"master_dashboard_{timestamp}"
            
            self.archive_old_files()
            self.save_to_file(content, filename)
            
            # Validate the export
            validation_result = self.validator.validate_file(self.base_path / f"{filename}.md")
            
            if not validation_result['complete']:
                logging.warning("Export appears incomplete!")
                logging.warning(f"Missing sections: {', '.join(validation_result['missing_sections'])}")
                
                # Try to fix using the last known good export
                previous_files = sorted(
                    list(self.base_path.glob("master_dashboard_*.md")),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                
                if len(previous_files) > 1:
                    reference_file = previous_files[1]  # Use second most recent file as reference
                    fixed_file = self.validator.fix_truncation(
                        self.base_path / f"{filename}.md",
                        reference_file
                    )
                    
                    if fixed_file:
                        logging.info("Created fixed version of truncated export")
                    else:
                        logging.error("Failed to fix truncated export")
                        
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

def setup_logging():
    """Sets up logging configuration"""
    log_dir = Path("notion_export/logs")
    log_dir.mkdir(exist_ok=True, parents=True)
    
    log_file = log_dir / "sync.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[handler, logging.StreamHandler()]
    )

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