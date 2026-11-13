# 猫咪记忆 AI · 后端

基于 **FastAPI + ChromaDB + DeepSeek** 的猫咪记忆应用后端。
核心能力：把主人随手记的猫咪备注向量化入库（RAG），提问时召回相关记忆并流式生成回答。
前端为 Next.js（见仓库 `frontend/` 目录），开发环境通过 Next 代理 `/api/*` 转发到本服务。

## 目录结构

```
backend/
├── main.py                  # 应用入口：FastAPI 实例、CORS、路由注册、根路由/favicon
├── config.py                # 配置：环境变量（.env）、路径、业务常量，集中管理
├── schemas.py               # Pydantic 请求/响应模型（ChatRequest）
├── routers/                 # 路由层：只管协议（参数校验、状态码）
│   ├── memories.py          # POST /upload-memory（记忆域）
│   └── chat.py              # POST /chat（对话域）
├── services/                # 服务层：业务逻辑
│   ├── vector_store.py      # ChromaDB 初始化、记忆集合、search_memories 语义检索
│   └── llm.py               # DeepSeek 客户端、系统提示词、stream_answer 流式生成
├── utils/
│   └── image.py             # 图片校验（Pillow）与落盘
├── uploads/                 # 上传图片存储目录（不入库）
├── chroma_db/               # ChromaDB 持久化数据（不入库）
├── .env                     # 密钥配置（禁止提交）
└── requirements.txt         # 依赖清单
```

## 分层约定

遵循 FastAPI 社区主流的分层风格，新增接口时照此模式扩展：

1. **路由层**（`routers/`）：`APIRouter(tags=[...])` 按业务域分组，只做参数校验与响应组装；
2. **服务层**（`services/`）：向量库、大模型等业务封装，路由层不直接接触底层细节；
3. **数据模型**（`schemas.py`）：Pydantic 模型集中定义；
4. **配置**（`config.py`）：所有环境变量与常量从这里取，改配置不动业务代码。

## API 一览

| 方法 | 路径 | 说明 | 响应 |
| ---- | ---- | ---- | ---- |
| POST | `/upload-memory` | 上传猫咪图片（multipart）+ 备注文本 | JSON：`{code, msg, data}` |
| POST | `/chat` | 传入 `{question}`，RAG 召回记忆后流式回答 | `text/plain` 流 |
| GET | `/` | 服务健康检查（含记忆条数） | JSON |
| GET | `/docs` | Swagger 交互式文档 | - |

### RAG 问答流程

```
用户提问 → ChromaDB 语义检索 Top-K 条记忆 → 拼进提示词 → DeepSeek 流式生成
```

- 向量化：ChromaDB 内置 all-MiniLM-L6-v2（首次使用自动下载到 `~/.cache/chroma`）；
- 流式返回：FastAPI `StreamingResponse` 产出纯文本，前端用 `fetch + ReadableStream` 实时渲染；
- 跨域：`CORSMiddleware` 全放行（开发模式），生产部署建议收紧 `allow_origins`。

## 本地开发

环境要求：Python 3.12+

```bash
cd backend

# 1. 创建虚拟环境（已有 venv/ 可跳过）
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. 配置密钥：在 .env 中填写
#    DEEPSEEK_API_KEY=sk-xxxx
#    DEEPSEEK_BASE_URL=https://api.deepseek.com（默认）
#    CHROMA_PATH=./chroma_db（默认）

# 3. 启动（--reload 改代码自动生效）
./venv/bin/python -m uvicorn main:app --reload --port 8000
```

启动后访问 http://127.0.0.1:8000/docs 查看交互式文档。

> 提示：首次调用 `/upload-memory` 时会下载向量化模型（约 83MB），
> 若网络不畅导致请求挂起，可手动下载模型包解压到 `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/`。

## TODO（二期规划）

- [ ] 图片 AI 识别：接入视觉模型，上传后自动生成图片描述并与备注合并
- [ ] `GET /memories`：记忆列表接口（分页、按时间排序）
- [ ] 猫咪习惯图谱：基于 metadata（时间、来源）做结构化统计与图谱数据接口
