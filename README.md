# Copy_Myself

Copy_Myself 是一个基于 LangGraph 的本地优先个人管家智能体。当前项目重点是一个 PyQt 桌面工作台：可以聊天、读取本地记忆、调用工具、展示执行阶段，并保留 CLI 和 FastAPI 作为测试与集成入口。

## 当前状态

- 主界面：PyQt 桌面工作台。
- 编排核心：LangGraph，流程为 `load_memory -> classify_intent -> run_tool -> create_response`。
- 模型接入：OpenAI-compatible `/chat/completions`，没有 API key 时自动使用本地 fallback。
- 记忆机制：默认使用 SQLite 图记忆 `GraphMemoryStore`；旧 JSONL 记忆仅作为完整记忆展示/归档。
- 工具系统：本地工具通过 MCP-style source 暴露，外部 MCP 服务配置已进入 GUI 设置页，但外部进程启动仍留在 adapter 边界之后。

## 安装

```powershell
python -m pip install -e .[dev]
```

如果 PowerShell 中文输出乱码，先切到 UTF-8：

```powershell
chcp 65001
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

## 运行

CLI：

```powershell
copy-myself "health check"
copy-myself "帮我整理今天的任务"
```

API：

```powershell
copy-myself-api
```

默认地址是 `http://127.0.0.1:8000`，当前接口：

- `GET /api/status`
- `POST /api/chat`

PyQt 工作台：

```powershell
copy-myself-gui
```

PyQt 工作台直接调用 LangGraph agent，不需要先启动 FastAPI。

## 模型配置

推荐在 PyQt 工作台的 `设置` 页填写：

- 模型名称
- Base URL
- API Key

保存后会写入项目根目录 `.env`，下一条消息立即使用当前选中的模型。也可以复制 `.env.example` 为 `.env` 后手动填写：

```powershell
COPY_MYSELF_ACTIVE_MODEL=deepseek-v4-pro
COPY_MYSELF_MODEL_NAME=deepseek-v4-pro
COPY_MYSELF_API_KEY=your_api_key_here
COPY_MYSELF_BASE_URL=https://api.deepseek.com/v1
COPY_MYSELF_MODEL_PROFILES=[]
COPY_MYSELF_MCP_SERVICES=[]
```

`COPY_MYSELF_API_KEY` 为空时，CLI、API、PyQt 仍可运行，只会返回本地 fallback 回复。

## 记忆文件

运行时记忆写入 `memory/`，该目录被 git 忽略：

- `memory_graph.sqlite3`：当前默认图记忆，保存每轮用户-助手对话节点和关系边。
- `full_memory.jsonl`：旧 JSONL 完整记忆，仅用于用户查看/归档。
- `sessions/<session_id>.jsonl`：旧 JSONL 会话记录。

PyQt 左侧 `记忆` 按钮会打开完整记忆查看器；主工作台不直接展示模型上下文，避免干扰对话。

## 工具和 MCP

本地工具放在 `src/copy_myself/tools/`，实现 `LocalTool`：

```python
from copy_myself.tools.base import LocalTool, ToolResult


class TodoTool(LocalTool):
    name = "todo"
    description = "Create, list, and update todo tasks."

    def run(self, arguments: dict[str, object]) -> ToolResult:
        return ToolResult(name=self.name, ok=True, data={"status": "ok"})
```

默认注册表会自动发现本地工具。模型分类节点会把工具目录发给模型，请让 `description` 足够清晰。

外部 MCP 服务可以先在 PyQt `设置` 页保存服务名和启动命令/URL；当前 GUI 负责记录和展示，真正的外部 MCP 进程调用应继续放在 adapter 层。

## 项目结构

```text
src/copy_myself/
  agent/      LangGraph 状态、节点和图装配
  api/        FastAPI 集成接口
  domain/     与 UI/API 解耦的领域模型
  gui/        PyQt 桌面工作台
  memory/     记忆协议、内存存储、JSONL 存储、SQLite 图记忆
  tools/      工具协议、注册表、本地工具和 MCP-style source
  cli.py      命令行入口
  config.py   .env 配置读取和保存
  logging.py  日志设置
docs/
  architecture.md
  development-roadmap.md
  project-review-log.md
  superpowers/plans/
  superpowers/specs/
tests/
```

## 仓库卫生

不要提交这些本地文件：

- `.env`、`.env.*`
- `keys`
- `memory/`
- `.idea/`、`.vscode/`
- `.pytest_cache/`、`__pycache__/`
- `src/*.egg-info/`
- `node_modules/`、旧前端构建目录

`src/copy_myself/gui/assets/brand_c.png` 是 PyQt 工作台使用的品牌图，不是运行缓存。

## 验证

报告完成前运行：

```powershell
python -m pytest -v
python -m compileall -q src tests
```

GUI 改动还需要在本地安装 PyQt6 后手动启动：

```powershell
copy-myself-gui
```

不要在没有成功启动窗口前声称 GUI 启动已验证。

## 下一步

1. 选择第一个真实个人管家能力，建议从“每日任务规划”开始。
2. 增强图记忆查看、编辑、合并和冲突处理。
3. 增加任务、提醒、笔记或日程工具。
4. 丰富 PyQt 执行 inspector，让每次 LangGraph 运行更可解释。
