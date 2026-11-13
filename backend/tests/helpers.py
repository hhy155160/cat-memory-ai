# -*- coding: utf-8 -*-
"""测试公共工具：与 conftest（夹具）分开，便于测试模块以包路径导入"""

from io import BytesIO

from PIL import Image


def make_png(width: int = 60, height: int = 60, color=(240, 230, 210)) -> bytes:
    """生成一张真实有效的 PNG 图片字节流（供上传/校验测试用）"""
    buf = BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()
