# -*- coding: utf-8 -*-
"""
配置模块
========
集中管理环境变量、路径与业务常量，所有模块从这里取配置，
后续新增配置项（如模型参数、限流阈值）只需修改本文件。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（backend/），所有相对路径以它为基准
BASE_DIR = Path(__file__).resolve().parent

# 加载 backend/.env（密钥类配置，禁止提交到 Git）
load_dotenv(BASE_DIR / ".env")

# ---------- 外部服务配置 ----------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db").strip()

# 相对路径统一以 backend/ 为基准，绝对路径直接使用
CHROMA_DIR = (BASE_DIR / CHROMA_PATH).resolve()

# ---------- 存储路径 ----------
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------- 业务常量 ----------
MODEL_NAME = "deepseek-chat"          # 对话模型
COLLECTION_NAME = "cat_memories"      # 记忆集合名
TOP_K = 3                             # RAG 每次召回的记忆条数
MAX_IMAGE_SIZE = 10 * 1024 * 1024     # 单张图片上限 10MB
ALLOWED_IMAGE_SUFFIX = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
