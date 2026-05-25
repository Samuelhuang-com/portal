"""
PPT 自動匯出 Service (C-4)
===========================

排程：每月固定日期（預設每月 5 日 08:00）自動產生飯店 Dashboard PPT，
      儲存至 static/exports/hotel_{year}_{month:02d}.pptx。

設計：
  - 所有 Dashboard 數據由後端獨立計算（不依賴前端 payload）
  - 使用 hotel_overview API functions 直接查 DB
  - 排程由 main.py 的 APScheduler 統一管理
  - 產出檔案保留最近 12 份（超過自動刪除最舊的）

Config（環境變數 / settings）：
  PPT_AUTO_EXPORT_DAY    = 5       # 每月幾號執行（1-28）
  PPT_AUTO_EXPORT_HOUR   = 8       # 幾點執行（0-23）
  PPT_AUTO_EXPORT_KEEP   = 12      # 保留最近幾份
"""

import json
import logging
import os
from datetime import datetime, date
from io import BytesIO
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ppt_auto_export")

EXPORT_DIR = Path(__file__).parent.parent / "static" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# 排程設定（可由 settings 覆蓋）
AUTO_EXPORT_DAY  = int(os.getenv("PPT_AUTO_EXPORT_DAY",  "5"))
AUTO_EXPORT_HOUR = int(os.getenv("PPT_AUTO_EXPORT_HOUR", "8"))
AUTO_EXPORT_KEEP = int(os.getenv("PPT_AUTO_EXPORT_KEEP", "12"))


def _compute_dashboard_frontend_data(year: int, month: int, db) -> dict:
    """
    後端自行計算 Dashboard 數據，替代前端 payload。
    回傳格式與 FrontendData 相容。
    """
    try:
        from app.routers.hotel_overview import (
            get_hotel_overview_stats,
            get_hotel_daily_hours,
            get_hotel_monthly_hours,
            get_hotel_person_hours,
        )
        from app.models.dazhi_repair import DazhiRepairCase

        # ── KPI Summary ──────────────────────────────────────────────────────
        stats = get_hotel_overview_stats(year, month, db)
        kpi_summary = {
            "total_cases":      stats.get("total_cases", 0),
            "total_completed":  stats.get("completed_cases", 0),
            "total_work_hours": stats.get("total_hours", 0),
            "completion_rate":  stats.get("completion_rate", 0),
        }

        # ── Source Cards ─────────────────────────────────────────────────────
        source_cards = []
        for src in stats.get("sources", []):
            source_cards.append({
                "category":       src.get("name", ""),
                "total":          src.get("total", 0),
                "completed":      src.get("completed", 0),
                "work_hours":     src.get("hours", 0),
                "completion_rate": src.get("rate", 0),
            })

        # ── Repair Costs ─────────────────────────────────────────────────────
        # 累計至指定月份的費用
        all_cases = db.query(DazhiRepairCase).all()
        outsource   = sum(c.outsource_fee   or 0 for c in all_cases
                          if c.occurred_at and
                          (c.occurred_at.year < year or
                           (c.occurred_at.year == year and c.occurred_at.month <= month)))
        maintenance = sum(c.maintenance_fee or 0 for c in all_cases
                          if c.occurred_at and
                          (c.occurred_at.year < year or
                           (c.occurred_at.year == year and c.occurred_at.month <= month)))
        deduction   = sum(c.deduction_fee   or 0 for c in all_cases
                          if c.occurred_at and
                          (c.occurred_at.year < year or
                           (c.occurred_at.year == year and c.occurred_at.month <= month))
                          if hasattr(c, "deduction_fee"))
        repair_costs = [
            {"category": "外包費", "amount": outsource},
            {"category": "保養費", "amount": maintenance},
            {"category": "扣款費", "amount": deduction},
        ]

        # ── Bar Chart Data（各來源工項/完成數）────────────────────────────────
        bar_chart_data = [
            {"date": s.get("name",""), "工項數": s.get("total",0), "完成數": s.get("completed",0)}
            for s in stats.get("sources", [])
        ]

        # ── Rate Chart Data（各來源完成率）────────────────────────────────────
        rate_chart_data = [
            {"date": s.get("name",""), "rate": s.get("rate", 0)}
            for s in stats.get("sources", [])
        ]

        # ── Trend Data（最近12個月）────────────────────────────────────────────
        monthly = get_hotel_monthly_hours(year, db)
        months_list = []
        for m in range(1, 13):
            label = f"{year}/{m:02d}"
            total_cases = 0
            completed_cases = 0
            for row in monthly.get("rows", []):
                cases = row.get("cases", [])
                if m - 1 < len(cases):
                    total_cases += cases[m - 1]
            months_list.append({
                "date":      label,
                "total":     total_cases,
                "completed": completed_cases,
            })
        dazhi_trend_data = months_list

        # ── Hours Pie Data（各來源工時占比）────────────────────────────────────
        daily = get_hotel_daily_hours(year, month, db)
        hours_pie_data = [
            {"category": r.get("category",""), "hours": r.get("total", 0)}
            for r in daily.get("rows", [])
        ]

        return {
            "kpi_summary":      kpi_summary,
            "source_cards":     source_cards,
            "repair_costs":     repair_costs,
            "bar_chart_data":   bar_chart_data,
            "rate_chart_data":  rate_chart_data,
            "dazhi_trend_data": dazhi_trend_data,
            "hours_pie_data":   hours_pie_data,
        }

    except Exception as e:
        logger.warning("_compute_dashboard_frontend_data failed: %s", e)
        return {}


def _cleanup_old_exports(keep: int = AUTO_EXPORT_KEEP):
    """保留最近 keep 份，刪除多餘的舊檔案"""
    files = sorted(EXPORT_DIR.glob("hotel_*.pptx"), key=lambda f: f.stat().st_mtime)
    while len(files) > keep:
        oldest = files.pop(0)
        try:
            oldest.unlink()
            logger.info("Deleted old export: %s", oldest.name)
        except Exception:
            pass


def run_auto_export():
    """
    APScheduler 呼叫的入口函式。
    計算上個月的數據並產生 PPTX，存至 EXPORT_DIR。
    """
    from app.core.database import SessionLocal
    from app.routers.hotel_ppt_export import (
        _build_hotel_pptx_v2, _load_merged_config, FrontendData,
    )

    now   = datetime.now()
    # 以「上個月」的資料為主
    if now.month == 1:
        year, month = now.year - 1, 12
    else:
        year, month = now.year, now.month - 1

    logger.info("PPT auto-export starting: %d/%02d", year, month)

    db = SessionLocal()
    try:
        config_list, template_id = _load_merged_config(db)
        enabled_config = [c for c in config_list if c.get("enabled")]

        # 計算 Dashboard 數據
        fd_dict = _compute_dashboard_frontend_data(year, month, db)
        frontend_data = FrontendData(**{k: v for k, v in fd_dict.items()
                                        if k in FrontendData.model_fields})

        buf = _build_hotel_pptx_v2(
            params         = {"year": year, "month": month, "inspection_date": ""},
            frontend_data  = frontend_data,
            enabled_config = enabled_config,
            db             = db,
            template_id    = template_id,
        )

        # 儲存至 static/exports/
        out_path = EXPORT_DIR / f"hotel_{year}_{month:02d}.pptx"
        out_path.write_bytes(buf.read())
        logger.info("PPT auto-export saved: %s", out_path)

        # 清理舊檔
        _cleanup_old_exports()

        # 寫入歷史紀錄
        try:
            from app.models.ppt_export_history import PptExportHistory
            hist = PptExportHistory(
                module_key    = "hotel_overview",
                year          = year,
                month         = month,
                exported_by   = "scheduler",
                exported_at   = now,
                sections_json = json.dumps(
                    [c["export_key"] for c in enabled_config], ensure_ascii=False
                ),
                template_id   = template_id,
            )
            db.add(hist)
            db.commit()
        except Exception as e:
            logger.warning("Failed to write auto-export history: %s", e)

    except Exception as e:
        logger.error("PPT auto-export failed: %s", e, exc_info=True)
    finally:
        db.close()
