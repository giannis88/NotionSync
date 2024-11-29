import os
from notion_client import Client
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_notion_access():
    load_dotenv()
    notion = Client(auth=os.getenv('NOTION_TOKEN'))
    
    databases = {
        'main': os.getenv('NOTION_DATABASE_ID'),
        'health': os.getenv('HEALTH_DATABASE_ID'),
        'business': os.getenv('BUSINESS_DATABASE_ID')
    }
    
    for db_type, db_id in databases.items():
        try:
            logger.info(f"Checking {db_type} database ({db_id})...")
            db = notion.databases.retrieve(database_id=db_id)
            logger.info(f"✓ Successfully accessed {db_type} database")
            logger.info(f"Properties: {list(db.get('properties', {}).keys())}")
        except Exception as e:
            logger.error(f"✗ Failed to access {db_type} database: {str(e)}")

if __name__ == "__main__":
    verify_notion_access() 