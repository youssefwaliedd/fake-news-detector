"""Structured JSON logging + a node-timing helper.

The ``timed_node`` decorator wraps every graph node so each run emits one JSON
line: {node, input_keys, output_keys, latency_ms}. This per-node trace is what
makes the pipeline legible in logs and demos.
"""
from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable

from pythonjsonlogger import jsonlogger

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Install a JSON formatter on the root logger (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    _CONFIGURED = True


logger = logging.getLogger("pipeline")


def timed_node(node: str) -> Callable:
    """Decorate a ``node(state) -> dict`` function with timing + structured logs."""

    def decorator(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        @wraps(fn)
        def wrapper(state: dict) -> dict:
            start = time.perf_counter()
            logger.info("node_start", extra={"node": node, "input_keys": sorted(state.keys())})
            try:
                result = fn(state)
            except Exception:  # noqa: BLE001 - log then re-raise for the graph to handle
                latency_ms = round((time.perf_counter() - start) * 1000, 1)
                logger.exception("node_error", extra={"node": node, "latency_ms": latency_ms})
                raise
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.info(
                "node_done",
                extra={
                    "node": node,
                    "output_keys": sorted((result or {}).keys()),
                    "latency_ms": latency_ms,
                },
            )
            return result

        return wrapper

    return decorator
