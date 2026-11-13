# -*- coding: utf-8 -*-
"""
图片工具（utils/image.py）测试
覆盖：图片校验、落盘命名、EXIF 拍摄时间解析
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi import HTTPException

from tests.helpers import make_png
from utils.image import extract_photo_time, save_image, validate_image


class TestValidateImage:
    """validate_image：图片合法性校验"""

    def test_valid_png_passes(self):
        """真实 PNG 通过校验，不抛异常"""
        validate_image(make_png())

    def test_fake_image_rejected(self):
        """伪装成 png 的随机字节 → 400"""
        with pytest.raises(HTTPException) as exc:
            validate_image(b"\x89PNG\r\n\x1a\n" + b"not-a-real-image" * 20)
        assert exc.value.status_code == 400
        assert "有效图片" in exc.value.detail

    def test_empty_bytes_rejected(self):
        """空字节 → 400"""
        with pytest.raises(HTTPException):
            validate_image(b"")


class TestSaveImage:
    """save_image：图片落盘"""

    def test_save_keeps_suffix(self, tmp_path):
        """合法后缀原样保留"""
        path = save_image(make_png(), "cat.png")
        assert path.suffix == ".png"
        assert path.exists()
        path.unlink()

    def test_save_unknown_suffix_falls_back_to_jpg(self, tmp_path):
        """非法/缺失后缀 → 兜底为 .jpg"""
        path = save_image(make_png(), "camera-file")
        assert path.suffix == ".jpg"
        path.unlink()

    def test_saved_content_intact(self):
        """落盘内容与原始字节一致"""
        contents = make_png()
        path = save_image(contents, "a.png")
        assert path.read_bytes() == contents
        path.unlink()


class TestExtractPhotoTime:
    """extract_photo_time：EXIF 拍摄时间"""

    def test_fallback_to_now_without_exif(self):
        """无 EXIF 的图片 → 回退当前时间（误差 1 分钟内），ISO 格式"""
        result = extract_photo_time(make_png())
        parsed = datetime.fromisoformat(result)
        assert abs(datetime.now() - parsed) < timedelta(minutes=1)

    def test_garbage_bytes_fallback(self):
        """垃圾字节解析失败 → 同样回退当前时间，不抛异常"""
        assert datetime.fromisoformat(extract_photo_time(b"garbage-bytes"))
