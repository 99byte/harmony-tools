# 开发者文档（Harmony Tools MCP）

## 环境与依赖

- Python ≥3.11
- HarmonyOS Command Line Tools（包含 `hdc`、`hvigorw`）
- 推荐安装：`pipx install git+<repository-url>` 或开发模式 `pip install -e .`

### 必需环境变量

- `HDC_PATH`：指向 `hdc` 可执行文件，或包含它的目录
- `HVIGORW_PATH`：指向 `hvigorw` 可执行文件，或包含它的目录

解析策略（目录/文件皆可）：

- 目录：自动在目录中查找 `hdc` 或 `bin/hdc`；`hvigorw` 或 `bin/hvigorw`
- 文件：直接使用指定路径

### 日志相关环境变量

- `HARMONY_TOOLS_LOG_DIR`：日志文件目录（默认使用 `~/.cache/harmony-tools` 或 `XDG_CACHE_HOME/harmony-tools`）。参考 `src/harmony_tools/logging_helper.py:12-31`。
- `HARMONY_TOOLS_LOG_LEVEL`：日志级别（默认 `INFO`）。参考 `src/harmony_tools/logging_helper.py:52-54`。

日志同时输出到文件与 `stderr`，HTTP 模式下终端可见；`stdio` 模式下可能被客户端捕获。

## 运行模式详解

入口：控制台脚本 `harmony-hdc-mcp` 指向 `harmony_tools.mcp_service:main`（`pyproject.toml:19-20`）。

- `stdio`（默认）：适合被 MCP 客户端直接拉起的子进程模式。
- `http`：独立服务器，支持多客户端并发连接，终端实时输出日志。

命令行参数（参考 `src/harmony_tools/mcp_service.py:20-84`）：

- `--transport {stdio,http}`：选择传输模式；`stdio` 或 `http`
- `--host`：HTTP 监听地址（默认 `127.0.0.1`）
- `--port`：HTTP 监听端口（默认 `10005`）

示例：

```bash
harmony-hdc-mcp                # stdio
harmony-hdc-mcp --transport http --port 10005 --host 127.0.0.1
```

## MCP 工具详解

工具由 `src/harmony_tools/tools.py` 注册到 `FastMCP` 应用。

### list_targets

- 功能：列出可用的 `hdc` 设备/模拟器（`list targets`）
- 位置：`src/harmony_tools/tools.py:24-29`
- 返回：标准化字典，含 `stdout`、`stderr`、`returncode`、`timed_out`

### shell

- 功能：在设备上执行任意 `hdc shell` 命令
- 参数：`command`（字符串，支持带空格参数）、`device`（可选）、`timeout`
- 位置：`src/harmony_tools/tools.py:31-42`

### hvigor_clean

- 功能：清理 Harmony 项目的构建产物
- 参数：`project_dir`、`no_daemon`、`timeout`
- 位置：`src/harmony_tools/tools.py:44-57`

### hvigor_assemble

- 功能：构建 HAP/HSP/HAR/APP
- 参数：`project_dir`、`target_type`、`module`、`product`、`build_mode`、`no_daemon`、`timeout`
- 位置：`src/harmony_tools/tools.py:59-111`
- 说明：自动映射到 `assembleHap/Hsp/Har/App`，并按类型填充 `-p` 参数（`module`、`product`、`buildMode`、`mode`）。

### hvigor_find_output

- 功能：查找 Hvigor 构建产物路径（HAP/APP）
- 参数：`project_dir`、`target_type`、`module`、`build_mode`、`product`
- 位置：`src/harmony_tools/tools.py:342-391`

### hdc_screenshot

- 功能：截取设备屏幕并保存到项目目录（JPEG）
- 参数：`project_dir`、`output_path`、`filename`、`device`、`timeout`
- 位置：`src/harmony_tools/tools.py:113-340`
- 流程：设备截图 → 传输到本地 → 清理临时文件；返回各步骤的结构化信息。

### hdc_install_app

- 功能：按 DevEco Studio 的方式安装并启动 HarmonyOS 应用
- 参数：`hap_path`、`bundle_name`、`ability_name`、`auto_start`、`force_stop`、`device`、`timeout`
- 位置：`src/harmony_tools/tools.py:393-606`
- 流程：停应用 → 建目录 → 传输 HAP → 安装 → 清理 → 启动（可选）；返回分步结果与总耗时。

## 返回结构示例

所有工具统一返回字典，至少包含：

```json
{
  "stdout": "",
  "stderr": "",
  "returncode": 0,
  "timed_out": false
}
```

部分工具返回增强信息（如 `success`、`steps`、`local_path`、`file_size_bytes` 等）。

## 长示例

### 构建 + 安装一条龙

```python
hvigor_assemble(project_dir="/path/to/project", target_type="hap", module="entry", build_mode="release")
o = hvigor_find_output(project_dir="/path/to/project", target_type="hap", module="entry", build_mode="release")
if o["exists"]:
    hdc_install_app(hap_path=o["path"], bundle_name="com.example.myapp", ability_name="EntryAbility", auto_start=True)
```

### 设备截图

```python
hdc_screenshot(project_dir="/path/to/project", output_path="screenshots", filename="ui_screenshot.jpeg")
```

## 故障排查（完整版）

- 找不到 `hdc`/`hvigorw`：确认路径与权限，优先绝对路径。
- 构建/安装失败：检查 `returncode` 与 `stderr`，按步骤定位问题。
- 超时或卡顿：提高 `timeout`、缩减构建/输出量、确认设备连接稳定。
- 权限错误：设备启用开发者模式并授权当前用户。

## 代码结构参考

- 入口与工具注册：`src/harmony_tools/mcp_service.py`、`src/harmony_tools/service_bootstrap.py`
- HDC/Hvigor 执行封装：`src/harmony_tools/hdc_runner.py`、`src/harmony_tools/hvigor_runner.py`
- 日志：`src/harmony_tools/logging_helper.py`