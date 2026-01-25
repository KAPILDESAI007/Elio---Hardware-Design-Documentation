import logging
from pathlib import Path

def setup_logger():
    log_dir = Path(r"C:\Working\Others\Python\Cloud App Projects\logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger("CloudAppLogger")
    logger.setLevel(logging.DEBUG)
    
    fh = logging.FileHandler(log_dir / "process.log")
    fh.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger
