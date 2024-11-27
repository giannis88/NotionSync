import os
from notion_client import Client
from datetime import datetime
from pathlib import Path
import logging
import random
import time
import re
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

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
        self.page_size = 250  # Increase from 100 to get more content per request

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
                response = self._retry_request(
                    lambda: self.notion.blocks.children.list(
                        block_id=table_id,
                        page_size=self.page_size,
                        start_cursor=start_cursor
                    )
                )
                
                all_rows.extend(response['results'])
                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')
                logging.info(f"Table processing: Got {len(response['results'])} rows, has_more: {has_more}")
                
            if not all_rows:
                return ""
            
            logging.info(f"Processing table with {len(all_rows)} total rows")
            
            markdown_table = []
            headers = []
            
            # Process header with full rich text
            for cell in all_rows[0]['table_row']['cells']:
                cell_text = "".join(t['plain_text'] for t in cell) if cell else ""
                headers.append(cell_text)
            
            # Create Markdown table header
            markdown_table.append("| " + " | ".join(headers) + " |")
            markdown_table.append("| " + " | ".join(["---"] * len(headers)) + " |")
            
            # Process data rows with full rich text
            row_count = 0
            for row in all_rows[1:]:
                cells = []
                for cell in row['table_row']['cells']:
                    cell_text = "".join(t['plain_text'] for t in cell) if cell else ""
                    cells.append(cell_text)
                markdown_table.append("| " + " | ".join(cells) + " |")
                row_count += 1
                
            logging.info(f"Table processing complete: {row_count} data rows processed")
            return "\n".join(markdown_table) + "\n\n"
            
        except Exception as e:
            logging.error(f"Error processing table: {str(e)}")
            return ""        
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