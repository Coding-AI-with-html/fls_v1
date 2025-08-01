import os
import sys
import inspect
import logging
from pathlib import Path
# ERROR CONTEXT
import datetime


# --- PATH HELPERS ---

def get_startup_path(alternate_path: str = os.getenv('TEMP', '')) -> Path:
    """
    Gets the startup path of either the 'frozen' exe or the running python script module.

    Parameters:
    - alternate_path: str
        If retrieving the startup path fails, alternate_path will be returned instead.

    Returns:
    - startup_path: Path
        An absolute path either to the 'frozen' startup exe or to the startup script module file.
    """	
    try:
        if getattr(sys, 'frozen', False):  
            base_dir = os.path.dirname(sys.executable)         # get folder of EXE startup file
        else:
            base_dir = os.path.dirname(__file__)  # get current folder of running module script

    except:
        base_dir = alternate_path

    return Path(base_dir)



def create_logfile_name(sub_dir: str = 'log', suffix: str = '.log', alternate_fullname: str = 'C:\\_temp_.log') -> Path:
    """
    Creates a logfile path based on the module or executable name.
    """
    try:
        startup_path = get_startup_path()
        if getattr(sys, 'frozen', False):
            module_name = Path(sys.executable).stem  # <<< THIS!
        else:
            module_name = Path(__file__).stem  # <<< ONLY if NOT frozen
        logfile = (startup_path / sub_dir / module_name).with_suffix(suffix)
    except Exception as e:
        print(f"Failed to create logfile name: {e}")
        logfile = Path(alternate_fullname).with_suffix(suffix)
    return logfile


# --- ROTATING FILE HANDLER ---

class RotatingTextFileHandler(logging.FileHandler):
    """
    Simple line-count based rotating file handler.
    When the number of lines exceeds max_lines, it clears the file.
    """
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
            if self.stream:
                self.stream.close()
            with open(self.filename, 'w', encoding=self.encoding or 'utf-8') as f:
                f.truncate(0)
            self.stream = self._open()
            self.line_count = 0
        except Exception as e:
            print(f"Failed to reset log file: {e}")

# --- LOGGER SETUP ---

_logger_registry = {}

def get_logger(name=None,level=logging.DEBUG):
    """
    Returns a logger named after the calling module.
    Creates it with a RotatingTextFileHandler if not already created.
    """

    if name is None:
        caller_frame = inspect.stack()[1]
        module = inspect.getmodule(caller_frame[0])
        name = module.__name__ if module else "UnknownModule"

    if name in _logger_registry:
        return _logger_registry[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        log_path = create_logfile_name(sub_dir='log', suffix='.log')
        os.makedirs(log_path.parent, exist_ok=True)
        handler = RotatingTextFileHandler(log_path, max_lines=1000)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _logger_registry[name] = logger
    return logger

# --- TESTING MAIN ---

def main():
    logger = get_logger()
    logger.info("This is an info log message.")
    logger.debug("This is a debug log message.")
    logger.warning("This is a warning log message.")

    log_file = create_logfile_name(sub_dir='log')
    print(f"Log file is stored at: {log_file}")

if __name__ == "__main__":
    main()



# ----------ERROR CONTEXT -----------

FLS_ERR_NoErrorContext = 10001
FLS_ERR_NoUnprocessedImage = 10002
FLS_ERR_InvalidInputFormat = 10003
FLS_ERR_ConnectionTimeout = 10004
FLS_ERR_NoPermission = 10005
FLS_ERR_ImageProcessingFailed = 10006
FLS_ERR_NO_IMAGE_AS_VIEW_SAVED = 10007

class ErrorContext:
    """
    A class to hold error information and log errors.
    """
    
    def __init__(self, logger=None):
        self.error = 0
        self.errordescription = ""
        self.logger = logger or get_logger()
        self.log_filename = create_logfile_name(sub_dir='log')

    def log_error(self):
        """
        Logs the current error details to the logfile if a logfile is specified.
        """
        if self.logger:
            self.logger.error(f"Error {self.error}: {self.errordescription}")

        if self.log_filename:  # Ensure the log file is defined before writing
            try:
                with open(self.log_filename, 'a') as log:
                    log.write("Logger is defined correctly")
                    log.write("\n")
            except Exception as e:
                print(f"Failed to write to log file '{self.log_filename}': {e}")
    @staticmethod        
    def get_error_string(error_index, locale="en-US", locale_filename = "text_logger"):
        """
        Defines error messages based on the error index(Needs more error_messages)
        IF there is a filename, then read it, and if there is not, then use context isntead of predifiend of error messages
        Args:
            error_index (int): The index of the error.

        Returns:
            str: The description of the error.
        """
        # TODO: insert swict locale command
        error_messages = {
            FLS_ERR_NoErrorContext: "Image context is empty or None.",
            FLS_ERR_NoUnprocessedImage: "No unprocessed images found.",
            FLS_ERR_InvalidInputFormat: "Invalid input format.",
            FLS_ERR_ConnectionTimeout: "Connection timeout.",
            FLS_ERR_NoPermission: "Insufficient permissions.",
            FLS_ERR_ImageProcessingFailed: "Error processing image.",
        }
        if locale_filename:
            try:
                with open(locale_filename, 'r') as file:
                    localized_messages = {}
                    for line in file:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            localized_messages[int(key)] = value
                    return localized_messages.get(error_index, "FLS_ERR : Undefined error index")
            except Exception as e:
                print(f"Failed to read localization file'{locale_filename}': {e}")

        return error_messages.get(error_index, "FLS_ERR: Undefined error index.")