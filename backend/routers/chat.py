# -*- coding: utf-8 -*-
"""
对话接口
========
POST /chat       —— RAG 检索记忆 + DeepSeek 流式回答（text/plain 纯文本流，一期兼容保留）
GET  /chat/stream —— 同样能力的 SSE 标准协议版本（EventSource 专用，推荐前端使用）
TODO(二期)：猫咪习惯图谱——可在此结合结构化统计结果，拼装进提示词
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from config import TOP_K
from schemas import ChatRequest
from services.llm import llm_client, stream_answer
from services.vector_store import search_memories

router = APIRouter(tags=["对话"])


@router.post("/chat", summary="基于记忆库的流式问答（text/plain 流）")
async def chat(body: ChatRequest) -> StreamingResponse:
    """RAG 检索 + DeepSeek 流式回答，返回纯文本流（text/plain）。一期前端使用，保留兼容。"""
    if llm_client is None:
        raise HTTPException(status_code=503, detail="未配置 DEEPSEEK_API_KEY，请在 backend/.env 中填写后重启服务")

    memories = search_memories(body.question.strip(), top_k=TOP_K)

    return StreamingResponse(
        stream_answer(body.question.strip(), memories),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ===================== SSE 标准协议版本 =====================
#
# SSE（Server-Sent Events）格式约定：
#   每个事件 = 一行或多行 "data: 内容" + 一个空行结尾
#   多行文本按行拆成多个 data: 行（SSE 规范要求）
#   客户端通过约定俗成的 "data: [DONE]" 判断流结束（OpenAI 生态惯例）


def _sse_frame(text: str) -> str:
    """
    把一段文本编码成 SSE 数据帧。
    例："你好\n呀" → "data: 你好\\ndata: 呀\\n\\n"
    （注意：结尾的 \\n\\n 是事件分隔符，浏览器收到空行才算收到一条完整事件）
    """
    lines = text.split("\n")
    return "".join(f"data: {line}\n" for line in lines) + "\n"


def _sse_stream(question: str, memories: list[str]):
    """
    把 stream_answer 的纯文本分片包装成 SSE 帧序列的生成器。
    - 正常分片：逐帧 yield
    - 生成中途异常：把错误包成一帧继续推给前端（前端能收到错误原因而不是连接直接断掉）
    - 流结束：发送 [DONE] 帧
    """
    try:
        for chunk in stream_answer(question, memories):
            if chunk:
                yield _sse_frame(chunk)
    except Exception as exc:  # 大模型调用异常：作为最后一帧内容推给前端
        yield _sse_frame(f"\n[生成失败：{exc}]")
    yield "data: [DONE]\n\n"  # 结束标记：前端收到后主动关闭 EventSource


@router.get("/chat/stream", summary="基于记忆库的 SSE 流式问答（EventSource 专用）")
async def chat_stream(question: str = Query(..., min_length=1)) -> StreamingResponse:
    """
    SSE 版问答接口。
    用 GET 是因为浏览器原生 EventSource 只支持 GET（问题通过 query 参数传递）。
    检索逻辑与 POST /chat 完全一致，仅输出协议不同。
    """
    if llm_client is None:
        raise HTTPException(status_code=503, detail="未配置 DEEPSEEK_API_KEY，请在 backend/.env 中填写后重启服务")

    q = question.strip()
    memories = search_memories(q, top_k=TOP_K)

    return StreamingResponse(
        _sse_stream(q, memories),
        media_type="text/event-stream; charset=utf-8",  # SSE 固定 MIME 类型
        headers={
            "Cache-Control": "no-cache",     # 禁止任何层缓存流
            "X-Accel-Buffering": "no",       # 告诉 Nginx 等反向代理不要缓冲，分片实时到达
        },
    )
