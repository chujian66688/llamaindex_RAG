# main_service 说明文档

## 1. 服务定位

`main_service` 是系统的主入口服务，负责：

- 对外提供 FastAPI HTTP 接口
- 用户注册、登录、JWT 鉴权
- 接收前端聊天请求，并转发给 `langgraph_service`
- 接收前端文档管理请求，并通过 HTTP 直接调用 `rag_api_service`

它本身不再承担知识库核心计算，也不直接运行 Agent 图。

---

## 2. 目录结构

```text
main_service/
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── chat.py          # 聊天接口
│   │   ├── documents.py     # 文档管理接口
│   │   └── users.py         # 用户与鉴权接口
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py
│       ├── langgraph_service.py  # 调用 langgraph_service
│       ├── rag_api_service.py    # 通过 HTTP 调用 rag_api_service
│       ├── memory_repository.py
│       └── user_repository.py
├── config/
│   └── settings.py
├── utils/
│   └── logger.py
├── db.py
├── models.py
├── pyproject.toml          # 依赖清单（uv 管理）
├── uv.lock                 # 依赖锁定文件
└── run.py
```

说明：
- `app/routers/chat.py` 负责聊天相关接口
- `app/routers/documents.py` 负责文档相关接口
- `app/routers/users.py` 负责用户与鉴权接口
- `app/services/langgraph_service.py` 负责调用 `langgraph_service`
- `app/services/rag_api_service.py` 负责通过 HTTP 调用 `rag_api_service`

---

## 3. 对外接口

### 3.1 健康检查
- `GET /api/health`

### 3.2 用户接口
- `POST /users/token`：登录
- `POST /users/register`：注册
- `POST /users/logout`：退出
- `GET /users/me`：获取当前用户
- `PUT /users/me`：更新当前用户
- `GET /users/all`：获取用户列表
- `DELETE /users/me`：删除当前用户

### 3.3 聊天接口
- `POST /api/chat/chat`：非流式聊天
- `POST /api/chat/chat/stream`：SSE 兼容流式聊天
- `GET /api/chat/history`：读取当前用户对话历史
- `POST /api/chat/clear`：清空当前用户短期会话

### 3.4 文档接口
- `POST /api/docs/upload`：上传文档
- `GET /api/docs/list`：文档列表
- `POST /api/docs/reset`：重置知识库

文档接口内部通过 HTTP 直接调用 `rag_api_service`，不再经过 MCP 协议。

---

## 4. 依赖关系

`main_service` 依赖两个外部服务：

1. **`langgraph_service`**
   - 用于多智能体对话
   - 默认地址来自 `LANGGRAPH_API_URL`（`:2024`）

2. **`rag_api_service`**
   - 用于文件上传、文档列表、系统重置
   - 默认地址来自 `RAG_API_URL`（`:8011`）

调用关系：

```text
前端/调用方 → main_service → langgraph_service (:2024)
前端/调用方 → main_service → HTTP REST → rag_api_service (:8011)
```

---

## 5. 启动方式

在项目根目录执行：

```bash
uv run --project main_service python main_service/run.py
```

默认监听：

- `http://127.0.0.1:8000`

---

## 6. 关键配置

配置文件：`main_service/config/settings.py`

重点环境变量：

- `POSTGRES_URL`：PostgreSQL 连接串
- `JWT_SECRET_KEY`：JWT 密钥
- `JWT_ALGORITHM`：JWT 算法
- `ACCESS_TOKEN_EXPIRE_MINUTES`：Token 过期时间
- `DASHSCOPE_MODEL`：默认聊天模型名
- `LANGGRAPH_API_URL`：LangGraph 服务地址
- `LANGGRAPH_ASSISTANT_ID`：LangGraph Assistant ID
- `RAG_API_URL`：rag_api_service 地址（默认 `http://127.0.0.1:8011/api/docs`）

---

## 7. 数据库说明

`main_service` 使用 PostgreSQL 存储：

- 用户信息表 `users`
- 长期记忆表 `long_term_memories`

启动时会自动建表，并自动创建默认管理员：

- 用户名：`root`
- 密码：`admin123`

建议上线前立即修改初始化密码逻辑。

---

## 8. 与其他服务的协作建议

推荐启动顺序：

1. 先启动 `rag_api_service`
2. 再启动 `mcp_service`
3. 再启动 `langgraph_service`
4. 最后启动 `main_service`

如果 `rag_api_service` 或 `langgraph_service` 未启动，`main_service` 的对应接口会返回转发错误。
