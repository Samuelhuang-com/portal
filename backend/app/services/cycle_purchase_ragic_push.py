"""
週期採購 —「匯總請購單」拋轉 Ragic 的推送客戶端

═══════════════════════════════════════════════════════════════════════════
⚠️ 現況（2026-07-16）：這是 STUB（假實作），還沒有真正打 Ragic API
═══════════════════════════════════════════════════════════════════════════

背景（見 0715 會議記錄 + docs/週期採購_Portal規劃評估_v1.1.md）：
  - 週期採購的料號主檔／週期設定／請購單／彙整單是 Portal 原生開發（獨立
    SQLite 資料庫 cycle-purchase.db），不對接 Ragic（見
    app/core/cycle_purchase_database.py 開頭說明）。
  - 但「匯總請購單」這個階段例外：Samuel 希望 Portal 產生的匯總請購單能
    「拋轉」到 Ragic，在 Ragic 端另外新增一張新的「匯總請購單」表單
    （不是既有的比價式「請購單」——現有請購單畫面有廠商(一)/(二)/(三) 三組
    比價欄位＋擬定廠商勾選，週期採購因為供應商已在料號對照表指定好、不比
    價，所以 Ragic 端的匯總請購單表單要拿掉這三組比價欄位，改成單一廠商
    欄位，由 Portal 直接帶入）。
  - 2026-07-16 與 Samuel 確認：Ragic 端這張新表單目前還沒建立，所以先做
    Portal 端全部功能（見 cycle_purchase_summary_service.push_summary_to_ragic），
    這裡的推送函式先做成 stub，回傳模擬成功結果，等 Ragic 端表單建好、
    拿到正式的 ragic_path／欄位代號之後，再把下面 TODO 的部分改成真正呼叫
    Ragic API。呼叫端（service 層）的介面不需要因此改變。

真正串接時需要的資訊（目前都還沒有，須向 Ragic 管理端確認）：
  - 新表單的 ragic_path（例如 /soutlet001/cycle-purchase/summary-request）
  - 新表單各欄位的 Ragic 欄位 ID／內部代號（Ragic API 寫入需要用欄位 ID
    而非顯示名稱）
  - 認證方式：沿用現有 RAGIC_API_KEY（參考舊有
    `ragic-cycle-purchase/scripts/ragic_client.py`，該檔案原本因為「與
    Ragic 脫鉤」的方向被建議封存，但因為這次匯總單需要真正寫入 Ragic，
    這支 client 可以拿回來參考，不要刪除）
  - 子表（部門別＋料號明細）在 Ragic API 寫入時的巢狀資料格式
"""
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class RagicPushError(Exception):
    """推送到 Ragic 失敗時拋出（stub 階段目前不會真的拋出，保留給未來真正串接用）。"""
    pass


def push_summary_document(document: dict[str, Any]) -> dict[str, Any]:
    """把一份「匯總請購單」文件推送到 Ragic。

    Args:
        document: 由 cycle_purchase_summary_service.push_summary_to_ragic() 組好的
            文件內容，結構大致為：
            {
                "batch_no": str,              # 本次拋轉批次號
                "cycle_name": str,
                "period_label": str,          # 期別，如 "2026-07"
                "company": str,                # 公司別
                "items": [                      # 依料號分組，每組含部門別＋小計
                    {
                        "item_code": str, "item_name": str, "unit": str,
                        "vendor_id": int | None, "vendor_name": str | None,
                        "unit_price": Decimal | None,
                        "departments": [
                            {"department_name": str, "adjusted_qty": int,
                             "subtotal": Decimal, ...},
                            ...
                        ],
                        "total_adjusted_qty": int, "total_amount": Decimal,
                    },
                    ...
                ],
            }

    Returns:
        {"ragic_record_id": str, "is_stub": bool, "message": str}

    ⚠️ STUB 實作：目前不會真的呼叫 Ragic API，只會記一筆 log 並回傳模擬的
    ragic_record_id（格式 "STUB-<batch_no>"），讓呼叫端（service 層）可以先
    把 Portal 這一側的拋轉狀態、按鈕、畫面都做完整測試。等 Ragic 端表單
    建好，把下面 TODO 區塊換成真正的 Ragic API 呼叫即可，不需要改動任何
    呼叫端程式碼或函式簽章。
    """
    batch_no = document.get("batch_no", "UNKNOWN")

    # ─────────────────────────────────────────────────────────────────
    # TODO（Ragic 端表單建好後才需要做）：
    #   1. 從 app.core.config.settings 讀取 RAGIC_API_KEY / RAGIC_BASE_URL
    #      （可參考 ragic-cycle-purchase/scripts/ragic_client.py 的既有寫法，
    #      不要整支複製，因為那支是舊的「Ragic 為主」架構假設，欄位對應
    #      需要重寫）
    #   2. 呼叫 Ragic API 的「新增記錄」端點，主表欄位對應 document 裡的
    #      cycle_name / period_label / company，子表對應 items[].departments
    #   3. 廠商欄位只會有一個值（items[].vendor_name），不要嘗試對應到
    #      Ragic 舊版請購單的「廠商(一)/(二)/(三)」三組欄位——那三組欄位
    #      在新表單裡應該已經被拿掉
    #   4. 從 Ragic API 回應取得真正的記錄 ID，取代下面的假值
    #   5. 呼叫失敗時 raise RagicPushError(...)，讓 service 層寫入
    #      ragic_push_error 並回傳 422 給前端
    # ─────────────────────────────────────────────────────────────────

    logger.warning(
        "[cycle_purchase_ragic_push] STUB 推送：batch_no=%s company=%s period=%s "
        "item_groups=%d — 尚未真正呼叫 Ragic API，Ragic 端「匯總請購單」表單尚未建立",
        batch_no, document.get("company"), document.get("period_label"),
        len(document.get("items", [])),
    )

    fake_record_id = f"STUB-{batch_no}"
    return {
        "ragic_record_id": fake_record_id,
        "is_stub": True,
        "message": (
            "已在 Portal 端標記為拋轉，但 Ragic 端「匯總請購單」表單尚未建立，"
            "這是模擬結果（stub），不是真正寫入 Ragic 的記錄"
        ),
    }
