"""Structured JSON logging setup using structlog."""

import logging
import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON output for production."""
    logging.basicConfig(level=getattr(logging, log_level.upper()))

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )
