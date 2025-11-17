"""MCP 服务入口：负责解析参数并启动 FastMCP 应用。"""

from __future__ import annotations

import argparse
import os

from .service_bootstrap import (
    app,
    hdc_executable_path,
    logger,
    log_file_path,
)

# 导入 tools 模块以注册所有 FastMCP 工具
from . import tools as _tools  # noqa: F401


def main() -> None:
    """Console script entrypoint."""

    parser = argparse.ArgumentParser(
        description="Harmony Tools MCP 服务 - HarmonyOS 开发命令的 MCP 封装"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="传输模式: stdio (默认, 子进程模式) 或 http (独立服务器模式)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP 模式的监听地址 (默认: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=10005,
        help="HTTP 模式的监听端口 (默认: 10005)",
    )
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("Harmony Tools MCP 服务启动")
    logger.info("=" * 80)
    logger.info("传输模式: %s", args.transport)
    if args.transport == "http":
        logger.info("监听地址: %s:%d", args.host, args.port)
    logger.info("日志文件: %s", log_file_path())
    logger.info("日志级别: %s", os.getenv("HARMONY_TOOLS_LOG_LEVEL", "INFO"))
    logger.info("HDC 路径: %s", hdc_executable_path())
    logger.info("工作目录: %s", os.getcwd())
    logger.info("可用工具列表:")
    logger.info("  - list_targets: 列出可用的 hdc 设备")
    logger.info("  - shell: 执行 hdc shell 命令")
    logger.info("  - hvigor_clean: 清理 Harmony 项目")
    logger.info("  - hvigor_assemble: 构建 HarmonyOS 应用包")
    logger.info("  - hvigor_find_output: 查找构建输出文件")
    logger.info("  - hdc_screenshot: 捕获设备屏幕截图")
    logger.info("  - hdc_install_app: 安装并启动 HarmonyOS 应用")
    logger.info("=" * 80)
    logger.info("服务已就绪，等待请求...")
    logger.info("=" * 80)

    try:
        if args.transport == "http":
            if args.port != 10005 or args.host != "127.0.0.1":
                app.settings.port = args.port
                app.settings.host = args.host
                logger.info("使用命令行参数: --port %d --host %s", args.port, args.host)

            actual_host = app.settings.host
            actual_port = app.settings.port

            logger.info("🚀 HTTP 服务器启动中...")
            logger.info("🌐 访问地址: http://%s:%d/mcp", actual_host, actual_port)
            logger.info("💡 提示: 在此终端可以看到所有请求日志和错误堆栈")

            app.run(transport="streamable-http")
        else:
            logger.info("📡 stdio 模式启动")
            app.run(transport="stdio")
    except Exception:
        logger.critical("=" * 80)
        logger.critical("MCP 服务崩溃！")
        logger.exception("崩溃详情:")
        logger.critical("=" * 80)
        raise


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
