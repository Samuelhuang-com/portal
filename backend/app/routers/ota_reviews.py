"""
OTA 口碑分析 — 評論 API Router
Prefix: /api/v1/ota/reviews

規格：`docs/SPEC_ota_reviews.md` §8.1

⚠️ 除必須 await UploadFile.read() 的匯入端點外，全部端點皆為同步 def ——
   async def 內直接呼叫同步 db.query() 會凍結整站
   （記憶 project_async_def_blocking_fix，Portal 曾因此全站無回應）。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import (APIRouter, Depends, File, HTTPException, Query, Response,
                     UploadFile)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.ota_review import (AlertUpdateIn, ImportResultOut,
                                    OtaReviewDetailOut, OtaReviewListOut)
from app.services import ota_import_service as IS
from app.services import ota_review_service as RS

router = APIRouter(dependencies=[Depends(get_current_user)])
_VIEW = require_permission("ota_reviews_view")
_ALERT = require_permission("ota_alerts_view")
_ADMIN = require_permission("ota_sources_admin")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # 10MB


def _attachment_headers(utf8_name: str, ascii_name: str) -> dict[str, str]:
    """
    產生可以放中文檔名的 `Content-Disposition`。

    ⚠️⚠️ **HTTP header 只能放 latin-1**。中文檔名直接塞進去會
       `UnicodeEncodeError` → **500**，而且是在回應組裝階段炸掉 ——
       前端只看到一句「下載失敗」，完全看不出是檔名的問題。

       2026-08-23 加 router 煙霧測試時一次抓到**兩支**都有這個病
       （Excel 匯出、CSV 範本下載），兩支都從 P1 就壞著 ——
       因為在那之前沒有任何測試真的呼叫過它們。
       出現兩次就抽共用，不要各修各的。

    做法是 RFC 5987：
      · `filename=`  純 ASCII 退路，給不支援的舊環境
      · `filename*=` 現代瀏覽器優先採用，可帶 UTF-8

    ⚠️ 不要只留 `filename*=` —— 少數舊環境會整個忽略而存成端點名稱。
    """
    from urllib.parse import quote

    return {
        "Content-Disposition":
            f'attachment; filename="{ascii_name}"; '
            f"filename*=UTF-8''{quote(utf8_name)}",
    }


def _filters(
    hotel_code: str, platform: str, start: str, end: str,
    min_score: float | None, max_score: float | None,
    score_below: float | None,
    sentiment: str, topic: str, keyword: str,
    alert_only: bool, alert_status: str, include_duplicate: bool,
) -> dict:
    """
    ⚠️ **這裡是所有篩選參數的單一集散地**，`list` 與 `export` 共用。
       新增篩選時**三個地方都要改**：本函式的簽章、本函式的 dict、
       以及兩個端點的呼叫。

       2026-08-23 踩過：只在 dict 裡加了 `low_score_only=low_score_only`
       卻沒加進簽章 → `NameError` → 整個清單 500。
       症狀是畫面上一句「載入評論失敗」，完全看不出是哪個參數的問題。
    """
    return dict(
        hotel_code=hotel_code, platform=platform, start=start, end=end,
        min_score=min_score, max_score=max_score, score_below=score_below,
        sentiment=sentiment, topic=topic, keyword=keyword,
        alert_only=alert_only, alert_status=alert_status,
        include_duplicate=include_duplicate,
    )


@router.get("", response_model=OtaReviewListOut, summary="OTA 評論清單")
def list_reviews(
    hotel_code: str = Query(""),
    platform: str = Query(""),
    start: str = Query("", description="評論日期起（YYYY-MM-DD）；不帶＝全部資料"),
    end: str = Query("", description="評論日期迄（YYYY-MM-DD）"),
    min_score: float | None = Query(None, description="統一 10 分制下限"),
    max_score: float | None = Query(None, description="統一 10 分制上限"),
    score_below: float | None = Query(
        None, ge=0, le=10,
        description="只看分數**低於**此值的（不含等於）。"
                    "帶 6.0 時與 Dashboard 的「負面評論」KPI 同條件"),
    sentiment: str = Query("", description="positive / neutral / negative"),
    topic: str = Query("", description="主題名稱，如「清潔」"),
    keyword: str = Query(""),
    alert_only: bool = Query(False),
    alert_status: str = Query(""),
    include_duplicate: bool = Query(False, description="是否顯示跨站重複的評論"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    """
    ⚠️ 分數篩選一律作用在 `score_10`（統一 10 分制），不是各站原始分數。
    ⚠️ 帶了 start／end 時，**日期解析失敗的評論不會出現** —— 它們不屬於任何區間。
    """
    return RS.list_reviews(
        db, page=page, page_size=page_size,
        **_filters(hotel_code, platform, start, end, min_score, max_score,
                   score_below, sentiment, topic, keyword,
                   alert_only, alert_status, include_duplicate),
    )


@router.get("/export", summary="匯出 Excel（沿用目前篩選條件）")
def export_reviews(
    hotel_code: str = Query(""),
    platform: str = Query(""),
    start: str = Query(""),
    end: str = Query(""),
    min_score: float | None = Query(None),
    max_score: float | None = Query(None),
    score_below: float | None = Query(None, ge=0, le=10),
    sentiment: str = Query(""),
    topic: str = Query(""),
    keyword: str = Query(""),
    alert_only: bool = Query(False),
    alert_status: str = Query(""),
    include_duplicate: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    content = RS.export_xlsx(
        db,
        **_filters(hotel_code, platform, start, end, min_score, max_score,
                   score_below, sentiment, topic, keyword,
                   alert_only, alert_status, include_duplicate),
    )
    stamp = f"{datetime.now():%Y%m%d_%H%M}"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_attachment_headers(f"OTA評論_{stamp}.xlsx",
                                    f"ota_reviews_{stamp}.xlsx"),
    )


@router.get("/import/template", summary="下載 CSV 匯入範本")
def download_template(_: User = Depends(_ADMIN)):
    return Response(
        content=IS.csv_template(),
        media_type="text/csv; charset=utf-8",
        headers=_attachment_headers("OTA評論匯入範本.csv",
                                    "ota_review_import_template.csv"),
    )


@router.post("/import/upload", response_model=ImportResultOut, summary="CSV 備援匯入")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(_ADMIN),
):
    """
    爬蟲失效時的救生艇（規格書 §6.6）。

    走與爬蟲完全相同的正規化與去重管線，不會產出第二種資料品質。
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="只接受 .csv 檔案")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="檔案超過 10MB 上限")
    if not content:
        raise HTTPException(status_code=400, detail="檔案是空的")

    return IS.import_reviews(db, content, user_id=str(user.id))


@router.get("/{review_id}", response_model=OtaReviewDetailOut, summary="評論明細（Drawer）")
def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    detail = RS.get_review_detail(db, review_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="找不到這則評論")
    return detail


@router.patch("/{review_id}/alert", response_model=OtaReviewDetailOut,
              summary="更新負評警示處理狀態")
def update_alert(
    review_id: int,
    payload: AlertUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(_ALERT),
):
    """
    ⚠️ 這四個警示欄位是人工營運資料，同步與重新分析都不會覆蓋它們
       （`ota_ingest_service.upsert_reviews` 有明確保護）。
    """
    detail = RS.update_alert(
        db, review_id,
        alert_status=payload.alert_status,
        alert_note=payload.alert_note,
        user_id=str(user.id),
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="找不到這則評論")
    return detail
