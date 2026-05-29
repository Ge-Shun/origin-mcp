# origin-mcp

[English](README.md)

`origin-mcp` 是一个本地 Model Context Protocol (MCP) 服务器，用于让 AI
助手在 Windows 上控制 Origin/OriginPro。它通过 OriginLab 的 Python 自动化接口连接
Origin，并提供数据导入、工作表编辑、绘图与图形美化、Origin 分析、图形导出以及
Origin 生命周期管理等工具。

本项目目前仍处于测试阶段。欢迎在真实 Origin 工作流中试用，提交 issue、改进建议或
pull request。

项目目标是让 AI 模型直接协作使用你本机安装的 Origin 环境，而不是只生成独立的绘图
代码。

## 功能亮点

- 将 CSV、TSV、TXT、DAT、XLS 和 Excel 数据导入 Origin 工作表。
- 读取、写入、排序、清空和导出工作表数据。
- 通过高层绘图入口创建常见 2D、3D、等高线、统计、极坐标、三元图、向量图、气泡图、
  图像图和矩阵图。
- 在本地知识库中索引 Origin 文档中的 Plot Type ID；需要专家 wrapper 时可启用 full
  tool profile。
- 检查和调整图页、图层、坐标轴、图例、标签、参考线、plot 样式和发表级样式。
- 支持 Nature 风格预设、语义色板、chart atlas 路由、图像板块标签和 QA checklist。
- 运行常见 Origin 分析，包括拟合、平滑、积分、微分、寻峰和描述统计。
- 将分析输出工作表读回 JSON，并在可能时规范化拟合参数和指标。
- 搜索和浏览本地 Origin 知识库，覆盖 MCP 工具、Plot Type ID、图形格式化、
  分析适配器、OriginPro API 笔记，以及带版本元数据的 OriginLab 官方
  LabTalk/X-Function/API 文档边界图。
- 导出图形、预览导出图像、保存项目，并安全释放或关闭 Origin。
- 通过本地 Origin GUI bridge 路由 Origin 操作，把 MCP server 运行环境与 Origin
  自动化运行环境分离。

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
