from .fls_gui import main
from core import text_logger

logger = text_logger.get_logger()
logger.info("This is a message from my_module.")

if __name__ == "__main__":
    main
