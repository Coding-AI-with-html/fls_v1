from src.utils.src.utils.text_logger import get_logger

logger = get_logger()

def test_logs():
    logger.debug("Debug message from test_logger.")
    logger.info("Info message from test_logger.")
    logger.warning("Warning message from test_logger.")
    logger.error("Error message from test_logger.")
    logger.critical("Critical message from test_logger.")
    assert True  # Dummy assertion to make it a "real" test

if __name__ == "__main__":
    test_logs()
    print("Logs have been written to app_log.txt in the project root.")
