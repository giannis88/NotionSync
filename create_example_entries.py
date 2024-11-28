from notion_client import Client
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

class NotionExampleCreator:
    def __init__(self):
        load_dotenv()
        self.notion = Client(auth=os.getenv('NOTION_TOKEN'))
        self.main_db_id = os.getenv('NOTION_DATABASE_ID')
        self.health_db_id = os.getenv('HEALTH_DATABASE_ID')
        
        if not self.main_db_id or not self.health_db_id:
            raise ValueError("Database IDs not found in .env file")

    def create_main_entries(self):
        """Create example entries in the main dashboard."""
        try:
            print(f"Creating entries in main database {self.main_db_id}")
            
            # Create Health Overview
            health_page = self.notion.pages.create(
                parent={"database_id": self.main_db_id},
                properties={
                    "Name": {"title": [{"text": {"content": "Gesundheits-Übersicht"}}]},
                    "Type": {"select": {"name": "Health"}},
                    "Status": {"select": {"name": "Active"}},
                    "Priority": {"select": {"name": "High"}},
                    "Created": {"date": {"start": datetime.now().isoformat()}},
                    "Tags": {"multi_select": [
                        {"name": "Health"},
                        {"name": "Thalassämie"}
                    ]}
                }
            )
            print("Created Health Overview entry")

            # Create Business Plan
            business_page = self.notion.pages.create(
                parent={"database_id": self.main_db_id},
                properties={
                    "Name": {"title": [{"text": {"content": "YouTube Kanal Planung"}}]},
                    "Type": {"select": {"name": "Business"}},
                    "Status": {"select": {"name": "In Progress"}},
                    "Priority": {"select": {"name": "Medium"}},
                    "Created": {"date": {"start": datetime.now().isoformat()}},
                    "Tags": {"multi_select": [
                        {"name": "Business"},
                        {"name": "YouTube"}
                    ]}
                }
            )
            print("Created Business Plan entry")

        except Exception as e:
            print(f"Error creating main entries: {str(e)}")

    def create_health_entries(self):
        """Create example health tracking entries."""
        try:
            print(f"Creating entries in health database {self.health_db_id}")
            
            # Create entries for the past 3 days
            for i in range(3):
                date = datetime.now() - timedelta(days=i)
                
                entry = self.notion.pages.create(
                    parent={"database_id": self.health_db_id},
                    properties={
                        "Title": {"title": [{"text": {"content": f"Gesundheits-Log {date.strftime('%Y-%m-%d')}"}}]},
                        "Date": {"date": {"start": date.strftime("%Y-%m-%d")}},
                        "Energy Level": {"number": 7},
                        "Medication Taken": {"checkbox": True},
                        "Pain Level": {"number": 2},
                        "Blood Values": {"rich_text": [{"text": {"content": "HB: 12.4, MCV: 68.8, MCH: 20.6"}}]},
                        "Notes": {"rich_text": [{"text": {"content": "Guter Tag, Medikamente wie geplant eingenommen."}}]},
                        "Symptoms": {"multi_select": [
                            {"name": "Fatigue"}
                        ]}
                    }
                )
                print(f"Created health entry for {date.strftime('%Y-%m-%d')}")

        except Exception as e:
            print(f"Error creating health entries: {str(e)}")

def main():
    try:
        creator = NotionExampleCreator()
        print("Creating example entries...")
        creator.create_main_entries()
        creator.create_health_entries()
        print("Example entries created successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
