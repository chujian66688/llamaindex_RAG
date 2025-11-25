# LlamaIndex RAG 实战项目

## 项目概述

这是一个基于 LlamaIndex 框架构建的检索增强生成（RAG）系统，提供了完整的文档处理、检索和对话功能。该系统能够将多种格式的文档（PDF、TXT、DOCX、Markdown）导入到向量数据库中，并通过混合检索策略（向量检索 + BM25）提供高质量的问答服务。

### 核心功能

- **多格式文档处理**：支持PDF、TXT、DOCX、Markdown等多种文档格式的上传和解析
- **混合检索策略**：结合向量检索和BM25关键词检索，提升检索精度
- **文档重排序**：使用专用的重排序模型优化检索结果质量
- **流式回答生成**：支持SSE流式返回生成内容，提供更好的用户体验
- **多会话管理**：支持多个独立会话的历史记录管理
- **用户认证机制**：基于JWT的安全认证系统
- **历史记录优化**：自动管理和优化会话历史长度，防止超长历史导致的性能问题

## 技术架构

### 系统架构

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  客户端应用  │ ──→ │  FastAPI API │ ──→ │ RAG Service │
└─────────────┘      └─────────────┘      └─────┬───────┘
                                               │
                       ┌───────────────────────┼───────────────────────┐
                       ▼                       ▼                       ▼
           ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
           │  Document       │     │  RAG            │     │  LLM            │
           │  Ingestion      │     │  Workflow       │     │  Model          │
           │  Pipeline       │     │                 │     │                 │
           └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
                    │                       │                       │
                    ▼                       ▼                       ▼
           ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
           │  ChromaDB       │     │  Redis          │     │  DashScope      │
           │  (向量存储)      │     │  (文档存储)     │     │  (文生模型)     │
           └─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 主要模块

1. **API层**：基于FastAPI提供RESTful API接口
2. **服务层**：封装核心RAG逻辑，处理请求适配
3. **核心层**：包含文档摄取、检索工作流和应用管理
4. **存储层**：使用ChromaDB和Redis进行数据持久化

## 项目结构

```
llamaindex实战案例-新/
├── app/                      # FastAPI应用
│   ├── __init__.py
│   ├── main.py               # 应用入口
│   ├── routers/              # API路由
│   │   ├── chat.py           # 聊天相关接口
│   │   ├── documents.py      # 文档相关接口
│   │   └── users.py          # 用户相关接口
│   ├── schemas.py            # Pydantic数据模型
│   └── services/             # 服务层
│       └── rag_service.py    # RAG服务封装
├── config/                   # 配置
│   └── settings.py           # 应用配置类
├── core/                     # 核心业务逻辑
│   ├── __init__.py
│   ├── application.py        # RAG应用主类
│   ├── documentManager.py    # 文档管理器
│   ├── events.py             # 事件定义
│   ├── ingestion.py          # 文档摄取管道
│   ├── pdf_parser.py         # PDF解析器
│   ├── pdfProcessor.py       # PDF处理器
│   └── workflow.py           # RAG工作流
├── file/                     # 文件存储
│   ├── chroma_db/            # Chroma向量数据库
│   ├── image/                # 图片存储
│   ├── logs/                 # 日志文件
│   └── storage_bm25/         # BM25索引存储
├── requirements.txt          # 项目依赖
├── test/                     # 测试目录
└── utils/                    # 工具类
    └── logger.py             # 日志配置
```

## 技术栈

### 核心框架
- **LlamaIndex**: RAG应用构建框架
- **FastAPI**: 高性能Web框架
- **Pydantic**: 数据验证和设置管理

### 模型与向量库
- **DashScope LLM**: 生成模型（通义千问）
- **HuggingFace Embedding**: 本地嵌入模型
- **ChromaDB**: 向量数据库
- **Redis**: 文档和索引存储

### 文档处理
- **PyPDF**: PDF文件处理
- **python-docx**: Word文档处理
- **Unstructured**: 非结构化数据处理

### 检索优化
- **BM25Retriever**: 关键词检索
- **SentenceTransformerRerank**: 文档重排序

## 核心功能模块

### 1. 文档摄取管道 (DocumentIngestionPipeline)

负责文档的上传、解析、切分、向量化和索引构建：

- 支持多格式文档处理
- 文档分块和向量化
- 索引持久化存储
- 缓存机制优化

### 2. RAG工作流 (RAGWorkflow)

实现检索增强生成的核心流程：

- 混合检索策略（向量检索 + BM25）
- 检索结果重排序
- 上下文构建和回答生成

### 3. RAG应用管理 (RAGApplication)

应用层面的功能整合：

- 多会话管理
- 流式/非流式查询支持
- 历史记录优化（防止超长历史导致的性能问题）
- 错误处理和日志记录

## API接口

### 文档管理

- **POST /api/docs/upload**: 上传并处理文档
- **GET /api/docs/list**: 获取已上传文档列表
- **POST /api/docs/reset**: 重置系统（清空索引等）

### 对话功能

- **POST /api/chat/query**: 发送问题，获取回答
- **POST /api/chat/stream**: 流式获取回答
- **POST /api/chat/clear**: 清空会话历史

### 用户管理

- **POST /users/register**: 用户注册
- **POST /users/login**: 用户登录

### 系统监控

- **GET /api/health**: 健康检查

## 配置说明

主要配置项位于 `config/settings.py`：

- **模型配置**: API密钥、模型名称、温度参数
- **文档处理**: 分块大小、重叠度
- **检索配置**: 相似度阈值、Top-K参数、重排序配置
- **存储路径**: 数据库和文件存储路径

## 安装与部署

### 前置条件

- Python 3.9+
- Redis服务
- CUDA环境（推荐，用于加速嵌入模型）

### 安装步骤

1. 克隆项目
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 配置环境变量（在.env文件中）：
   ```
   DASHSCOPE_API_KEY=your_api_key_here
   ```
4. 启动应用：
   ```bash
   python -m app.main
   ```

### Docker部署

（待实现）

## 使用示例

### 文档上传与处理

```python
from app.services.rag_service import RAGService

rag_service = RAGService()
result = rag_service.upload_files(["path/to/file.pdf"])
print(result)
```

### 发起查询

```python
from app.services.rag_service import RAGService

rag_service = RAGService()
history, error = rag_service.query("session_1", "请介绍项目的核心功能")
if not error:
    print(history[-1]['content'])  # 打印最新回答
```

### 流式查询

```python
from app.services.rag_service import RAGService
import asyncio

async def main():
    rag_service = RAGService()
    async for chunk in rag_service.query_stream("session_1", "请详细介绍RAG技术", True):
        if chunk['type'] == 'text':
            print(chunk['content'], end='', flush=True)

asyncio.run(main())
```

## 系统优化

1. **历史记录管理**：实现了智能的历史记录长度限制和截断机制，防止过长历史导致的空回复问题
2. **图片处理优化**：改进了Markdown图片提取逻辑，支持Windows路径格式和图片去重
3. **检索优化**：使用混合检索和重排序策略提升检索质量
4. **错误处理**：完善的异常捕获和日志记录机制

## 注意事项

1. **API密钥安全**：请妥善保管您的DashScope API密钥
2. **存储容量**：监控向量数据库和Redis存储的使用情况
3. **性能优化**：对于大规模文档集，可能需要调整分块大小和检索参数
4. **安全配置**：生产环境中请修改CORS设置，限制允许的来源

## 扩展方向

1. 支持更多文档格式
2. 实现文档更新和版本控制
3. 添加文档摘要和可视化功能
4. 多模型支持和模型切换
5. 添加用户权限管理

## 许可证

MIT License
