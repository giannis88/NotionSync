from notion_client import Client
import os
from dotenv import load_dotenv

class NotionDatabaseSetup:
    def __init__(self):
        load_dotenv()
        self.notion = Client(auth=os.getenv('NOTION_TOKEN'))

    def create_main_database(self, page_id):
        """Create the main dashboard database in the specified page."""
        try:
            # Create the main database
            database = self.notion.databases.create(
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
                    "Created": {"date": {}},
                    "Last Updated": {"last_edited_time": {}},
                    "Tags": {"multi_select": {
                        "options": [
                            {"name": "Health", "color": "red"},
                            {"name": "ADHS", "color": "orange"},
                            {"name": "Thalassämie", "color": "yellow"},
                            {"name": "Business", "color": "green"},
                            {"name": "YouTube", "color": "blue"},
                            {"name": "Personal", "color": "purple"}
                        ]
                    }}
                }
            )
            print(f"Main database created successfully! ID: {database['id']}")
            return database['id']
        
        except Exception as e:
            print(f"Error creating database: {str(e)}")
            return None

    def create_health_database(self, page_id):
        """Create the health tracking database."""
        try:
            database = self.notion.databases.create(
                parent={"page_id": page_id},
                title=[{
                    "type": "text",
                    "text": {"content": "Health Tracking"}
                }],
                icon={
                    "type": "emoji",
                    "emoji": "🏥"
                },
                properties={
                    "Title": {"title": {}},
                    "Date": {"date": {}},
                    "Energy Level": {
                        "number": {
                            "format": "number"
                        }
                    },
                    "Medication Taken": {"checkbox": {}},
                    "Pain Level": {
                        "number": {
                            "format": "number"
                        }
                    },
                    "Blood Values": {"rich_text": {}},
                    "Notes": {"rich_text": {}},
                    "Symptoms": {"multi_select": {
                        "options": [
                            {"name": "Fatigue", "color": "red"},
                            {"name": "Pain", "color": "yellow"},
                            {"name": "Anxiety", "color": "blue"}
                        ]
                    }}
                }
            )
            print(f"Health database created successfully! ID: {database['id']}")
            return database['id']
        
        except Exception as e:
            print(f"Error creating health database: {str(e)}")
            return None

def main():
    setup = NotionDatabaseSetup()
    
    # Get the page ID where you want to create the database
    page_id = input("Enter the Notion page ID where you want to create the database: ")
    
    # Create main database
    main_db_id = setup.create_main_database(page_id)
    if main_db_id:
        print(f"\nMain database created successfully!")
        print(f"Please update your .env file with:")
        print(f"NOTION_DATABASE_ID={main_db_id}")
        
        # Create health database
        health_db_id = setup.create_health_database(page_id)
        if health_db_id:
            print(f"\nHealth database created successfully!")
            print(f"Health database ID: {health_db_id}")

if __name__ == "__main__":
    main()
