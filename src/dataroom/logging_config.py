"""CLI logging setup — keep third-party libraries quiet by default."""

from __future__ import annotations

import logging
import sys

_QUIET_LOGGERS = (
    "httpx",
    "httpcore",
    "sentence_transformers",
    "transformers",
    "huggingface_hub",
    "faiss",
    "torch",
    "urllib3",
)

_BENIGN_ASYNCIO_MARKERS = (
    "ConnectionResetError",
    "WinError 10054",
    "_ProactorBasePipeTransport._call_connection_lost",
    "forcibly closed by the remote host",
)


class _BenignAsyncioNoiseFilter(logging.Filter):
    """Drop benign Windows asyncio errors when a browser disconnects from Streamlit."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "asyncio":
            return True
        message = record.getMessage()
        if any(marker in message for marker in _BENIGN_ASYNCIO_MARKERS):
            return False
        if record.exc_info and isinstance(record.exc_info[1], ConnectionResetError):
            return False
        return True


def configure_cli_logging(*, verbose: bool = False) -> None:
    """Configure logging for ``dataroom`` CLI commands."""
    root_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=root_level,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )
    logging.getLogger("dataroom").setLevel(logging.DEBUG if verbose else logging.INFO)
    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.DEBUG if verbose else logging.WARNING)


def _asyncio_exception_handler(loop, context: dict) -> None:
    """Ignore connection resets on Windows when Streamlit/Uvicorn clients disconnect."""
    exc = context.get("exception")
    if isinstance(exc, ConnectionResetError):
        return
    message = str(context.get("message", ""))
    if "connection_lost" in message and isinstance(exc, ConnectionResetError):
        return
    loop.default_exception_handler(context)


def configure_streamlit_logging() -> None:
    """Configure logging before launching the Streamlit UI."""
    configure_cli_logging(verbose=False)
    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.addFilter(_BenignAsyncioNoiseFilter())
    if sys.platform == "win32":
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.set_exception_handler(_asyncio_exception_handler)
