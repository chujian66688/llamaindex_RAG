# langgraph_service 说明文档

## 1. 服务定位

`langgraph_service` 是系统中的多智能体编排服务，负责：

- 维护 LangGraph 对话图
- 管理短期记忆与状态恢复
- 进行意图识别与多节点路由
- 通过 MCP over HTTP 调用 `mcp_service.query_rag` 获取知识库能力

它不直接对前端暴露业务 API，而是供 `main_service` 调用。

---

## 2. 目录结构

```text
langgraph_service/
├── my_agent/
│   ├── agent.py
│   ├── utils/
│   │   ├── nodes.py
│   │   ├── state.py
│   │   └── tools.py
│   └── writing_subgraph/
│       ├── graph.py
│       ├── nodes.py
│       └── state.py
├── config/
│   └── settings.py
├── db.py
├── models.py
├── langgraph_app.py
├── langgraph.json
├── pyproject.toml        # 依赖清单（uv 管理）
└── uv.lock               # 依赖锁定文件
```

说明：
- `my_agent/agent.py`：图构建入口
- `my_agent/utils/nodes.py`：各个节点逻辑
- `my_agent/utils/tools.py`：MCP 工具调用封装
- `my_agent/writing_subgraph/`：写作子图（包含 `writing_agent` 和 `review_agent`）
- `langgraph.json`：LangGraph CLI 配置文件

---

## 3. 图结构说明

当前图的大致流程为：

```text
START
  -> summarize
  -> intent_router
      -> knowledge_agent -> knowledge_guard -> fallback_search / finalize
      -> writing_workflow -> finalize
      -> chat_agent -> finalize
  -> finalize
  -> END
```

主要节点职责：

- `summarize`：短期记忆摘要（langmem SummarizationNode）
- `intent_router`：识别是知识问答、写作还是普通聊天
- `knowledge_agent`：通过 MCP 调知识库
- `knowledge_guard`：守卫节点，检测回答质量，决定是否降级
- `fallback_search`：知识库答不好时兜底搜索（Tavily）
- `writing_workflow`：写作子图，内部包含 `writing_agent` 和 `review_agent`
- `chat_agent`：普通聊天
- `finalize`：收尾，提取 answer/sources/intent 返回给调用方

---

## 4. 对外使用方式

`main_service` 通过 `LANGGRAPH_API_URL` 调用本服务（使用 langgraph-sdk）：

- `POST /runs/wait`：发起对话等待完成
- `GET /threads/{thread_id}/state`：获取对话状态
- `DELETE /threads/{thread_id}`：删除对话线程

本服务默认作为 LangGraph Server 运行。

---

## 5. 与 mcp_service 的关系

本服务中的 `knowledge_agent` 不直接访问向量库，而是通过 MCP streamable-http 调用 `mcp_service.query_rag`。

MCP 调用链路：

```text
knowledge_agent → MCP over HTTP → mcp_service:query_rag → HTTP REST → rag_api_service:query
```

调用入口在 `my_agent/utils/tools.py`。

---

## 6. 启动方式

推荐在项目根目录执行：

```bash
uv run --project langgraph_service langgraph dev --config langgraph_service/langgraph.json
```

配置文件中的图入口为：

```text
./my_agent/agent.py:graph
```

---

## 7. 关键配置

配置文件：`langgraph_service/config/settings.py`

重点环境变量：

- `POSTGRES_URL`：PostgreSQL 连接串
- `DASHSCOPE_API_KEY`：模型调用密钥
- `DASHSCOPE_BASE_URL`：模型接口地址
- `DASHSCOPE_MODEL`：默认模型
- `MODEL_TEMPERATURE`：默认温度
- `MCP_SERVICE_URL`：mcp_service MCP 地址

---

## 8. 运行依赖

1. **PostgreSQL**
   - 用于 checkpointer、长期记忆

2. **mcp_service**
   - 知识库能力来源（`query_rag`）
   - 需要通过 HTTP 调用 `rag_api_service`

3. **模型 API**
   - 用于对话、意图分类、写作、审校

如果 `mcp_service` 没有启动，知识问答节点会失败或退化。

---

## 9. 调试建议

常见检查项：

1. `POSTGRES_URL` 是否可连接
2. 模型 API Key 是否配置正确
3. `mcp_service` 是否能单独启动（依赖于 `rag_api_service`）
4. `rag_api_service` 是否能单独启动
5. `langgraph.json` 中图路径是否正确
6. `main_service` 中 `LANGGRAPH_API_URL` 是否指向本服务
