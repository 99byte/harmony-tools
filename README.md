# Harmony Tools MCP 服务

本仓库提供一个基于 Model Context Protocol (MCP) 的服务端，实现了对 HarmonyOS 命令行工具（`hdc`、`hvigor` 等）的封装。借助 `FastMCP`，可以将本服务注册到任何支持 MCP 协议的客户端，让常用的 HarmonyOS 开发任务以结构化 JSON 的形式返回。

## 功能亮点

- **设备管理**：通过 `hdc` 列出设备、执行 shell、收发文件。
- **构建自动化**：封装 `hvigor` 任务，支持 HAP/HSP/HAR/APP 构建。
- **应用生命周期**：一条命令完成安装、停止、启动与清理。
- **UI 测试/模拟器**：保留 `hdc` 子命令入口，可在 MCP 中触发。
- **构建产物定位**：自动查找 HAP/APP 输出，避免手动找路径。
- **结构化响应**：所有工具都返回 stdout/stderr/returncode/timed_out 等字段，便于客户端渲染与诊断。
- **与 DevEco Studio 行为一致**：安装流程等逻辑与官方 IDE 保持同步。

## 环境要求

- Python 3.11 及以上。
- [HarmonyOS Command Line Tools](https://developer.huawei.com/consumer/cn/download/command-line-tools-for-hmos)（官方工具包，内含 hdc 与 hvigor）。

### 获取 HarmonyOS 命令行工具

建议使用官方 Command Line Tools 工具包（含完整开发链），下载后解压并配置环境变量即可使用。

🔗 **下载地址**：[HarmonyOS Command Line Tools](https://developer.huawei.com/consumer/cn/download/command-line-tools-for-hmos)

### 环境变量配置

`HDC_PATH`、`HVIGORW_PATH` 可按两种方式配置：

#### 方式 1️⃣：指向具体可执行文件（推荐）

```bash
export HDC_PATH=/path/to/hdc
export HVIGORW_PATH=/path/to/hvigorw
```

#### 方式 2️⃣：指向包含可执行文件的目录（自动查找）

```bash
# 自动查找 hdc 或 bin/hdc
export HDC_PATH=/path/to/tools

# 自动查找 hvigorw 或 bin/hvigorw
export HVIGORW_PATH=/path/to/hvigor
```

### 推荐配置示例

假设将官方工具包解压到 `~/command-line-tools`：

```bash
# 写入 ~/.bashrc 或 ~/.zshrc
export HDC_PATH=~/command-line-tools/sdk/default/openharmony/toolchains/hdc
export HVIGORW_PATH=~/command-line-tools/bin/hvigorw
```

> 建议使用绝对路径（以 `/` 开头），避免相对路径带来解析误差。

## 安装方式

### 方式一：全局工具安装（推荐给最终用户）

```bash
# 使用 pipx（推荐，隔离环境并全局暴露可执行）
pipx install git+<repository-url>

# 或使用 uv 的工具安装（同样全局暴露入口）
uv tool install git+<repository-url>
```

安装成功后，`harmony-hdc-mcp` 可在系统 PATH 中直接使用，便于在任意工程的 MCP 配置中引用。

### 方式二：源码安装（开发调试场景）

```bash
git clone <repository-url>
cd harmony-tools
uv pip install -e .
# 或标准 pip
pip install -e .
```

### 方式三：从仓库安装（指定分支或版本）

```bash
uv pip install git+<repository-url>
# 或标准 pip
pip install git+<repository-url>
```

> 若使用 `uv run` 在某工程目录执行，需要该工程环境已安装本包；这不等同于全局可用。面向最终用户，优先使用“全局工具安装”。

## 运行服务

服务支持两种运行模式，可按需求选择。

### 模式一：stdio（默认）

适合由 MCP 客户端（如 Claude Desktop）直接拉起子进程的场景。

```bash
# 根据需要配置环境变量
export HDC_PATH=~/command-line-tools/sdk/default/openharmony/toolchains
export HVIGORW_PATH=~/command-line-tools/bin

# 启动 MCP 服务
harmony-hdc-mcp
```

**客户端配置示例（stdio）**

```json
{
  "mcpServers": {
    "harmony-tools": {
      "command": "harmony-hdc-mcp",
      "env": {
        "HDC_PATH": "/path/to/command-line-tools/sdk/default/openharmony/toolchains/hdc",
        "HVIGORW_PATH": "/path/to/command-line-tools/bin/hvigorw"
      }
    }
  }
}
```

### 模式二：HTTP（调试与多客户端场景推荐）

**优势**
- 服务独立运行，终端实时输出日志与异常。
- 支持多个客户端同时连接。
- 可随时重启，不影响 IDE/编辑器。

**启动方式**

```bash
# 推荐：脚本一键启动
./start_http_server.sh

# 或手动指定端口
harmony-hdc-mcp --transport http --port 15005

# 自定义地址
harmony-hdc-mcp --transport http --host 0.0.0.0 --port 8080
```

启动后终端会显示：

```
🚀 HTTP 服务器启动中...
🌐 访问地址: http://127.0.0.1:10005/mcp
💡 提示: 在此终端可以看到所有请求日志和错误堆栈
```

**客户端配置示例（HTTP）**

```json
{
  "mcpServers": {
    "harmony-tools": {
      "transport": "http",
      "url": "http://127.0.0.1:10005/mcp"
    }
  }
}
```

**注意事项**
- `HDC_PATH`、`HVIGORW_PATH` 需在启动服务前设置，而不是在客户端中设置。
- 默认端口为 `10005`，可通过 `--port` 自定义。
- 所有请求日志、异常堆栈会输出到运行服务的终端。

**设置环境变量的方式**

```bash
# 临时设置
HDC_PATH=/path/to/hdc HVIGORW_PATH=/path/to/hvigorw ./start_http_server.sh

# 长期设置（写入 shell 配置后再执行脚本）
./start_http_server.sh
```

## 可用 MCP 工具

### HDC 工具

| 工具名称          | 功能说明                                   |
| ----------------- | ------------------------------------------ |
| `list_targets`    | 列出已连接的设备或模拟器                   |
| `shell`           | 在目标设备上执行任意 shell 命令            |
| `hdc_install_app` | 模拟 DevEco Studio 的完整安装流程          |
| `hdc_screenshot`  | 使用 `snapshot_display` 抓取屏幕并保存本地 |

### Hvigor 构建工具

| 工具名称            | 功能说明                                    |
| ------------------- | ------------------------------------------- |
| `hvigor_clean`      | 清理项目构建产物                            |
| `hvigor_assemble`   | 构建 HAP/HSP/HAR/APP 等多种产物             |
| `hvigor_find_output`| 自动定位 HAP 或 APP 的输出文件              |

所有工具都会返回统一的 JSON 结果，包含命令行、输出、退出码与是否超时等信息：

```json
{
  "command": ["hdc", "…"],
  "command_line": "hdc …",
  "stdout": "",
  "stderr": "",
  "returncode": 0,
  "timed_out": false
}
```

客户端可以依据这些字段渲染日志、判定失败或继续链式调用。

## 使用示例

### 编译 Harmony 应用

```python
# 清理项目
hvigor_clean(project_dir="/path/to/app", no_daemon=True)

# 构建 HAP
hvigor_assemble(
    project_dir="/path/to/app",
    target_type="hap",
    module="entry",
    build_mode="release",
)

# 构建 APP
hvigor_assemble(
    project_dir="/path/to/app",
    target_type="app",
    product="default",
    build_mode="release",
)

# 构建 HSP
hvigor_assemble(
    project_dir="/path/to/app",
    target_type="hsp",
    module="library",
)
```

### 构建 + 安装一条龙

```python
# 1. 构建 HAP
hvigor_assemble(
    project_dir="/path/to/project",
    target_type="hap",
    module="entry",
    build_mode="release",
)

# 2. 查找产物
result = hvigor_find_output(
    project_dir="/path/to/project",
    target_type="hap",
    module="entry",
    build_mode="release",
)

# 3. 安装到设备
if result["exists"]:
    hdc_install_app(
        hap_path=result["path"],
        bundle_name="com.example.myapp",
        ability_name="EntryAbility",
        auto_start=True,
        force_stop=True,
    )
```

### 设备截图

```python
# 保存到项目根目录
hdc_screenshot(project_dir="/path/to/project")

# 保存到子目录
hdc_screenshot(project_dir="/path/to/project", output_path="screenshots")

# 自定义文件名
hdc_screenshot(
    project_dir="/path/to/project",
    output_path="docs/images",
    filename="ui_screenshot.png",
)
```

返回结果示例：

```json
{
  "success": true,
  "local_path": "/path/to/project/screenshots/screenshot_20251114_161020.png",
  "filename": "screenshot_20251114_161020.png",
  "file_size_bytes": 245678
}
```

参考资料：[HarmonyOS 截图指南](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-screenshot)

## 常见问题排查

- **`hdc` 找不到**：确认已安装 Command Line Tools 并正确设置 `HDC_PATH`（可以指向文件或目录）。
- **`hvigorw` 找不到**：确认 `HVIGORW_PATH` 配置正确，建议直接指向 `command-line-tools/bin/hvigorw`。
- **Permission denied**：若指向目录却无法执行，请改为指向具体文件或检查目录权限。
- **MCP 服务无响应**：构建输出过大可能阻塞；本项目已限制输出（HDC 500 行，Hvigor 100 行），如仍卡死请提高超时或减小输出。
- **工具版本不兼容**：保持 Command Line Tools 与当前 HarmonyOS SDK 同步。
- **权限相关报错**：确认设备已开启开发者模式，并允许当前用户访问。
- **命令行参数传递**：和 CLI 保持一致，例如 `hdc_uitest(arguments="run -p entry -s SmokeSuite")`。

## 开发者指引

核心代码位于 `src/harmony_tools/`。入口文件是 `harmony_tools/mcp_service.py`，`hdc_runner.py`/`hvigor_runner.py` 负责封装子进程执行逻辑。若需扩展功能，可参考 [AGENTS.md](AGENTS.md) 了解项目结构、编码规范与测试要求，然后新增对应的 MCP 工具或 Runner 即可。
