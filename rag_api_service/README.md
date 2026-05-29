# rag_api_service 说明文档

## 1. 服务定位

`rag_api_service` 是系统中的 RAG 核心服务，负责：

- 文件上传与文档摄取（PDF/文本 → 分块 → 向量化 → 入库）
- 文档管理（文档列表）
- 系统重置
- RAG 知识库问答（检索 → 重排 → 生成）

它是整个系统里的"知识库引擎"，拥有完整的 RAG 核心代码和独立的数据目录。

---

## 2. 目录结构

```text
rag_api_service/
├── core/
│   ├── application.py      # RAGApplication 主类
│   ├── ingestion.py        # 文档摄取管道
│   ├── workflow.py         # RAGWorkflow 混合检索工作流
│   ├── pdf_parser.py       # PDF 处理器 (pymupdf4llm)
│   ├── pdfProcessor.py     # PDF 处理器 (unstructured，旧版)
│   ├── documentManager.py  # ChromaDB 文档管理器
│   └── events.py           # 工作流事件定义
├── utils/
│   └── logger.py           # 日志工具
├── config/
│   └── settings.py         # 服务配置
├── file/                   # 数据目录
│   ├── chroma_db/          # ChromaDB 向量数据库
│   ├── storage_bm25/       # BM25 索引
│   ├── documents/          # 文档文件
│   ├── image/              # PDF 提取的图片
│   ├── storage/            # 通用存储
│   └── logs/               # 日志文件
├── rest_api.py             # REST API 路由
├── run.py                  # 启动入口
├── pyproject.toml          # 依赖清单（uv 管理）
└── uv.lock                 # 依赖锁定文件
```

---

## 3. REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/docs/upload` | 上传文件（multipart），触发文档摄取 |
| GET  | `/api/docs/documents` | 返回已入库文档列表 |
| GET  | `/api/docs/chunks/{doc_id}` | 获取文档分块详情（支持分页） |
| DELETE | `/api/docs/documents/{doc_id}` | 删除单个文档 |
| GET  | `/api/docs/config/chunk` | 获取当前分块配置 |
| PUT  | `/api/docs/config/chunk` | 更新分块配置（chunk_size/chunk_overlap） |
| POST | `/api/docs/reset` | 重置系统 |
| POST | `/api/docs/query` | 知识库问答 |

### `/api/docs/query` 请求格式

```json
{
    "query": "用户问题"
}
```

返回格式：

```json
{
    "answer": "回答内容",
    "sources": ["来源1", "来源2"]
}
```

---

## 4. 启动方式

在项目根目录执行：

```bash
uv run --project rag_api_service python rag_api_service/run.py
```

默认监听：

- `http://127.0.0.1:8011`

---

## 5. 关键配置

配置文件：`rag_api_service/config/settings.py`

重点环境变量：

- `DASHSCOPE_API_KEY`：模型调用密钥
- `DASHSCOPE_BASE_URL`：模型接口地址
- `DASHSCOPE_MODEL`：默认模型
- `MODEL_TEMPERATURE`：默认温度
- `EMBEDDING_MODEL_PATH`：Embedding 模型路径
- `CHUNK_SIZE`：文本切块大小
- `RERANK_MODEL_PATH`：重排模型路径
- `SIMILARITY_TOP_K`：检索召回数量
- `RERANK_TOP_K`：重排保留数量

路径类配置：

- `CHROMA_PERSIST_DIR`、`BM25_PERSIST_DIR`、`DOCUMENTS_DIR`、`PDF_IMAGE_DIR` 自动基于 `rag_api_service/file/` 生成

---

## 6. 运行依赖

1. **Redis**（默认 `127.0.0.1:6379`）— 文档存储、索引存储
2. **ChromaDB**（本地持久化）— 向量存储
3. **本地模型**（Embedding + Reranker）或远程 API
4. 文档目录可读写

---

## 7. 被调用关系

```text
main_service  → HTTP REST → rag_api_service  (文件上传/文档列表/重置)
mcp_service   → HTTP REST → rag_api_service  (RAG 查询 /api/docs/query)
```
