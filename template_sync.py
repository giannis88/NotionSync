# -*- coding: utf-8 -*-
from notion_client import Client
import os
from datetime import datetime
from dotenv import load_dotenv
import json
import sys
import re
from pathlib import Path

# Set UTF-8 encoding for stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class NotionTemplateSync:
    def __init__(self):
        load_dotenv()
        self.notion = Client(auth=os.getenv('NOTION_TOKEN'))
        self.main_db_id = os.getenv('NOTION_DATABASE_ID')
        self.templates_dir = Path('templates')

    def markdown_to_blocks(self, markdown_content):
        """Convert markdown content to Notion blocks."""
        blocks = []
        lines = markdown_content.split('\n')
        current_list = []
        in_table = False
        table_rows = []
        table_header = None

        for line in lines:
            # Skip empty lines
            if not line.strip():
                if current_list:
                    blocks.extend(current_list)
                    current_list = []
                if in_table and table_rows:
                    # Process the table
                    if len(table_rows) >= 2:  # Must have at least header and separator
                        table_width = len(table_rows[0])
                        # Remove separator row
                        table_rows.pop(1)
                        blocks.append({
                            "type": "table",
                            "table": {
                                "table_width": table_width,
                                "has_column_header": True,
                                "has_row_header": False,
                                "children": [
                                    {
                                        "type": "table_row",
                                        "table_row": {
                                            "cells": [[{"text": {"content": cell.strip()}}] for cell in row]
                                        }
                                    } for row in table_rows if all(not cell.startswith('-') for cell in row)
                                ]
                            }
                        })
                    in_table = False
                    table_rows = []
                continue

            # Headers
            if line.startswith('#'):
                level = len(re.match(r'^#+', line).group())
                text = line.lstrip('#').strip()
                if level <= 3:
                    blocks.append({
                        "type": f"heading_{level}",
                        f"heading_{level}": {
                            "rich_text": [{"text": {"content": text}}]
                        }
                    })
                continue

            # Checkboxes
            if line.strip().startswith('- [ ]') or line.strip().startswith('- [x]'):
                checked = line.strip().startswith('- [x]')
                text = line.strip()[5:].strip()
                blocks.append({
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"text": {"content": text}}],
                        "checked": checked
                    }
                })
                continue

            # Bullet points
            if line.strip().startswith('- '):
                text = line.strip()[2:].strip()
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": text}}]
                    }
                })
                continue

            # Tables
            if line.strip().startswith('|'):
                cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
                if not in_table:
                    in_table = True
                    table_rows = []
                table_rows.append(cells)
                continue

            # Regular text
            if not in_table:
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": line.strip()}}]
                    }
                })

        return blocks

    def sync_template(self, template_file):
        """Sync a single template file with Notion."""
        try:
            # Read template file
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract metadata from frontmatter
            metadata = {}
            if content.startswith('---'):
                _, frontmatter, content = content.split('---', 2)
                for line in frontmatter.strip().split('\n'):
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()

            # Convert markdown to Notion blocks
            blocks = self.markdown_to_blocks(content)

            # Create template in Notion
            page = self.notion.pages.create(
                parent={"database_id": self.main_db_id},
                icon={"type": "emoji", "emoji": metadata.get('icon', '📄')},
                properties={
                    "Name": {"title": [{"text": {"content": metadata.get('title', template_file.stem)}}]},
                    "Type": {"select": {"name": "Template"}},
                    "Status": {"select": {"name": "Template"}},
                    "Tags": {"multi_select": [{"name": tag.strip()} for tag in metadata.get('tags', 'Template').split(',')]}
                },
                children=blocks
            )
            print(f"Synced template: {metadata.get('title', template_file.stem)}")
            return page

        except Exception as e:
            print(f"Error syncing template {template_file}: {str(e)}")
            return None

    def sync_all_templates(self):
        """Sync all markdown templates with Notion."""
        try:
            print("Syncing templates...")
            for template_file in self.templates_dir.glob('*.md'):
                self.sync_template(template_file)
            print("Templates synced successfully!")
        except Exception as e:
            print(f"Error syncing templates: {str(e)}")

def main():
    try:
        sync = NotionTemplateSync()
        sync.sync_all_templates()
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
