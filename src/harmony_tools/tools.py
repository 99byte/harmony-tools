"""FastMCP 工具定义，实现 Harmony Tools 暴露给客户端的能力。"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import Context

from .build_helper import find_app_output, find_hap_output
from .service_bootstrap import (
    InvalidArgumentsError,
    app,
    execute_hdc,
    execute_hvigor,
    logger,
    split_arguments,
)


@app.tool()
def list_targets(ctx: Context) -> dict:
    """列出可用的 hdc 设备/模拟器。"""

    return execute_hdc(["list", "targets"], timeout=15.0)


@app.tool()
def shell(
    ctx: Context,
    command: str,
    device: str | None = None,
    timeout: float = 120.0,
) -> dict:
    """在目标设备上执行 hdc shell 命令。"""

    shell_args = ["shell"] + split_arguments(command)
    return execute_hdc(shell_args, device=device, timeout=timeout)


@app.tool()
def hvigor_clean(
    ctx: Context,
    project_dir: str,
    no_daemon: bool = True,
    timeout: float = 900.0,
) -> dict:
    """清理 Harmony 项目的构建产物。"""

    args = ["clean"]
    if no_daemon:
        args.append("--no-daemon")
    return execute_hvigor(args, project_dir=project_dir, timeout=timeout)


@app.tool()
def hvigor_assemble(
    ctx: Context,
    project_dir: str,
    target_type: str,
    module: str | None = None,
    product: str = "default",
    build_mode: str = "debug",
    no_daemon: bool = True,
    timeout: float = 900.0,
) -> dict:
    """构建 HarmonyOS 应用包（HAP/HSP/HAR/APP）。"""

    valid_types = {"hap", "hsp", "har", "app"}
    if target_type not in valid_types:
        raise InvalidArgumentsError(
            f"Invalid target_type '{target_type}'. Must be one of: {valid_types}"
        )

    target_type_lower = target_type.lower()
    if target_type_lower == "hap":
        task_name = "assembleHap"
        mode = "module"
    elif target_type_lower == "hsp":
        task_name = "assembleHsp"
        mode = "module"
    elif target_type_lower == "har":
        task_name = "assembleHar"
        mode = "module"
    elif target_type_lower == "app":
        task_name = "assembleApp"
        mode = "project"
    else:
        raise InvalidArgumentsError(f"Unsupported target_type: {target_type}")

    args = [task_name, "--mode", mode]

    if target_type_lower in {"hap", "hsp", "har"}:
        if module:
            args.extend(["-p", f"module={module}@{product}"])
        args.extend(["-p", f"product={product}"])

    if target_type_lower in {"hap", "app"}:
        args.extend(["-p", f"buildMode={build_mode}"])

    if target_type_lower == "app":
        args.extend(["-p", f"product={product}"])

    if no_daemon:
        args.append("--no-daemon")

    return execute_hvigor(args, project_dir=project_dir, timeout=timeout)


@app.tool()
def hdc_screenshot(
    ctx: Context,
    project_dir: str,
    output_path: str | None = None,
    filename: str | None = None,
    device: str | None = None,
    timeout: float = 30.0,
) -> dict:
    """捕获 HarmonyOS 设备屏幕截图并保存到项目目录。"""

    start_time = time.time()

    logger.info(
        "开始截图: project_dir=%s, output_path=%s, filename=%s, device=%s",
        project_dir,
        output_path,
        filename,
        device,
    )

    if not os.path.isdir(project_dir):
        logger.error("项目目录不存在: %s", project_dir)
        return {
            "success": False,
            "error": f"项目目录不存在: {project_dir}",
        }

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.jpeg"
        logger.info("自动生成文件名: %s", filename)

    if not filename.lower().endswith((".jpeg", ".jpg")):
        base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
        original_filename = filename
        filename = f"{base_name}.jpeg"
        logger.info("文件名扩展名调整: %s -> %s", original_filename, filename)

    if output_path:
        local_dir = Path(project_dir) / output_path
    else:
        local_dir = Path(project_dir)

    try:
        if not local_dir.exists():
            logger.info("创建输出目录: %s", local_dir)
            local_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.error("创建输出目录失败: %s, error=%s", local_dir, exc)
        return {
            "success": False,
            "error": f"创建输出目录失败: {exc}",
        }

    local_path = local_dir / filename
    logger.info("本地保存路径: %s", local_path)

    device_temp_path = f"/data/local/tmp/screenshot_{uuid.uuid4().hex}.jpeg"
    logger.info("设备临时路径: %s", device_temp_path)

    try:
        step_start = time.time()
        logger.info("步骤 1/3: 在设备上截图")
        snapshot_result = execute_hdc(
            ["shell", "snapshot_display", "-f", device_temp_path],
            device=device,
            timeout=timeout,
        )
        step_time = int((time.time() - step_start) * 1000)
        logger.info(
            "步骤 1/3 完成，耗时 %d ms，returncode=%d",
            step_time,
            snapshot_result.get("returncode", -1),
        )

        snapshot_stdout = snapshot_result.get("stdout", "").lower()
        snapshot_stderr = snapshot_result.get("stderr", "")

        if snapshot_result.get("returncode") != 0:
            logger.error(
                "截图命令返回非零状态码: returncode=%d",
                snapshot_result.get("returncode"),
            )
            logger.error("截图 stdout: %s", snapshot_result.get("stdout"))
            logger.error("截图 stderr: %s", snapshot_stderr)
            return {
                "success": False,
                "error": "截图失败",
                "snapshot_result": snapshot_result,
            }

        if "error:" in snapshot_stdout:
            logger.error("截图输出包含错误信息: %s", snapshot_result.get("stdout"))
            return {
                "success": False,
                "error": "截图失败",
                "snapshot_result": snapshot_result,
            }

        if snapshot_stderr:
            logger.warning("截图 stderr: %s", snapshot_stderr)

        logger.info("截图 stdout: %s", snapshot_result.get("stdout", "").strip())

        step_start = time.time()
        logger.info("步骤 2/3: 传输截图到本地")
        recv_result = execute_hdc(
            ["file", "recv", device_temp_path, str(local_path)],
            device=device,
            timeout=timeout,
        )
        step_time = int((time.time() - step_start) * 1000)
        logger.info(
            "步骤 2/3 完成，耗时 %d ms，returncode=%d",
            step_time,
            recv_result.get("returncode", -1),
        )

        recv_stdout = recv_result.get("stdout", "").lower()
        recv_stderr = recv_result.get("stderr", "")

        if recv_result.get("returncode") != 0:
            logger.error(
                "传输命令返回非零状态码: returncode=%d", recv_result.get("returncode")
            )
            logger.error("传输 stdout: %s", recv_result.get("stdout"))
            logger.error("传输 stderr: %s", recv_stderr)
            logger.info("传输失败，尝试清理设备临时文件")
            cleanup_result = execute_hdc(
                ["shell", "rm", device_temp_path],
                device=device,
                timeout=10.0,
            )
            logger.info("清理结果: returncode=%d", cleanup_result.get("returncode", -1))
            return {
                "success": False,
                "error": "文件传输失败",
                "recv_result": recv_result,
            }

        if "[fail]" in recv_stdout or "error" in recv_stdout:
            logger.error("传输输出包含失败信息: %s", recv_result.get("stdout"))
            logger.info("传输失败，尝试清理设备临时文件")
            cleanup_result = execute_hdc(
                ["shell", "rm", device_temp_path],
                device=device,
                timeout=10.0,
            )
            logger.info("清理结果: returncode=%d", cleanup_result.get("returncode", -1))
            return {
                "success": False,
                "error": "文件传输失败",
                "recv_result": recv_result,
            }

        if recv_stderr:
            logger.warning("传输 stderr: %s", recv_stderr)

        logger.info("传输 stdout: %s", recv_result.get("stdout", "").strip())

        step_start = time.time()
        logger.info("步骤 3/3: 清理设备临时文件 %s", device_temp_path)
        cleanup_result = execute_hdc(
            ["shell", "rm", device_temp_path],
            device=device,
            timeout=10.0,
        )
        step_time = int((time.time() - step_start) * 1000)
        logger.info(
            "步骤 3/3 完成，耗时 %d ms，returncode=%d",
            step_time,
            cleanup_result.get("returncode", -1),
        )
        if cleanup_result.get("stderr"):
            logger.warning("清理 stderr: %s", cleanup_result.get("stderr"))

        file_size = 0
        if local_path.exists():
            file_size = local_path.stat().st_size
            logger.info("截图文件大小: %d bytes (%.2f KB)", file_size, file_size / 1024)
        else:
            logger.warning("本地文件不存在: %s", local_path)

        total_time_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "截图完成: success=True, 总耗时 %d ms, 文件大小 %d bytes",
            total_time_ms,
            file_size,
        )

        return {
            "success": True,
            "total_time_ms": total_time_ms,
            "local_path": str(local_path),
            "filename": filename,
            "device_temp_path": device_temp_path,
            "file_size_bytes": file_size,
            "snapshot_result": snapshot_result,
            "recv_result": recv_result,
            "cleanup_result": cleanup_result,
        }

    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.exception("截图时发生异常: %s", exc)

        try:
            logger.info("尝试清理设备临时文件 %s", device_temp_path)
            cleanup_result = execute_hdc(
                ["shell", "rm", device_temp_path],
                device=device,
                timeout=10.0,
            )
            logger.info(
                "异常清理完成: returncode=%d", cleanup_result.get("returncode", -1)
            )
        except Exception as cleanup_exc:  # noqa: S110
            logger.error("清理设备临时文件失败: %s", cleanup_exc)

        total_time_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "total_time_ms": total_time_ms,
            "error": str(exc),
            "error_type": exc.__class__.__name__,
            "device_temp_path": device_temp_path,
        }


@app.tool()
def hvigor_find_output(
    ctx: Context,
    project_dir: str,
    target_type: str = "hap",
    module: str = "entry",
    build_mode: str = "debug",
    product: str = "default",
) -> dict:
    """查找 Hvigor 构建的输出文件路径（HAP/APP）。"""

    valid_types = {"hap", "app"}
    if target_type not in valid_types:
        raise InvalidArgumentsError(
            f"Invalid target_type '{target_type}'. Must be one of: {valid_types}"
        )

    if target_type == "hap":
        result = find_hap_output(
            project_dir=project_dir,
            module=module,
            build_mode=build_mode,
            product=product,
        )
        return {
            "path": result.path,
            "exists": result.exists,
            "size_bytes": result.size_bytes,
            "modified_time": result.modified_time,
            "module": result.module,
            "product": result.product,
            "build_mode": result.build_mode,
            "target_type": "hap",
        }

    result = find_app_output(
        project_dir=project_dir,
        build_mode=build_mode,
        product=product,
    )
    return {
        "path": result.path,
        "exists": result.exists,
        "size_bytes": result.size_bytes,
        "modified_time": result.modified_time,
        "product": result.product,
        "build_mode": result.build_mode,
        "target_type": "app",
    }


@app.tool()
def hdc_install_app(
    ctx: Context,
    hap_path: str,
    bundle_name: str | None = None,
    ability_name: str = "EntryAbility",
    auto_start: bool = True,
    force_stop: bool = True,
    device: str | None = None,
    timeout: float = 120.0,
) -> dict:
    """按照 DevEco Studio 的方式完整安装 HarmonyOS 应用。"""

    start_time = time.time()
    steps: dict[str, dict] = {}
    temp_dir = f"/data/local/tmp/{uuid.uuid4().hex}"

    logger.info(
        "开始安装应用: hap_path=%s, bundle_name=%s, device=%s, temp_dir=%s",
        hap_path,
        bundle_name,
        device,
        temp_dir,
    )

    if not os.path.isfile(hap_path):
        logger.error("HAP 文件不存在或不是文件: %s", hap_path)
        return {
            "success": False,
            "error": f"HAP 文件不存在或不是文件: {hap_path}",
            "hap_path": hap_path,
            "bundle_name": bundle_name,
            "temp_dir": temp_dir,
            "steps": steps,
        }

    hap_size = os.path.getsize(hap_path)
    logger.info("HAP 文件大小: %d bytes (%.2f MB)", hap_size, hap_size / 1024 / 1024)

    try:
        if force_stop and bundle_name:
            step_start = time.time()
            logger.info("步骤 1/6: 强制停止应用 %s", bundle_name)
            stop_result = execute_hdc(
                ["shell", "aa", "force-stop", bundle_name],
                device=device,
                timeout=timeout,
            )
            steps["stop"] = stop_result
            step_time = int((time.time() - step_start) * 1000)
            logger.info(
                "步骤 1/6 完成，耗时 %d ms，returncode=%d",
                step_time,
                stop_result.get("returncode", -1),
            )
            if stop_result.get("stderr"):
                logger.warning("停止应用 stderr: %s", stop_result.get("stderr"))
        else:
            logger.info(
                "步骤 1/6: 跳过（force_stop=%s, bundle_name=%s）",
                force_stop,
                bundle_name,
            )

        step_start = time.time()
        logger.info("步骤 2/6: 创建临时目录 %s", temp_dir)
        mkdir_result = execute_hdc(
            ["shell", "mkdir", temp_dir],
            device=device,
            timeout=timeout,
        )
        steps["create_dir"] = mkdir_result
        step_time = int((time.time() - step_start) * 1000)
        logger.info(
            "步骤 2/6 完成，耗时 %d ms，returncode=%d",
            step_time,
            mkdir_result.get("returncode", -1),
        )
        if mkdir_result.get("returncode") != 0:
            logger.error(
                "创建临时目录失败: stdout=%s, stderr=%s",
                mkdir_result.get("stdout"),
                mkdir_result.get("stderr"),
            )

        step_start = time.time()
        logger.info("步骤 3/6: 传输 HAP 文件到设备 (%.2f MB)", hap_size / 1024 / 1024)
        transfer_result = execute_hdc(
            ["file", "send", hap_path, temp_dir],
            device=device,
            timeout=timeout,
        )
        steps["transfer"] = transfer_result
        step_time = int((time.time() - step_start) * 1000)
        transfer_speed = (
            (hap_size / 1024 / 1024) / (step_time / 1000) if step_time > 0 else 0
        )
        logger.info(
            "步骤 3/6 完成，耗时 %d ms，传输速度 %.2f MB/s，returncode=%d",
            step_time,
            transfer_speed,
            transfer_result.get("returncode", -1),
        )
        if transfer_result.get("returncode") != 0:
            logger.error(
                "传输文件失败: stdout=%s, stderr=%s",
                transfer_result.get("stdout"),
                transfer_result.get("stderr"),
            )
        elif transfer_result.get("stderr"):
            logger.warning("传输文件 stderr: %s", transfer_result.get("stderr"))

        step_start = time.time()
        logger.info("步骤 4/6: 安装应用")
        install_result = execute_hdc(
            ["shell", "bm", "install", "-p", temp_dir],
            device=device,
            timeout=timeout,
        )
        steps["install"] = install_result
        step_time = int((time.time() - step_start) * 1000)
        logger.info(
            "步骤 4/6 完成，耗时 %d ms，returncode=%d",
            step_time,
            install_result.get("returncode", -1),
        )
        logger.info("安装结果 stdout: %s", install_result.get("stdout"))
        if install_result.get("stderr"):
            logger.warning("安装应用 stderr: %s", install_result.get("stderr"))
        if install_result.get("returncode") != 0:
            logger.error(
                "安装应用失败: returncode=%d", install_result.get("returncode")
            )

        step_start = time.time()
        logger.info("步骤 5/6: 清理临时目录 %s", temp_dir)
        cleanup_result = execute_hdc(
            ["shell", "rm", "-rf", temp_dir],
            device=device,
            timeout=timeout,
        )
        steps["cleanup"] = cleanup_result
        step_time = int((time.time() - step_start) * 1000)
        logger.info(
            "步骤 5/6 完成，耗时 %d ms，returncode=%d",
            step_time,
            cleanup_result.get("returncode", -1),
        )
        if cleanup_result.get("stderr"):
            logger.warning("清理临时目录 stderr: %s", cleanup_result.get("stderr"))

        if auto_start and bundle_name:
            step_start = time.time()
            logger.info("步骤 6/6: 启动应用 %s/%s", bundle_name, ability_name)
            start_result = execute_hdc(
                ["shell", "aa", "start", "-a", ability_name, "-b", bundle_name],
                device=device,
                timeout=timeout,
            )
            steps["start"] = start_result
            step_time = int((time.time() - step_start) * 1000)
            logger.info(
                "步骤 6/6 完成，耗时 %d ms，returncode=%d",
                step_time,
                start_result.get("returncode", -1),
            )
            if start_result.get("stderr"):
                logger.warning("启动应用 stderr: %s", start_result.get("stderr"))
        else:
            logger.info(
                "步骤 6/6: 跳过（auto_start=%s, bundle_name=%s）",
                auto_start,
                bundle_name,
            )

        total_time_ms = int((time.time() - start_time) * 1000)
        success = steps.get("install", {}).get("returncode", -1) == 0

        logger.info("应用安装完成: success=%s, 总耗时 %d ms", success, total_time_ms)

        return {
            "success": success,
            "total_time_ms": total_time_ms,
            "hap_path": hap_path,
            "bundle_name": bundle_name,
            "temp_dir": temp_dir,
            "steps": steps,
        }

    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.exception("安装应用时发生异常: %s", exc)

        try:
            logger.info("尝试清理临时目录 %s", temp_dir)
            cleanup_result = execute_hdc(
                ["shell", "rm", "-rf", temp_dir], device=device, timeout=30.0
            )
            logger.info(
                "异常清理完成: returncode=%d", cleanup_result.get("returncode", -1)
            )
        except Exception as cleanup_exc:  # noqa: S110
            logger.error("清理临时目录失败: %s", cleanup_exc)

        total_time_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "total_time_ms": total_time_ms,
            "hap_path": hap_path,
            "bundle_name": bundle_name,
            "temp_dir": temp_dir,
            "error": str(exc),
            "error_type": exc.__class__.__name__,
            "steps": steps,
        }
