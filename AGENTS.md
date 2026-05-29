# AGENTS.md — RAG_project

## 服务与端口

| 服务 | 入口 | 端口 | 技术栈 |
|---------|-----------|------|-------|
| `chat-ai-ui-main/` | `npm run dev` | `:5173` | Vue 3, TypeScript, Vite 6, Element Plus 2, Tailwind CSS 4, Pinia 3, Axios, Vue Router, Marked, Highlight.js |
| `rag_api_service/` | `uv run --project rag_api_service python rag_api_service/run.py` | `:8011` | FastAPI, LlamaIndex, ChromaDB, BM25, Sentence-Transformers, PyMuPDF — 完整 RAG 服务 |
| `mcp_service/` | `uv run --project mcp_service python mcp_service/run.py` | `:8010/mcp` | FastMCP 纯代理，HTTP 调 rag_api_service |
| `langgraph_service/` | `uv run --project langgraph_service langgraph dev --config langgraph_service/langgraph.json` | `:2024` | LangGraph, LangMem, LangChain-Tavily, MCP Adapters, PostgreSQL checkpointer |
| `main_service/` | `uv run --project main_service python main_service/run.py` | `:8000` | FastAPI, SQLAlchemy, PyJWT, pwdlib[argon2], langgraph-sdk |

**启动顺序**: rag_api_service → mcp_service → langgraph_service → main_service → chat-ai-ui-main.

## 架构

```
chat-ai-ui-main (Vue 3 :5173) → main_service (FastAPI HTTP :8000)
            ├── HTTP (REST) → rag_api_service (:8011)   // 文件上传/文档管理/重置
            ├── HTTP (langgraph-sdk) → langgraph_service (:2024)
            │       └── MCP over HTTP → mcp_service (:8010)  // 仅 query_rag
            │               └── HTTP REST → rag_api_service (:8011)
            └── HTTP (REST) → rag_api_service (:8011)   // 文档列表
```

- 所有环境变量从项目根目录 `.env` 加载（通过 `python-dotenv` 在 import 时自动加载）。
- **需要 PostgreSQL**（`POSTGRES_URL` 在 `.env` 中）。默认连接串：`postgresql+psycopg://postgres:123456@127.0.0.1:5432/langgraph_agents`。
- **需要 Redis**（`rag_api_service` 使用，默认 `127.0.0.1:6379`）。
- 默认管理员：`root` / `admin123`（`main_service` 启动时自动创建）。
- `main_service` 通过 `langgraph-sdk` 调用 `langgraph_service`（`POST /runs/wait`、`GET /threads/{id}/state`、`DELETE /threads/{id}`）。
- `main_service` 通过 HTTP REST 直接调用 `rag_api_service`（上传/列表/重置，不再走 MCP）。
- `langgraph_service` 通过 MCP streamable-http 调用 `mcp_service.query_rag`。
- `mcp_service.query_rag` 通过 HTTP 调用 `rag_api_service` 的 `/api/docs/query` 接口。

## 职责分离

| 服务 | 职责 |
|------|------|
| `chat-ai-ui-main` | 前端 UI，用户交互界面，聊天、文档管理、登录注册 |
| `rag_api_service` | 文件上传 (multipart)、文档列表、系统重置、RAG 查询 — REST API |
| `mcp_service` | 仅保留 `query_rag` 一个 MCP 工具 — AI Agent 调用入口 |
| `langgraph_service` | 多 Agent 编排，`knowledge_agent` 通过 MCP 调 `query_rag` |
| `main_service` | 对外 HTTP 入口，JWT 鉴权，组合上面三个服务 |

`rag_api_service` 拥有完整 RAG 核心代码（core/ingestion、workflow、pdf_parser），自身管理数据目录。
`mcp_service` 是纯 HTTP 代理，不包含任何 RAG 代码，通过 HTTP 调用 `rag_api_service` 的 `/api/docs/query`。

## 数据目录

`rag_api_service` 的数据存储在 `rag_api_service/file/` 下：
- `chroma_db/` — ChromaDB 向量数据库
- `storage_bm25/` — BM25 索引
- `documents/` — 文档文件
- `image/` — PDF 提取的图片
- `storage/` — 通用存储
- `logs/` — 日志文件

## LangGraph 图

```text
START → summarize → intent_router → (knowledge_agent | writing_workflow | chat_agent)
                knowledge_agent → knowledge_guard → (fallback_search | finalize)
                writing_workflow → finalize
                fallback_search → finalize
                chat_agent → finalize
                finalize → END
```

- `knowledge_agent` 调用 `mcp_service.query_rag`；`knowledge_guard` 守卫节点检测到回答质量差时降级到 `fallback_search`（Tavily 搜索）。
- `writing_workflow` 是写作子图，内部包含 `writing_agent` 和 `review_agent` 两个节点。
- 短期记忆通过 `langmem.SummarizationNode` 管理；长期记忆工具（`create_manage_memory_tool`/`create_search_memory_tool`）已在 `tools.py` 中定义。
- 线程/用户隔离：`main_service` 将用户名通过 `uuid5` 映射为确定性 UUID 作为 LangGraph thread ID。

## 命令（在项目根目录执行）

```powershell
# 安装依赖（每个服务独立虚拟环境，Python 3.11）
cd rag_api_service && uv sync --python 3.11 && cd ..
cd mcp_service && uv sync --python 3.11 && cd ..
cd langgraph_service && uv sync --python 3.11 && cd ..
cd main_service && uv sync --python 3.11 && cd ..

# 安装前端依赖
cd chat-ai-ui-main/chat-ai-ui-main && npm install && cd ../..

# 按顺序启动（使用 uv run）
uv run --project rag_api_service python rag_api_service/run.py          # :8011
uv run --project mcp_service python mcp_service/run.py                  # :8010/mcp
uv run --project langgraph_service langgraph dev --config langgraph_service/langgraph.json  # :2024
uv run --project main_service python main_service/run.py                # :8000

# 启动前端（新终端）
cd chat-ai-ui-main/chat-ai-ui-main && npm run dev                      # :5173
```

## 仓库注意事项

- 没有 lint、typecheck、测试框架或 CI 配置 — 假设没有自动化基础设施。
- `test/` 目录是临时脚本和示例文件，不是测试套件。
- `.env` 含有真实 API 密钥 — 不要提交或泄露。
- `mcp_service/run.py` 使用 `transport="streamable-http"`（FastMCP）。
- `rag_api_service` 拥有完整 RAG 核心代码（core/ingestion、workflow、pdf_parser），自身管理数据目录。
- `mcp_service` 是纯 HTTP 代理，不包含任何 RAG 代码，通过 HTTP 调用 `rag_api_service` 的 `/api/docs/query`。
- `langgraph_service` 在 Windows 上需要 `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`（已在 `agent.py` 中处理）。
