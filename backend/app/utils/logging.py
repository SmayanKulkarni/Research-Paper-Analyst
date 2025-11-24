import logging

logger = logging.getLogger("research-analyzer")
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
