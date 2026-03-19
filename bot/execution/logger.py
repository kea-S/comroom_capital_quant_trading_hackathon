import logging
import os
import sys

def setup_logger(name="trading_bot", level=logging.INFO):
    """
    Sets up a logger that outputs to both a file and the console.
    """
    # Create absolute path for log file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, "logs.txt")
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
logger = setup_logger()
