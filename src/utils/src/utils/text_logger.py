import logging
import os
import inspect

# Custom file handler that resets the log file after a specified number of lines
class RotatingTextFileHandler(logging.FileHandler):
    def __init__(self, filename, max_lines=1000, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
        self.filename = filename
        self.max_lines = max_lines
        self.line_count = self._get_existing_line_count()  # Line counter
    def emit(self, record):
        # reset the file if limit reached
        if self.line_count >= self.max_lines:
            self._reset_file()
        super().emit(record)
        self.line_count += 1  # Increase line counter after each log line

    def _get_existing_line_count(self):
        # Get current log file num count
        if not os.path.exists(self.filename):
            return 0
        try:
            with open(self.filename, 'r', encoding=self.encoding or 'utf-8') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0  # Fallback if file can't be read

    def _reset_file(self):
        # Clear the log file and reset line count
        try:
            self.stream.close()  # Close the current stream
            with open(self.filename, 'w', encoding=self.encoding or 'utf-8') as f:
                f.truncate(0)  # clear file content
            self.stream = self._open()  # Reopen stream
            self.line_count = 0
        except Exception as e:
            print(f"Failed to reset log file: {e}")

#!!! Set log file path to the current working dir !!!!
# TODO:
# set log file path to root/general working directory
LOG_FILE = os.path.join(os.getcwd(), "app_log.txt")

# Dictionary to hold and reuse loggers per module
_logger_registry = {}

def get_logger(level=logging.DEBUG):
    """
    Creates or returns a logger with the caller's module name.
    Each module has their own.
    """
    # Get calling module name using stack inspection
    caller_frame = inspect.stack()[1]
    module = inspect.getmodule(caller_frame[0])
    module_name = module.__name__ if module else "UnknownModule"

    # Return existing logger if already created
    if module_name in _logger_registry:
        return _logger_registry[module_name]

    # Create logger for this module
    logger = logging.getLogger(module_name)
    logger.setLevel(level)

    # add handler if it doesint exist already
    if not logger.hasHandlers():
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler = RotatingTextFileHandler(LOG_FILE, max_lines=1000)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Save to registry for reuse
    _logger_registry[module_name] = logger
    return logger
