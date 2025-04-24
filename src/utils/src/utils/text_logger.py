# -*- coding: utf-8 -*-
import os
import sys
import inspect
import logging
from pathlib import Path

# --- PATH HELPERS ---

def get_startup_path(alternate_path: str = os.getenv('TEMP', '')) -> Path:
    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)  # If bundled as EXE
        else:
            base_dir = os.path.dirname(__file__)  # Normal script path
    except:
        base_dir = alternate_path
    return Path(base_dir)

def create_logfile_name(sub_dir: str = 'log', suffix: str = '.log', alternate_fullname: str = 'C:\\_temp_.log') -> Path:
    try:
        startup_path = get_startup_path()
        module_name = __file__.split(os.path.sep)[-1]
        logfile = (Path.joinpath(startup_path, sub_dir) / module_name).with_suffix(suffix)
    except:
        logfile = Path(alternate_fullname).with_suffix(suffix)
    return logfile

# --- ROTATING FILE HANDLER ---

class RotatingTextFileHandler(logging.FileHandler):
    def __init__(self, filename, max_lines=1000, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
        self.filename = filename
        self.max_lines = max_lines
        self.line_count = self._get_existing_line_count()

    def emit(self, record):
        if self.line_count >= self.max_lines:
            self._reset_file()
        super().emit(record)
        self.line_count += 1

    def _get_existing_line_count(self):
        if not os.path.exists(self.filename):
            return 0
        try:
            with open(self.filename, 'r', encoding=self.encoding or 'utf-8') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def _reset_file(self):
        try:
            self.stream.close()
            with open(self.filename, 'w', encoding=self.encoding or 'utf-8') as f:
                f.truncate(0)
            self.stream = self._open()
            self.line_count = 0
        except Exception as e:
            print(f"Failed to reset log file: {e}")

# --- LOGGER SETUP ---

_logger_registry = {}

def get_logger(level=logging.DEBUG):
    """
    Returns a logger named after the calling module.
    Creates it with a RotatingTextFileHandler.
    """
    caller_frame = inspect.stack()[1]
    module = inspect.getmodule(caller_frame[0])
    module_name = module.__name__ if module else "UnknownModule"

    if module_name in _logger_registry:
        return _logger_registry[module_name]

    logger = logging.getLogger(module_name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        log_path = create_logfile_name(sub_dir='log', suffix='.log')
        os.makedirs(log_path.parent, exist_ok=True)
        handler = RotatingTextFileHandler(log_path, max_lines=1000)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _logger_registry[module_name] = logger
    return logger

# --- TESTING MAIN ---

def main():
    logger = get_logger()
    logger.info("This is an info log message.")
    logger.debug("This is a debug log message.")
    logger.warning("This is a warning log message.")

    print(f"Log file is stored at: {create_logfile_name(sub_dir='log')}")

if __name__ == "__main__":
    main()
