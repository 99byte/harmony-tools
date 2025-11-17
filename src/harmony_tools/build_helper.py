"""构建产物查找和管理工具。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class BuildOutput:
    """构建产物信息。"""

    path: str
    exists: bool
    size_bytes: int | None = None
    modified_time: str | None = None
    module: str | None = None
    product: str | None = None
    build_mode: str | None = None


def find_hap_output(
    project_dir: str,
    module: str = "entry",
    build_mode: Literal["debug", "release"] | str = "debug",
    product: str = "default",
) -> BuildOutput:
    """查找 Hvigor 构建的 HAP 输出文件。

    根据 DevEco Studio 的标准输出路径查找构建产物。
    路径模式：{project_dir}/{module}/build/{product}/outputs/{product}/{module}-{product}-signed.hap

    参数:
        project_dir: 项目根目录
        module: 模块名称，默认 "entry"
        build_mode: 构建模式（debug/release），默认 "debug"
        product: 产品名称，默认 "default"

    返回:
        BuildOutput 对象，包含文件路径和元信息
    """
    project_path = Path(project_dir)

    # 标准路径模式
    # 例如: entry/build/default/outputs/default/entry-default-signed.hap
    standard_path = (
        project_path
        / module
        / "build"
        / product
        / "outputs"
        / product
        / f"{module}-{product}-signed.hap"
    )

    # 备选路径模式（可能包含构建模式）
    alternative_paths = [
        # 包含 build_mode 的路径
        project_path
        / module
        / "build"
        / product
        / "outputs"
        / build_mode
        / f"{module}-{product}-signed.hap",
        # 不带 product 的路径
        project_path / module / "build" / "outputs" / f"{module}-signed.hap",
        # 带 build_mode 但不带 product
        project_path / module / "build" / "outputs" / build_mode / f"{module}-signed.hap",
        # 老版本路径
        project_path / module / "build" / "outputs" / "hap" / build_mode / f"{module}.hap",
    ]

    # 首先检查标准路径
    if standard_path.exists():
        return _create_build_output(
            standard_path, module=module, product=product, build_mode=build_mode
        )

    # 尝试备选路径
    for alt_path in alternative_paths:
        if alt_path.exists():
            return _create_build_output(
                alt_path, module=module, product=product, build_mode=build_mode
            )

    # 如果都不存在，返回标准路径（exists=False）
    return BuildOutput(
        path=str(standard_path),
        exists=False,
        module=module,
        product=product,
        build_mode=build_mode,
    )


def find_app_output(
    project_dir: str,
    build_mode: Literal["debug", "release"] | str = "debug",
    product: str = "default",
) -> BuildOutput:
    """查找 Hvigor 构建的 APP 输出文件（完整应用包）。

    参数:
        project_dir: 项目根目录
        build_mode: 构建模式（debug/release），默认 "debug"
        product: 产品名称，默认 "default"

    返回:
        BuildOutput 对象，包含文件路径和元信息
    """
    project_path = Path(project_dir)

    # APP 包的标准路径模式
    # 例如: build/default/outputs/default/MyApp-default-signed.app
    possible_paths = [
        # 标准路径
        project_path / "build" / product / "outputs" / product / f"*-{product}-signed.app",
        # 包含 build_mode 的路径
        project_path / "build" / product / "outputs" / build_mode / f"*-{product}-signed.app",
        # 简化路径
        project_path / "build" / "outputs" / "app" / build_mode / "*.app",
    ]

    # 使用 glob 查找匹配的文件
    for pattern in possible_paths:
        matches = list(project_path.glob(str(pattern.relative_to(project_path))))
        if matches:
            # 如果有多个匹配，选择最新的
            latest = max(matches, key=lambda p: p.stat().st_mtime if p.exists() else 0)
            return _create_build_output(
                latest, module=None, product=product, build_mode=build_mode
            )

    # 如果都不存在，返回预期的标准路径
    expected_path = project_path / "build" / product / "outputs" / product
    return BuildOutput(
        path=str(expected_path / "app-signed.app"),
        exists=False,
        product=product,
        build_mode=build_mode,
    )


def _create_build_output(
    path: Path,
    module: str | None = None,
    product: str | None = None,
    build_mode: str | None = None,
) -> BuildOutput:
    """创建 BuildOutput 对象，包含文件元信息。"""
    if path.exists():
        stat = path.stat()
        from datetime import datetime

        modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
        return BuildOutput(
            path=str(path),
            exists=True,
            size_bytes=stat.st_size,
            modified_time=modified_time,
            module=module,
            product=product,
            build_mode=build_mode,
        )
    else:
        return BuildOutput(
            path=str(path),
            exists=False,
            module=module,
            product=product,
            build_mode=build_mode,
        )


__all__ = ["BuildOutput", "find_hap_output", "find_app_output"]
