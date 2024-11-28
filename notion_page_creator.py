import os
from notion_client import Client
from datetime import datetime
import json
from pathlib import Path
from dotenv import load_dotenv

class NotionPageCreator:
    def __init__(self):
        load_dotenv()
        self.notion = Client(auth=os.getenv('NOTION_TOKEN'))
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        
    def create_markdown_block(self, text):
        """Convert markdown text to Notion blocks."""
        blocks = []
        current_block = {"content": ""}
        
        for line in text.split('\n'):
            # Headers
            if line.startswith('# '):
                if current_block["content"]:
                    blocks.append(current_block)
                blocks.append({
                    "type": "heading_1",
                    "heading_1": {"rich_text": [{"text": {"content": line[2:]}}]}
                })
                current_block = {"content": ""}
            elif line.startswith('## '):
                if current_block["content"]:
                    blocks.append(current_block)
                blocks.append({
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": line[3:]}}]}
                })
                current_block = {"content": ""}
            elif line.startswith('### '):
                if current_block["content"]:
                    blocks.append(current_block)
                blocks.append({
                    "type": "heading_3",
                    "heading_3": {"rich_text": [{"text": {"content": line[4:]}}]}
                })
                current_block = {"content": ""}
            # Checkboxes
            elif line.startswith('- [ ] '):
                if current_block["content"]:
                    blocks.append(current_block)
                blocks.append({
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"text": {"content": line[6:]}}],
                        "checked": False
                    }
                })
                current_block = {"content": ""}
            # Tables
            elif line.startswith('|'):
                if current_block["content"]:
                    blocks.append(current_block)
                # Start collecting table rows
                table_rows = [line]
                current_block = {"type": "table", "rows": []}
            # Regular paragraph
            else:
                if line.strip():
                    if current_block.get("type") != "paragraph":
                        if current_block["content"]:
                            blocks.append(current_block)
                        current_block = {
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"text": {"content": line}}]
                            }
                        }
                    else:
                        current_block["paragraph"]["rich_text"][0]["text"]["content"] += "\n" + line

        if current_block["content"] or current_block.get("type"):
            blocks.append(current_block)
            
        return blocks

    def create_dashboard_pages(self):
        """Create Notion pages from markdown files."""
        dashboard_dir = Path("dashboard")
        if not dashboard_dir.exists():
            raise FileNotFoundError("Dashboard directory not found")

        # Create main dashboard page
        main_dashboard_path = dashboard_dir / "main_dashboard.md"
        if main_dashboard_path.exists():
            with open(main_dashboard_path, 'r', encoding='utf-8') as f:
                main_content = f.read()
                
            # Create main dashboard page
            main_page = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "Name": {"title": [{"text": {"content": "Master Dashboard"}}]},
                    "Type": {"select": {"name": "Dashboard"}},
                    "Created": {"date": {"start": datetime.now().isoformat()}}
                },
                children=self.create_markdown_block(main_content)
            )
            
            # Create subpages
            subpages = {
                "health_hub.md": "🏥 Health Hub",
                "business_center.md": "💼 Business Center",
                "personal_growth.md": "❤️ Personal Growth"
            }
            
            for filename, title in subpages.items():
                filepath = dashboard_dir / filename
                if filepath.exists():
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Create subpage
                    subpage = self.notion.pages.create(
                        parent={"page_id": main_page["id"]},
                        properties={
                            "title": {"title": [{"text": {"content": title}}]}
                        },
                        children=self.create_markdown_block(content)
                    )
                    print(f"Created {title} page")
            
            print("All dashboard pages created successfully!")
            return main_page["url"]
        else:
            raise FileNotFoundError("Main dashboard file not found")

def main():
    try:
        creator = NotionPageCreator()
        dashboard_url = creator.create_dashboard_pages()
        print(f"Dashboard created successfully! View it here: {dashboard_url}")
    except Exception as e:
        print(f"Error creating Notion pages: {str(e)}")

if __name__ == "__main__":
    main()
