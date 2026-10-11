"""
戰情 KPI 異常告警（A1～A5）— 2026-10-10 新增
規格：docs/SPEC_war_room.md §7

設計原則（沿用 sync_alert_service）：
① 只讀業務資料；偵測結果「先列清單、再由人決定寄不寄」。自動寄送預設關閉（auto_send=False）。
② 去重：記在 system_settings 的 JSON（war_room.alert_sent），不寫 Memo —— Memo 會出現在行事曆。
③ 寄不出去不影響其他流程；沒設收件人／收件人不在白名單 → 靜默略過。
④ 收件人由有權限的人在「戰情 KPI → 告警 → 收件人」維護（存 system_settings JSON，不用 .env）：
   每位收件人可勾選館別（飯店／商場／兩者）。「整棟」類告警寄給所有啟用收件人。
   維護名單需 war_room_view ＋ WAR_ROOM_ALLOWED_EMAILS（白名單，管理員也受限，§11.7）；
   收件人本身只是收信對象，不必是 Portal 使用者。

口徑：報修一律「今日現況」，排除 is_ragic_deleted 與 is_excluded_flag（使用者裁示 2026-10-07）。
"""
from __future__ import annotations

import html as _html
import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import twnow
from app.models.system_setting import SystemSetting

logger = logging.getLogger("war_room_alert")

KEY_SETTINGS = "war_room.alert_settings"
KEY_SENT = "war_room.alert_sent"
KEY_LOG = "war_room.alert_log"
KEY_RECIPIENTS = "war_room.alert_recipients"

TYPE_LABEL = {
    "A1": "報修久未完成",
    "A2": "巡檢未填",
    "A3": "巡檢異常",
    "A4": "IHG 保養異常（待料）",
    "A5": "同房反覆報修",
}
LEVEL_LABEL = {"critical": "嚴重", "warning": "警告", "info": "資訊"}
LEVEL_ORDER = {"critical": 0, "warning": 1, "info": 2}
VENUE_LABEL = {"hotel": "飯店", "mall": "商場", "both": "整棟"}
# 巡檢模組 → 館別。整棟巡檢涵蓋兩館 → both（寄給兩館收件人聯集）
MODULE_VENUE = {"mall_facility_inspection": "mall", "full_building_inspection": "both"}

DEFAULTS: dict[str, Any] = {
    "enabled": {"A1": True, "A2": True, "A3": True, "A4": True, "A5": True},
    "repair_warn_days": 7,
    "repair_critical_days": 14,
    "inspect_deadline": "18:00",
    "ihg_lookback_days": 2,
    "repeat_critical_days": 3,
    "room_repeat_count": 3,
    "room_repeat_days": 30,
    "auto_send": False,
}


# ── 設定／已寄紀錄（system_settings JSON）──────────────────────────────────────
def _get_json(db: Session, key: str, default: Any) -> Any:
    row = db.get(SystemSetting, key)
    if not row or not row.value:
        return default
    try:
        return json.loads(row.value)
    except Exception:
        return default


def _set_json(db: Session, key: str, value: Any, who: str = "system") -> None:
    row = db.get(SystemSetting, key)
    txt = json.dumps(value, ensure_ascii=False)
    if row:
        row.value, row.updated_by = txt, who
    else:
        db.add(SystemSetting(key=key, value=txt, updated_by=who))
    db.commit()


def get_settings(db: Session) -> dict[str, Any]:
    saved = _get_json(db, KEY_SETTINGS, {})
    cfg = {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}
    cfg["enabled"] = {**DEFAULTS["enabled"], **(saved.get("enabled") or {})}
    return cfg


def save_settings(db: Session, patch: dict[str, Any], who: str) -> dict[str, Any]:
    cfg = get_settings(db)

    def _int(k: str, lo: int, hi: int) -> None:
        if k in patch and patch[k] is not None:
            v = int(patch[k])
            if not lo <= v <= hi:
                raise ValueError(f"{k} 須介於 {lo}～{hi}")
            cfg[k] = v

    _int("repair_warn_days", 1, 365)
    _int("repair_critical_days", 1, 365)
    _int("ihg_lookback_days", 1, 14)
    _int("repeat_critical_days", 1, 30)
    _int("room_repeat_count", 2, 20)
    _int("room_repeat_days", 7, 180)
    if cfg["repair_critical_days"] < cfg["repair_warn_days"]:
        raise ValueError("嚴重天數不可小於警告天數")
    if patch.get("inspect_deadline") is not None:
        t = str(patch["inspect_deadline"]).strip()
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t):
            raise ValueError("巡檢截止時間格式須為 HH:MM")
        cfg["inspect_deadline"] = t
    if patch.get("auto_send") is not None:
        cfg["auto_send"] = bool(patch["auto_send"])
    if isinstance(patch.get("enabled"), dict):
        for k in TYPE_LABEL:
            if k in patch["enabled"]:
                cfg["enabled"][k] = bool(patch["enabled"][k])
    _set_json(db, KEY_SETTINGS, cfg, who)
    return cfg


def _sent_map(db: Session) -> dict[str, str]:
    return _get_json(db, KEY_SENT, {})


def _mark_sent(db: Session, keys: list[str], day: date) -> None:
    m = _sent_map(db)
    for k in keys:
        m[k] = day.isoformat()
    cutoff = (day - timedelta(days=120)).isoformat()      # 太舊的丟掉，避免無限長大
    m = {k: v for k, v in m.items() if v >= cutoff}
    _set_json(db, KEY_SENT, m, "system")


def _append_log(db: Session, entry: dict[str, Any]) -> None:
    log = _get_json(db, KEY_LOG, [])
    log.insert(0, entry)
    _set_json(db, KEY_LOG, log[:100], "system")


def get_log(db: Session) -> list[dict[str, Any]]:
    return _get_json(db, KEY_LOG, [])


# ── 偵測 ─────────────────────────────────────────────────────────────────────
def _mk(typ: str, level: str, venue: str, key: str, title: str, detail: str,
        *, floor: str = "", room: str = "", ref: Optional[dict] = None,
        since: str = "", wait_days: Optional[int] = None) -> dict[str, Any]:
    return {
        "key": key, "type": typ, "type_label": TYPE_LABEL[typ],
        "level": level, "level_label": LEVEL_LABEL[level],
        "venue": venue, "venue_label": VENUE_LABEL[venue],
        "title": title, "detail": detail,
        "floor": floor, "room": room, "ref": ref or {},
        "since": since, "wait_days": wait_days,
    }


def _repeat_days(a: dict[str, Any], cfg: dict[str, Any]) -> Optional[int]:
    """None＝同一件事只通知一次；N＝距上次通知滿 N 天才再通知。"""
    t = a["type"]
    if t == "A1":
        return cfg["repeat_critical_days"] if a["level"] == "critical" else 1
    if t == "A5":
        return 7
    return None            # A2（key 含日期）／A3／A4


def _detect_a1(db: Session, wr: Any, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for r in wr._open_repairs(db):
        wd = r["wait_days"]
        if wd is None or wd < cfg["repair_warn_days"]:
            continue
        level = "critical" if wd >= cfg["repair_critical_days"] else "warning"
        venue = "hotel" if r["source"] == "dazhi" else "mall"
        loc = r["room"] or r["floor_raw"] or "—"
        out.append(_mk(
            "A1", level, venue, f"A1:{r['source']}:{r['ragic_id']}",
            f"{r['source_label']} {r['case_no'] or r['ragic_id']} 已等待 {wd} 天未完成",
            f"{r['title']}｜位置：{loc}｜狀態：{r['status'] or '—'}｜發生：{r['occurred_at']}",
            floor=(r["floors"] or [""])[0], room=r["room"],
            ref={"kind": "repair", "source": r["source"], "ragic_id": r["ragic_id"],
                 "ragic_url": r["ragic_url"]},
            since=r["occurred_at"], wait_days=wd))
    return out


def _detect_points(db: Session, wr: Any, cfg: dict[str, Any], ref: date,
                   now: datetime) -> list[dict[str, Any]]:
    out = []
    dl_h, dl_m = (int(x) for x in cfg["inspect_deadline"].split(":"))
    # A3：巡檢異常 —— 看 ref 與前一天（每日彙整在隔天早上，不能漏掉昨晚的）
    if cfg["enabled"].get("A3"):
        for d in (ref, ref - timedelta(days=1)):
            for p in wr._all_points(db, d.strftime("%Y/%m/%d")):
                if p["status"] != "abnormal":
                    continue
                venue = MODULE_VENUE.get(p["module"], "both")
                out.append(_mk(
                    "A3", "critical", venue, f"A3:{p['id']}:{d.isoformat()}",
                    f"{p['module_label']}｜{p['label']} 巡檢異常（{d.isoformat()}）",
                    f"{p['group_label']}｜樓層 {p['floor_key'].upper()}"
                    + (f"｜設備編號 {p['equipment_code']}" if p["equipment_code"] else ""),
                    floor=p["floor_key"],
                    ref={"kind": "point", "point_id": p["id"], "date": d.isoformat()},
                    since=d.isoformat()))
    # A2：巡檢未填 —— 只在「今天」且過了截止時間才算
    if (cfg["enabled"].get("A2") and ref == now.date()
            and (now.hour, now.minute) >= (dl_h, dl_m)):
        grp: dict[tuple[str, str], list[dict]] = {}
        for p in wr._all_points(db, ref.strftime("%Y/%m/%d")):
            if p["status"] == "unchecked":
                grp.setdefault((p["module"], p["floor_key"]), []).append(p)
        for (module, fk), pts in grp.items():
            names = "、".join(x["label"] for x in pts[:8]) + ("…" if len(pts) > 8 else "")
            out.append(_mk(
                "A2", "warning", MODULE_VENUE.get(module, "both"),
                f"A2:{module}:{fk}:{ref.isoformat()}",
                f"{pts[0]['module_label']} {fk.upper()} 仍有 {len(pts)} 個點位未填（已過 {cfg['inspect_deadline']}）",
                names, floor=fk,
                ref={"kind": "points", "module": module, "floor_key": fk,
                     "point_ids": [x["id"] for x in pts], "date": ref.isoformat()},
                since=ref.isoformat()))
    return out


def _detect_a4(db: Session, cfg: dict[str, Any], ref: date) -> list[dict[str, Any]]:
    from app.models.ihg_room_maintenance import IHGRoomMaintenanceMaster
    from app.routers.ihg_room_maintenance import _calc_record_status
    from app.routers.work_journal import _ragic_url, _SOURCE_PATH
    days = [ref - timedelta(days=i) for i in range(cfg["ihg_lookback_days"])]
    fmts = [d.strftime(f) for d in days for f in ("%Y/%m/%d", "%Y-%m-%d")]
    rows = (db.query(IHGRoomMaintenanceMaster)
              .filter(IHGRoomMaintenanceMaster.maint_date.in_(fmts)).all())
    out = []
    for m in rows:
        if _calc_record_status(m.raw_json) != "abnormal":
            continue
        d = (m.maint_date or "")[:10].replace("/", "-")
        out.append(_mk(
            "A4", "warning", "hotel", f"A4:{m.ragic_id}",
            f"{m.room_no} 客房保養異常（待料）{d}",
            f"保養人員：{m.assignee_name or '—'}｜檢查：{m.checker_name or '—'}"
            + (f"｜備註：{m.notes}" if m.notes else ""),
            floor=f"{int(m.room_no[:-2])}f" if m.room_no and m.room_no[:-2].isdigit() else "",
            room=m.room_no or "",
            ref={"kind": "ihg", "ragic_id": m.ragic_id, "room": m.room_no,
                 "ragic_url": _ragic_url(_SOURCE_PATH["ihg"], m.ragic_id)},
            since=d))
    return out


def _detect_a5(db: Session, wr: Any, cfg: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    from app.models.dazhi_repair import DazhiRepairCase
    from app.models.luqun_repair import LuqunRepairCase
    since = now - timedelta(days=cfg["room_repeat_days"])
    groups: dict[tuple[str, str], list[Any]] = {}
    for model, venue in ((DazhiRepairCase, "hotel"), (LuqunRepairCase, "mall")):
        rows = (db.query(model)
                  .filter(model.is_ragic_deleted.is_(False), model.occurred_at >= since).all())
        for c in rows:
            if c.is_excluded_flag:
                continue
            room, _ = wr._repair_location(c)
            if room:
                groups.setdefault((venue, room), []).append(c)
    out = []
    for (venue, room), cs in groups.items():
        if len(cs) < cfg["room_repeat_count"]:
            continue
        cs.sort(key=lambda c: c.occurred_at, reverse=True)
        def _one(c: Any) -> str:
            t = re.sub(r"\s+", " ", c.title or c.case_no or "").strip()
            return f"{c.occurred_at:%m/%d} {t[:40]}{'…' if len(t) > 40 else ''}"
        lines = "；".join(_one(c) for c in cs[:5]) + (f"…等 {len(cs)} 筆" if len(cs) > 5 else "")
        out.append(_mk(
            "A5", "info", venue, f"A5:{venue}:{room}",
            f"{room} 近 {cfg['room_repeat_days']} 天報修 {len(cs)} 次",
            lines, floor=f"{int(room[:-2])}f" if room[:-2].isdigit() else "", room=room,
            ref={"kind": "room", "room": room}, since=cs[-1].occurred_at.strftime("%Y-%m-%d")))
    return out


def compute_alerts(db: Session, *, ref_date: Optional[date] = None,
                   now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """只偵測、不寄信。每筆附上 last_sent／due（依去重規則，現在該不該寄）。"""
    from app.routers import war_room as wr          # 延遲 import：避免與 router 循環
    now = now or twnow()
    ref = ref_date or now.date()
    cfg = get_settings(db)
    out: list[dict[str, Any]] = []
    if cfg["enabled"].get("A1"):
        out += _detect_a1(db, wr, cfg)
    if cfg["enabled"].get("A2") or cfg["enabled"].get("A3"):
        out += _detect_points(db, wr, cfg, ref, now)
    if cfg["enabled"].get("A4"):
        out += _detect_a4(db, cfg, ref)
    if cfg["enabled"].get("A5"):
        out += _detect_a5(db, wr, cfg, now)

    sent = _sent_map(db)
    today = now.date()
    for a in out:
        last = sent.get(a["key"], "")
        a["last_sent"] = last
        rep = _repeat_days(a, cfg)
        if not last:
            a["due"] = True
        elif rep is None:
            a["due"] = False
        else:
            a["due"] = (today - date.fromisoformat(last)).days >= rep
    out.sort(key=lambda a: (LEVEL_ORDER[a["level"]], a["type"], -(a["wait_days"] or 0)))
    return out


# ── 收件人（由使用者在畫面維護）────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")


def get_recipient_list(db: Session) -> list[dict[str, Any]]:
    return _get_json(db, KEY_RECIPIENTS, [])


def save_recipient_list(db: Session, items: list[dict[str, Any]], who: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for it in items:
        email = str(it.get("email") or "").strip().lower()
        if not email:
            continue
        if not _EMAIL_RE.match(email):
            raise ValueError(f"email 格式不正確：{email}")
        if email in seen:
            raise ValueError(f"email 重複：{email}")
        seen.add(email)
        venues = [v for v in dict.fromkeys(it.get("venues") or []) if v in ("hotel", "mall")]
        if not venues:
            raise ValueError(f"{email} 請至少選一個館別")
        out.append({"email": email, "name": str(it.get("name") or "").strip()[:50],
                    "venues": venues, "enabled": bool(it.get("enabled", True))})
    if len(out) > 100:
        raise ValueError("收件人最多 100 位")
    _set_json(db, KEY_RECIPIENTS, out, who)
    return out


def recipients(db: Session) -> dict[str, Any]:
    """{'hotel': [email…], 'mall': [email…]}（只含啟用者）"""
    res: dict[str, Any] = {"hotel": [], "mall": []}
    for r in get_recipient_list(db):
        if not r.get("enabled", True):
            continue
        for v in r.get("venues", []):
            if v in res:
                res[v].append(r["email"])
    return res


def plan_mail(db: Session, alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """依收件人所屬館別分組：回傳 [{emails, venues, alerts}]。同一個人兩館都在 → 看到全部。"""
    rc = recipients(db)
    who: dict[str, set[str]] = {}
    for v in ("hotel", "mall"):
        for e in rc[v]:
            who.setdefault(e, set()).add(v)
    groups: dict[frozenset, list[str]] = {}
    for e, vs in who.items():
        groups.setdefault(frozenset(vs), []).append(e)
    plans = []
    for vs, emails in groups.items():
        sel = [a for a in alerts if a["venue"] == "both" or a["venue"] in vs]
        if sel:
            plans.append({"emails": sorted(emails), "venues": sorted(vs), "alerts": sel})
    return plans


# ── 信件內容與寄送 ───────────────────────────────────────────────────────────
_COLOR = {"critical": "#e74c3c", "warning": "#faad14", "info": "#4BA8E8"}


def render_mail(alerts: list[dict[str, Any]], title: str) -> tuple[str, str, str]:
    n_crit = sum(1 for a in alerts if a["level"] == "critical")
    subject = f"【Portal 戰情 KPI】{title} {len(alerts)} 項" + (f"（{n_crit} 項嚴重）" if n_crit else "")
    esc = _html.escape
    rows = "".join(
        f'<tr><td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;">'
        f'<span style="color:{_COLOR[a["level"]]};">●</span> {a["level_label"]}</td>'
        f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;">'
        f'<span style="color:#6b7280;font-size:12px;">{a["venue_label"]} · {a["type"]} {esc(a["type_label"])}</span><br>'
        f'<b>{esc(a["title"])}</b><br>'
        f'<span style="color:#6b7280;font-size:12px;">{esc(a["detail"])}</span></td></tr>'
        for a in alerts)
    body = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,'Microsoft JhengHei',sans-serif;background:#f0f4f8;padding:24px;">
<div style="max-width:720px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;">
<div style="background:linear-gradient(135deg,#1B3A5C,#4BA8E8);padding:20px 28px;">
<h2 style="color:#fff;margin:0;font-size:18px;">戰情 KPI 異常告警</h2>
<p style="color:rgba(255,255,255,.8);margin:4px 0 0;font-size:12px;">{twnow():%Y-%m-%d %H:%M} · 共 {len(alerts)} 項</p></div>
<div style="padding:20px 28px;"><table style="width:100%;border-collapse:collapse;font-size:14px;">{rows}</table>
<p style="color:#9ca3af;font-size:12px;margin-top:16px;">詳情請至 Portal「戰情 KPI → 告警」查看。</p></div></div></body></html>"""
    text = f"戰情 KPI 異常告警（{len(alerts)} 項）\n\n" + "\n\n".join(
        f"[{a['level_label']}] {a['venue_label']} {a['type']} {a['title']}\n  {a['detail']}" for a in alerts)
    return subject, body, text


def send_alerts(db: Session, alerts: list[dict[str, Any]], *, by: str, mode: str,
                dry_run: bool = False, title: str = "異常告警") -> dict[str, Any]:
    """寄出 alerts。dry_run＝只回傳「會寄給誰、寄哪些」，不寄、不記錄。"""
    plans = plan_mail(db, alerts)
    plan_out = [{"emails": p["emails"], "venues": p["venues"], "count": len(p["alerts"]),
                 "titles": [a["title"] for a in p["alerts"]]} for p in plans]
    result: dict[str, Any] = {
        "dry_run": dry_run, "plans": plan_out,
        "sent_mails": 0, "sent_alerts": 0, "errors": [],
    }
    if dry_run or not plans:
        if not plans:
            result["message"] = "沒有可寄的對象：尚未設定收件人（請按「收件人」新增並啟用）。"
        return result
    from app.services.email_service import _send
    ok_keys: set[str] = set()
    for p in plans:
        subject, html, text = render_mail(p["alerts"], title)
        for addr in p["emails"]:
            try:
                _send(addr, "", subject, html, text)
                result["sent_mails"] += 1
                ok_keys.update(a["key"] for a in p["alerts"])
            except Exception as exc:          # noqa: BLE001 — 寄不出去不連累主流程
                result["errors"].append(f"{addr}: {str(exc)[:200]}")
                logger.warning("戰情告警寄送失敗 %s：%s", addr, exc)
    if ok_keys:
        _mark_sent(db, sorted(ok_keys), twnow().date())
        _append_log(db, {"at": twnow().strftime("%Y-%m-%d %H:%M"), "by": by, "mode": mode,
                         "alerts": len(ok_keys), "mails": result["sent_mails"],
                         "recipients": sorted({e for p in plans for e in p["emails"]})})
    result["sent_alerts"] = len(ok_keys)
    return result


# ── 排程進入點（零參數、同步函式；AsyncIOScheduler 會丟到 executor 執行）───────
def _run(critical_only: bool, title: str, mode: str) -> dict[str, Any]:
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        cfg = get_settings(db)
        alerts = [a for a in compute_alerts(db) if a["due"]]
        if critical_only:
            alerts = [a for a in alerts if a["level"] == "critical"]
        if not alerts:
            return {"skipped": True, "message": "沒有需要通知的項目。"}
        if not cfg["auto_send"]:
            # 預設乾跑：只記 log，不寄信（使用者在「告警」頁手動決定）
            logger.info("war_room_alert[%s] 乾跑：%d 項待通知（auto_send=false，未寄信）", mode, len(alerts))
            return {"skipped": True, "dry_run": True, "pending": len(alerts)}
        return send_alerts(db, alerts, by="scheduler", mode=mode, title=title)
    except Exception:                       # noqa: BLE001
        logger.exception("war_room_alert 執行失敗")
        return {"skipped": True, "error": True}
    finally:
        db.close()


def _for_sync_tool(r: dict[str, Any]) -> dict[str, Any]:
    """對齊 sync_tool 期待的回傳格式。errors 一律 0：「寄不出去」不等於這支程式壞了（同 sync_alert）。"""
    return {
        "fetched": int(r.get("pending") or r.get("sent_alerts") or 0),
        "upserted": int(r.get("sent_alerts") or 0),
        "errors": 0, "skipped": bool(r.get("skipped")),
        "message": r.get("message") or (
            "乾跑（auto_send 關閉）：%s 項待通知，未寄信" % r.get("pending") if r.get("dry_run")
            else "寄出 %s 封、涵蓋 %s 項" % (r.get("sent_mails"), r.get("sent_alerts"))),
        "send_errors": r.get("errors") or [],
    }


def scan_critical() -> dict[str, Any]:
    """sync_tool 進入點：只處理嚴重等級（建議每 30 分）。"""
    return _for_sync_tool(_run(True, "嚴重異常", "scan"))


def daily_digest() -> dict[str, Any]:
    """sync_tool 進入點：每日彙整（建議每天 08:30）。"""
    return _for_sync_tool(_run(False, "每日彙整", "daily"))
