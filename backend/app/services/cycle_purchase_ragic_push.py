"""
週期採購 —「匯總請購單」拋轉 Ragic 的推送客戶端

═══════════════════════════════════════════════════════════════════════════
2026-09-15：已從 stub 改成真正呼叫 Ragic API
═══════════════════════════════════════════════════════════════════════════

目標表單（2026-09-15 Samuel 裁示）：
    https://ap12.ragic.com/soutlet001/community-management-department/57
    表單名稱「週採採購單」，由 Samuel 從管理部「採購單」(sheet 23) 複製出來後，
    在設計模式調整過四個地方：
      1. 採購編號自動編號格式 樂管採{...} → **樂管週採{0,number,00000}**
         （不改會跟 sheet 23 既有的 樂管採00001~00079 撞號）
      2. 「*請購部門」改名為「期別」、選單改自由輸入文字
         （匯總單一張橫跨多部門，主表填不出單一部門；部門別改放子表）
      3. 「*到貨日期」取消必填（Portal 的彙整單沒有到貨日資料，留空給採購後補）
      4. 新增主表 公司別／週期名稱／拋轉批次號／拋轉時間／Portal備註，
         子表新增 料號／部門／Portal彙整列ID

⚠️ **四個金額欄位是 Ragic 公式，Portal 一律不送**（2026-09-15 Samuel 裁示，
   與 SPEC_匯總請購單_Ragic表單.md 第 5 節寫的「由 Portal 帶入」相反，以這裡為準）：
     子表「擬定廠商金額」= C5*F5（數量 × 單價）
     主表「小計」        = G5（子表金額加總）
     主表「營業稅」      = F10*0.05（未稅外加 5%）
     主表「總計」        = F10+F11
   自己算容易因為四捨五入跟 Ragic 差一元，而且之後有人在 Ragic 手改數量時，
   Portal 帶進去的死值不會跟著變，反而會變成錯的。
   同理「項次」是 $SEQ 自動序號、「採購編號」是自動編號，兩個都不送。

   ⚠️⚠️ **但是：Ragic 的公式在 API 寫入時預設「不會執行」**（2026-09-15 實測，
   樂管週採00001 寫進去之後 小計／營業稅／總計／子表金額／項次 全部是空字串）。
   必須在 query string 帶 **`doFormula=true`** 才會算，`doDefaultValue=true` 則是
   讓「項次」的 $SEQ 與其他預設值生效。兩個參數缺一，單子就會是一張沒有金額的
   空殼，而且 API 回的是 status=SUCCESS，**不會有任何錯誤**——這是最容易漏掉、
   又最難發現的坑。實測（樂管週採00002）帶上之後：
       小計 2060、營業稅 103、總計 2163、子表金額 1770/290、項次 1/2　全部正確。

⚠️ **子表列的順序與 key 的大小相反**：Ragic 是由「負數 key 的絕對值大的先排」，
   送 -1=A、-2=B 進去，出來會是 項次1=B、項次2=A。所以 build_payload() 是用
   `-(總列數 - index)` 產生 key，讓第一列拿到最大的絕對值。純排版問題，不影響金額。

⚠️ **子表「擬定廠商單價」在 Ragic 端是必填**。Ragic API 是**整筆退**不是跳過該列，
   所以沒有單價的彙整列絕對不能送進來——呼叫端（cycle_purchase_summary_service）
   必須先把「沒有廠商」與「有廠商但沒單價」的列都濾掉並列進未拋轉清單。

欄位代號全部放在 app/core/config.py 的 RAGIC_CP_* 設定值，不寫死在這裡；
Ragic 端若重建表單，只要改 .env／config 預設值即可，不用動程式。
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class RagicPushError(Exception):
    """推送到 Ragic 失敗時拋出，由 service 層轉成 SummaryServiceError 回 422 給前端。"""
    pass


# ───────────────────────────────────────────────────────────────────────────
# 小工具
# ───────────────────────────────────────────────────────────────────────────

def _sheet_url() -> str:
    return (
        f"https://{settings.RAGIC_CP_SUMMARY_SERVER_URL}"
        f"/{settings.RAGIC_CP_SUMMARY_ACCOUNT}"
        f"/{settings.RAGIC_CP_SUMMARY_PATH}"
    )


def _num(value: Any) -> str:
    """數字欄位轉字串。None／空值一律回空字串（Ragic 收到空字串會存成空）。

    ⚠️ 不要用 str(Decimal)，Decimal('120.0000') 會變成 '120.0000'，
    Ragic 的數字欄位收得下但顯示會帶一串零。
    """
    if value is None or value == "":
        return ""
    if isinstance(value, Decimal):
        # 去掉尾端多餘的 0，但保留必要的小數位
        normalized = value.normalize()
        # Decimal('1E+3').normalize() 會變成科學記號，用 quantize 還原
        if normalized == normalized.to_integral_value():
            return str(normalized.quantize(Decimal(1)))
        return format(normalized, "f")
    return str(value)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


# ───────────────────────────────────────────────────────────────────────────
# 主要函式
# ───────────────────────────────────────────────────────────────────────────

def build_payload(document: dict[str, Any]) -> dict[str, Any]:
    """把一份「單一廠商」的匯總請購單文件轉成 Ragic API 的 JSON payload。

    抽成獨立函式是為了可以在沒有網路的情況下單獨測試欄位對應
    （見 backend/tests/test_cycle_purchase_ragic_push.py）。
    """
    s = settings
    payload: dict[str, Any] = {
        s.RAGIC_CP_F_PERIOD:    _text(document.get("period_label")),
        s.RAGIC_CP_F_COMPANY:   _text(document.get("company")),
        s.RAGIC_CP_F_CYCLE:     _text(document.get("cycle_name")),
        s.RAGIC_CP_F_VENDOR:    _text(document.get("vendor_name")),
        s.RAGIC_CP_F_PURPOSE:   _text(document.get("purpose")),
        s.RAGIC_CP_F_APPLICANT: _text(document.get("applicant") or s.RAGIC_CP_SUMMARY_APPLICANT),
        s.RAGIC_CP_F_BATCH:     _text(document.get("batch_no")),
        s.RAGIC_CP_F_PUSHED_AT: _text(document.get("pushed_at")),
        s.RAGIC_CP_F_NOTE:      _text(document.get("portal_note")),
        # 到貨日期（RAGIC_CP_F_ARRIVAL）刻意不送 —— Portal 沒有這個資料，
        # Ragic 端已改成非必填，留給採購跟廠商談完之後人工填。
    }

    lines = document.get("lines", [])
    total = len(lines)
    rows: dict[str, dict[str, str]] = {}
    for idx, line in enumerate(lines):
        # ⚠️ key 用 -(總列數 - index)，讓第一列拿到絕對值最大的負號。
        #    Ragic 是「絕對值大的排前面」，直接用 -1、-2… 會讓明細整個反序。
        rows[f"-{total - idx}"] = {
            s.RAGIC_CP_SF_ITEM_CODE:  _text(line.get("item_code")),
            s.RAGIC_CP_SF_ITEM_NAME:  _text(line.get("item_name")),
            s.RAGIC_CP_SF_DEPT:       _text(line.get("department_name")),
            s.RAGIC_CP_SF_QTY:        _num(line.get("qty")),
            s.RAGIC_CP_SF_UNIT:       _text(line.get("unit")),
            s.RAGIC_CP_SF_NOTE:       _text(line.get("note")),
            s.RAGIC_CP_SF_PRICE:      _num(line.get("unit_price")),
            s.RAGIC_CP_SF_SUMMARY_ID: _text(line.get("summary_id")),
            # 擬定廠商金額（C5*F5）與 項次（$SEQ）是 Ragic 自己算的，不送
        }
    payload[f"_subtable_{settings.RAGIC_CP_SUBTABLE}"] = rows
    return payload


def push_summary_document(document: dict[str, Any]) -> dict[str, Any]:
    """把**一家廠商**的匯總請購單推送到 Ragic，回傳這一張單的識別資訊。

    Args:
        document: 由 cycle_purchase_summary_service._build_vendor_documents() 組好的
            單一廠商文件：
            {
                "batch_no": "CPSUM-202609-春大直-0001",
                "cycle_name": "工程備品週採",
                "period_label": "2026-09",
                "company": "春大直",
                "vendor_id": 3,
                "vendor_name": "茂忠",
                "purpose": "2026-09 工程備品週採 匯總請購（春大直）",
                "applicant": "Samuel",
                "pushed_at": "2026/09/15 21:30:00",
                "portal_note": "由 Portal 週期採購模組自動產生，明細請勿手動修改",
                "lines": [
                    {"item_code": "CH-E0301001", "item_name": "…", "department_name": "工務部",
                     "qty": 1, "unit": "個", "note": None,
                     "unit_price": Decimal("290.0000"), "summary_id": 137},
                    …
                ],
            }

    Returns:
        {"ragic_record_id": str, "ragic_no": str, "is_stub": bool, "message": str}
        ragic_record_id 是 Ragic 的內部 _ragicId；ragic_no 是表單上的「採購編號」
        （樂管週採00001），對帳時人看的是後者。

    Raises:
        RagicPushError: 連線失敗、HTTP 非 2xx、或 Ragic 回傳 status != SUCCESS。
    """
    batch_no = document.get("batch_no", "UNKNOWN")
    vendor_name = document.get("vendor_name") or "—"

    # 關閉開關：Ragic 端維護中或測試環境不想真的寫入時，設 RAGIC_CP_SUMMARY_ENABLED=false
    # 就會退回舊的 stub 行為（Portal 端狀態照常更新，但不碰 Ragic）。
    if not settings.RAGIC_CP_SUMMARY_ENABLED:
        logger.warning(
            "[cycle_purchase_ragic_push] RAGIC_CP_SUMMARY_ENABLED=false，"
            "batch_no=%s vendor=%s 改走 stub，未真正寫入 Ragic", batch_no, vendor_name,
        )
        return {
            "ragic_record_id": f"STUB-{batch_no}",
            "ragic_no": "",
            "is_stub": True,
            "message": "RAGIC_CP_SUMMARY_ENABLED=false，這是模擬結果，沒有真正寫入 Ragic",
        }

    payload = build_payload(document)
    url = _sheet_url()

    try:
        resp = httpx.post(
            url,
            headers={"Authorization": f"Basic {settings.RAGIC_API_KEY}"},
            # ⚠️ doFormula / doDefaultValue 兩個都不能省，見檔頭說明：
            #    少了它們 Ragic 照樣回 SUCCESS，但小計／營業稅／總計／子表金額／
            #    項次會全部是空的，變成一張沒有金額的空殼單。
            params={"api": "", "v": "3", "doFormula": "true", "doDefaultValue": "true"},
            json=payload,
            timeout=settings.RAGIC_CP_SUMMARY_TIMEOUT,
            verify=settings.RAGIC_VERIFY_SSL,
        )
    except Exception as exc:  # noqa: BLE001 — httpx 的例外種類很多，一律轉成自己的錯誤
        logger.error(
            "[cycle_purchase_ragic_push] 連線 Ragic 失敗：batch_no=%s vendor=%s url=%s err=%s",
            batch_no, vendor_name, url, exc,
        )
        raise RagicPushError(f"連線 Ragic 失敗（{vendor_name}）：{exc}") from exc

    if resp.status_code >= 400:
        logger.error(
            "[cycle_purchase_ragic_push] Ragic 回 HTTP %s：batch_no=%s vendor=%s body=%s",
            resp.status_code, batch_no, vendor_name, resp.text[:500],
        )
        raise RagicPushError(
            f"Ragic 回 HTTP {resp.status_code}（{vendor_name}）：{resp.text[:300]}"
        )

    try:
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        # Ragic 權限不足時會回 HTML 登入頁而不是 JSON，這裡要講清楚，
        # 否則錯誤訊息只會是一句 JSONDecodeError，看不出是權限問題。
        logger.error(
            "[cycle_purchase_ragic_push] Ragic 回傳不是 JSON：batch_no=%s body=%s",
            batch_no, resp.text[:500],
        )
        raise RagicPushError(
            f"Ragic 回傳的不是 JSON（{vendor_name}），"
            f"最常見原因是這把 API Key 對該表單沒有新增權限：{resp.text[:200]}"
        ) from exc

    status = str(data.get("status", "")).upper()
    if status != "SUCCESS":
        msg = data.get("msg") or data.get("message") or str(data)[:300]
        logger.error(
            "[cycle_purchase_ragic_push] Ragic 回報失敗：batch_no=%s vendor=%s resp=%s",
            batch_no, vendor_name, str(data)[:500],
        )
        raise RagicPushError(f"Ragic 拒絕寫入（{vendor_name}）：{msg}")

    record = data.get("data") or {}
    # ⚠️ 不可以寫 `data.get("ragicId") or record.get("_ragicId") or ""`
    #    ——Ragic 的第一筆記錄 ragicId 就是 **0**，0 在 Python 是 falsy，
    #    整串 or 會一路掉到 ""，第一張單的記錄 ID 就這樣不見了。
    #    （2026-09-15 用 樂管週採00001 實測到，ragicId 真的回 0。）
    raw_id = data.get("ragicId")
    if raw_id is None:
        raw_id = record.get("_ragicId")
    ragic_record_id = "" if raw_id is None else str(raw_id)

    ragic_no = _text(record.get(settings.RAGIC_CP_F_DOC_NO) or record.get("採購編號"))

    # 空殼防呆：帶了 doFormula 還是算不出小計，代表 Ragic 端的公式被動過或
    # 參數被擋掉。這種單在 Ragic 看起來是正常的一張單，只是金額全空，
    # 不主動檢查的話沒有人會發現。
    subtotal = _text(record.get(settings.RAGIC_CP_F_SUBTOTAL))
    if not subtotal:
        logger.warning(
            "[cycle_purchase_ragic_push] ⚠️ %s 寫入成功但小計是空的——"
            "請確認 Ragic 端「小計/營業稅/總計」的公式還在，以及 doFormula 參數有生效",
            ragic_no or ragic_record_id,
        )

    logger.info(
        "[cycle_purchase_ragic_push] 已寫入 Ragic：batch_no=%s vendor=%s ragicId=%s 單號=%s 明細=%d 列",
        batch_no, vendor_name, ragic_record_id, ragic_no or "—", len(document.get("lines", [])),
    )

    return {
        "ragic_record_id": ragic_record_id,
        "ragic_no": ragic_no,
        "is_stub": False,
        "message": f"已寫入 Ragic 週採匯總請購單 {ragic_no or ragic_record_id}",
    }
