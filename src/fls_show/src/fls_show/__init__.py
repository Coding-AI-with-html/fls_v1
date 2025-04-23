from .fls_show import main
from utils import get_logger

logger = get_logger()
logger.info("This is a message from my_module.")

if __name__ == "__main__":
    main
