# 猫咪记忆 AI · 前端

基于 **Next.js 16（App Router）+ TypeScript + Tailwind CSS v4 + axios** 的猫咪记忆应用前端。
后端为 FastAPI（见仓库 `backend/` 目录），通过 RAG + DeepSeek 实现"记忆入库"与"流式问答"。

## 目录结构

```
frontend/
├── app/                        # 路由层（Next.js App Router 约定，只放薄壳）
│   ├── layout.tsx              # 根布局：顶部导航、页脚（预留记忆列表/习惯图谱入口）
│   ├── globals.css             # 全局样式：米白 + 暖橙的温柔主题（Tailwind v4）
│   ├── page.tsx                # / 路由 → 挂载 views/HomeView
│   └── chat/
│       └── page.tsx            # /chat 路由 → 挂载 views/ChatView
├── views/                      # 页面级业务代码（与 app/ 同级，路由文件保持干净）
│   ├── HomeView.tsx            # 首页：图片选择 + 备注输入 + 保存（调用 /upload-memory）
│   └── ChatView.tsx            # 对话页：消息窗口 + 流式回答（调用 /chat）
├── components/                 # 可复用组件
│   └── MessageBubble.tsx       # 聊天气泡（导出 ChatMessage 类型，供多处复用）
├── lib/
│   └── api.ts                  # axios 实例：后端地址、超时、统一错误提取
└── public/                     # 静态资源
```

## 分层约定

新增页面时遵循同一模式，保持代码职责清晰：

1. **路由层**（`app/xxx/page.tsx`）：只负责挂载视图，不写业务逻辑；
2. **视图层**（`views/XxxView.tsx`）：页面级状态与业务逻辑；
3. **组件层**（`components/`）：跨页面可复用的 UI 片段；
4. **数据层**（`lib/api.ts`）：接口地址与 axios 配置集中管理。

> 注意：不要使用 `pages/` 作为目录名，它是 Next.js Pages Router 的保留目录，会与 App Router 冲突。

## 页面说明

| 路由 | 视图 | 调用接口 | 说明 |
| ---- | ---- | -------- | ---- |
| `/` | `HomeView` | `POST /upload-memory` | 图片以 `multipart/form-data` 上传，备注文本写入后端向量库 |
| `/chat` | `ChatView` | `POST /chat` | 流式返回纯文本，实时渲染 |

### 流式请求的实现说明

- 后端 `/chat` 返回 `text/plain` 流式响应（FastAPI `StreamingResponse`）；
- 浏览器端 axios 不支持读取流（`responseType: "stream"` 仅 Node.js 可用），
  因此对话页使用原生 `fetch` + `ReadableStream` 逐块读取，其余请求走 axios；
- 跨域由后端 `CORSMiddleware` 处理，前端无需配置代理。

## 本地开发

环境要求：**Node.js ≥ 20.9**（Next.js 16 最低要求，推荐用 nvm 切换：`nvm use 20`）。

```bash
# 1. 启动后端（仓库根目录下）
cd backend
./venv/bin/python -m uvicorn main:app --reload --port 8000

# 2. 启动前端
cd frontend
npm install
npm run dev
```

浏览器访问 http://localhost:3000，后端地址固定为 `http://127.0.0.1:8000`（见 `lib/api.ts`）。

## 常用脚本

```bash
npm run dev     # 开发服务器（http://localhost:3000）
npm run build   # 生产构建（含 TypeScript 类型检查与 ESLint）
npm run start   # 运行生产构建
npm run lint    # ESLint 检查
```

## TODO（二期规划）

- [ ] `/memories` 记忆列表页面：展示历史记忆与图片
- [ ] `/habits` 习惯图谱页面：基于记忆的结构化统计与图谱展示
- [ ] 图片 AI 自动识别：上传后由视觉模型自动生成备注
- [ ] 对话多轮上下文与消息历史本地缓存
