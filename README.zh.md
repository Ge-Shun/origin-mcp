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
- 创建常见 2D、3D、等高线、统计、极坐标、三元图、向量图、气泡图、图像图和矩阵图。
- 覆盖 Origin 文档中的 Plot Type ID，并提供直接 MCP 工具。
- 检查和调整图页、图层、坐标轴、图例、标签、参考线、plot 样式和发表级样式。
- 支持 Nature 风格预设、语义色板、chart atlas 路由、图像板块标签和 QA checklist。
- 运行常见 Origin 分析，包括拟合、平滑、积分、微分、寻峰和描述统计。
- 将分析输出工作表读回 JSON，并在可能时规范化拟合参数和指标。
- 搜索和浏览本地 Origin 知识库，覆盖 MCP 工具、Plot Type ID、图形格式化、
  分析适配器、OriginPro API 笔记和 LabTalk/X-Function 路由。
- 导出图形、预览导出图像、保存项目，并安全释放或关闭 Origin。
- 通过本地 Origin GUI bridge 路由 Origin 操作，把 MCP server 运行环境与 Origin
  自动化运行环境分离。

## 环境要求

- Windows
- 已安装并授权的 Origin 或 OriginPro
- 当前主要测试目标是 Origin/OriginPro 2026，其他 Origin 版本暂不保证兼容
- 推荐 Python 3.11 或 3.12；Python 3.10 受支持，但测试较少
- Origin 的 `originpro` 包和 `pywin32`

Python 3.14 等较新的 Python 版本可能可以运行 MCP 服务器本身，但 Origin 自动化相关包
不一定已经发布兼容 wheel。如果在较新的 Python 版本上安装失败，请使用 Python 3.11
或 3.12。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[origin]"
```

如果你的 Origin 安装环境已经能提供 `originpro`：

```powershell
python -m pip install -e .
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

在 Origin 内用根目录 `addon.py` 启动 bridge 后，可运行
`python examples\smoke_bridge.py` 验证真实的导入、绘图、导出和保存项目流程。
`addon.py` 内不需要手动改源码目录。

## 知识库

服务器通过 MCP 工具暴露结构化本地知识库。使用 `origin_query_knowledge` 或各集合
专用 query 工具搜索；使用 `origin_browse_knowledge` 或各集合专用 browse 工具按稳定
路径查看完整条目。MCP 工具索引会从当前 server 工具 docstring 自动生成，因此会跟随
已实现工具面更新。

当前集合包括 `mcp_tools`、`reference`、`python_api`、`labtalk` 和 `official_docs`。
知识库是面向操作的精选索引；需要官方精确语法的条目会带 OriginLab 官方文档 URL。

## 安全说明

该服务器可以读取本地数据文件、写入导出的图形和项目文件，并控制本地 Origin 会话。
请只在可信 MCP 客户端中使用。必要时可用 `ORIGIN_MCP_ALLOWED_ROOTS` 限制文件访问范围。

如果 Origin 提示正在被其他程序控制，请先调用 `origin_detach`。只有在确认没有未保存
工作后，才使用 `origin_force_quit`。

## 许可证

MIT。见 [LICENSE](LICENSE)。
