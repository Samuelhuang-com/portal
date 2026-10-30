"""
樓層底圖格式轉換：WebP／PNG／JPG／PDF → WebP（2026-10-30）

- 格式以檔頭判斷（不信任副檔名）。
- WebP：直接沿用（只解析尺寸，不需 Pillow）。
- PNG／JPG：Pillow 轉 WebP。
- PDF：PyMuPDF 把指定頁渲染成點陣圖（預設 150 DPI），再轉 WebP。
- 最長邊超過 MAX_SIDE 時等比縮小，避免超大底圖拖慢地圖。
- 缺少 Pillow／PyMuPDF 時，丟出 ConverterUnavailable（前端顯示明確訊息）。
"""
from __future__ import annotations

import io
from dataclasses import dataclass

MAX_SIDE = 8000                  # 輸出最長邊上限（px）
MAX_INPUT_PIXELS = 150_000_000   # 解碼炸彈防護
WEBP_QUALITY = 92


class ConverterUnavailable(RuntimeError):
    """伺服器缺少轉換所需套件。"""


class UnsupportedFormat(ValueError):
    """不是支援的檔案格式、或內容無法讀取。"""


@dataclass
class ConvertResult:
    webp:          bytes
    width:         int
    height:        int
    source_format: str    # webp / png / jpeg / pdf
    page:          int    # 實際使用的頁碼（非 PDF 為 1）
    page_count:    int    # 來源頁數（非 PDF 為 1）


def detect_format(data: bytes) -> str | None:
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:5] == b"%PDF-":
        return "pdf"
    return None


def webp_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X":
        w = int.from_bytes(data[24:27], "little") + 1
        h = int.from_bytes(data[27:30], "little") + 1
    elif chunk == b"VP8 ":
        if data[23:26] != b"\x9d\x01\x2a":
            return None
        w = int.from_bytes(data[26:28], "little") & 0x3FFF
        h = int.from_bytes(data[28:30], "little") & 0x3FFF
    elif chunk == b"VP8L":
        if data[20] != 0x2F:
            return None
        bits = int.from_bytes(data[21:25], "little")
        w = (bits & 0x3FFF) + 1
        h = ((bits >> 14) & 0x3FFF) + 1
    else:
        return None
    return (w, h) if w > 0 and h > 0 else None


def _pil_to_webp(img) -> tuple[bytes, int, int]:
    from PIL import Image
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if ("A" in img.getbands() or img.mode in ("P", "LA")) else "RGB")
    w, h = img.size
    longest = max(w, h)
    if longest > MAX_SIDE:
        scale = MAX_SIDE / longest
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=WEBP_QUALITY, method=6)
    return buf.getvalue(), img.size[0], img.size[1]


def _open_pil(data: bytes):
    try:
        from PIL import Image
    except ImportError as exc:
        raise ConverterUnavailable("伺服器未安裝 Pillow，無法轉換此格式") from exc
    Image.MAX_IMAGE_PIXELS = MAX_INPUT_PIXELS
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise UnsupportedFormat(f"無法讀取圖片：{exc}") from exc
    return img


def convert_to_webp(data: bytes, page: int = 1, dpi: int = 150) -> ConvertResult:
    fmt = detect_format(data)
    if fmt is None:
        raise UnsupportedFormat("不支援的檔案格式（僅接受 WebP、PNG、JPG、PDF）")

    if fmt == "webp":
        size = webp_size(data)
        if size is None:
            raise UnsupportedFormat("WebP 檔案無法解析")
        return ConvertResult(data, size[0], size[1], "webp", 1, 1)

    if fmt in ("png", "jpeg"):
        out, w, h = _pil_to_webp(_open_pil(data))
        return ConvertResult(out, w, h, fmt, 1, 1)

    # PDF：先渲染指定頁，再轉 WebP
    try:
        import pymupdf
    except ImportError as exc:
        raise ConverterUnavailable("伺服器未安裝 PyMuPDF，無法轉換 PDF") from exc
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise UnsupportedFormat(f"無法開啟 PDF：{exc}") from exc
    try:
        n = doc.page_count
        if n == 0:
            raise UnsupportedFormat("PDF 沒有任何頁面")
        if not (1 <= page <= n):
            raise UnsupportedFormat(f"頁碼超出範圍（此 PDF 共 {n} 頁）")
        png = doc[page - 1].get_pixmap(dpi=dpi, alpha=False).tobytes("png")
    finally:
        doc.close()
    out, w, h = _pil_to_webp(_open_pil(png))
    return ConvertResult(out, w, h, "pdf", page, n)
