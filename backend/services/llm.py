# -*- coding: utf-8 -*-
"""
大模型服务
==========
封装 DeepSeek 客户端与流式生成逻辑，与具体路由解耦，
后续更换/新增模型（如视觉模型）只需扩展本模块。
"""

from collections.abc import Generator

from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

# DeepSeek 兼容 OpenAI 协议，直接复用 OpenAI SDK
# 未配置密钥时为 None，接口层给出明确提示，避免服务启动即崩溃
llm_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL) if DEEPSEEK_API_KEY else None

# 系统提示词：约束 AI 角色，确保回答基于记忆、不编造
SYSTEM_PROMPT = (
    "你是猫咪记忆 AI 助手，帮主人回忆和了解自家猫咪的生活。"
    "请严格依据提供的【猫咪记忆】内容回答，语气亲切自然；"
    "若记忆中没有相关信息，请如实说明并建议主人补充记录，不要编造。"
)


def build_prompt(question: str, memories: list[str]) -> list[dict]:
    """组装消息列表：把召回的记忆拼进用户提示词"""
    context = "\n".join(f"- {m}" for m in memories) if memories else "（暂无相关记忆）"
    user_prompt = f"【猫咪记忆】\n{context}\n\n【问题】{question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def stream_answer(question: str, memories: list[str]) -> Generator[str, None, None]:
    """
    调用 DeepSeek 流式生成回答。
    以生成器方式逐段产出文本，前端可用 fetch + ReadableStream 实时渲染。
    """
    try:
        stream = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=build_prompt(question, memories),
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


# TODO(二期)：DeepSeek 官方 API 暂无多模态模型，照片 AI 自动描述待接入
# 兼容 OpenAI vision 协议的视觉模型后，在此扩展 describe_photo() 函数。
