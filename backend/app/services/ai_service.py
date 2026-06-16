"""
飯店營運 AI 助理 — 工單查詢服務
使用 Anthropic Claude tool calling 實作自然語言工單查詢

設計原則：
  - Tool Calling（非 NL2SQL）：Claude 只能呼叫預定義工具，無法執行任意 SQL
  - Grounding：System Prompt 明確禁止 Claude 編造資料
  - 查詢量保護：單次最多回傳 AI_QUERY_MAX_ROWS 筆（預設 50）
  - 權限隔離：依用戶 permissions 限制可查詢的地點
  - 對話記憶：攜帶最近 10 則訊息歷史
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Claude Tool 定義 ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "query_repair_cases",
        "description": (
            "查詢工務維修工單清單。可依地點、樓層、狀態、年月、"
            "負責單位、關鍵字、最少未結天數等條件篩選。"
            "支援飯店工務部和商場工務報修兩個資料來源。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "enum": ["飯店", "商場", "全部"],
                    "description": "工單來源地點（飯店=飯店工務部，商場=商場工務）",
                },
                "floor": {
                    "type": "string",
                    "description": "樓層，例如 'B1', 'B2', '1F', '2F'；留空不限",
                },
                "status": {
                    "type": "string",
                    "enum": ["已結案", "未結案", "全部"],
                    "description": "工單結案狀態",
                },
                "year": {
                    "type": "integer",
                    "description": "西元年，例如 2026；留空不限",
                },
                "month": {
                    "type": "integer",
                    "description": "月份 1–12；留空不限",
                },
                "responsible_unit": {
                    "type": "string",
                    "description": "負責單位名稱（部分比對）；留空不限",
                },
                "keyword": {
                    "type": "string",
                    "description": "標題關鍵字搜尋；留空不限",
                },
                "min_close_days": {
                    "type": "number",
                    "description": "最少結案天數，用於查詢「超過 N 天仍未結案」的工單",
                },
            },
            "required": ["location", "status"],
        },
    },
    {
        "name": "get_repair_summary",
        "description": (
            "取得工務工單統計摘要，包含各狀態數量、平均結案天數、費用統計。"
            "適合回答「上個月一共有幾件」「平均結案天數是多少」等聚合型問題。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "enum": ["飯店", "商場", "全部"],
                    "description": "工單來源地點（飯店=飯店工務部，商場=商場工務）",
                },
                "year": {
                    "type": "integer",
                    "description": "西元年；留空不限",
                },
                "month": {
                    "type": "integer",
                    "description": "月份 1–12；留空不限",
                },
            },
            "required": ["location"],
        },
    },
]

# ── 工具執行函式 ──────────────────────────────────────────────────────────────

def _apply_filters(q, model, params: dict):
    """套用共用篩選條件到 SQLAlchemy query"""
    floor = params.get("floor", "")
    year = params.get("year")
    month = params.get("month")
    responsible_unit = params.get("responsible_unit", "")
    keyword = params.get("keyword", "")
    status_filter = params.get("status", "全部")
    min_close_days = params.get("min_close_days")

    if floor:
        q = q.filter(
            model.floor_normalized.contains(floor) | model.floor.contains(floor)
        )
    if year:
        q = q.filter(model.year == year)
    if month:
        q = q.filter(model.month == month)
    if responsible_unit:
        q = q.filter(model.responsible_unit.contains(responsible_unit))
    if keyword:
        q = q.filter(model.title.contains(keyword))
    if status_filter == "已結案":
        q = q.filter(model.is_completed == True)  # noqa: E712
    elif status_filter == "未結案":
        q = q.filter(model.is_completed == False)  # noqa: E712
    if min_close_days is not None:
        # 對未結案工單，用「距今天數」估算；對已結案，用 close_days
        q = q.filter(model.close_days >= min_close_days)
    return q


def _row_to_dict(r, location: str) -> dict:
    """ORM 物件 → 可序列化 dict"""
    return {
        "location": location,
        "case_no": r.case_no or "",
        "title": (r.title or "")[:60],
        "floor": r.floor_normalized or r.floor or "",
        "status": "已結案" if r.is_completed else "未結案",
        "occurred_at": r.occurred_at.strftime("%Y-%m-%d") if r.occurred_at else "",
        "responsible_unit": r.responsible_unit or "",
        "close_days": r.close_days,
        "total_fee": float(r.total_fee or 0),
    }


def _execute_query_repair_cases(
    db: Session, params: dict, allowed_locations: list[str], max_rows: int
) -> dict:
    """tool: query_repair_cases 的執行邏輯"""
    from app.models.dazhi_repair import DazhiRepairCase
    from app.models.luqun_repair import LuqunRepairCase

    location = params.get("location", "全部")
    results: list[dict] = []
    total_count = 0

    # 飯店工務部
    if location in ("飯店", "全部") and "飯店" in allowed_locations:
        q = db.query(DazhiRepairCase)
        q = _apply_filters(q, DazhiRepairCase, params)
        cnt = q.count()
        total_count += cnt
        rows = (
            q.order_by(DazhiRepairCase.occurred_at.desc())
            .limit(max_rows - len(results))
            .all()
        )
        results.extend(_row_to_dict(r, "飯店") for r in rows)

    # 商場工務報修（luqun）
    if location in ("商場", "全部") and "商場" in allowed_locations:
        q = db.query(LuqunRepairCase)
        q = _apply_filters(q, LuqunRepairCase, params)
        cnt = q.count()
        total_count += cnt
        remaining = max_rows - len(results)
        if remaining > 0:
            rows = (
                q.order_by(LuqunRepairCase.occurred_at.desc())
                .limit(remaining)
                .all()
            )
            results.extend(_row_to_dict(r, "商場") for r in rows)

    return {
        "total_count": total_count,
        "displayed_count": len(results),
        "truncated": total_count > max_rows,
        "cases": results,
    }


def _execute_get_repair_summary(
    db: Session, params: dict, allowed_locations: list[str]
) -> dict:
    """tool: get_repair_summary 的執行邏輯"""
    from app.models.dazhi_repair import DazhiRepairCase
    from app.models.luqun_repair import LuqunRepairCase

    location = params.get("location", "全部")
    year = params.get("year")
    month = params.get("month")
    summary: dict[str, dict] = {}

    def _stats(model, loc_name: str) -> dict:
        q = db.query(model)
        if year:
            q = q.filter(model.year == year)
        if month:
            q = q.filter(model.month == month)
        total = q.count()
        completed = q.filter(model.is_completed == True).count()  # noqa: E712
        pending = total - completed

        avg_q = db.query(func.avg(model.close_days)).filter(
            model.is_completed == True,  # noqa: E712
            model.close_days.isnot(None),
        )
        if year:
            avg_q = avg_q.filter(model.year == year)
        if month:
            avg_q = avg_q.filter(model.month == month)
        avg_days = avg_q.scalar()

        fee_q = db.query(func.sum(model.total_fee))
        if year:
            fee_q = fee_q.filter(model.year == year)
        if month:
            fee_q = fee_q.filter(model.month == month)
        total_fee = fee_q.scalar() or 0

        return {
            "location": loc_name,
            "total": total,
            "completed": completed,
            "pending": pending,
            "avg_close_days": round(float(avg_days), 1) if avg_days else None,
            "total_fee": float(total_fee),
        }

    if location in ("飯店", "全部") and "飯店" in allowed_locations:
        summary["飯店"] = _stats(DazhiRepairCase, "飯店")
    if location in ("商場", "全部") and "商場" in allowed_locations:
        summary["商場"] = _stats(LuqunRepairCase, "商場")

    return summary


# ── 主要呼叫入口 ──────────────────────────────────────────────────────────────

def run_ai_query(
    question: str,
    messages: list[dict],
    db: Session,
    allowed_locations: list[str],
) -> dict:
    """
    自然語言工單查詢主函式

    Args:
        question: 用戶當前問題
        messages: 歷史對話 [{"role": "user"|"assistant", "content": str}]
        db: SQLAlchemy Session
        allowed_locations: 用戶有權限查詢的地點 e.g. ["大直", "商場"]

    Returns:
        {
            "answer": str,          # Claude 自然語言回答
            "has_table": bool,      # 是否有表格資料
            "table_data": list,     # 表格資料列
            "total_count": int|None # 符合條件總筆數
        }
    """
    import anthropic

    max_rows: int = getattr(settings, "AI_QUERY_MAX_ROWS", 50)
    model: str = getattr(settings, "ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_prompt = f"""你是飯店集團工務部的 AI 查詢助理，協助使用者用自然語言查詢工務維修工單資料。

【強制規則】
1. 你只能根據工具回傳的真實資料作答，絕對禁止自行捏造任何工單編號、數量或內容
2. 若查詢結果為空，說「查無符合條件的工單記錄」，不要猜測或推斷
3. 結果超過 {max_rows} 筆時，工具會自動截斷，請在回答中說明「共 X 筆，顯示前 {max_rows} 筆」
4. 使用者在本次登入僅能查詢以下地點：{', '.join(allowed_locations) if allowed_locations else '（無任何工單查詢權限）'}
5. 若使用者詢問無權限的地點，說明「您目前無該地點的查詢權限」
6. 一律使用繁體中文回答；數量加「件」、天數加「天」、金額前加「NT$」並加千分位逗號
7. 統計摘要問題（幾件、平均幾天）優先使用 get_repair_summary 工具，效率更高

今天日期：{datetime.now().strftime('%Y 年 %m 月 %d 日')}
"""

    # 組裝 API messages（保留最近 10 則歷史）
    api_messages: list[dict] = []
    for msg in messages[-10:]:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    api_messages.append({"role": "user", "content": question})

    # ── 第一次 API 呼叫 ────────────────────────────────────────────────────────
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        tools=TOOLS,
        messages=api_messages,
    )

    table_data: list[dict] = []
    total_count: Optional[int] = None
    has_table = False

    # ── Tool calling 迴圈 ──────────────────────────────────────────────────────
    iteration = 0
    while response.stop_reason == "tool_use" and iteration < 5:
        iteration += 1
        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            logger.info("AI tool call: %s %s", block.name, block.input)
            try:
                if block.name == "query_repair_cases":
                    result = _execute_query_repair_cases(
                        db, block.input, allowed_locations, max_rows
                    )
                    if result.get("cases"):
                        has_table = True
                        table_data = result["cases"]
                        total_count = result["total_count"]
                elif block.name == "get_repair_summary":
                    result = _execute_get_repair_summary(
                        db, block.input, allowed_locations
                    )
                else:
                    result = {"error": f"未知工具：{block.name}"}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
            except Exception as exc:
                logger.error("Tool %s 執行失敗: %s", block.name, exc, exc_info=True)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"error": str(exc)}, ensure_ascii=False),
                    "is_error": True,
                })

        # 繼續對話，帶入 tool results
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            tools=TOOLS,
            messages=api_messages + [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": tool_results},
            ],
        )

    # ── 取出最終文字回答 ──────────────────────────────────────────────────────
    answer = ""
    for block in response.content:
        if hasattr(block, "text"):
            answer = block.text
            break

    return {
        "answer": answer,
        "has_table": has_table,
        "table_data": table_data,
        "total_count": total_count,
    }
