"""
STARK Structured Logger
=======================
Centralized logging with file rotation and structured output.

Module 9 of 9 - Utilities
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from datetime import datetime

from core.constants import (
    LOGS_DIR,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_TO_FILE,
    LOG_FILE_MAX_BYTES,
    LOG_FILE_BACKUP_COUNT,
)


class STARKLogger:
    """
    Centralized logging configuration for STARK.
    
    Features:
    - Structured format with timestamp, module, level, message
    - Console and file output
    - Log file rotation at 10MB
    - Configurable log level via LOG_LEVEL constant
    
    Usage:
        # In any module:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Message here")
        
        # Or use the setup function once at startup:
        from utils.logger import setup_logging
        setup_logging()
    """
    
    _initialized = False
    
    @classmethod
    def setup(
        cls,
        log_level: Optional[str] = None,
        log_dir: Optional[Path] = None,
        log_to_file: Optional[bool] = None,
    ) -> None:
        """
        Configure the root logger for STARK.
        
        Args:
            log_level: Override LOG_LEVEL constant
            log_dir: Override LOGS_DIR constant
            log_to_file: Override LOG_TO_FILE constant
        """
        if cls._initialized:
            return
        
        level = getattr(logging, log_level or LOG_LEVEL, logging.INFO)
        log_dir = log_dir or LOGS_DIR
        to_file = log_to_file if log_to_file is not None else LOG_TO_FILE
        
        # Create logs directory
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if to_file:
            log_file = log_dir / f"stark_{datetime.now():%Y%m%d}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=LOG_FILE_MAX_BYTES,
                backupCount=LOG_FILE_BACKUP_COUNT,
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            root_logger.addHandler(file_handler)
        
        cls._initialized = True
        
        # Log startup
        logger = logging.getLogger(__name__)
        logger.info(f"STARK logging initialized: level={log_level or LOG_LEVEL}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger with the given name.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Configured logger instance
        """
        if not cls._initialized:
            cls.setup()
        return logging.getLogger(name)


def setup_logging(
    log_level: Optional[str] = None,
    log_dir: Optional[Path] = None,
    log_to_file: Optional[bool] = None,
) -> None:
    """
    Initialize STARK logging.
    
    Call once at application startup.
    """
    STARKLogger.setup(log_level, log_dir, log_to_file)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with optional auto-setup."""
    return STARKLogger.get_logger(name)
