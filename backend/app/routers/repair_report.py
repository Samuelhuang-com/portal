"""
報修未完成報表 API Router
Prefix: /api/v1/repair-report

端點：
  GET  /unfinished-cases          — 聚合未完成案件（飯店+商場）
  GET  /export                    — 匯出 Excel
  GET  /recipients                — 列出收件人
  POST /recipients                — 新增收件人
  PUT  /recipients/{id}           — 更新收件人
  DELETE /recipients/{id}         — 刪除收件人
  POST /recipients/{id}/test-send — 寄送測試信給單一收件人
  GET  /schedule                  — 讀取排程設定
  PUT  /schedule                  — 更新排程設定
  POST /send-now                  — 手動立即寄送
  GET  /mail-logs                 — 查詢寄送紀錄

權限：
  repair_unfinished_report_view   — 查看報表、匯出 Excel
  repair_unfinished_report_manage — 管理收件人、排程、手動寄送
  repair_unfinished_report_admin  — 查看寄送紀錄
"""
from __future__ import annotations

import io
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.repair_report import (
    RepairReportMailLog,
    RepairReportRecipient,
    RepairReportScheduleSettings,
)
from app.schemas.repair_report import (
    MailLogListResponse,
    MailLogOut,
    ManualSendRequest,
    ManualSendResponse,
    RecipientCreate,
    RecipientOut,
    RecipientUpdate,
    ScheduleSettingsOut,
    ScheduleSettingsUpdate,
    SendResult,
    TestSendResponse,
    UnfinishedCasesResponse,
)
from app.services import repair_report_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── 工具：reschedule APScheduler job ──────────────────────────────────────────

def _reschedule_job(send_time: str) -> None:
    """排程設定更新後，即時更新 APScheduler CronTrigger。"""
    try:
        from app.core.scheduler import scheduler as _scheduler
        from apscheduler.triggers.cron import CronTrigger as _CronTrigger
        h, m = send_time.split(":")
        _scheduler.reschedule_job(
            "repair_report_daily_send",
            trigger=_CronTrigger(hour=int(h), minute=int(m)),
        )
        logger.info(f"[RepairReport] Scheduler reschedule → {send_time}")
    except Exception as exc:
        logger.warning(f"[RepairReport] reschedule_job 失敗（非致命）: {exc}")


# ── 報修未完成案件查詢 ────────────────────────────────────────────────────────

@router.get(
    "/unfinished-cases",
    summary="聚合未完成案件（飯店 + 商場）",
    dependencies=[Depends(require_permission("repair_unfinished_report_view"))],
)
def get_unfinished_cases(
    year:                int            = Query(..., description="年度"),
    month:               int            = Query(..., description="月份"),
    source:              str            = Query("all",  description="all / hotel / mall"),
    status_filter:       Optional[str]  = Query(None,   description="過濾特定狀態值"),
    overdue_only:        bool           = Query(False,  description="只顯示可能逾期案件"),
    repair_type_filter:  Optional[str]  = Query(None,   description="過濾工項類別"),
    keyword:             Optional[str]  = Query(None,   description="關鍵字搜尋"),
    page:                int            = Query(1,      ge=1),
    page_size:           int            = Query(50,     ge=1, le=200),
    db: Session = Depends(get_db),
):
    result = svc.get_unfinished_cases(
        db=db,
        year=year,
        month=month,
        source=source,
        status_filter=status_filter,
        overdue_only=overdue_only,
        repair_type_filter=repair_type_filter,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return result


# ── Excel 匯出 ────────────────────────────────────────────────────────────────

@router.get(
    "/export",
    summary="匯出 Excel（串流）",
    dependencies=[Depends(require_permission("repair_unfinished_report_view"))],
)
def export_excel(
    year:         int           = Query(...),
    month:        int           = Query(...),
    source:       str           = Query("all"),
    overdue_only: bool          = Query(False),
    keyword:      Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    cases = svc.get_all_unfinished_cases(
        db=db,
        year=year,
        month=month,
        include_hotel=(source in ("all", "hotel")),
        include_mall=(source in ("all", "mall")),
    )

    if overdue_only:
        cases = [c for c in cases if c["is_overdue"]]
    if keyword:
        kw = keyword.lower()
        cases = [
            c for c in cases
            if any(kw in (c.get(f) or "").lower()
                   for f in ("case_no", "floor", "title", "status", "responsible_unit", "finance_note"))
        ]

    excel_bytes = svc.generate_excel(cases, year, month)
    filename    = f"報修未完成報表_{year}{month:02d}_{date.today().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── 收件人管理 ────────────────────────────────────────────────────────────────

@router.get(
    "/recipients",
    summary="列出所有收件人",
    response_model=list[RecipientOut],
    dependencies=[Depends(require_permission("repair_unfinished_report_manage"))],
)
def list_recipients(db: Session = Depends(get_db)):
    return db.query(RepairReportRecipient).order_by(RepairReportRecipient.id).all()


@router.post(
    "/recipients",
    summary="新增收件人",
    response_model=RecipientOut,
    dependencies=[Depends(require_permission("repair_unfinished_report_manage"))],
)
def create_recipient(
    payload: RecipientCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(RepairReportRecipient).filter_by(email=payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Email {payload.email} 已存在")

    obj = RepairReportRecipient(
        **payload.model_dump(),
        created_by=current_user.email or "",
        updated_by=current_user.email or "",
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put(
    "/recipients/{recipient_id}",
    summary="更新收件人",
    response_model=RecipientOut,
    dependencies=[Depends(require_permission("repair_unfinished_report_manage"))],
)
def update_recipient(
    recipient_id: int,
    payload: RecipientUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = db.query(RepairReportRecipient).filter_by(id=recipient_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="收件人不存在")

    update_data = payload.model_dump(exclude_none=True)
    # 若更新 email，確認不重複
    if "email" in update_data:
        dup = (
            db.query(RepairReportRecipient)
            .filter(
                RepairReportRecipient.email == update_data["email"],
                RepairReportRecipient.id != recipient_id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail=f"Email {update_data['email']} 已被其他收件人使用")

    for k, v in update_data.items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    obj.updated_by = current_user.email or ""
    db.commit()
    db.refresh(obj)
    return obj


@router.delete(
    "/recipients/{recipient_id}",
    summary="刪除收件人",
    dependencies=[Depends(require_permission("repair_unfinished_report_manage"))],
)
def delete_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
):
    obj = db.query(RepairReportRecipient).filter_by(id=recipient_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="收件人不存在")
    db.delete(obj)
    db.commit()
    return {"success": True}


@router.post(
    "/recipients/{recipient_id}/test-send",
    summary="寄送測試信給單一收件人",
    response_model=TestSendResponse,
    dependencies=[Depends(require_permission("repair_unfinished_report_manage"))],
)
def test_send_to_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
):
    rcpt = db.query(RepairReportRecipient).filter_by(id=recipient_id).first()
    if not rcpt:
        raise HTTPException(status_code=404, detail="收件人不存在")

    now   = datetime.now()
    year  = now.year
    month = now.month

    cases = svc.get_all_unfinished_cases(db, year, month)
    kpi   = svc._calc_kpi(cases, year, month, now.date())

    subject   = f"【測試】報修未完成報表 {year}年{month:02d}月"
    html_body = svc._build_html_body(year, month, kpi, has_attachment=False)
    text_body = svc._build_text_body(year, month, kpi)

    try:
        svc.send_single_email(
            to_email=rcpt.email,
            to_name=rcpt.name,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        return TestSendResponse(success=True, message=f"測試信已寄送至 {rcpt.email}")
    except Exception as exc:
        logger.error(f"[RepairReport] 測試寄送失敗 {rcpt.email}: {exc}")
        return TestSendResponse(success=False, message=str(exc))


# ── 排程設定 ──────────────────────────────────────────────────────────────────

@router.get(
    "/schedule",
    summary="讀取排程設定",
    response_model=ScheduleSettingsOut,
    dependencies=[Depends(require_permission("repair_unfinished_report_manage"))],
)
def get_schedule(db: Session = Depends(get_db)):
    sched = db.query(RepairReportScheduleSettings).first()
    if not sched:
        svc.ensure_default_schedule(db)
        sched = db.query(RepairReportScheduleSettings).first()
    return sched


@router.put(
    "/schedule",
    summary="更新排程設定",
    response_model=ScheduleSettingsOut,
    dependencies=[Depends(require_permission("repair_unfinished_report_manage"))],
)
def update_schedule(
    payload: ScheduleSettingsUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sched = db.query(RepairReportScheduleSettings).first()
    if not sched:
        svc.ensure_default_schedule(db)
        sched = db.query(RepairReportScheduleSettings).first()

    for k, v in payload.model_dump().items():
        setattr(sched, k, v)
    sched.updated_at = datetime.utcnow()
    sched.updated_by = current_user.email or ""
    db.commit()
    db.refresh(sched)

    # 即時更新 APScheduler job 的 CronTrigger
    _reschedule_job(sched.send_time)

    return sched


# ── 手動立即寄送 ──────────────────────────────────────────────────────────────

@router.post(
    "/send-now",
    summary="手動立即寄送報表",
    response_model=ManualSendResponse,
    dependencies=[Depends(require_permission("repair_unfinished_report_manage"))],
)
def send_now(
    payload: ManualSendRequest,
    db: Session = Depends(get_db),
):
    # 決定收件人
    if payload.recipient_ids:
        recipients = (
            db.query(RepairReportRecipient)
            .filter(RepairReportRecipient.id.in_(payload.recipient_ids))
            .all()
        )
    else:
        recipients = (
            db.query(RepairReportRecipient)
            .filter(RepairReportRecipient.is_active == True)
            .all()
        )

    if not recipients:
        raise HTTPException(status_code=400, detail="無可用收件人（請先新增並啟用收件人）")

    cases = svc.get_all_unfinished_cases(
        db,
        payload.year,
        payload.month,
        include_hotel=payload.include_hotel,
        include_mall=payload.include_mall,
    )
    now   = datetime.now()
    kpi   = svc._calc_kpi(cases, payload.year, payload.month, now.date())

    hotel_count = kpi["hotel_unfinished"]
    mall_count  = kpi["mall_unfinished"]
    total       = kpi["total_unfinished"]

    subject = (
        f"【報修未完成報表】{payload.year}年{payload.month:02d}月"
        f"｜未完成 {total} 件｜飯店 {hotel_count} 件｜商場 {mall_count} 件"
    )
    html_body = svc._build_html_body(
        payload.year, payload.month, kpi,
        has_attachment=payload.include_excel_attachment,
    )
    text_body = svc._build_text_body(payload.year, payload.month, kpi)

    attachment: Optional[tuple[str, bytes]] = None
    attachment_filename: Optional[str] = None
    if payload.include_excel_attachment:
        excel_bytes = svc.generate_excel(cases, payload.year, payload.month)
        attachment_filename = f"報修未完成報表_{payload.year}{payload.month:02d}_{now.strftime('%Y%m%d')}.xlsx"
        attachment = (attachment_filename, excel_bytes)

    results: list[SendResult] = []
    send_time_str = now.strftime("%H:%M")

    for rcpt in recipients:
        status  = "failed"
        err_msg = None
        try:
            svc.send_single_email(
                to_email=rcpt.email,
                to_name=rcpt.name,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                attachment=attachment,
            )
            status = "success"
        except Exception as exc:
            err_msg = str(exc)[:500]

        results.append(SendResult(
            recipient_email=rcpt.email,
            recipient_name=rcpt.name,
            success=(status == "success"),
            error_message=err_msg,
        ))

        db.add(RepairReportMailLog(
            send_date=now.date(),
            send_time=send_time_str,
            report_year=payload.year,
            report_month=payload.month,
            recipient_email=rcpt.email,
            recipient_name=rcpt.name,
            subject=subject,
            status=status,
            error_message=err_msg,
            hotel_unfinished_count=hotel_count,
            mall_unfinished_count=mall_count,
            total_unfinished_count=total,
            attachment_filename=attachment_filename,
        ))

    db.commit()

    sent_count   = sum(1 for r in results if r.success)
    failed_count = len(results) - sent_count

    return ManualSendResponse(
        sent_count=sent_count,
        failed_count=failed_count,
        results=results,
    )


# ── 寄送紀錄查詢 ──────────────────────────────────────────────────────────────

@router.get(
    "/mail-logs",
    summary="查詢寄送紀錄",
    response_model=MailLogListResponse,
    dependencies=[Depends(require_permission("repair_unfinished_report_admin"))],
)
def get_mail_logs(
    year:    Optional[int] = Query(None),
    month:   Optional[int] = Query(None),
    status:  Optional[str] = Query(None, description="success / failed / skipped"),
    email:   Optional[str] = Query(None),
    page:    int           = Query(1, ge=1),
    page_size: int         = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(RepairReportMailLog)

    if year:
        q = q.filter(RepairReportMailLog.report_year == year)
    if month:
        q = q.filter(RepairReportMailLog.report_month == month)
    if status:
        q = q.filter(RepairReportMailLog.status == status)
    if email:
        q = q.filter(RepairReportMailLog.recipient_email.contains(email))

    total = q.count()
    items = (
        q.order_by(RepairReportMailLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return MailLogListResponse(items=items, total=total)
