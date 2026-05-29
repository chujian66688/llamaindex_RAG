# Chat AI 用户界面

这是 Chat AI 应用的前端部分，基于 Vue 3 构建的现代化聊天界面。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript 超集
- **Vite 6** - 下一代前端构建工具
- **Element Plus 2** - Vue 3 UI 组件库
- **Tailwind CSS 4** - 实用优先的 CSS 框架
- **Pinia 3** - Vue 状态管理库（支持持久化）
- **Axios** - HTTP 客户端
- **Vue Router** - Vue 路由管理
- **Marked** - Markdown 渲染
- **Highlight.js** - 代码语法高亮

## 功能特性

- 用户登录/注册
- 多轮对话聊天
- 流式响应（SSE）
- 文档上传与管理
- 知识库问答
- 会话历史管理
- 响应式布局

## 安装与运行

### 1. 安装依赖

```bash
cd chat-ai-ui-main/chat-ai-ui-main
npm install
```

### 2. 配置环境变量

在根目录创建 `.env` 文件：

```env
VITE_API_URL=http://localhost:8000
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173/

## 目录结构

```
src/
├── api/          # API 接口定义
├── assets/       # 静态资源
├── components/   # 通用组件
├── router/       # 路由配置
├── stores/       # Pinia 状态管理
├── views/        # 页面视图
├── App.vue       # 根组件
└── main.ts       # 入口文件
```

## 依赖关系

前端通过 HTTP 调用 `main_service`（默认 `http://localhost:8000`）：

- `/users/*` - 用户认证接口
- `/api/chat/*` - 聊天接口
- `/api/docs/*` - 文档管理接口

## 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。
