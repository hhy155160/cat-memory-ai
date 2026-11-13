# -*- coding: utf-8 -*-
"""
图片工具
========
图片校验、落盘与 EXIF 解析，供上传接口使用。
TODO(二期)：接入视觉模型后，可在此追加"从图片生成描述"的工具函数。
"""

import io
import uuid
from datetime import datetime
from pathlib import Path

import exifread
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from config import ALLOWED_IMAGE_SUFFIX, UPLOAD_DIR


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


def extract_photo_time(contents: bytes) -> str:
    """
    读取图片 EXIF 中的原始拍摄时间（DateTimeOriginal）。
    读取失败或缺失时，回退为当前时间。统一返回 ISO 格式字符串。
    """
    try:
        tags = exifread.process_file(io.BytesIO(contents), details=False)
        raw = tags.get("EXIF DateTimeOriginal")
        if raw:
            # EXIF 时间格式如 "2025:01:01 12:00:00"，转为 ISO 格式
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").isoformat(timespec="seconds")
    except Exception:
        pass  # EXIF 解析失败不影响主流程，回退当前时间
    return datetime.now().isoformat(timespec="seconds")
