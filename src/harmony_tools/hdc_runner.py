"""Utilities for invoking the HarmonyOS hdc command."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import re
import shlex
import subprocess
from typing import Mapping, Sequence

logger = logging.getLogger("harmony_tools")


@dataclass(slots=True)
class HdcResult:
    """Represents the outcome of an hdc invocation."""

    command: list[str]
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False

    @property
    def command_line(self) -> str:
        """Return the canonical command string."""

        return " ".join(shlex.quote(part) for part in self.command)

    @staticmethod
    def _strip_ansi_codes(text: str) -> str:
        """移除文本中的 ANSI 转义码（颜色代码等）。

        某些 hdc 命令的输出可能包含 ANSI 转义码，
        这些代码在 JSON 序列化时可能导致 MCP 客户端出现问题。

        参数:
            text: 包含 ANSI 转义码的文本

        返回:
            清理后的纯文本
        """
        # ANSI 转义码的正则表达式模式
        # 匹配 ESC[ 开头的控制序列
        ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*m')
        return ansi_escape_pattern.sub('', text)

    def as_dict(self) -> dict:
        """JSON-serialisable representation used by the MCP tools."""

        return {
            "command": self.command,
            "command_line": self.command_line,
            "stdout": self._strip_ansi_codes(self.stdout.strip()),
            "stderr": self._strip_ansi_codes(self.stderr.strip()),
            "returncode": self.returncode,
            "timed_out": self.timed_out,
        }


class HdcRunner:
    """Encapsulates how we call hdc and capture its output."""

    def __init__(self, executable: str | None = None) -> None:
        self._executable = self._resolve_executable(
            executable or os.getenv("HDC_PATH", "hdc")
        )

    @staticmethod
    def _resolve_executable(path: str) -> str:
        """解析 hdc 可执行文件路径，支持目录自动查找。

        如果提供的是目录，会尝试以下路径：
        1. {path}/hdc (Unix/Linux/macOS)
        2. {path}/hdc.exe (Windows)
        3. {path}/bin/hdc
        4. {path}/bin/hdc.exe

        参数:
            path: 可执行文件路径或包含可执行文件的目录

        返回:
            解析后的可执行文件路径
        """
        expanded_path = os.path.expanduser(os.path.expandvars(path))

        # 如果路径不存在，原样返回（可能是 PATH 中的命令如 "hdc"）
        if not os.path.exists(expanded_path):
            return expanded_path

        # 如果是文件，直接返回
        if os.path.isfile(expanded_path):
            return expanded_path

        # 如果是目录，尝试查找可执行文件
        if os.path.isdir(expanded_path):
            candidates = [
                os.path.join(expanded_path, "hdc"),
                os.path.join(expanded_path, "hdc.exe"),
                os.path.join(expanded_path, "bin", "hdc"),
                os.path.join(expanded_path, "bin", "hdc.exe"),
            ]
            for candidate in candidates:
                if os.path.isfile(candidate):
                    return candidate

        # 无法解析，返回原路径
        return expanded_path

    def run(
        self,
        args: Sequence[str],
        *,
        device: str | None = None,
        timeout: float | None = 120.0,
        env: Mapping[str, str] | None = None,
        max_output_lines: int = 500,
    ) -> HdcResult:
        """运行 hdc 命令。

        参数:
            args: 传递给 hdc 的参数
            device: 目标设备 ID（可选）
            timeout: 超时时间（秒）
            env: 额外的环境变量
            max_output_lines: 最多保留的输出行数（默认 500），用于防止输出过大

        返回:
            HdcResult 对象
        """
        command: list[str] = [self._executable]
        if device:
            command += ["-t", device]
        command += list(args)

        # 记录命令行（用于调试）
        command_line = " ".join(shlex.quote(part) for part in command)
        logger.debug("执行 hdc 命令: %s (timeout=%.1fs)", command_line, timeout or 0)

        final_env = os.environ.copy()
        if env:
            final_env.update(env)

        import time
        start_time = time.time()

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=final_env,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # 限制输出大小，防止 MCP 消息过大
            stdout = self._truncate_output(completed.stdout, max_output_lines)
            stderr = self._truncate_output(completed.stderr, max_output_lines)

            logger.debug("hdc 命令完成: returncode=%d, 耗时 %d ms, stdout_len=%d, stderr_len=%d",
                        completed.returncode, duration_ms, len(stdout), len(stderr))

            if completed.returncode != 0:
                logger.warning("hdc 命令失败: returncode=%d, cmd=%s", completed.returncode, command_line)
                if stderr.strip():
                    logger.warning("hdc stderr: %s", stderr.strip()[:500])  # 只记录前 500 字符

        except subprocess.TimeoutExpired as exc:  # pragma: no cover - requires slow device
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("hdc 命令超时: timeout=%.1fs, 实际耗时 %d ms, cmd=%s",
                        timeout or 0, duration_ms, command_line)

            stdout = self._truncate_output(exc.stdout or "", max_output_lines)
            stderr = self._truncate_output(
                exc.stderr or "timeout waiting for hdc",
                max_output_lines
            )
            return HdcResult(
                command=command,
                stdout=stdout,
                stderr=stderr,
                returncode=-1,
                timed_out=True,
            )
        except FileNotFoundError as exc:  # pragma: no cover - depends on user env
            logger.error("找不到 hdc 可执行文件: %s", self._executable)
            raise RuntimeError(
                f"Unable to execute '{self._executable}'. Ensure hdc is installed and on PATH."
            ) from exc
        except Exception as exc:  # pragma: no cover - unexpected errors
            duration_ms = int((time.time() - start_time) * 1000)
            logger.exception("执行 hdc 命令时发生异常: cmd=%s, 耗时 %d ms, error=%s",
                           command_line, duration_ms, exc)
            raise

        return HdcResult(
            command=command,
            stdout=stdout,
            stderr=stderr,
            returncode=completed.returncode,
        )

    @staticmethod
    def _truncate_output(output: str, max_lines: int) -> str:
        """截断输出，只保留最后 N 行。

        某些 hdc 命令（如 bm dump、file send）可能产生大量输出，
        限制输出大小可以防止 MCP 消息过大导致传输问题。

        参数:
            output: 原始输出
            max_lines: 最多保留的行数

        返回:
            截断后的输出
        """
        if not output:
            return output

        lines = output.splitlines()
        total_lines = len(lines)

        if total_lines <= max_lines:
            return output

        # 保留最后 N 行，并添加截断提示
        truncated_lines = lines[-max_lines:]
        truncation_notice = f"[Output truncated: showing last {max_lines} of {total_lines} lines]"

        return truncation_notice + "\n" + "\n".join(truncated_lines)


__all__ = ["HdcRunner", "HdcResult"]
