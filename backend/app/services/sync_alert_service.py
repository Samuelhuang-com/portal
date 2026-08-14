"""
同步告警與資料鮮度監控

建立日期：2026-08-13
起因：2026-08-13 一天之內連續兩次「我查才發現」，兩次都沒有任何告警：

  ① 訂房回補／訂房增量／每日快照三個模組**從未執行過** —— DEV 機器
     `SCHEDULER_ENABLED=false`，而它們只登錄在 `main.py` 的 APScheduler、
     沒登錄進 `sync_tool.py MODULES`。`ohip_inventory_snapshot` 一直是 0 筆。
  ② 訂房回補顯示「24/24 完成」，實際 2025-08、2025-11、2026-02 整月 0 筆。

在此之前，同步失敗只寫進 `module_sync_log.status='error'`，`is_anomaly` 更是
只 `print()` 到 console（`main.py:1200`）——不寄信、不通知、前端也沒有畫面。
資料斷了沒人知道，是整個 Portal 最大的隱性風險。

═══════════════════════════════════════════════════════════════════════════
設計原則
═══════════════════════════════════════════════════════════════════════════
① **只讀不寫業務資料。** 本服務只查 log 表、只寄信、只寫去重用的 Memo。
② **同一個問題一天只寄一次。** 沿用合約模組的慣例：以 `Memo`
   （`source='sync_alert'`、`source_id='{key}_{YYYY-MM-DD}'`）做每日冪等去重。
   sync_tool 最短 15 分一輪，沒有去重會變成一天 96 封信，很快就沒人看。
③ **寄不出去不能讓同步失敗。** 所有 SMTP 例外都吞掉並記在回傳值裡 ——
   告警機制本身壞掉，不該連帶把同步流程也弄壞。
④ **沒設收件人就靜默跳過**，不報錯（多數開發機不會設 SMTP）。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import twnow
from app.models.memo import Memo
from app.models.module_sync_log import ModuleSyncLog

logger = logging.getLogger("sync_alert")

# 連續失敗幾次才告警。1 次可能只是網路抖動，Ragic 偶爾也會 502。
CONSECUTIVE_FAILURES = 2

# 資料鮮度門檻（小時）。超過這麼久沒有成功同步就告警。
# ⚠️ 取 6 小時而不是 1 小時：自動同步最長間隔 8 小時（INTERVAL_OPTIONS），
#    但多數模組是 30 分一輪。6 小時足以濾掉單次失敗，又不會拖到隔天才發現。
STALE_HOURS = 6

# 這些模組不納入鮮度檢查 —— 它們本來就是「補完就不再跑」或「一天一次」
FRESHNESS_EXEMPT = {
    "市場區隔歷史回補", "訂房歷史回補",   # 補完即 skip，不會再有新紀錄
}

MEMO_SOURCE = "sync_alert"


def _recipients() -> list[str]:
    """收件人清單。未設定就回空 list（呼叫端會靜默跳過）。"""
    raw = (getattr(settings, "ALERT_EMAIL_TO", "") or "").strip()
    return [x.strip() for x in raw.replace(";", ",").split(",") if x.strip()]


def _already_sent(db: Session, key: str, today: str) -> bool:
    """今天是否已針對同一個問題寄過信。"""
    return db.query(Memo.id).filter(
        Memo.source == MEMO_SOURCE,
        Memo.source_id == f"{key}_{today}",
    ).first() is not None


def _mark_sent(db: Session, key: str, today: str, title: str, body: str) -> None:
    """⚠️ 寫失敗不能讓告警流程掛掉 —— 大不了明天再寄一次。"""
    try:
        db.add(Memo(title=title, body=body, visibility="org",
                    author="系統", author_id="", source=MEMO_SOURCE,
                    source_id=f"{key}_{today}"))
        db.commit()
    except Exception:
        db.rollback()


# ── 各項檢查 ────────────────────────────────────────────────────────────────

def _check_failures(db: Session) -> list[dict[str, Any]]:
    """連續失敗的模組。"""
    issues = []
    names = [r[0] for r in db.query(ModuleSyncLog.module_name).distinct().all()]
    for name in names:
        recent = (db.query(ModuleSyncLog.status)
                    .filter(ModuleSyncLog.module_name == name)
                    .order_by(ModuleSyncLog.started_at.desc())
                    .limit(CONSECUTIVE_FAILURES).all())
        if len(recent) < CONSECUTIVE_FAILURES:
            continue
        if all(r[0] == "error" for r in recent):
            last = (db.query(ModuleSyncLog)
                      .filter(ModuleSyncLog.module_name == name)
                      .order_by(ModuleSyncLog.started_at.desc()).first())
            issues.append({
                "key": f"fail_{name}", "level": "error", "module": name,
                "title": f"「{name}」連續 {CONSECUTIVE_FAILURES} 次同步失敗",
                "detail": (last.error_msg or "")[:300] if last else "",
            })
    return issues


def _check_stale(db: Session) -> list[dict[str, Any]]:
    """資料鮮度：太久沒有成功同步。

    🎯 這一項就是為了抓「模組根本沒在跑」—— 2026-08-13 那三個從未執行的模組，
       在舊機制下完全無聲無息，因為「從來沒失敗過」（因為從來沒跑過）。
    """
    issues = []
    cutoff = twnow() - timedelta(hours=STALE_HOURS)
    rows = (db.query(ModuleSyncLog.module_name,
                     func.max(ModuleSyncLog.started_at))
              .filter(ModuleSyncLog.status != "error")
              .group_by(ModuleSyncLog.module_name).all())
    for name, last_ok in rows:
        if name in FRESHNESS_EXEMPT or not last_ok:
            continue
        if last_ok < cutoff:
            hours = int((twnow() - last_ok).total_seconds() // 3600)
            issues.append({
                "key": f"stale_{name}", "level": "warning", "module": name,
                "title": f"「{name}」已 {hours} 小時沒有成功同步",
                "detail": f"最後一次成功：{last_ok:%Y-%m-%d %H:%M}",
            })
    return issues


def _check_anomaly(db: Session) -> list[dict[str, Any]]:
    """`is_anomaly`：抓到 0 筆但過去平均遠大於 0。

    舊行為只 `print()` 到 console（`main.py:1200`），等於沒人看得到。
    """
    issues = []
    since = twnow() - timedelta(hours=24)
    rows = (db.query(ModuleSyncLog)
              .filter(ModuleSyncLog.is_anomaly.is_(True),
                      ModuleSyncLog.started_at >= since)
              .order_by(ModuleSyncLog.started_at.desc()).all())
    seen = set()
    for r in rows:
        if r.module_name in seen:
            continue
        seen.add(r.module_name)
        issues.append({
            "key": f"anomaly_{r.module_name}", "level": "warning",
            "module": r.module_name,
            "title": f"「{r.module_name}」同步結果異常：這次抓到 0 筆",
            "detail": "過去幾次都有資料，這次卻是 0 —— 可能是來源端被清空或篩選條件變了。",
        })
    return issues


def _check_opera_backfill(db: Session) -> list[dict[str, Any]]:
    """OPERA 訂房回補的**真實缺口**（天數，不是段數）。

    🎯 2026-08-13 的「假性完成」就是這裡漏掉的：進度顯示 24/24，
       實際整月 0 筆。改用逐日檢查後，這一項才有意義。
    """
    issues = []
    try:
        from app.services import opera_reservation_sync as SY
        from app.services import ohip_client
        if not ohip_client.is_configured():
            return []
        for ds, label in (("reservation", "訂房"), ("block", "團體")):
            p = SY.backfill_progress(db, ds)
            missing = int(p.get("missing_days") or 0)
            if missing > 0:
                issues.append({
                    "key": f"backfill_{ds}", "level": "warning",
                    "module": f"OPERA {label}回補",
                    "title": f"OPERA {label}歷史資料還缺 {missing} 天",
                    "detail": (f"涵蓋 {p['covered_days']}/{p['total_days']} 天，"
                               f"還要補 {p['pending_chunks']} 段。"
                               f"下一段：{(p.get('next_chunk') or {}).get('start')}"
                               f"～{(p.get('next_chunk') or {}).get('end')}。"
                               "在「訂房分析」頁按「補下一段」，"
                               "或用同步工具的「訂房歷史回補」一次補完。"),
                })
    except Exception as exc:      # noqa: BLE001
        logger.warning("回補檢查失敗（不影響其他告警）：%s", exc)
    return issues


def _check_snapshot(db: Session) -> list[dict[str, Any]]:
    """每日快照今天有沒有跑。

    ⚠️ 這一項的嚴重性和其他不同：**快照錯過的日子永遠補不回來**
       （OPERA 不提供歷史查詢），所以列為 error 而不是 warning。
    """
    try:
        from app.models.realtime import OhipSnapshotRun
        from app.services import ohip_client
        if not ohip_client.is_configured():
            return []
        today_s = date.today().isoformat()
        done = (db.query(OhipSnapshotRun.id)
                  .filter(OhipSnapshotRun.snapshot_date == today_s,
                          OhipSnapshotRun.status != "failed").first())
        if done:
            return []
        return [{
            "key": "snapshot_missing", "level": "error", "module": "OHIP 每日快照",
            "title": f"{today_s} 的每日快照還沒跑",
            "detail": ("快照只能存「當下」，錯過的日子 OPERA 不提供補查，"
                       "永遠補不回來。請確認同步工具的「OHIP 每日快照」有在執行。"),
        }]
    except Exception as exc:      # noqa: BLE001
        logger.warning("快照檢查失敗（不影響其他告警）：%s", exc)
        return []


# ── 對外 ────────────────────────────────────────────────────────────────────

def collect_issues(db: Session) -> list[dict[str, Any]]:
    """只檢查、不寄信 —— 給前端的健康狀態頁共用。"""
    return (_check_failures(db) + _check_stale(db) + _check_anomaly(db)
            + _check_opera_backfill(db) + _check_snapshot(db))


def _render(issues: list[dict[str, Any]]) -> tuple[str, str]:
    rows = "".join(
        f'<tr><td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;">'
        f'<span style="color:{"#e74c3c" if i["level"] == "error" else "#faad14"};">'
        f'{"●" if i["level"] == "error" else "▲"}</span></td>'
        f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;">'
        f'<b>{i["title"]}</b><br>'
        f'<span style="color:#6b7280;font-size:12px;">{i["detail"]}</span></td></tr>'
        for i in issues)
    html = f"""
<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,'Microsoft JhengHei',sans-serif;background:#f0f4f8;padding:24px;">
  <div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;
              box-shadow:0 2px 8px rgba(27,58,92,0.10);">
    <div style="background:linear-gradient(135deg,#1B3A5C,#4BA8E8);padding:20px 28px;">
      <h2 style="color:#fff;margin:0;font-size:18px;">資料同步告警</h2>
      <p style="color:rgba(255,255,255,.8);margin:4px 0 0;font-size:12px;">
        {twnow():%Y-%m-%d %H:%M} · 共 {len(issues)} 項</p>
    </div>
    <div style="padding:20px 28px;">
      <table style="width:100%;border-collapse:collapse;font-size:14px;">{rows}</table>
      <p style="color:#9ca3af;font-size:12px;margin-top:16px;">
        同一個問題一天只寄一次。處理完之後不必回覆，隔天沒有再收到就代表恢復正常。
      </p>
    </div>
  </div>
</body></html>""".strip()
    text = "資料同步告警\n\n" + "\n\n".join(
        f"[{i['level'].upper()}] {i['title']}\n  {i['detail']}" for i in issues)
    return html, text


def check_and_alert(*, triggered_by: str = "scheduler") -> dict[str, Any]:
    """檢查同步健康，有問題就寄信。**零參數**，可直接登錄進 `sync_tool.py`。

    回傳格式對齊 sync_tool 的期待：`fetched` / `upserted` / `errors`。
    ⚠️ `errors` 一律回 0 —— 「發現問題」不等於「這支程式失敗」，
       回非 0 會讓同步工具把這一輪標成紅燈，反而分不清是誰壞了。
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        issues = collect_issues(db)
        if not issues:
            return {"fetched": 0, "upserted": 0, "errors": 0,
                    "skipped": True, "message": "同步狀態正常，無告警。"}

        to = _recipients()
        if not to:
            # 沒設收件人不算失敗 —— 多數開發機不會設 SMTP
            return {"fetched": len(issues), "upserted": 0, "errors": 0,
                    "skipped": True, "issues": [i["title"] for i in issues],
                    "message": "偵測到問題但未設定 ALERT_EMAIL_TO，未寄信。"}

        today_s = date.today().isoformat()
        fresh = [i for i in issues if not _already_sent(db, i["key"], today_s)]
        if not fresh:
            return {"fetched": len(issues), "upserted": 0, "errors": 0,
                    "skipped": True, "message": "今天已針對這些問題寄過信。"}

        html, text = _render(fresh)
        n_err = sum(1 for i in fresh if i["level"] == "error")
        subject = (f"【Portal】資料同步告警 {len(fresh)} 項"
                   + (f"（{n_err} 項嚴重）" if n_err else ""))

        sent = 0
        send_error = ""
        try:
            from app.services.email_service import _send
            for addr in to:
                _send(addr, "", subject, html, text)
                sent += 1
        except Exception as exc:      # noqa: BLE001
            # ⚠️ 告警寄不出去，不該連帶讓呼叫端失敗（見檔頭原則③）
            send_error = str(exc)[:300]
            logger.warning("告警信寄送失敗：%s", exc)

        if sent:
            for i in fresh:
                _mark_sent(db, i["key"], today_s, i["title"], i["detail"])

        return {"fetched": len(issues), "upserted": sent, "errors": 0,
                "skipped": False,
                "issues": [i["title"] for i in fresh],
                "send_error": send_error,
                "message": f"寄出 {sent} 封，涵蓋 {len(fresh)} 項問題。"}
    finally:
        db.close()
