import logging
import os
import sys
from config import LOG_FILE

def setup_logger(name="trading_bot", log_file="../logs/logs.txt", level=logging.INFO):
    """
    Sets up a logger that outputs to both a file and the console.
    """
    print(f"log_file={log_file}")
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent potential duplication if setup is called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # File Handler - append mode
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setFormatter(formatter)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Add handlers correctly
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Single instance for the whole bot
logger = setup_logger(log_file=str(LOG_FILE))
