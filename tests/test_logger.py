from ..src.utils.src.utils.text_logger import get_logger

logger = get_logger()

def run_test_logs():
    logger.debug("Debug message from test_logger.")
    logger.info("Info message from test_logger.")
    logger.warning("Warning message from test_logger.")
    logger.error("Error message from test_logger.")
    logger.critical("Critical message from test_logger.")

if __name__ == "__main__":
    run_test_logs()
    print("Logs have been written to app_log.txt in the project root.")
