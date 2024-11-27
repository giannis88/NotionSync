from auto_notion_sync import NotionSync, setup_logging
import logging

def main():
    setup_logging()
    try:
        syncer = NotionSync()
        syncer.initialize_dashboard_structure()
        logging.info("Dashboard structure initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize dashboard: {str(e)}")
        raise

if __name__ == "__main__":
    main()
