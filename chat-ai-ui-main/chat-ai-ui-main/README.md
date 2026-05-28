# Chat AI 用户界面

这是 Chat AI 应用的前端部分。它是一个基于 **Vue.js 3** 的应用程序，通过自定义 API 与 [Stream Chat](https://getstream.io)、您的 [Neon](https://neon.tech) PostgreSQL 数据库和 [Open AI](https://platform.openai.com) 进行交互。

<img src="./src/assets/screen.png" />

该应用的 Express 后端 API 可在[此处](https://github.com/bradtraversy/chat-ai-api)找到。

## 安装说明

1. 克隆仓库
2. 运行 `npm install`
3. 在根目录创建 `.env` 文件并添加以下环境变量：

```
VITE_API_URL=http://localhost:8000
```

4. Run the server with `npm run dev` and open on `http://localhost:5173/`