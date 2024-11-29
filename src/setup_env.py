import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_environment():
    # Load environment variables
    load_dotenv()
    
    # Create required directories
    directories = [
        os.getenv('TEMPLATE_DIR', 'templates'),
        os.getenv('LOG_DIR', 'logs'),
        os.getenv('DATA_DIR', 'data'),
        os.getenv('BACKUP_DIR', 'backups')
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
        else:
            logger.info(f"Directory already exists: {directory}")

if __name__ == "__main__":
    setup_environment()
