# -*- coding: utf-8 -*-
"""
猫咪记忆 AI · FastAPI 后端（一期）
==================================

一期能力：
    1. POST /upload-memory —— 上传猫咪图片 + 手动输入备注(note)，只把 note 文本写入 ChromaDB 向量库
    2. POST /chat          —— 根据 question 做 RAG 检索，调用 DeepSeek(deepseek-chat) 流式返回回答

二期扩展点（代码中已用 TODO(二期) 标注）：
    - 图片 AI 识别：图片已原样落盘到 uploads/，后续接视觉模型自动生成 note
    - 猫咪习惯图谱：基于向量库 metadata（时间、来源等）做结构化统计与图谱展示
"""

from __future__ import annotations

import io
import os
import uuid
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

# ===================== 一、配置加载 =====================
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db").strip()

# 相对路径统一以 backend/ 为基准，绝对路径直接使用
CHROMA_DIR = (BASE_DIR / CHROMA_PATH).resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 业务常量（集中管理，便于后续调整）
MODEL_NAME = "deepseek-chat"          # 对话模型
COLLECTION_NAME = "cat_memories"      # 记忆集合名
TOP_K = 3                             # RAG 每次召回的记忆条数
MAX_IMAGE_SIZE = 10 * 1024 * 1024     # 单张图片上限 10MB
ALLOWED_IMAGE_SUFFIX = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

# ===================== 二、服务初始化 =====================
# 1) 文本向量化模型：ChromaDB 内置的 all-MiniLM-L6-v2，首次运行会自动下载模型文件
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# 2) ChromaDB 持久化客户端：数据自动落盘到 CHROMA_PATH
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# 3) 记忆集合：一期只存 note 文本，metadata 预留时间/图片来源等字段
memory_collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_fn,
)

# 4) DeepSeek 客户端：DeepSeek 兼容 OpenAI 协议，直接复用 OpenAI SDK
#    未配置密钥时为 None，接口层给出明确提示，避免服务启动即崩溃
llm_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL) if DEEPSEEK_API_KEY else None

# ===================== 三、FastAPI 应用 =====================
app = FastAPI(
    title="猫咪记忆 AI 后端",
    description="上传猫咪图片+备注建立记忆库，并通过 RAG 问答回忆猫咪的生活",
    version="0.1.0",
)

# 跨域配置：允许前端（如 Vite/本地静态页）直接调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== 四、请求体模型 =====================
class ChatRequest(BaseModel):
    """问答请求体"""
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")

# 系统提示词：约束 AI 角色，确保回答基于记忆、不编造
SYSTEM_PROMPT = (
    "你是猫咪记忆 AI 助手，帮主人回忆和了解自家猫咪的生活。"
    "请严格依据提供的【猫咪记忆】内容回答，语气亲切自然；"
    "若记忆中没有相关信息，请如实说明并建议主人补充记录，不要编造。"
)

# ===================== 五、工具函数 =====================

def save_image(contents: bytes, original_name: str) -> Path:
    """把图片原样落盘到 uploads/，返回保存路径（二期图片解析可直接读取该文件）"""
    suffix = Path(original_name or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIX:
        suffix = ".jpg"
    target = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    target.write_bytes(contents)
    return target


def validate_image(contents: bytes) -> None:
    """用 Pillow 校验文件是否是有效图片（防止伪装成图片的其他文件）"""
    try:
        with Image.open(io.BytesIO(contents)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="上传的文件不是有效图片")


def search_memories(question: str, top_k: int = TOP_K) -> list[str]:
    """RAG 检索：按语义相似度召回最相关的 top_k 条记忆文本"""
    if memory_collection.count() == 0:
        return []
    result = memory_collection.query(query_texts=[question], n_results=min(top_k, memory_collection.count()))
    documents = result.get("documents") or []
    return documents[0] if documents else []


def stream_answer(question: str, memories: list[str]):
    """
    调用 DeepSeek 流式生成回答。
    以生成器方式逐段产出文本，前端可用 fetch + ReadableStream 实时渲染。
    """
    context = "\n".join(f"- {m}" for m in memories) if memories else "（暂无相关记忆）"
    user_prompt = f"【猫咪记忆】\n{context}\n\n【问题】{question}"

    try:
        stream = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            temperature=0.7,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception as exc:  # 网络/鉴权等异常统一回传给前端
        yield f"\n[生成失败：{exc}]"

# ===================== 六、接口 =====================

@app.post("/upload-memory", summary="上传猫咪记忆（图片 + 备注）")
async def upload_memory(
    file: UploadFile = File(..., description="猫咪图片"),
    note: str = Form(..., description="用户手动输入的备注文字"),
) -> dict:
    """保存一条猫咪记忆：图片落盘，note 文本写入向量库。"""
    note = note.strip()
    if not note:
        raise HTTPException(status_code=400, detail="备注内容不能为空")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="图片超过 10MB 限制")

    # 1) 校验图片合法性（一期不做 AI 识别）
    validate_image(contents)
    # TODO(二期)：在此接入视觉模型，自动生成图片描述并与 note 合并
    image_path = save_image(contents, file.filename)

    # 2) note 文本写入向量库，metadata 预留扩展字段
    memory_id = uuid.uuid4().hex
    memory_collection.add(
        ids=[memory_id],
        documents=[note],
        metadatas=[{
            "source": "user_note",
            "image_path": str(image_path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }],
    )

    return {
        "code": 0,
        "msg": "记忆保存成功",
        "data": {"id": memory_id, "note": note, "image_path": str(image_path)},
    }


@app.post("/chat", summary="基于记忆库的流式问答")
async def chat(body: ChatRequest) -> StreamingResponse:
    """RAG 检索 + DeepSeek 流式回答，返回纯文本流（text/plain）。"""
    if llm_client is None:
        raise HTTPException(status_code=503, detail="未配置 DEEPSEEK_API_KEY，请在 backend/.env 中填写后重启服务")

    question = body.question.strip()
    # TODO(二期)：猫咪习惯图谱——可在此结合结构化统计结果，拼装进提示词
    memories = search_memories(question)

    return StreamingResponse(
        stream_answer(question, memories),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
