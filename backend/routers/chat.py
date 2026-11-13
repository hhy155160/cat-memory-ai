# -*- coding: utf-8 -*-
"""
对话接口
========
POST /chat —— RAG 检索记忆 + DeepSeek 流式回答
TODO(二期)：猫咪习惯图谱——可在此结合结构化统计结果，拼装进提示词
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config import TOP_K
from schemas import ChatRequest
from services.llm import llm_client, stream_answer
from services.vector_store import search_memories

router = APIRouter(tags=["对话"])


@router.post("/chat", summary="基于记忆库的流式问答")
async def chat(body: ChatRequest) -> StreamingResponse:
    """RAG 检索 + DeepSeek 流式回答，返回纯文本流（text/plain）。"""
    if llm_client is None:
        raise HTTPException(status_code=503, detail="未配置 DEEPSEEK_API_KEY，请在 backend/.env 中填写后重启服务")

    memories = search_memories(body.question.strip(), top_k=TOP_K)

    return StreamingResponse(
        stream_answer(body.question.strip(), memories),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
