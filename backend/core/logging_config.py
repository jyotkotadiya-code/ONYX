import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from backend.core.config import settings


def _create_handler(log_file: Path, level: int = logging.INFO) -> RotatingFileHandler:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=3,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def setup_loggers() -> dict[str, logging.Logger]:
    log_dir = settings.resolve_path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%H:%M:%S")
    )

    error_handler = _create_handler(log_dir / "errors.log", level=logging.ERROR)

    configs = {
        "app": log_dir / "app.log",
        "ingestion": log_dir / "ingestion.log",
        "retrieval": log_dir / "retrieval.log",
        "errors": log_dir / "errors.log",
    }

    loggers = {}
    for name, file_path in configs.items():
        logger = logging.getLogger(f"rag.{name}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not logger.handlers:
            logger.addHandler(_create_handler(file_path, logging.INFO))
            logger.addHandler(console_handler)
            if name != "errors":
                logger.addHandler(error_handler)
        loggers[name] = logger

    return loggers


_loggers = setup_loggers()
app_logger = _loggers["app"]
ingestion_logger = _loggers["ingestion"]
retrieval_logger = _loggers["retrieval"]
error_logger = _loggers["errors"]
