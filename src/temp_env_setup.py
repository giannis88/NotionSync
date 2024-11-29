import os

os.environ['NOTION_TOKEN'] = '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'
os.environ['NOTION_PAGE_ID'] = '14ce4a7d76a480f9bdb7dbb74774cf83'

from notion_client import Client
from datetime import datetime

def setup_notion_dashboard():
    notion = Client(auth=os.environ['NOTION_TOKEN'])
    page_id = os.environ['NOTION_PAGE_ID']
    
    # Create main database
    database = notion.databases.create(
        parent={"page_id": page_id},
        title=[{
            "type": "text",
            "text": {"content": "Personal Dashboard"}
        }],
        properties={
            "Name": {"title": {}},
            "Type": {
                "select": {
                    "options": [
                        {"name": "Health", "color": "red"},
                        {"name": "Business", "color": "blue"},
                        {"name": "Personal", "color": "green"},
                        {"name": "Dashboard", "color": "default"}
                    ]
                }
            },
            "Status": {
                "select": {
                    "options": [
                        {"name": "Active", "color": "green"},
                        {"name": "In Progress", "color": "yellow"},
                        {"name": "Completed", "color": "blue"},
                        {"name": "On Hold", "color": "red"}
                    ]
                }
            },
            "Priority": {
                "select": {
                    "options": [
                        {"name": "High", "color": "red"},
                        {"name": "Medium", "color": "yellow"},
                        {"name": "Low", "color": "blue"}
                    ]
                }
            },
            "Created": {"date": {}}
        }
    )
    
    # Create initial entries
    create_dashboard_entry(notion, database['id'], "Business Center", "Business")
    create_dashboard_entry(notion, database['id'], "Health Hub", "Health")
    
    return database['id']

def create_dashboard_entry(notion, database_id, name, entry_type):
    notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "Name": {"title": [{"text": {"content": name}}]},
            "Type": {"select": {"name": entry_type}},
            "Status": {"select": {"name": "Active"}},
            "Priority": {"select": {"name": "High"}},
            "Created": {"date": {"start": datetime.now().date().isoformat()}}
        }
    )

if __name__ == "__main__":
    database_id = setup_notion_dashboard()
    print(f"Created Notion database with ID: {database_id}")
