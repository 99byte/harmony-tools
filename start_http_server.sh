#!/bin/bash
# 启动 Harmony Tools MCP HTTP 服务
# 使用方法: ./start_http_server.sh

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}Harmony Tools MCP HTTP 服务${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# 检查环境变量
if [ -z "$HDC_PATH" ]; then
    echo -e "${YELLOW}警告: HDC_PATH 环境变量未设置${NC}"
    echo "请设置 HDC_PATH 指向 hdc 工具路径"
fi

if [ -z "$HVIGORW_PATH" ]; then
    echo -e "${YELLOW}警告: HVIGORW_PATH 环境变量未设置${NC}"
    echo "请设置 HVIGORW_PATH 指向 hvigorw 工具路径"
fi

echo ""
echo -e "${GREEN}启动服务...${NC}"
echo -e "监听地址: ${BLUE}http://127.0.0.1:10005/mcp${NC}"
echo -e "按 ${YELLOW}Ctrl+C${NC} 停止服务"
echo ""
echo -e "${BLUE}=================================${NC}"
echo ""

# 启动 HTTP 服务
# 所有日志会显示在此终端
uv run harmony-hdc-mcp --transport http --port 10005
