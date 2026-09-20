"""
週期採購 — 彙整單 API Router
Prefix: /api/v1/cycle-purchase

2026-07-11（第三期：彙整＋轉採購單）：
GET    /summary                         彙整單清單（依週期／期別／公司／供應商／狀態篩選）
GET    /summary/vendor-groups           轉採購單畫面用：依公司＋供應商分組統計（僅 draft）
PUT    /summary/{id}                    調整量／調整原因（僅 draft 可編輯）
POST   /summary/convert-to-po           轉採購單（指定週期＋期別＋公司＋供應商）

2026-07-16（匯總請購單改版，見 models/cycle_purchase_summary.py 開頭說明）：
GET    /summary/department-breakdown    依料號分組展開部門別＋小計（匯總請購單畫面用）
POST   /summary/push-to-ragic           拋轉到 Ragic「★週採請購單」(sheet 58)
                                         ⚠️ 2026-09-15 起是**真的寫入 Ragic**，且
                                         **依廠商拆單**：一家廠商一張 Ragic 單、共用
                                         同一個 batch_no。已拋轉過的列逐列略過（不再
                                         整批擋下）；缺供應商／缺單價的列回在
                                         not_pushed；單一廠商失敗回在 failed。
POST   /summary/cancel-ragic-push       取消拋轉（2026-08-09 新增，清掉拋轉標記，
                                         可重新拋轉，也解開「已拋轉不能退回請購單」）

2026-07-16（第二次調整，「彙整單產生方式」改版，見
services/cycle_purchase_summary_service.py 開頭說明——原本 POST /summary/generate
是靠使用者輸入的「週期＋期別」字串完全比對抓資料，期別字串不一致就會查到
0 筆；已整個移除，不保留備用路徑）：
GET    /summary/eligible-requests       列出某週期＋公司＋期別下，已關閉且尚未
                                         被彙整過的請購單，供勾選
POST   /summary/generate-from-requests  把勾選的請購單彙整成彙整列（period_label
                                         由系統從勾選的請購單本身的 period_label
                                         讀出來）

2026-07-17（第三次調整，配合請購單流程大改版——拿掉送出／核准，改成「關閉」）：
eligible-requests／generate-from-requests 的判斷條件從「status == approved」
改成「is_closed == True」，月份篩選也從「approved_at 換算年月」改成直接比對
period_label，見 services/cycle_purchase_summary_service.py 開頭第三次調整說明。

2026-08-09（第四次調整，「彙整單退回請購單」）：
GET    /summary/summarized-requests     列出某週期＋公司＋期別下已彙整的請購單
                                         （含 can_unsummarize／block_reason）
POST   /summary/unsummarize-request     把單一一張請購單退回未彙整狀態，並重算
                                         受影響的 draft 彙整列（退回原因必填）
兩支都掛 cycle_purchase_buyer 權限（與「產生彙整」同一個權限，退回是產生彙整
的反向操作，不另開新 permission key）。
"""
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.core.database import get_db
from app.dependencies import require_any_permission, require_permission
from app.models.user import User
from app.schemas.cycle_purchase_summary import (
    ConvertToPoPayload, DepartmentBreakdownOut, EligibleRequestOut, GenerateFromRequestsPayload,
    CancelRagicPushPayload, CancelRagicPushResult,
    PushToRagicPayload, PushToRagicResult, RagicPushedDateRange, RagicPushedDocOut,
    SummarizedRequestOut, SummaryOut, SummaryUpdate,
    UnsummarizeRequestPayload, UnsummarizeResult, VendorGroupOut,
)
from app.schemas.cycle_purchase_po import PODetail
from app.services import cycle_purchase_summary_service as svc
from app.services.cycle_purchase_summary_service import SummaryServiceError

router = APIRouter()


# 2026-09-18 新增的欄位。ORM 一宣告，**每一句碰到該表的 SELECT 都會帶上它**，
# 所以 migration 沒跑的話不是「新功能沒作用」而是「整組端點 500」。
_MIGRATION_HINTS = {
    # 2026-09-20：`ragic_dept` 已從 ORM 移除（Ragic 子表部門改自由文字，不需要
    # 七選一對照），不會再因為缺這個欄位而 500，所以這裡也不用再提示它。
    "ragic_record_url": (
        "cycle_purchase_summary.ragic_record_url",
        "cpragicurl",
    ),
}


def _schema_guard(exc: Exception):
    """把「資料庫少了某個欄位」翻成看得懂的話，而不是丟一句 PG 的 UndefinedColumn。

    ⚠️ 這個訊息要講清楚**是環境沒升級、不是使用者操作錯**——這個專案吃過一次
    「守衛訊息把欄位不存在寫成像是使用者做錯事」的虧，見專案記憶
    `feedback_stale_backend_symptom`。

    回 503 而不是 422：422 的語意是「你送的東西有問題」，但這裡是伺服器自己
    還沒升級完，使用者換個輸入也沒用。
    """
    msg = str(exc)
    for col, (full, revision) in _MIGRATION_HINTS.items():
        if col in msg and ("does not exist" in msg or "UndefinedColumn" in msg or "no such column" in msg):
            raise HTTPException(
                status_code=503,
                detail=(
                    f"資料庫還缺少 {full} 欄位，這是**環境尚未升級**，不是操作問題。"
                    f"請先在 backend 執行 `alembic -c alembic_cp.ini upgrade head`"
                    f"（對應 revision `{revision}`），**再重啟後端**。"
                    f"（順序反過來會因為缺欄位而整組端點 500）"
                ),
            )
    return None


def _handle(fn, *args, **kwargs):
    """共用：把 SummaryServiceError 轉成 422，統一錯誤訊息格式。

    另外攔「資料庫缺欄位」（migration 沒跑）並翻成 503 ＋ 可照做的指示，
    見 _schema_guard。
    """
    try:
        return fn(*args, **kwargs)
    except SummaryServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 — 只攔缺欄位，其餘原樣往上丟
        _schema_guard(e)
        raise


@router.get("/summary", response_model=List[SummaryOut], summary="週期採購彙整單清單")
def list_summary(
    cycle_id: Optional[int] = Query(None),
    period_label: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    department_id: Optional[int] = Query(None),
    _: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(
        svc.list_summary,
        db, cycle_id=cycle_id, period_label=period_label,
        company=company, vendor_id=vendor_id, status=status_,
        department_id=department_id,
    )


@router.get(
    "/summary/ragic-pushed",
    response_model=List[RagicPushedDocOut],
    summary="已彙整 Ragic 請購單：把已拋轉的彙整列還原成一張張 Ragic 單據（可依拋轉日期篩選）",
)
def list_ragic_pushed(
    start: Optional[date] = Query(None, description="拋轉日期起（含當天）"),
    end: Optional[date] = Query(None, description="拋轉日期迄（含當天）"),
    cycle_id: Optional[int] = Query(None),
    company: Optional[str] = Query(None),
    _: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    """一列＝一張 Ragic 單據。日期篩選打在 **`ragic_pushed_at`（拋轉時間）**，
    不是期別——使用者問的是「這段時間我推了什麼」，8 月的期別可能 9 月才推。
    `start`／`end` 皆可省略（＝不限）。"""
    return _handle(
        svc.list_ragic_pushed_documents,
        db, start=start, end=end, cycle_id=cycle_id, company=company,
    )


@router.get(
    "/summary/ragic-pushed/date-range",
    response_model=RagicPushedDateRange,
    summary="已拋轉資料的最早／最晚拋轉日（給 StandardRangePicker 當 anchor）",
)
def ragic_pushed_date_range(
    _: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    """⚠️ CLAUDE.md §8.2：快捷要以**資料最後一天**為基準而不是今天。
    拋轉是人工動作、不是每天都有，用今天當基準「本月」很容易框到一段完全沒資料的
    區間，使用者會以為資料不見了。"""
    return _handle(svc.ragic_pushed_date_range, db)


@router.get(
    "/summary/ragic-link",
    summary="取得 Ragic「週採匯總請購單」表單連結（彙整單頁右上角「在 Ragic 查看」用）",
)
def get_ragic_link(
    _: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_buyer")),
):
    """回傳 Ragic 表單網址，**由後端依 config 組出來，前端不要自己拼**——
    表單位置（server／account／path）只有 config.py 那一份真實來源，
    前端硬寫一份之後 Ragic 搬家就會有一邊沒改到。

    ⚠️ 這支只給到「表單」層級。Ragic 的 UI **不吃** `?<欄位代號>,eq,<值>` 這種
    網址篩選（2026-09-15 實測，帶了照樣列出全部），所以沒辦法用批次號連到篩選結果。

    **單筆深連結走另一條路**：拋轉當下就把完整網址存進
    `cycle_purchase_summary.ragic_record_url`（alembic_cp `cpragicurl`），
    「依供應商分組」與「已彙整 Ragic 請購單」TAB 用的是那個值，不是這支。
    """
    return {
        "url": (
            f"https://{settings.RAGIC_CP_SUMMARY_SERVER_URL}"
            f"/{settings.RAGIC_CP_SUMMARY_ACCOUNT}"
            f"/{settings.RAGIC_CP_SUMMARY_PATH}"
        ),
        "sheet_label": "週採匯總請購單",
        "enabled": settings.RAGIC_CP_SUMMARY_ENABLED,
    }


@router.get(
    "/summary/department-breakdown",
    response_model=List[DepartmentBreakdownOut],
    summary="匯總請購單畫面用：依料號分組展開部門別＋小計",
)
def department_breakdown(
    cycle_id: int = Query(...),
    period_label: str = Query(...),
    company: Optional[str] = Query(None),
    _: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.list_department_breakdown, db, cycle_id, period_label, company)


@router.get(
    "/summary/vendor-groups",
    response_model=List[VendorGroupOut],
    summary="轉採購單畫面用：依公司＋供應商分組統計（僅草稿）",
)
def vendor_groups(
    cycle_id: int = Query(...),
    period_label: str = Query(...),
    company: Optional[str] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.list_vendor_groups, db, cycle_id, period_label, company)


@router.get(
    "/summary/eligible-requests",
    response_model=List[EligibleRequestOut],
    summary="列出某週期＋公司＋期別下，已關閉且尚未被彙整過的請購單（供勾選產生彙整）",
)
def eligible_requests(
    cycle_id: int = Query(...),
    company: str = Query(...),
    year_month: str = Query(..., description="期別，格式 YYYY-MM，依請購單 period_label 判斷"),
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.list_eligible_requests, db, cycle_id, company, year_month)


@router.post(
    "/summary/generate-from-requests",
    response_model=List[SummaryOut],
    summary="把勾選的請購單彙整成彙整列（period_label 由系統從請購單本身的 period_label 讀出來）",
)
def generate_summary_from_requests(
    payload: GenerateFromRequestsPayload,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.generate_summary_from_requests, db, payload.request_ids)


@router.get(
    "/summary/summarized-requests",
    response_model=List[SummarizedRequestOut],
    summary="列出某週期＋公司＋期別下已彙整的請購單（供退回勾選；退不了的會附 block_reason）",
)
def summarized_requests(
    cycle_id: int = Query(...),
    company: str = Query(...),
    year_month: str = Query(..., description="期別，格式 YYYY-MM，依請購單 period_label 判斷"),
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.list_summarized_requests, db, cycle_id, company, year_month)


@router.post(
    "/summary/unsummarize-request",
    response_model=UnsummarizeResult,
    summary="退回請購單（把單一一張已彙整的請購單改回未彙整，並重算受影響的草稿彙整列）",
)
def unsummarize_request(
    payload: UnsummarizeRequestPayload,
    current_user: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.unsummarize_request, db, payload.request_id, payload.reason, current_user)


@router.put("/summary/{summary_id}", response_model=SummaryOut, summary="調整彙整列的調整量／調整原因")
def update_summary_item(
    summary_id: int,
    payload: SummaryUpdate,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    row = _handle(svc.update_summary_item, db, summary_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="彙整列不存在")
    return row


@router.post(
    "/summary/convert-to-po",
    response_model=PODetail,
    status_code=status.HTTP_201_CREATED,
    summary="轉採購單（同一週期＋期別＋公司＋供應商的草稿彙整列合成一張採購單）",
)
def convert_to_po(
    payload: ConvertToPoPayload,
    current_user: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(
        svc.convert_to_po,
        db, payload.cycle_id, payload.period_label, payload.company, payload.vendor_id,
        current_user,
    )


@router.post(
    "/summary/push-to-ragic",
    response_model=PushToRagicResult,
    summary="拋轉到 Ragic「★週採請購單」(sheet 58)，依廠商＋部門拆單",
)
def push_to_ragic(
    payload: PushToRagicPayload,
    current_user: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    """依「廠商＋部門」拆單真正寫入 Ragic。**部分成功也是 200**——成功的在
    documents、Ragic 拒絕的在 failed、缺供應商／缺單價／部門沒對照 Ragic 部門
    而沒送出去的列在 not_pushed，前端要三段都顯示。要重推某個已拋轉的範圍，
    先呼叫 POST /summary/cancel-ragic-push 清掉標記。

    `resolve_user_names`：Ragic 主表「請購人」要帶部門承辦人的**姓名**，但
    承辦人 id 存在 cycle-purchase.db、姓名在 portal.db。service 層維持只碰
    cycle-purchase.db（比照 cycle_purchase_masters._attach_owner_names 的做法），
    跨庫查詢包成 callable 由這裡傳進去。
    """
    def _resolve_user_names(user_ids):
        ids = [i for i in (user_ids or []) if i]
        if not ids:
            return {}
        users = portal_db.query(User).filter(User.id.in_(ids)).all()
        return {u.id: u.full_name for u in users}

    return _handle(
        svc.push_summary_to_ragic,
        db, payload.cycle_id, payload.period_label, payload.company, current_user,
        resolve_user_names=_resolve_user_names,
    )


@router.post(
    "/summary/cancel-ragic-push",
    response_model=CancelRagicPushResult,
    summary="取消拋轉（清掉該範圍的 Ragic 拋轉標記，可重新拋轉，也解開退回請購單的限制）",
)
def cancel_ragic_push(
    payload: CancelRagicPushPayload,
    current_user: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    """取消的是「拋轉」這個標記，不動彙整列本身的 status／po_id。
    ⚠️ Ragic 端真正串接之後，這裡要另外決定 Ragic 那筆記錄怎麼處理，
    見 services/cycle_purchase_summary_service.cancel_ragic_push() 的 TODO。"""
    return _handle(
        svc.cancel_ragic_push,
        db, payload.cycle_id, payload.period_label, payload.company,
        payload.reason, current_user,
    )
