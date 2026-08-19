"""
VRCVideoTester (vrcvt) - Logging Subsystem with Dual Console and File Handlers
"""

import sys
import logging
from pathlib import Path
from typing import Optional

class ColorFormatter(logging.Formatter):
    """Custom ANSI color logging formatter for terminal output."""
    
    COLOR_RESET = "\033[0m"
    COLOR_BOLD = "\033[1m"
    COLOR_RED = "\033[31m"
    COLOR_GREEN = "\033[32m"
    COLOR_YELLOW = "\033[33m"
    COLOR_CYAN = "\033[36m"
    COLOR_GRAY = "\033[90m"

    FORMATS = {
        logging.DEBUG: COLOR_GRAY + "%(asctime)s [DEBUG] %(message)s" + COLOR_RESET,
        logging.INFO: COLOR_CYAN + "%(message)s" + COLOR_RESET,
        logging.WARNING: COLOR_YELLOW + "[!] %(message)s" + COLOR_RESET,
        logging.ERROR: COLOR_RED + "[!] ERROR: %(message)s" + COLOR_RESET,
        logging.CRITICAL: COLOR_BOLD + COLOR_RED + "[CRITICAL] %(message)s" + COLOR_RESET
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, "%(message)s")
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

class VRCLogger:
    """Manages application logging across terminal stdout and persistent log files."""

    def __init__(self, log_file: Optional[Path] = None, verbosity: int = logging.INFO):
        self.logger = logging.getLogger("vrcvt")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        # Console Stream Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(verbosity)
        console_handler.setFormatter(ColorFormatter())
        self.logger.addHandler(console_handler)

        # File Handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def success(self, msg: str) -> None:
        self.logger.info(f"\033[32m[✓] {msg}\033[0m")

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)

    def debug(self, msg: str) -> None:
        self.logger.debug(msg)

# Global default logger instance
logger = VRCLogger(log_file=Path("vrcvt.log"))
