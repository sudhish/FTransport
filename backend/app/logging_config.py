"""
Logging configuration for FTransport backend
"""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

def setup_logging():
    """Setup logging with separate files for different components"""
    
    # Create logs directory
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)8s | %(name)s | %(filename)s:%(lineno)d | %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)8s | %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove default handlers
    root_logger.handlers.clear()
    
    # 1. Main application log (rotating)
    main_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "ftransport.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    main_handler.setFormatter(detailed_formatter)
    main_handler.setLevel(logging.INFO)
    root_logger.addHandler(main_handler)
    
    # 2. Error log (rotating) 
    error_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "error.log",
        maxBytes=5*1024*1024,   # 5MB
        backupCount=3
    )
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    # 3. Transfer workflow log (rotating)
    transfer_logger = logging.getLogger("transfer")
    transfer_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "transfers.log", 
        maxBytes=20*1024*1024,  # 20MB
        backupCount=5
    )
    transfer_handler.setFormatter(detailed_formatter)
    transfer_logger.addHandler(transfer_handler)
    transfer_logger.setLevel(logging.INFO)
    
    # 4. API requests log (rotating)
    api_logger = logging.getLogger("api")
    api_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "api.log",
        maxBytes=10*1024*1024,  # 10MB  
        backupCount=3
    )
    api_handler.setFormatter(detailed_formatter)
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)
    
    # 5. NotebookLM service log (rotating)
    notebooklm_logger = logging.getLogger("notebooklm")
    notebooklm_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "notebooklm.log",
        maxBytes=5*1024*1024,   # 5MB
        backupCount=3
    )
    notebooklm_handler.setFormatter(detailed_formatter)
    notebooklm_logger.addHandler(notebooklm_handler)
    notebooklm_logger.setLevel(logging.INFO)
    
    # 6. Google Drive service log (rotating)
    gdrive_logger = logging.getLogger("google_drive")
    gdrive_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "google_drive.log",
        maxBytes=5*1024*1024,   # 5MB
        backupCount=3
    )
    gdrive_handler.setFormatter(detailed_formatter)
    gdrive_logger.addHandler(gdrive_handler)
    gdrive_logger.setLevel(logging.INFO)
    
    # 7. Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Log the setup
    logging.info("🗂️ Logging system initialized")
    logging.info(f"📁 Log files location: {logs_dir}")
    
    return {
        "logs_dir": logs_dir,
        "loggers": {
            "main": root_logger,
            "transfer": transfer_logger,
            "api": api_logger,
            "notebooklm": notebooklm_logger,
            "google_drive": gdrive_logger
        }
    }

def get_logger(name: str = None):
    """Get a logger instance"""
    if name:
        return logging.getLogger(name)
    return logging.getLogger()