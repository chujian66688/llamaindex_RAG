# Tuling-Ai 智能问答与写作助手系统

一个基于 RAG（检索增强生成）和多智能体编排的企业级 AI 助手系统，支持知识库问答、智能写作和普通对话三大核心功能。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           chat-ai-ui-main (Vue 3)                          │
│                              http://localhost:5173                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ HTTP REST
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          main_service (FastAPI)                             │
│                          http://localhost:8000                              │
│                    JWT 鉴权 · 用户管理 · 会话管理                              │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                           │
                    │ langgraph-sdk              │ HTTP REST
                    ▼                           ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│    langgraph_service            │   │      rag_api_service            │
│    http://localhost:2024        │   │      http://localhost:8011      │
│  多智能体编排 · 意图路由           │   │  RAG 核心 · 文档管理            │
└─────────────────────────────────┘   └─────────────────────────────────┘
                    │                           ▲
                    │ MCP over HTTP              │ HTTP REST
                    ▼                           │
┌─────────────────────────────────────────────────────────────────────────────┐
│                          mcp_service (FastMCP)                              │
│                         http://localhost:8010/mcp                           │
│                           query_rag 工具代理                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 知识库问答 (Knowledge)
- 支持 PDF、TXT、Markdown 等文档上传
- 基于 ChromaDB 的向量检索 + BM25 的混合检索
- 自动分块、向量化、索引构建
- 支持重排序（Rerank）提升检索质量
- 检索失败时自动降级到 Tavily 网络搜索

### 2. 智能写作 (Writing)
- 多阶段写作流程：理解需求 → 搜索资料 → 生成大纲 → 撰写文章 → 审核修订
- 支持人机交互：在写作过程中可暂停并请求用户确认
- 子图架构：写作流程独立于主图，便于扩展

### 3. 普通对话 (Chat)
- 基于 LLM 的多轮对话
- 短期记忆自动摘要（langmem SummarizationNode）
- 长期记忆存储（PostgreSQL）

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3, TypeScript, Vite 6, Element Plus 2, Tailwind CSS 4, Pinia 3, Axios, Vue Router, Marked, Highlight.js |
| **后端网关** | FastAPI, SQLAlchemy, PyJWT, pwdlib[argon2], langgraph-sdk |
| **智能体编排** | LangGraph, LangMem, LangChain-Tavily, MCP Adapters |
| **RAG 核心** | LlamaIndex, ChromaDB, BM25, Sentence-Transformers, PyMuPDF |
| **协议层** | FastMCP (MCP over HTTP) |
| **数据库** | PostgreSQL (checkpointer + 长期记忆), Redis (文档存储), ChromaDB (向量存储) |

## 服务说明

### chat-ai-ui-main (`:5173`)
前端用户界面，提供聊天、文档管理、登录注册等功能。

**核心特性：**
- 流式响应（SSE）实时显示
- 知识库开关控制
- 会话历史管理
- 响应式布局

### main_service (`:8000`)
系统主入口服务，负责用户鉴权和请求路由。

**主要接口：**
- `/users/*` - 用户认证（登录/注册/退出）
- `/api/chat/*` - 聊天接口（流式/非流式）
- `/api/docs/*` - 文档管理（上传/列表/重置）

### langgraph_service (`:2024`)
多智能体编排服务，基于 LangGraph 构建。

**图结构：**
```
START → summarize → intent_router → (knowledge_agent | writing_workflow | chat_agent)
                knowledge_agent → knowledge_guard → (fallback_search | finalize)
                writing_workflow → finalize
                fallback_search → finalize
                chat_agent → finalize
                finalize → END
```

**节点职责：**
- `summarize` - 短期记忆摘要
- `intent_router` - 意图识别与路由
- `knowledge_agent` - 知识库问答（通过 MCP 调用）
- `knowledge_guard` - 回答质量守卫
- `fallback_search` - Tavily 搜索兜底
- `writing_workflow` - 写作子图（含 writing_agent + review_agent）
- `chat_agent` - 普通对话
- `finalize` - 收尾提取

### rag_api_service (`:8011`)
RAG 核心服务，负责文档处理和知识库问答。

**REST API：**
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/docs/upload` | 上传文件 |
| GET | `/api/docs/documents` | 文档列表 |
| GET | `/api/docs/chunks/{doc_id}` | 文档分块详情 |
| DELETE | `/api/docs/documents/{doc_id}` | 删除文档 |
| GET | `/api/docs/config/chunk` | 获取分块配置 |
| PUT | `/api/docs/config/chunk` | 更新分块配置 |
| POST | `/api/docs/reset` | 重置系统 |
| POST | `/api/docs/query` | 知识库问答 |

### mcp_service (`:8010/mcp`)
MCP 协议适配层，仅暴露 `query_rag` 工具。

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

### 1. 克隆项目

```bash
git clone <repository-url>
cd Tuling-Ai
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入实际配置：

```bash
cp .env.example .env
```

**必填配置（3 项）：**

```env
# 模型 API 密钥（选择一个提供商即可）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# PostgreSQL 连接串
POSTGRES_URL=postgresql+psycopg://postgres:your_password@127.0.0.1:5432/langgraph_agents
```

**可选配置：**

```env
# Tavily 搜索（知识库兜底搜索功能）
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# JWT 密钥（生产环境建议修改）
JWT_SECRET_KEY=your-super-secret-key-change-me
```

> 完整配置项请参考 `.env.example` 文件，包含详细注释说明。

### 3. 安装依赖

```powershell
# Python 服务（每个服务独立虚拟环境）
cd rag_api_service && uv sync --python 3.11 && cd ..
cd mcp_service && uv sync --python 3.11 && cd ..
cd langgraph_service && uv sync --python 3.11 && cd ..
cd main_service && uv sync --python 3.11 && cd ..

# 前端
cd chat-ai-ui-main/chat-ai-ui-main && npm install && cd ../..
```

### 4. 启动服务

按顺序启动（每个服务一个终端）：

```powershell
# 1. RAG 核心服务
uv run --project rag_api_service python rag_api_service/run.py

# 2. MCP 代理服务
uv run --project mcp_service python mcp_service/run.py

# 3. LangGraph 服务
uv run --project langgraph_service langgraph dev --config langgraph_service/langgraph.json

# 4. 主入口服务
uv run --project main_service python main_service/run.py

# 5. 前端（新终端）
cd chat-ai-ui-main/chat-ai-ui-main && npm run dev
```

### 5. 访问系统

- 前端界面：http://localhost:5173
- 主服务 API：http://localhost:8000/docs
- LangGraph UI：http://localhost:2024

**默认管理员：**
- 用户名：`root`
- 密码：`admin123`

## 目录结构

```
Tuling-Ai/
├── chat-ai-ui-main/          # 前端 Vue 3 应用
│   └── chat-ai-ui-main/
│       ├── src/
│       │   ├── api/          # API 接口
│       │   ├── components/   # 组件
│       │   ├── stores/       # Pinia 状态
│       │   └── views/        # 页面
│       └── package.json
├── main_service/             # 主入口服务
│   ├── app/
│   │   ├── routers/          # 路由（chat/documents/users）
│   │   └── services/         # 服务层
│   ├── config/
│   └── models.py             # 数据库模型
├── langgraph_service/        # LangGraph 编排服务
│   ├── my_agent/
│   │   ├── agent.py          # 图构建入口
│   │   ├── utils/            # 节点、状态、工具
│   │   └── writing_subgraph/ # 写作子图
│   └── config/
├── rag_api_service/          # RAG 核心服务
│   ├── core/
│   │   ├── application.py    # RAG 主类
│   │   ├── ingestion.py      # 文档摄取
│   │   ├── workflow.py       # 检索工作流
│   │   └── pdf_parser.py     # PDF 解析
│   ├── file/                 # 数据目录
│   │   ├── chroma_db/        # 向量数据库
│   │   ├── storage_bm25/     # BM25 索引
│   │   └── documents/        # 文档文件
│   └── config/
├── mcp_service/              # MCP 代理服务
│   ├── mcp_server.py
│   └── config/
├── .env                      # 环境变量
└── AGENTS.md                 # 架构文档
```

## 数据流

### 知识库问答流程
```
用户提问 → main_service → langgraph_service
    → intent_router (识别为 knowledge)
    → knowledge_agent → MCP → mcp_service → rag_api_service
    → ChromaDB 向量检索 + BM25 检索
    → 重排序 → 生成回答
    → knowledge_guard (质量检查)
    → finalize → 返回用户
```

### 写作流程
```
用户请求写作 → main_service → langgraph_service
    → intent_router (识别为 writing)
    → writing_workflow (子图)
        → understand (理解需求)
        → research (搜索资料)
        → outline (生成大纲)
        → draft (撰写文章)
        → review (审核)
        → revise (修订)
        → format_output (格式化)
    → finalize → 返回用户
```

## 配置说明

### rag_api_service 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CHUNK_SIZE` | 文本分块大小 | 512 |
| `CHUNK_OVERLAP` | 分块重叠 | 50 |
| `SIMILARITY_TOP_K` | 向量检索数量 | 5 |
| `RERANK_TOP_K` | 重排保留数量 | 3 |
| `EMBEDDING_MODEL_PATH` | Embedding 模型路径 | - |
| `RERANK_MODEL_PATH` | Rerank 模型路径 | - |

### langgraph_service 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `POSTGRES_URL` | PostgreSQL 连接串 | - |
| `MCP_SERVICE_URL` | MCP 服务地址 | http://127.0.0.1:8010/mcp |
| `DASHSCOPE_MODEL` | 默认模型 | qwen-turbo |

### main_service 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JWT_SECRET_KEY` | JWT 密钥 | - |
| `JWT_ALGORITHM` | JWT 算法 | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间 | 1440 |
| `LANGGRAPH_API_URL` | LangGraph 服务地址 | http://127.0.0.1:2024 |
| `RAG_API_URL` | RAG 服务地址 | http://127.0.0.1:8011/api/docs |

## 常见问题

### 1. 服务启动失败
- 检查 PostgreSQL 和 Redis 是否运行
- 检查端口是否被占用
- 查看各服务的 `file/logs/` 目录下的日志

### 2. 模型调用失败
- 确认 API Key 配置正确
- 检查网络连接
- 尝试切换模型提供商

### 3. 文档上传失败
- 确认文件格式支持（PDF/TXT/MD）
- 检查 `rag_api_service/file/` 目录权限
- 查看 Redis 是否正常运行

## 开发指南

### 添加新的 Agent 节点

1. 在 `langgraph_service/my_agent/utils/nodes.py` 添加节点函数
2. 在 `langgraph_service/my_agent/agent.py` 注册节点和边
3. 更新 `langgraph_service/my_agent/utils/state.py` 状态定义

### 添加新的 MCP 工具

1. 在 `mcp_service/mcp_server.py` 添加工具函数
2. 在 `rag_api_service/rest_api.py` 添加对应 API
3. 更新 `langgraph_service/my_agent/utils/tools.py` 工具调用

## 许可证

[待添加]

## 贡献者

[待添加]
