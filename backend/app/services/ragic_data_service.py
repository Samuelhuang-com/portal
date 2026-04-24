"""
統一 Ragic 資料存取層 (ragic_data_service.py)
=============================================
提供 main list + detail merge，解決：
  - 主表資料不完整（subform 欄位缺失）
  - 花費工時/完工時間等欄位在 detail 才完整
  - N+1 問題（asyncio.gather + Semaphore 批次抓取）
  - 圖片 URL 解析

快取策略（stale-while-revalidate）：
  - 主表快取 (TTL 30s)：快速，首次回應用
  - 完整合併快取 (TTL 120s)：完整，背景更新
  - 首次請求：立即回傳主表資料 + 觸發背景 detail fetch
  - 後續請求：命中完整快取，幾乎 0ms
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── 設定 ──────────────────────────────────────────────────────────────────────
MAIN_CACHE_TTL   = 30    # 主表快取 TTL（秒）
MERGED_CACHE_TTL = 120   # 完整合併快取 TTL（秒）
DETAIL_SEMAPHORE = 10    # 最大並發 detail 請求數
MAX_WORK_DAYS    = 365   # 合理工作天數上限（防止年份誤植 2026×24=48624hr）

# ── 圖片欄位名稱（Ragic sheet 實際欄名） ────────────────────────────────────
IMAGE_FIELD_LUQUN = "維修照上傳"   # 樂群：維修照上傳
IMAGE_FIELD_DAZHI = "上傳圖片"    # 大直：上傳圖片

# ── 內部快取 ─────────────────────────────────────────────────────────────────
_main_cache:   dict[str, tuple[dict, float]] = {}   # {key: (raw_dict, ts)}
_merged_cache: dict[str, tuple[list, float]] = {}   # {key: (merged_list, ts)}
_bg_tasks:     set[asyncio.Task] = set()            # 追蹤背景 task（防 GC）


# ═════════════════════════════════════════════════════════════════════════════
# 公開 API
# ═════════════════════════════════════════════════════════════════════════════

async def get_merged_records(
    adapter: RagicAdapter,
    cache_key: str,
    limit: int = 500,
    extra_params: dict | None = None,
) -> list[dict]:
    """
    核心方法：回傳完整合併資料（主表 + detail）。

    快取命中（merged，TTL 120s）→ 直接回傳
    快取命中（main，TTL 30s）→ 回傳主表資料，背景觸發 detail merge
    快取全部過期 → fetch 主表 → 回傳 → 背景觸發 detail merge
    """
    now = time.monotonic()

    # ── 1. 命中完整合併快取 ────────────────────────────────────────────────
    if cache_key in _merged_cache:
        records, ts = _merged_cache[cache_key]
        if now - ts < MERGED_CACHE_TTL:
            logger.debug(f"[RagicData] merged cache hit: {cache_key}")
            return records
        # stale：回傳舊資料，同時觸發背景更新
        raw_data = _main_cache.get(cache_key, (None, 0))[0]
        if raw_data is not None:
            _trigger_bg_merge(adapter, cache_key, raw_data)
        return records  # 回傳 stale 資料，不讓用戶等待

    # ── 2. 命中主表快取（無完整快取）────────────────────────────────────────
    if cache_key in _main_cache:
        raw_data, ts = _main_cache[cache_key]
        if now - ts < MAIN_CACHE_TTL:
            logger.debug(f"[RagicData] main cache hit, bg merge: {cache_key}")
            _trigger_bg_merge(adapter, cache_key, raw_data)
            return _raw_to_list(raw_data)

    # ── 3. 全部過期：重新 fetch 主表 ─────────────────────────────────────────
    logger.info(f"[RagicData] fetching main list: {cache_key}")
    try:
        raw_data = await adapter.fetch_all(limit=limit, extra_params=extra_params)
    except Exception as exc:
        logger.error(f"[RagicData] main list fetch failed ({cache_key}): {exc}")
        # 回傳 stale merged（如果有）
        if cache_key in _merged_cache:
            return _merged_cache[cache_key][0]
        return []

    _main_cache[cache_key] = (raw_data, time.monotonic())
    _trigger_bg_merge(adapter, cache_key, raw_data)
    return _raw_to_list(raw_data)


def invalidate(cache_key: str) -> None:
    """清除指定 cache（sync 後呼叫）"""
    _main_cache.pop(cache_key, None)
    _merged_cache.pop(cache_key, None)
    logger.info(f"[RagicData] cache invalidated: {cache_key}")


def invalidate_all() -> None:
    _main_cache.clear()
    _merged_cache.clear()
    logger.info("[RagicData] all caches invalidated")


# ═════════════════════════════════════════════════════════════════════════════
# 圖片解析
# ═════════════════════════════════════════════════════════════════════════════

def _abs_url(url: str, server: str = "ap12.ragic.com") -> str:
    """將相對/協議相對 URL 補全為 https 絕對 URL"""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return f"https://{server}{url}"
    if url.startswith("http"):
        return url
    # 相對路徑
    return f"https://{server}/{url}"


def parse_images(raw_value, server="ap12.ragic.com", account="soutlet001"):
    """
    解析 Ragic 附件/圖片欄位，回傳 [{url, filename}, ...]。

    Ragic 附件欄位的值可能是：
      1. 純檔名字串（最常見）→ 用 file.jsp API 組成下載 URL
      2. HTML <a href='//...'><img src='//...'></a>
      3. 直接 URL 字串

    Ragic 檔案下載 API：
      https://{server}/sims/file.jsp?a={account}&f={encoded_filename}
    """
    import re
    from urllib.parse import quote

    if not raw_value:
        return []

    if isinstance(raw_value, list):
        result = []
        for item in raw_value:
            if isinstance(item, dict):
                url = item.get("url") or item.get("src") or item.get("href") or ""
                fname = item.get("name") or item.get("filename") or ""
                if url:
                    result.append({"url": _abs_url(url, server), "filename": fname})
                elif fname:
                    dl_url = f"https://{server}/sims/file.jsp?a={account}&f={quote(fname)}"
                    result.append({"url": dl_url, "filename": fname})
            elif isinstance(item, str) and (item.startswith("http") or item.startswith("//")):
                result.append({"url": _abs_url(item, server), "filename": ""})
            elif isinstance(item, str) and item.strip():
                fname = item.strip()
                dl_url = f"https://{server}/sims/file.jsp?a={account}&f={quote(fname)}"
                result.append({"url": dl_url, "filename": fname})
        return result

    if not isinstance(raw_value, str):
        return []
    raw_str = raw_value.strip()
    if not raw_str:
        return []

    result = []
    covered = []

    # ── <a href="...">（可包含 <img>）→ 優先用 href ─────────────────────────
    for m in re.finditer(r'<a\b[^>]+\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         raw_str, re.IGNORECASE | re.DOTALL):
        href = _abs_url(m.group(1), server)
        inner = m.group(2)
        covered.append(m.span())
        filename = re.sub(r'<[^>]+>', '', inner).strip()
        result.append({"url": href, "filename": filename})

    # ── 獨立 <img src="..."> ─────────────────────────────────────────────────
    for m in re.finditer(r'<img\b[^>]+\bsrc=["\']([^"\']+)["\']', raw_str, re.IGNORECASE):
        pos = m.start()
        if any(s <= pos < e for s, e in covered):
            continue
        url = _abs_url(m.group(1), server)
        if not any(r["url"] == url for r in result):
            result.append({"url": url, "filename": ""})

    # ── 已有 HTML 結果 → 直接回傳 ───────────────────────────────────────────
    if result:
        return result

    # ── 純 URL ──────────────────────────────────────────────────────────────
    if raw_str.startswith("http") or raw_str.startswith("//"):
        return [{"url": _abs_url(raw_str, server), "filename": ""}]

    # ── 純檔名（最常見的 Ragic 附件格式）────────────────────────────────────
    # 多個檔名以換行或逗號分隔
    filenames = [f.strip() for f in re.split(r'[\n,;]', raw_str) if f.strip()]
    for fname in filenames:
        # 跳過明顯的 HTML 殘留
        if '<' in fname or '>' in fname:
            continue
        dl_url = f"https://{server}/sims/file.jsp?a={account}&f={quote(fname)}"
        result.append({"url": dl_url, "filename": fname})

    return result



# ═════════════════════════════════════════════════════════════════════════════
# 工時合理性驗證
# ═════════════════════════════════════════════════════════════════════════════

def safe_work_days_to_hours(days_raw: Any) -> float:
    """
    將「工作天數」轉為小時，並過濾異常值（如誤植年份 2026）。
    MAX_WORK_DAYS = 365；超過視為無效，回傳 0.0。
    """
    try:
        days = float(str(days_raw).strip().replace(",", ""))
    except (ValueError, TypeError):
        return 0.0
    if days <= 0 or days > MAX_WORK_DAYS:
        return 0.0
    return round(days * 24, 2)


# ═════════════════════════════════════════════════════════════════════════════
# 內部工具
# ═════════════════════════════════════════════════════════════════════════════

def _raw_to_list(raw_data: dict) -> list[dict]:
    """將 fetch_all 回傳的 {id: row} 轉為 [{_ragic_id, ...fields}, ...]"""
    result = []
    for rid, row in raw_data.items():
        record = dict(row)
        record["_ragic_id"] = str(rid)
        result.append(record)
    return result


async def _fetch_detail(
    adapter: RagicAdapter,
    record_id: str,
    semaphore: asyncio.Semaphore,
) -> dict:
    """取得單筆 detail（帶 semaphore 限流）"""
    async with semaphore:
        try:
            resp = await adapter.fetch_one(record_id)
            # Ragic detail 回傳格式：{record_id: {...}} 或直接 {...}
            if isinstance(resp, dict):
                inner = resp.get(record_id) or resp.get(str(record_id))
                data = inner if isinstance(inner, dict) else {
                    k: v for k, v in resp.items() if not str(k).startswith("_")
                }
                # 記錄圖片欄位的實際值（方便排查格式問題）
                for img_key in ("上傳圖片", "維修照上傳", "維修照", "圖片"):
                    v = data.get(img_key)
                    if v:
                        logger.debug(f"[RagicData] detail {record_id} {img_key!r}={repr(v)[:120]}")
                return data
        except Exception as exc:
            logger.warning(f"[RagicData] detail {record_id} failed: {exc}")
        return {}


def _merge(main: dict, detail: dict) -> dict:
    """合併：detail 有非空值的欄位優先覆蓋 main"""
    merged = dict(main)
    for k, v in detail.items():
        if v not in (None, "", [], {}):
            merged[k] = v
    return merged


async def _do_merge(
    adapter: RagicAdapter,
    cache_key: str,
    raw_data: dict,
) -> None:
    """背景任務：批次抓 detail，merge 後寫入 merged_cache"""
    logger.info(f"[RagicData] bg merge start: {cache_key} ({len(raw_data)} records)")
    semaphore = asyncio.Semaphore(DETAIL_SEMAPHORE)

    async def task(rid: str, row: dict) -> dict:
        detail = await _fetch_detail(adapter, rid, semaphore)
        merged = _merge(row, detail)
        merged["_ragic_id"] = str(rid)
        return merged

    tasks = [task(rid, row) for rid, row in raw_data.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged_list: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning(f"[RagicData] bg merge item failed: {r}")
        else:
            merged_list.append(r)

    _merged_cache[cache_key] = (merged_list, time.monotonic())
    logger.info(f"[RagicData] bg merge done: {cache_key} ({len(merged_list)} records)")


def _trigger_bg_merge(
    adapter: RagicAdapter,
    cache_key: str,
    raw_data: dict,
) -> None:
    """
    觸發背景 detail fetch（stale-while-revalidate）。
    使用 asyncio.create_task，不阻塞當前請求。
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = loop.create_task(_do_merge(adapter, cache_key, raw_data))
            _bg_tasks.add(task)
            task.add_done_callback(_bg_tasks.discard)
    except RuntimeError:
        pass  # no running loop，略過背景任務
