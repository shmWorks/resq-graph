"""
sim_logger.py – Sprint 7 (US-028)

Centralised logging infrastructure for the ResQ-Graph simulation.

Responsibilities
----------------
1. Configure the Python ``logging`` package once at startup with:
   - A console handler (colourised if available).
   - A rotating file handler writing to ``outputs/sim.log``.
2. Maintain an in-memory ring-buffer of the last *N* human-readable log
   lines so the Pygame renderer can draw the HUD log-strip and the
   expandable log-history overlay without touching the filesystem.

Public API
----------
    from src.simulation.sim_logger import setup_logging, SimLogBuffer

    # Once at startup:
    setup_logging(level="INFO", log_file="outputs/sim.log")

    # Shared buffer instance passed to the renderer:
    log_buf = SimLogBuffer(capacity=200)
    log_buf.attach()   # starts intercepting log records

    # Renderer reads:
    recent = log_buf.tail(5)   # list[str] – last 5 lines
    all_lines = log_buf.all()  # list[str] – full ring-buffer
"""
from __future__ import annotations

import collections
import logging
import logging.handlers
import os
from typing import Sequence


# ── Colour codes (ANSI) ────────────────────────────────────────────────────────

_LEVEL_COLOURS: dict[int, str] = {
    logging.DEBUG:   "\033[36m",   # cyan
    logging.INFO:    "\033[32m",   # green
    logging.WARNING: "\033[33m",   # yellow
    logging.ERROR:   "\033[31m",   # red
    logging.CRITICAL:"\033[35m",   # magenta
}
_RESET = "\033[0m"


class _ColouredFormatter(logging.Formatter):
    """Apply ANSI colour codes to the level-name field."""

    _FMT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    _DATEFMT = "%H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        colour = _LEVEL_COLOURS.get(record.levelno, "")
        record.levelname = f"{colour}{record.levelname}{_RESET}"
        return super().format(record)

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt=self._DATEFMT)


class _PlainFormatter(logging.Formatter):
    _FMT    = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    _DATEFMT = "%H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt=self._DATEFMT)


# ── Public setup function ──────────────────────────────────────────────────────

def setup_logging(
    level: str | int = "INFO",
    log_file: str | None = "outputs/sim.log",
) -> None:
    """Configure the root logger for the simulation.

    Parameters
    ----------
    level:
        Minimum log level (e.g. ``"DEBUG"``, ``"INFO"``, ``logging.WARNING``).
    log_file:
        Path to the rotating log file.  Pass ``None`` to disable file logging.
        Parent directories are created automatically.
    """
    numeric_level = (
        getattr(logging, level.upper(), logging.INFO)
        if isinstance(level, str)
        else level
    )

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Avoid adding duplicate handlers if called more than once
    root.handlers.clear()

    # ── Console handler ────────────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(numeric_level)
    try:
        import sys
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            ch.setFormatter(_ColouredFormatter())
        else:
            ch.setFormatter(_PlainFormatter())
    except Exception:
        ch.setFormatter(_PlainFormatter())
    root.addHandler(ch)

    # ── Rotating file handler ──────────────────────────────────────────────
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,   # 5 MB per file
            backupCount=3,
            encoding="utf-8",
        )
        fh.setLevel(numeric_level)
        fh.setFormatter(_PlainFormatter())
        root.addHandler(fh)

    logging.getLogger(__name__).info(
        "Logging configured: level=%s, file=%s", level, log_file
    )


# ── In-memory ring-buffer ──────────────────────────────────────────────────────

class _BufferHandler(logging.Handler):
    """Logging handler that appends formatted records to a deque."""

    def __init__(self, buffer: collections.deque) -> None:
        super().__init__()
        self._buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._buffer.append(msg)
        except Exception:
            self.handleError(record)


class SimLogBuffer:
    """Thread-safe ring-buffer of recent log lines for on-screen display.

    Parameters
    ----------
    capacity:
        Maximum number of log lines to retain.  Older lines are discarded
        automatically (``deque`` with ``maxlen``).

    Usage
    -----
    Create one shared instance, call :meth:`attach` once after
    :func:`setup_logging`, then pass it to the renderer.

    ::

        buf = SimLogBuffer(capacity=200)
        buf.attach()
        recent = buf.tail(5)   # e.g. for the HUD strip
    """

    _FMT = "%(asctime)s [%(levelname)-8s] %(message)s"
    _DATEFMT = "%H:%M:%S"

    def __init__(self, capacity: int = 200) -> None:
        self._deque: collections.deque[str] = collections.deque(maxlen=capacity)
        self._handler: _BufferHandler | None = None

    def attach(self, logger_name: str | None = None) -> None:
        """Start intercepting log records.

        Parameters
        ----------
        logger_name:
            Name of the logger to attach to.  ``None`` attaches to the root
            logger (captures everything).
        """
        handler = _BufferHandler(self._deque)
        handler.setFormatter(logging.Formatter(fmt=self._FMT, datefmt=self._DATEFMT))
        target = logging.getLogger(logger_name)
        target.addHandler(handler)
        self._handler = handler

    def tail(self, n: int = 5) -> list[str]:
        """Return the last *n* log lines (most recent last)."""
        items = list(self._deque)
        return items[-n:]

    def all(self) -> list[str]:
        """Return all buffered log lines in chronological order."""
        return list(self._deque)

    def clear(self) -> None:
        """Flush the buffer."""
        self._deque.clear()

    def __len__(self) -> int:
        return len(self._deque)
