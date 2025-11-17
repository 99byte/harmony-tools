# Harmony Tools MCP 服务

将 HarmonyOS 命令行工具（`hdc`、`hvigor` 等）封装为 MCP 服务，接入任意支持 MCP 的客户端，常用开发任务以结构化 JSON 返回。

## 快速上手

- 前置条件：Python ≥3.11；已安装 HarmonyOS Command Line Tools。
- 下载地址：[HarmonyOS Command Line Tools](https://developer.huawei.com/consumer/cn/download/command-line-tools-for-hmos)
- 配置必需环境变量：
```bash
# 解压后在 command-line-tools/sdk/default/openharmony/toolchains 目录下
export HDC_PATH=/path/to/hdc
# 解压后在 command-line-tools/bin 目录下
export HVIGORW_PATH=/path/to/hvigorw
```

### 安装

```bash
# 全局安装（推荐）
uv tool install git+<repository-url>

# 开发模式（本地源码）
uv pip install -e .
```

### 启动

- `stdio`（默认）：
  - `uv run harmony-tools-mcp`
- `http`（调试/多客户端）：
  - `uv run harmony-tools --transport http`
  - 或 `./start_http_server.sh`

### 客户端最小配置示例

- `stdio`：
```json
{
  "mcpServers": {
    "harmony-tools": {
      "command": "harmony-tools-mcp",
      "env": {
        "HDC_PATH": "/path/to/hdc", 
        "HVIGORW_PATH": "/path/to/hvigorw"
      }
    }
  }
}
```

- `http`：
```json
{
  "mcpServers": {
    "harmony-tools": {
      "transport": "http", 
      "url": "http://127.0.0.1:10005/mcp"}
  }
}
```

## 可用工具一览

- `list_targets`、`shell`
- `hvigor_clean`、`hvigor_assemble`、`hvigor_find_output`
- `hdc_screenshot`、`hdc_install_app`

## 常见问题（精简）

- 找不到 `hdc`/`hvigorw`：检查并设置 `HDC_PATH`、`HVIGORW_PATH`。
- 无响应或超时：适当提高超时或减少输出量。
- 权限问题：设备开启开发者模式并授予访问权限。

## 开发者文档

详细技术说明（环境变量、运行模式、工具参数与返回结构、长示例、完整排障）见 `docs/DEVELOPER.md`。
