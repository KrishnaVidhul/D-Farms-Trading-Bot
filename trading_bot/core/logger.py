
import logging
import logging.handlers
import os
import sys

def setup_logger(name, log_file=None, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File Handler (Rotating)
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5 # 10MB x 5 backups
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
    return logger
