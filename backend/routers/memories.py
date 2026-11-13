# -*- coding: utf-8 -*-
"""
记忆接口
========
POST /upload-memory —— 上传猫咪图片 + 备注，图片落盘、note 写入向量库
TODO(二期)：GET /memories —— 记忆列表；习惯图谱统计接口
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import MAX_IMAGE_SIZE
from services.vector_store import add_memory
from utils.image import extract_photo_time, save_image, validate_image

router = APIRouter(tags=["记忆"])


@router.post("/upload-memory", summary="上传猫咪记忆（图片 + 备注）")
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
    image_path = save_image(contents, file.filename)

    # 2) 读取 EXIF 拍摄时间（缺失回退当前时间）
    photo_time = extract_photo_time(contents)

    # 3) 记忆写入向量库（增删改查统一由 services/vector_store.py 提供）
    memory_id = add_memory(note, image_path=str(image_path), photo_time=photo_time)

    return {
        "code": 0,
        "msg": "记忆保存成功",
        "data": {"id": memory_id, "note": note, "image_path": str(image_path), "photo_time": photo_time},
    }
