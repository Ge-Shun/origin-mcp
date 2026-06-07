# origin-mcp

[![PyPI version](https://img.shields.io/pypi/v/origin-mcp)](https://pypi.org/project/origin-mcp/)
[![Downloads](https://static.pepy.tech/badge/origin-mcp)](https://pepy.tech/projects/origin-mcp)
[![Python versions](https://img.shields.io/pypi/pyversions/origin-mcp)](https://pypi.org/project/origin-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
- 运行拟合、平滑、积分、寻峰、描述统计、插值、归一化、t 检验、FFT/IFFT 和相关分析等 Origin 分析。
- 通过本地 Origin GUI bridge 导出图形和项目。
- 将画好的图保存为可复用的用户模板，之后可搜索匹配并套用到同类型图形（见 [docs/tools.md](docs/tools.md#user-template-library)）。

## Nature 风格图形

默认情况下，origin-mcp 会保留当前 Origin 图形模板自带的样式。如果希望得到更接近
论文插图的清爽科研图，可以直接告诉 AI 助手“使用 Nature 格式”来创建或美化图形。
该预设会应用色盲友好的调色板、更醒目的科研图线条、Arial 字体以及更简洁的图例。

如果需要更细的控制，也可以让助手列出可用调色板。更详细的调色板和样式控制见
[docs/tools.md](docs/tools.md#palette-catalog)。

## 环境要求

- Windows
- 已安装并授权的 Origin 或 OriginPro
- 当前主要测试目标是 Origin/OriginPro 2026，其他 Origin 版本暂不保证兼容
- Origin 内嵌 Python 及其预装的 `originpro` 包

### Python 版本支持

`origin-mcp` 以两个协作进程运行，受支持的 Python 版本按角色区分：

- **MCP server core**（`python -m origin_mcp` 进程，仅通过本机回环与 bridge
  通信）：Python 3.10+。CI 会在 Windows 上使用 Python 3.10、3.11、3.12、3.13
  和 3.14 测试该核心进程。
- **Origin bridge**（`addon.py`）：运行在 Origin 自带的内嵌 Python 中，版本由你
  安装的 Origin 决定，无需自行选择。

本项目不把外部 `originpro` 自动化作为受支持的 MCP backend。请在 Origin 内嵌
Python 中启动 bridge，再让 MCP server 通过本机回环连接它。

## 安装

从 PyPI 安装 MCP server 核心：

```bash
pip install origin-mcp
```

这就是 MCP server 需要的全部：它以 `python -m origin_mcp` 运行，仅通过本机回环
与 bridge 通信。bridge 运行在 Origin 自带的内嵌 Python 中，并自行安装依赖（见下文
「在 Origin 内启动 bridge」一节）。

可选的 `origin-mcp[origin]` extra 会把 `originpro` 和 `pywin32` 装进同一环境；
标准的 bridge 流程并不需要它。若想基于源码使用，在仓库根目录运行 `pip install -e .`。

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

**Origin App（推荐日常使用）。** 按 [docs/origin-ui-buttons.md](docs/origin-ui-buttons.md)
一次性生成并安装两个 bridge App。之后在 Apps 库里点 **Origin MCP Bridge Start** 启动
bridge，点 **Origin MCP Bridge Stop** 关闭。

**Python Console（临时使用或排查问题）。** 打开 Origin 的 **Python Console**，粘贴这一行
（把路径换成你的项目路径）：

```python
import runpy; runpy.run_path(r"C:\path\to\origin-mcp\addon.py", run_name="__main__")
```

看到 `Bridge is running inside Origin.` 提示框即表示启动成功，使用工具期间保持该控制台
运行。要关闭时，让 MCP 助手关闭 bridge（它会调用 `origin_bridge_shutdown`），或双击
`scripts\stop-bridge.cmd`（或运行 `python scripts\stop_bridge.py`）。两种方式都不会
关闭 Origin。

若缺少依赖包或 bridge 起不来，请参阅 [docs/origin-bridge.md](docs/origin-bridge.md)。

## 安全性

bridge 只监听 `127.0.0.1`，并默认用每次会话自动生成的 token 验证本机请求，正常使用
无需额外安全配置。

请把该 token 当作凭据对待：任何持有它的本机进程都能用完整工具集驱动 Origin，包括通过
`origin_run_labtalk` 执行任意 LabTalk 代码。token 每次会话生成，写入当前用户临时目录下
属主可访问的文件（Windows 上为 `%TEMP%/origin-mcp/bridge.json`）；在标准单用户机器上，
该目录已由操作系统权限保护。但若你把 `TEMP` 或 `ORIGIN_MCP_BRIDGE_HANDSHAKE` 重定向到
其他本机用户可读的目录，token（以及对 Origin 的控制权）就会暴露给他们。设置
`ORIGIN_MCP_BRIDGE_NO_AUTH` 会彻底取消 token 边界，仅在你完全信任本机所有进程时使用。

如需限制工具可读写的文件范围，可设置 `ORIGIN_MCP_ALLOWED_ROOTS` 为允许访问的目录。
除非你完全信任本机所有进程，否则不要关闭 bridge 鉴权。

## 许可证

MIT。见 [LICENSE](LICENSE)。
