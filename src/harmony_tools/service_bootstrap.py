"""Bootstrap utilities and shared helpers for the Harmony Tools MCP service."""

from __future__ import annotations

import os
import shlex
import time
import traceback
import uuid
from functools import wraps
from typing import Sequence

from mcp.server.fastmcp import FastMCP

from .hdc_runner import HdcResult, HdcRunner
from .hvigor_runner import HvigorResult, HvigorRunner
from .logging_helper import (
    configure_logger,
    log_file_path,
)

# ============================================================================
# FastMCP 服务基础配置
# ============================================================================
_DEFAULT_PORT = 10005
_DEFAULT_HOST = "127.0.0.1"

_HTTP_PORT = int(os.environ.get("PORT", _DEFAULT_PORT))
_HTTP_HOST = os.environ.get("HOST", _DEFAULT_HOST)

app = FastMCP("harmony-tools", host=_HTTP_HOST, port=_HTTP_PORT)
_runner = HdcRunner()
_hvigor_runner = HvigorRunner()
logger = configure_logger()


class InvalidArgumentsError(ValueError):
    """当命令参数无法解析时抛出。"""


def split_arguments(arguments: str) -> list[str]:
    """使用 shlex 拆分命令字符串。"""

    try:
        return shlex.split(arguments)
    except ValueError as exc:  # pragma: no cover - depends on user input
        raise InvalidArgumentsError(str(exc)) from exc


def execute_hdc(
    args: Sequence[str],
    *,
    device: str | None = None,
    timeout: float | None = 120.0,
) -> dict:
    """执行 hdc 命令并返回序列化结果。"""

    if not args:
        raise InvalidArgumentsError("hdc command cannot be empty")

    result: HdcResult = _runner.run(args, device=device, timeout=timeout)
    return result.as_dict()


def execute_hvigor(
    args: Sequence[str],
    *,
    project_dir: str,
    timeout: float | None = 900.0,
) -> dict:
    """执行 hvigor 命令并返回序列化结果。"""

    result: HvigorResult = _hvigor_runner.run(
        args, project_dir=project_dir, timeout=timeout
    )
    return result.as_dict()


def _format_tool_exception(tool_name: str, exc: Exception) -> dict:
    """返回工具执行异常时的结构化 payload。"""

    return {
        "success": False,
        "error": str(exc),
        "error_type": exc.__class__.__name__,
        "tool": tool_name,
        "log_file": log_file_path(),
        "traceback": traceback.format_exc(),
    }


_original_app_tool = app.tool


def _format_params(kwargs: dict) -> str:
    """格式化参数用于日志输出，使其更易读。"""

    filtered = {k: v for k, v in kwargs.items() if k != "ctx"}

    if not filtered:
        return "{}"

    parts = []
    for key, value in filtered.items():
        if isinstance(value, str) and len(value) > 100:
            parts.append(f"{key}={value[:100]}...")
        elif isinstance(value, (list, dict)) and len(str(value)) > 200:
            parts.append(f"{key}={str(value)[:200]}...")
        else:
            parts.append(f"{key}={value!r}")

    return "{" + ", ".join(parts) + "}"


def _safe_tool(*tool_args, **tool_kwargs):
    """包装 FastMCP 工具，防止异常导致服务崩溃。"""

    decorator = _original_app_tool(*tool_args, **tool_kwargs)

    def register(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            request_id = uuid.uuid4().hex[:8]
            start_time = time.time()

            try:
                logger.info("=" * 60)
                logger.info("[请求 %s] 接收到工具调用: %s", request_id, func.__name__)

                log_kwargs = {k: v for k, v in kwargs.items() if k != "ctx"}
                if log_kwargs:
                    logger.info("[请求 %s] 参数详情:", request_id)
                    for key, value in log_kwargs.items():
                        try:
                            if isinstance(value, str) and len(value) > 200:
                                logger.info(
                                    "[请求 %s]   %s = %s... (长度: %d)",
                                    request_id,
                                    key,
                                    value[:200],
                                    len(value),
                                )
                            else:
                                logger.info("[请求 %s]   %s = %r", request_id, key, value)
                        except Exception:  # noqa: S110 - 避免参数格式化异常导致失败
                            logger.info("[请求 %s]   %s = <无法格式化>", request_id, key)
                else:
                    logger.info("[请求 %s] 无参数", request_id)

                logger.info("[请求 %s] 开始执行...", request_id)

                result = func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - 兜底
                duration_ms = int((time.time() - start_time) * 1000)
                try:
                    logger.error("=" * 60)
                    logger.error("[请求 %s] 工具执行异常: %s", request_id, func.__name__)
                    logger.error("[请求 %s] 耗时: %d ms", request_id, duration_ms)
                    params_str = _format_params(log_kwargs) if "log_kwargs" in locals() else "{}"
                    logger.error("[请求 %s] 参数: %s", request_id, params_str)
                    logger.exception("[请求 %s] 异常详情:", request_id)
                    logger.error("=" * 60)
                except Exception:  # noqa: S110
                    pass
                return _format_tool_exception(func.__name__, exc)

            duration_ms = int((time.time() - start_time) * 1000)

            status = None
            success = None
            if isinstance(result, dict):
                if "success" in result:
                    success = result["success"]
                    status = f"success={success}"
                elif "returncode" in result:
                    returncode = result["returncode"]
                    status = f"returncode={returncode}"
                    success = returncode == 0

            if status is None:
                status = "completed"
                success = True

            if success:
                logger.info(
                    "[请求 %s] ✓ 执行成功: %s (%s) 耗时 %d ms",
                    request_id,
                    func.__name__,
                    status,
                    duration_ms,
                )
            else:
                logger.warning(
                    "[请求 %s] ✗ 执行失败: %s (%s) 耗时 %d ms",
                    request_id,
                    func.__name__,
                    status,
                    duration_ms,
                )
                logger.warning(
                    "[请求 %s] 失败时的参数: %s", request_id, _format_params(log_kwargs)
                )
                if isinstance(result, dict) and "error" in result:
                    logger.warning(
                        "[请求 %s] 错误信息: %s", request_id, result["error"]
                    )

            logger.info("=" * 60)
            return result

        return decorator(wrapped)

    return register


app.tool = _safe_tool


def hdc_executable_path() -> str:
    """返回当前解析到的 hdc 可执行文件路径。"""

    return _runner._executable


def hvigor_executable_path() -> str:
    """返回当前解析到的 hvigorw 可执行文件路径。"""

    return _hvigor_runner._executable


__all__ = [
    "app",
    "logger",
    "log_file_path",
    "InvalidArgumentsError",
    "split_arguments",
    "execute_hdc",
    "execute_hvigor",
    "hdc_executable_path",
    "hvigor_executable_path",
]
