# mcp_service 说明文档

## 1. 服务定位

`mcp_service` 是系统中的 MCP 协议适配层，负责：

- 通过 MCP over HTTP 暴露 `query_rag` 工具
- 将 MCP 工具调用转换为 HTTP REST 请求，转发给 `rag_api_service`

它是纯 HTTP 代理，**不包含任何 RAG 核心代码**，所有知识库能力来自 `rag_api_service`。

---

## 2. 目录结构

```text
mcp_service/
├── config/
│   └── settings.py       # 服务配置（仅 HTTP 代理相关）
├── mcp_server.py         # MCP tool 定义入口
├── run.py                # 启动入口
├── pyproject.toml        # 依赖清单（uv 管理）
└── uv.lock               # 依赖锁定文件
```

---

## 3. 提供的 MCP 工具

当前仅暴露一个 MCP 工具：

- `query_rag(query)`：执行知识库问答

内部实现：通过 `httpx.post` 调用 `rag_api_service` 的 `/api/docs/query` 接口。

调用关系：

```text
langgraph_service → MCP over HTTP → mcp_service → HTTP REST → rag_api_service
```

---

## 4. 启动方式

在项目根目录执行：

```bash
uv run --project mcp_service python mcp_service/run.py
```

默认 MCP 地址：

- `http://127.0.0.1:8010/mcp`

---

## 5. 关键配置

配置文件：`mcp_service/config/settings.py`

重点环境变量：

- `RAG_API_HOST`：rag_api_service 地址（默认 `127.0.0.1`）
- `RAG_API_PORT`：rag_api_service 端口（默认 `8011`）

---

## 6. 运行依赖

- `rag_api_service` 必须在启动前运行
- 无需 Redis、ChromaDB、本地模型

---

## 7. 被调用关系

```text
langgraph_service → MCP over HTTP → mcp_service:query_rag
```
