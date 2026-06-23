"""Tests for Streamlit / CLI logging configuration."""

import logging

from dataroom.logging_config import (
    _BenignAsyncioNoiseFilter,
    configure_streamlit_logging,
)


def test_benign_asyncio_filter_drops_connection_reset():
    flt = _BenignAsyncioNoiseFilter()
    record = logging.LogRecord(
        name="asyncio",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)",
        args=(),
        exc_info=None,
    )
    assert flt.filter(record) is False


def test_benign_asyncio_filter_keeps_other_errors():
    flt = _BenignAsyncioNoiseFilter()
    record = logging.LogRecord(
        name="asyncio",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="Something else failed",
        args=(),
        exc_info=None,
    )
    assert flt.filter(record) is True


def test_configure_streamlit_logging_installs_filter():
    configure_streamlit_logging()
    asyncio_logger = logging.getLogger("asyncio")
    assert any(isinstance(f, _BenignAsyncioNoiseFilter) for f in asyncio_logger.filters)
