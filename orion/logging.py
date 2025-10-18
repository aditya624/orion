import logging, sys

def init_logger():
    logger = logging.getLogger("orion")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
    )
    handler.setFormatter(fmt)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger

logger = init_logger()