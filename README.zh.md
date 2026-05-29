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

## 文档

- [工具与兼容性参考](docs/tools.md)
- [MCP 客户端配置](docs/mcp-config.md)
- [Origin GUI bridge](docs/origin-bridge.md)
- [Agent bootstrap 指南](docs/agentic/origin-mcp-bootstrap.md)

在 Origin 内用根目录 `addon.py` 启动 bridge 后，可运行
`python examples\smoke_bridge.py` 验证真实的导入、绘图、导出和保存项目流程。
`addon.py` 内不需要手动改源码目录。
如果不确定 bridge 是否启动或为何连不上，先调用 `origin_doctor`；它会返回
核心诊断信息。详细 checklist 可在知识库中搜索 `bridge diagnostics`。
需要关闭 Origin 内前台 bridge 时，优先调用 `origin_bridge_shutdown`，默认会请求
bridge 停止服务并释放 Origin 自动化连接；这样比在 Origin Python Console 里按
`Ctrl+C` 更可靠。

MCP server 默认使用 compact profile，降低模型选工具成本。启动 server
前设置 `ORIGIN_MCP_TOOL_PROFILE=full` 可暴露所有 worksheet、graph、analysis 和
`origin_plot_*` 专家工具。

## 知识库

服务器通过 MCP 工具暴露结构化本地知识库。使用 `origin_query_knowledge` 或各集合
专用 query 工具搜索；使用 `origin_browse_knowledge` 或各集合专用 browse 工具按稳定
路径查看完整条目。MCP 工具索引会从当前 server 工具 docstring 自动生成，因此会跟随
已实现工具面更新。

当前集合包括 `mcp_tools`、`reference`、`python_api`、`labtalk` 和 `official_docs`。
知识库是面向操作的精选索引；需要官方精确语法的条目会带 OriginLab 官方文档 URL，
以及 `doc_family`、`doc_kind`、`versions` 和验证日期等元数据。
可选脚本 `scripts/update_official_docs_index.py` 可刷新官方文档生成索引覆盖层，用于
LabTalk command 页面、X-Function 页面和 originpro API 页面。

## 安全说明

该服务器可以读取本地数据文件、写入导出的图形和项目文件，并控制本地 Origin 会话。
请只在可信 MCP 客户端中使用。必要时可用 `ORIGIN_MCP_ALLOWED_ROOTS` 限制文件访问范围。

如果 Origin 提示正在被其他程序控制，请先调用 `origin_detach`。只有在确认没有未保存
工作后，才使用 `origin_force_quit`。

## 许可证

MIT。见 [LICENSE](LICENSE)。
