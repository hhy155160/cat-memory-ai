# -*- coding: utf-8 -*-
"""
数据模型（Schemas）
====================
Pydantic 请求/响应模型。按 FastAPI 惯例与路由解耦，
二期新增接口时在本文件（或拆分子模块）补充对应模型。
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """问答请求体"""
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
