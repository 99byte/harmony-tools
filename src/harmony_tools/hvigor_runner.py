"""Utilities for invoking the hvigor wrapper."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import shlex
import subprocess
from typing import Mapping, Sequence


@dataclass(slots=True)
class HvigorResult:
    """Represents the outcome of an hvigorw invocation."""

    command: list[str]
    cwd: str
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

        Hvigor 输出包含 ANSI 转义码用于终端颜色显示，
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
            "cwd": self.cwd,
            "stdout": self._strip_ansi_codes(self.stdout.strip()),
            "stderr": self._strip_ansi_codes(self.stderr.strip()),
            "returncode": self.returncode,
            "timed_out": self.timed_out,
        }


class HvigorRunner:
    """Encapsulates hvigorw execution for Harmony projects."""

    def __init__(self, executable: str | None = None) -> None:
        self._executable = self._resolve_executable(
            executable or os.getenv("HVIGORW_PATH") or "./hvigorw"
        )

    @staticmethod
    def _resolve_executable(path: str) -> str:
        """解析 hvigorw 可执行文件路径，支持目录自动查找。

        如果提供的是目录，会尝试以下路径：
        1. {path}/hvigorw
        2. {path}/bin/hvigorw

        参数:
            path: 可执行文件路径或包含可执行文件的目录

        返回:
            解析后的可执行文件路径
        """
        expanded_path = os.path.expanduser(os.path.expandvars(path))

        # 如果路径不存在，原样返回（稍后会在执行时报错）
        if not os.path.exists(expanded_path):
            return expanded_path

        # 如果是文件，直接返回
        if os.path.isfile(expanded_path):
            return expanded_path

        # 如果是目录，尝试查找可执行文件
        if os.path.isdir(expanded_path):
            candidates = [
                os.path.join(expanded_path, "hvigorw"),
                os.path.join(expanded_path, "bin", "hvigorw"),
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
        project_dir: str,
        timeout: float | None = 900.0,
        env: Mapping[str, str] | None = None,
        max_output_lines: int = 100,
    ) -> HvigorResult:
        """运行 hvigorw 命令。

        参数:
            args: 传递给 hvigorw 的参数
            project_dir: 项目目录（作为工作目录）
            timeout: 超时时间（秒）
            env: 额外的环境变量
            max_output_lines: 最多保留的输出行数（默认 100），用于防止输出过大

        返回:
            HvigorResult 对象
        """
        resolved_project_dir = os.path.expanduser(os.path.expandvars(project_dir))

        if not project_dir:
            raise ValueError("project_dir is required for hvigor builds")
        if not os.path.isdir(resolved_project_dir):
            raise ValueError(
                f"project_dir '{project_dir}' does not exist or is not a directory"
            )

        command: list[str] = [self._executable]
        command += list(args)

        final_env = os.environ.copy()
        if env:
            final_env.update(env)

        try:
            completed = subprocess.run(
                command,
                cwd=resolved_project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=final_env,
            )

            # 限制输出大小，只保留最后 N 行关键信息
            stdout = self._truncate_output(completed.stdout, max_output_lines)
            stderr = self._truncate_output(completed.stderr, max_output_lines)

        except subprocess.TimeoutExpired as exc:  # pragma: no cover - requires slow build
            stdout = self._truncate_output(exc.stdout or "", max_output_lines)
            stderr = self._truncate_output(
                exc.stderr or "timeout waiting for hvigorw",
                max_output_lines
            )
            return HvigorResult(
                command=command,
                cwd=resolved_project_dir,
                stdout=stdout,
                stderr=stderr,
                returncode=-1,
                timed_out=True,
            )
        except FileNotFoundError as exc:  # pragma: no cover - depends on user env
            raise RuntimeError(
                f"Unable to execute '{self._executable}'. Ensure hvigorw exists in the project "
                "or set HVIGORW_PATH to the wrapper path."
            ) from exc

        return HvigorResult(
            command=command,
            cwd=resolved_project_dir,
            stdout=stdout,
            stderr=stderr,
            returncode=completed.returncode,
        )

    @staticmethod
    def _truncate_output(output: str, max_lines: int) -> str:
        """截断输出，只保留最后 N 行。

        Hvigor 构建会产生大量输出，这会导致：
        1. MCP 消息过大
        2. 内存占用过高
        3. JSON 序列化缓慢

        因此只保留最后的关键信息（通常包含错误信息或构建结果）。

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


__all__ = ["HvigorRunner", "HvigorResult"]
