"""Logging utilities for the Harmony Tools MCP service."""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path


LOG_DIR_ENV = "HARMONY_TOOLS_LOG_DIR"
LOG_LEVEL_ENV = "HARMONY_TOOLS_LOG_LEVEL"
_LOGGER: logging.Logger | None = None
_LOG_PATH: Path | None = None
_HOOK_INSTALLED = False


def _default_log_dir() -> Path:
    """Return the directory where log files should be stored."""

    custom_dir = os.getenv(LOG_DIR_ENV)
    if custom_dir:
        return Path(custom_dir).expanduser()

    xdg_cache = os.getenv("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache).expanduser() / "harmony-tools"

    return Path.home() / ".cache" / "harmony-tools"


def configure_logger() -> logging.Logger:
    """Configure and return the shared Harmony Tools logger.

    日志会同时输出到：
    1. 日志文件（用于持久化记录）
    2. stderr（用于终端实时查看，便于调试）
       注意：在 stdio 模式下，stderr 可能会被子进程管理器捕获
             在 HTTP 模式下，stderr 会直接显示在运行服务的终端
    """

    global _LOGGER, _LOG_PATH

    if _LOGGER is not None:
        return _LOGGER

    log_dir = _default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    _LOG_PATH = log_dir / "harmony-tools.log"

    logger = logging.getLogger("harmony_tools")
    logger.setLevel(os.getenv(LOG_LEVEL_ENV, "INFO").upper())
    logger.propagate = False

    # 格式化器
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # Handler 1: 输出到文件（用于持久化）
    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_PATH,
        maxBytes=1_048_576,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler 2: 输出到 stderr（用于终端实时查看）
    # 在 HTTP 模式下，这些日志会直接显示在终端
    # 在 stdio 模式下，stderr 可能会被客户端捕获或忽略
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    logger.info("日志系统初始化完成")
    logger.info("  - 文件日志: %s", _LOG_PATH)
    logger.info("  - 终端日志: stderr (HTTP 模式下可见)")

    _LOGGER = logger
    return logger


def log_file_path() -> str:
    """Return the absolute path to the current log file."""

    global _LOG_PATH

    if _LOG_PATH is None:
        configure_logger()

    assert _LOG_PATH is not None  # for type checkers
    return str(_LOG_PATH)


__all__ = [
    "configure_logger",
    "log_file_path",
    "LOG_DIR_ENV",
    "LOG_LEVEL_ENV",
]
