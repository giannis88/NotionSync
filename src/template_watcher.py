# -*- coding: utf-8 -*-
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import shutil
import logging
from pathlib import Path
from template_sync import NotionTemplateSync
import json

class TemplateHandler(FileSystemEventHandler):
    def __init__(self):
        self.template_sync = NotionTemplateSync()
        self.setup_logging()
        self.last_sync = {}  # Track last sync time for each file
        self.setup_backup_dir()

    def setup_logging(self):
        """Set up logging configuration."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "template_sync.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_backup_dir(self):
        """Set up backup directory structure."""
        self.backup_dir = Path("backups/templates")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup metadata file if it doesn't exist
        self.backup_metadata_file = self.backup_dir / "backup_metadata.json"
        if not self.backup_metadata_file.exists():
            with open(self.backup_metadata_file, "w") as f:
                json.dump({}, f)

    def create_backup(self, template_path):
        """Create a backup of the template before syncing."""
        try:
            template_path = Path(template_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{template_path.stem}_{timestamp}{template_path.suffix}"
            
            # Create backup
            shutil.copy2(template_path, backup_path)
            
            # Update metadata
            with open(self.backup_metadata_file, "r") as f:
                metadata = json.load(f)
            
            if template_path.stem not in metadata:
                metadata[template_path.stem] = []
            
            metadata[template_path.stem].append({
                "timestamp": timestamp,
                "backup_path": str(backup_path),
                "original_path": str(template_path)
            })
            
            # Keep only last 5 backups
            if len(metadata[template_path.stem]) > 5:
                old_backup = metadata[template_path.stem].pop(0)
                old_backup_path = Path(old_backup["backup_path"])
                if old_backup_path.exists():
                    old_backup_path.unlink()
            
            with open(self.backup_metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Created backup: {backup_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            return False

    def should_sync(self, template_path):
        """Determine if the template should be synced based on last sync time."""
        current_time = time.time()
        if template_path in self.last_sync:
            # Only sync if more than 5 seconds have passed since last sync
            if current_time - self.last_sync[template_path] < 5:
                return False
        self.last_sync[template_path] = current_time
        return True

    def on_modified(self, event):
        """Handle template modification events."""
        if event.is_directory:
            return
        
        if not event.src_path.endswith('.md'):
            return
            
        template_path = event.src_path
        if not self.should_sync(template_path):
            return
            
        try:
            self.logger.info(f"Template modified: {template_path}")
            
            # Create backup before sync
            if self.create_backup(template_path):
                # Sync template to Notion
                self.template_sync.sync_template(Path(template_path))
                self.logger.info(f"Template synced successfully: {template_path}")
            else:
                self.logger.error(f"Skipping sync due to backup failure: {template_path}")
                
        except Exception as e:
            self.logger.error(f"Error syncing template: {str(e)}")

def start_watcher():
    """Start the template watcher."""
    try:
        templates_dir = Path("templates")
        if not templates_dir.exists():
            logging.error(f"Templates directory not found: {templates_dir}")
            return

        event_handler = TemplateHandler()
        observer = Observer()
        observer.schedule(event_handler, str(templates_dir), recursive=False)
        observer.start()
        
        logging.info(f"Watching templates directory: {templates_dir}")
        
        # When running as a service, we don't want to block with input
        # Instead, we'll use an infinite loop that can be broken by the service
        while True:
            time.sleep(1)
            
    except Exception as e:
        logging.error(f"Error in template watcher: {str(e)}")
        raise
    finally:
        if 'observer' in locals():
            observer.stop()
            observer.join()
            logging.info("Template watcher stopped")

if __name__ == "__main__":
    start_watcher()
