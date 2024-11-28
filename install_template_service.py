# -*- coding: utf-8 -*-
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time
from pathlib import Path
import logging
from template_watcher import start_watcher
import threading

class TemplateWatcherService(win32serviceutil.ServiceFramework):
    _svc_name_ = "NotionTemplateWatcher"
    _svc_display_name_ = "Notion Template Watcher Service"
    _svc_description_ = "Watches Notion templates directory and syncs changes to Notion"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_alive = True
        self.setup_logging()

    def setup_logging(self):
        """Set up logging configuration."""
        try:
            # Change to the script's directory
            os.chdir(str(Path(__file__).parent))
            
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_dir / "service.log"),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
            self.logger.info("Service logging initialized")
        except Exception as e:
            servicemanager.LogErrorMsg(f"Failed to setup logging: {str(e)}")

    def SvcStop(self):
        """Stop the service."""
        try:
            self.logger.info("Received stop signal")
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            self.is_alive = False
        except Exception as e:
            self.logger.error(f"Error stopping service: {str(e)}")

    def SvcDoRun(self):
        """Run the service."""
        try:
            self.logger.info("Starting service")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            # Start the watcher in a separate thread
            self.watcher_thread = threading.Thread(target=self.run_watcher)
            self.watcher_thread.daemon = True
            self.watcher_thread.start()
            
            # Main service loop
            while self.is_alive:
                # Check if the stop event is signaled
                if win32event.WaitForSingleObject(self.stop_event, 1000) == win32event.WAIT_OBJECT_0:
                    break
                time.sleep(1)
            
            self.logger.info("Service stopped")
            
        except Exception as e:
            self.logger.error(f"Service error: {str(e)}")
            servicemanager.LogErrorMsg(f"Service error: {str(e)}")

    def run_watcher(self):
        """Run the template watcher in a separate thread."""
        try:
            self.logger.info("Starting template watcher")
            start_watcher()
        except Exception as e:
            self.logger.error(f"Watcher error: {str(e)}")
            servicemanager.LogErrorMsg(f"Watcher error: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TemplateWatcherService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(TemplateWatcherService)
