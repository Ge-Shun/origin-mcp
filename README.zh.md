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
- Origin 内嵌 Python 及其预装的 `originpro` 包

### Python 版本支持

`origin-mcp` 以两个协作进程运行，受支持的 Python 版本按角色区分：

- **MCP server core**（`python -m origin_mcp` 进程，仅通过本机回环与 bridge
  通信）：Python 3.10+。本地检查目前已在 Python 3.12 和 3.14 上通过，3.10/3.11/
  3.13 预期同样可用。
- **Origin bridge**（`addon.py`）：运行在 Origin 自带的内嵌 Python 中，版本由你
  安装的 Origin 决定，无需自行选择。

本项目不把外部 `originpro` 自动化作为受支持的 MCP backend。请在 Origin 内嵌
Python 中启动 bridge，再让 MCP server 通过本机回环连接它。

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
      "command": "python",
      "args": ["-m", "origin_mcp"]
    }
  }
}
```

如果 `python` 不是已安装 `origin-mcp` 的 Python 3.10+ 解释器，请改用该解释器的
`python.exe` 绝对路径。更多示例见 [docs/mcp-config.md](docs/mcp-config.md)。

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
