# origin-mcp

![origin-mcp cover](docs/assets/github-readme-cover.png)

[![PyPI version](https://img.shields.io/pypi/v/origin-mcp)](https://pypi.org/project/origin-mcp/)
[![Downloads](https://static.pepy.tech/badge/origin-mcp)](https://pepy.tech/projects/origin-mcp)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://pypi.org/project/origin-mcp/)
[![origin-mcp MCP server](https://glama.ai/mcp/servers/Ge-Shun/origin-mcp/badges/score.svg)](https://glama.ai/mcp/servers/Ge-Shun/origin-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md)

`origin-mcp` 是一个本地 Model Context Protocol (MCP) 服务器，用于让 AI
助手在 Windows 上控制 Origin/OriginPro。经过鉴权的本地 bridge 运行在 Origin 内部，
确保自动化始终位于 UI 线程。本项目仍处于测试阶段，欢迎真实工作流反馈和贡献。

## 功能亮点

- 导入、编辑、转换和导出工作表、矩阵、图像及 Data Connector 数据。
- 创建并调整 2D、3D、等高线、统计和专用图形。
- 运行拟合、信号处理、统计、Peak Analyzer 和批处理工作流。
- 管理项目、文件夹、Notes、模板、分析操作与多面板布局。
- 使用可复用模板、调色板和可选的
  [Nature 风格预设](docs/tools.md#palette-catalog)制作出版级图形。

## 快速开始

需要 Windows、已授权的 Origin/OriginPro，以及供 MCP server 使用的 Python 3.10+。
当前目标版本为 Origin 2026/2026b；bridge 使用 Origin 自带的 Python。

1. 安装 MCP server：

```bash
pip install origin-mcp
```

2. 添加 MCP 客户端配置；如果 `python` 指向其他环境，请改用对应 `python.exe` 的
   绝对路径：

```json
{
  "mcpServers": {
    "origin": {
      "command": "python",
      "args": ["-m", "origin_mcp"]
    }
  }
}
```

3. 安装 Origin Start/Stop App，完成简短的
   [注册步骤](docs/origin-ui-buttons.md)，然后在每次 Origin 会话中点击一次
   **Origin MCP Bridge Start**：

```powershell
origin-mcp install-origin-app --force
```

4. 验证 bridge 和 Origin 实时连接：

```powershell
origin-mcp status
origin-mcp doctor --ping-origin
```

两个诊断命令都支持 `--json`。手动启动和故障排查见
[bridge 指南](docs/origin-bridge.md)。

## 文档

- [MCP 客户端配置](docs/mcp-config.md)
- [Origin Start/Stop App](docs/origin-ui-buttons.md)
- [Bridge 安装与故障排查](docs/origin-bridge.md)
- [工具、配置档、绘图样式与错误恢复](docs/tools.md)
- [Agent 自动配置指南](docs/agentic/origin-mcp-bootstrap.md)

## 开发

从源码安装可运行 `pip install -e .`，完整本地检查使用：

```bash
python scripts/dev_check.py --tests
```

## 安全性

bridge 只监听 `127.0.0.1`，默认使用每次会话生成的 token 鉴权。请把 token 当作凭据，
将握手文件保存在当前用户私有目录；除非信任所有本机进程，否则不要设置
`ORIGIN_MCP_BRIDGE_NO_AUTH`。可通过 `ORIGIN_MCP_ALLOWED_ROOTS` 限制工具访问的文件范围。

## 许可证

MIT。见 [LICENSE](LICENSE)。
