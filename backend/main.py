# -*- coding: utf-8 -*-
"""
猫咪记忆 AI · FastAPI 后端（一期）
==================================

应用入口：只负责创建 FastAPI 实例、注册中间件与路由。
业务代码按以下分层组织，新增接口时照此模式扩展：

    config.py             配置（环境变量、路径、常量）
    schemas.py            Pydantic 请求/响应模型
    routers/              路由层（memories 记忆、chat 对话）
    services/             服务层（vector_store 向量库、llm 大模型）
    utils/                工具（image 图片校验与落盘）

二期能力（代码中已用 TODO(二期) 标注）：
    - 图片 AI 识别：接入视觉模型自动生成 note
    - 记忆列表 /memories 与猫咪习惯图谱 /habits
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from routers import chat, memories
from services.vector_store import count_memories

# ===================== FastAPI 应用 =====================
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

# 注册路由
app.include_router(memories.router)
app.include_router(chat.router)


# ===================== 系统级路由 =====================
@app.get("/", summary="服务信息", include_in_schema=False)
async def index() -> dict:
    """根路径：便于浏览器直接访问确认服务已启动"""
    return {
        "code": 0,
        "msg": "猫咪记忆 AI 后端运行中",
        "version": app.version,
        "docs": "/docs",
        "memories": count_memories(),
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """浏览器默认会请求 favicon，直接返回 204 避免日志里出现 404"""
    return Response(status_code=204)
