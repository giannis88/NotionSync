# -*- coding: utf-8 -*-
from notion_client import Client
import os
from datetime import datetime
from dotenv import load_dotenv
import json
import sys

# Set UTF-8 encoding for stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class NotionTemplateManager:
    def __init__(self):
        load_dotenv()
        self.notion = Client(auth=os.getenv('NOTION_TOKEN'))
        self.main_db_id = os.getenv('NOTION_DATABASE_ID')
        self.health_db_id = os.getenv('HEALTH_DATABASE_ID')

    def create_template_pages(self):
        """Create template pages in Notion."""
        templates = {
            "health_daily": {
                "title": "Tägliche Gesundheitsvorlage",
                "emoji": "🏥",
                "content": [
                    {
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"text": {"content": "Tägliche Gesundheitsüberwachung"}}]}
                    },
                    {
                        "type": "to_do",
                        "to_do": {"rich_text": [{"text": {"content": "Medikamente eingenommen"}}]}
                    },
                    {
                        "type": "to_do",
                        "to_do": {"rich_text": [{"text": {"content": "Blutwerte gemessen"}}]}
                    },
                    {
                        "type": "divider",
                        "divider": {}
                    },
                    {
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"text": {"content": "Symptome & Energie"}}]}
                    },
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": "Energielevel (1-10): "}}]}
                    },
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": "Schmerzlevel (1-10): "}}]}
                    },
                    {
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": [{"text": {"content": "Beobachtete Symptome:"}}]}
                    },
                    {
                        "type": "divider",
                        "divider": {}
                    },
                    {
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"text": {"content": "Blutwerte"}}]}
                    },
                    {
                        "type": "table",
                        "table": {
                            "table_width": 2,
                            "has_column_header": True,
                            "has_row_header": False,
                            "children": [
                                {
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [
                                            [{"text": {"content": "Wert"}}],
                                            [{"text": {"content": "Messung"}}]
                                        ]
                                    }
                                },
                                {
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [
                                            [{"text": {"content": "HB"}}],
                                            [{"text": {"content": ""}}]
                                        ]
                                    }
                                },
                                {
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [
                                            [{"text": {"content": "MCV"}}],
                                            [{"text": {"content": ""}}]
                                        ]
                                    }
                                },
                                {
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [
                                            [{"text": {"content": "MCH"}}],
                                            [{"text": {"content": ""}}]
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
            "business_project": {
                "title": "Projekt Template",
                "emoji": "💼",
                "content": [
                    {
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"text": {"content": "Projektübersicht"}}]}
                    },
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": "Projektziel: "}}]}
                    },
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": "Deadline: "}}]}
                    },
                    {
                        "type": "divider",
                        "divider": {}
                    },
                    {
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"text": {"content": "Hauptaufgaben"}}]}
                    },
                    {
                        "type": "to_do",
                        "to_do": {"rich_text": [{"text": {"content": "Task 1"}}]}
                    },
                    {
                        "type": "to_do",
                        "to_do": {"rich_text": [{"text": {"content": "Task 2"}}]}
                    },
                    {
                        "type": "to_do",
                        "to_do": {"rich_text": [{"text": {"content": "Task 3"}}]}
                    },
                    {
                        "type": "divider",
                        "divider": {}
                    },
                    {
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"text": {"content": "Ressourcen"}}]}
                    },
                    {
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": [{"text": {"content": "Budget: "}}]}
                    },
                    {
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": [{"text": {"content": "Team: "}}]}
                    }
                ]
            },
            "personal_growth": {
                "title": "Persönliche Entwicklung",
                "emoji": "🌱",
                "content": [
                    {
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"text": {"content": "Entwicklungsziele"}}]}
                    },
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": "Hauptziel: "}}]}
                    },
                    {
                        "type": "divider",
                        "divider": {}
                    },
                    {
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"text": {"content": "Aktionsplan"}}]}
                    },
                    {
                        "type": "to_do",
                        "to_do": {"rich_text": [{"text": {"content": "Schritt 1"}}]}
                    },
                    {
                        "type": "to_do",
                        "to_do": {"rich_text": [{"text": {"content": "Schritt 2"}}]}
                    },
                    {
                        "type": "to_do",
                        "to_do": {"rich_text": [{"text": {"content": "Schritt 3"}}]}
                    },
                    {
                        "type": "divider",
                        "divider": {}
                    },
                    {
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"text": {"content": "Fortschrittsmessung"}}]}
                    },
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": "Aktueller Stand: "}}]}
                    },
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": "Nächster Meilenstein: "}}]}
                    }
                ]
            }
        }

        try:
            for template_name, template_data in templates.items():
                # Create template page in the main database
                page = self.notion.pages.create(
                    parent={"database_id": self.main_db_id},
                    icon={"type": "emoji", "emoji": template_data["emoji"]},
                    properties={
                        "Name": {"title": [{"text": {"content": template_data["title"]}}]},
                        "Type": {"select": {"name": "Template"}},
                        "Status": {"select": {"name": "Template"}},
                        "Tags": {"multi_select": [{"name": "Template"}]}
                    },
                    children=template_data["content"]
                )
                print(f"Created template: {template_data['title']}")

        except Exception as e:
            print(f"Error creating templates: {str(e)}")

def main():
    try:
        template_manager = NotionTemplateManager()
        print("Creating templates...")
        template_manager.create_template_pages()
        print("Templates created successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
