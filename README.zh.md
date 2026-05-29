# origin-mcp

[English](README.md)

`origin-mcp` 是一个本地 Model Context Protocol (MCP) 服务器，用于让 AI
助手在 Windows 上控制 Origin/OriginPro。它通过 OriginLab 的 Python 自动化接口连接
Origin，并提供数据导入、工作表编辑、绘图与图形美化、Origin 分析、图形导出以及
Origin 生命周期管理等工具。

本项目目前仍处于测试阶段。欢迎在真实 Origin 工作流中试用，提交 issue、改进建议或
pull request。

## 功能亮点

- 将 CSV、TSV、TXT、DAT、XLS 和 Excel 数据导入 Origin 工作表。
- 读取、写入、排序、清空和导出工作表数据。
- 创建并调整常见 2D、3D、等高线、统计和专用图形。
- 运行拟合、平滑、积分、寻峰和描述统计等 Origin 分析。
- 通过本地 Origin GUI bridge 导出图形和项目。

## 环境要求

- Windows
- 已安装并授权的 Origin 或 OriginPro
- 当前主要测试目标是 Origin/OriginPro 2026，其他 Origin 版本暂不保证兼容
- MCP server 运行环境需要 Python 3.10+
- 安装 Origin 自动化相关包时推荐 Python 3.11 或 3.12
- Origin 的 `originpro` 包和 `pywin32`

MCP server core 目标是支持 Python 3.10+；本地检查目前已在 Python 3.12 和 3.14 上
通过。Origin 自动化包可能滞后于较新的 Python 版本，因此需要导入 `originpro` 或
`pywin32` 的环境建议使用 Python 3.11 或 3.12。

## Agentic Setup

把下面这段发给你的 AI agent，让它按步骤自配置：

```text
Fetch and follow this bootstrap guide end to end:
https://raw.githubusercontent.com/Ge-Shun/origin-mcp/main/docs/agentic/origin-mcp-bootstrap.md
```

## MCP 配置

MCP 客户端配置示例：

```json
{
  "mcpServers": {
    "origin": {
      "command": "C:\\path\\to\\origin-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "origin_mcp"]
    }
  }
}
```

请将 `C:\\path\\to\\origin-mcp` 替换为你的本地项目路径。更多示例见
[docs/mcp-config.md](docs/mcp-config.md)。

## 在 Origin 内启动 bridge

bridge 跑在 Origin 自带的 Python 里，这样 `originpro` 始终在 Origin 的 UI 线程上
执行。无需任何额外配置，每个 Origin 会话启动一次即可：

1. 打开 Origin，再打开它的 **Python Console**。
2. 粘贴这一行（把路径换成你的项目路径）：

```python
import runpy; runpy.run_path(r"C:\path\to\origin-mcp\addon.py", run_name="__main__")
```

看到 `Bridge is running inside Origin.` 提示框即表示启动成功，使用工具期间保持该
控制台运行。

**要关闭时，直接让你的 MCP 助手关闭 Origin bridge 即可** —— 它会调用
`origin_bridge_shutdown`，无需另开终端或在控制台里输入。如果不用助手，双击
`scripts\stop-bridge.cmd`（或运行 `python scripts\stop_bridge.py`）即可发送同样的
关闭请求：serve 的控制台会回到提示符，Origin 不会被关闭。

若缺少依赖包或 bridge 起不来，请参阅 [docs/origin-bridge.md](docs/origin-bridge.md)。

## 许可证

MIT。见 [LICENSE](LICENSE)。
