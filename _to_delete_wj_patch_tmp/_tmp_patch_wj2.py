import hashlib, sys

SRC = "backend/app/routers/work_journal.py"
DST = "backend/app/routers/_wj_patched_tmp.py"

data = open(SRC, "r", encoding="utf-8").read()

expected_sha = "d5acb206e5b448d5fff61b4a7464fb97d101f804be7981c25f470e08bef932fd"
actual_sha = hashlib.sha256(data.encode("utf-8")).hexdigest()
if actual_sha != expected_sha:
    print("SHA MISMATCH, aborting. actual=", actual_sha)
    sys.exit(1)

# ── Patch 1: insert new helpers (_parse_pm_datetime / _group_pm_worklog_rows)
#    right before _pm_detail_records_payload ──────────────────────────────────

OLD_HELPERS_ANCHOR = '''def _pm_detail_records_payload(recs: list) -> list[dict]:'''

NEW_HELPERS = '''def _parse_pm_datetime(s: str) -> Optional[datetime]:
    """解析週期保養子表（Sheet24／Sheet28 巢狀維修記錄）的 Ragic 原始日期時間字串，
    例如 '2026/07/13 09:14:26' 或 '2026/07/13 09:14'。解析失敗（含空字串）回 None。
    2026-07-14 新增：供 _group_pm_worklog_rows 依「時間開始」實際日期歸戶使用。"""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _group_pm_worklog_rows(recs: list, target: _date, fallback_person: str) -> list[dict]:
    """
    週期保養（mall_pm／full_bldg_pm）維修記錄子表版本的 _group_detail_rows。
    子表 start_time/end_time 為 Ragic 原始字串（非 datetime），先以 _parse_pm_datetime 解析，
    再篩選至「時間開始」日期 == target 後按人員（staff_name）分組合併。
    回傳 [{person, work_min(int|None), start_time, end_time}]。

    規格（2026-06-11 業主確認 _group_detail_rows，2026-07-14 推廣至週期保養類）：
    有維修記錄（子表）時，一律以子表「時間開始」實際日期歸戶，不採用工單頭排定日期
    （例如颱風延期：排定日期 07/10、實際維修 07/13 → 工作日誌應呈現在 07/13）。
    """
    groups: dict[str, dict] = {}
    for r in recs:
        start_dt = _parse_pm_datetime(r.start_time)
        if not start_dt or start_dt.date() != target:
            continue
        end_dt = _parse_pm_datetime(r.end_time)
        sec = 0.0
        has_end = end_dt is not None
        if end_dt and end_dt > start_dt:
            sec = (end_dt - start_dt).total_seconds()
        for person in _split_detail_persons(r.staff_name, fallback_person):
            g = groups.setdefault(person, {
                "sec": 0.0, "has_end": False, "min_start": None, "max_end": None,
            })
            g["sec"] += sec
            g["has_end"] = g["has_end"] or has_end
            if g["min_start"] is None or start_dt < g["min_start"]:
                g["min_start"] = start_dt
            if end_dt and (g["max_end"] is None or end_dt > g["max_end"]):
                g["max_end"] = end_dt

    out = []
    for person, g in groups.items():
        out.append({
            "person":     person,
            "work_min":   round(g["sec"] / 60) if g["has_end"] else None,
            "start_time": g["min_start"].strftime("%H:%M") if g["min_start"] else "",
            "end_time":   g["max_end"].strftime("%H:%M")   if g["max_end"]   else "",
        })
    return out


def _pm_detail_records_payload(recs: list) -> list[dict]:'''

assert data.count(OLD_HELPERS_ANCHOR) == 1, f"anchor count={data.count(OLD_HELPERS_ANCHOR)}"
data = data.replace(OLD_HELPERS_ANCHOR, NEW_HELPERS, 1)

# ── Patch 2: _fetch_mall_pm ───────────────────────────────────────────────────

OLD_MALL_PM = '''def _fetch_mall_pm(db: Session, year: int, month: int, day: int) -> list[dict]:
    """商場週期保養：mall_pm_batch + mall_pm_batch_item（+ mall_pm_item_worklog 維修記錄子表）"""
    rows = []
    period_month = f"{year}/{month:02d}"
    sched_day    = f"{month:02d}/{day:02d}"

    batches = (
        db.query(MallPeriodicMaintenanceBatch)
        .filter(MallPeriodicMaintenanceBatch.period_month == period_month)
        .all()
    )
    if not batches:
        return rows
    batch_map = {b.ragic_id: b for b in batches}
    batch_ids = set(batch_map.keys())

    items = (
        db.query(MallPeriodicMaintenanceItem)
        .filter(
            MallPeriodicMaintenanceItem.batch_ragic_id.in_(batch_ids),
            MallPeriodicMaintenanceItem.scheduled_date == sched_day,
        )
        .all()
    )
    if not items:
        return rows

    # 預載維修記錄子表（Sheet24 巢狀子表格），依項目分組、按子表項次排序
    item_ids = {item.ragic_id for item in items}
    wl_map: dict[str, list] = defaultdict(list)
    for wl in db.query(MallPMItemWorklog).filter(MallPMItemWorklog.item_ragic_id.in_(item_ids)).all():
        wl_map[wl.item_ragic_id].append(wl)
    for wls in wl_map.values():
        wls.sort(key=lambda w: w.seq_no)

    for item in items:
        batch = batch_map.get(item.batch_ragic_id)
        task = " ".join(filter(None, [item.task_name, item.location]))
        est  = item.estimated_minutes if item.estimated_minutes else None
        wm   = int(item.estimated_minutes) if item.estimated_minutes and item.estimated_minutes > 0 else None
        detail_recs = _pm_detail_records_payload(wl_map.get(item.ragic_id, []))
        for person in _persons(item.executor_name):
            rows.append(_make_row(
                source="mall_pm",
                category="例行維護",
                task=task or "(無說明)",
                person=person,
                est_min=est,
                start_time=item.start_time or "",
                end_time=item.end_time or "",
                work_min=wm,
                remark=item.result_note or "",
                ragic_id=item.ragic_id,
                ragic_url=_ragic_url(_SOURCE_PATH["mall_pm"], item.ragic_id),
                detail_records=detail_recs,
                detail={
                    "日誌編號":  (batch.journal_no if batch else "") or "",
                    "保養月份":  (batch.period_month if batch else "") or "",
                    "類別":      item.category or "",
                    "頻率":      item.frequency or "",
                    "區域":      item.location or "",
                    "排定日期":  item.scheduled_date or "",
                    "排定人員":  item.scheduler_name or "",
                    "執行人員":  item.executor_name or "",
                    "完成狀況":  "已完成" if item.is_completed else "未完成",
                    "執行結果":  item.result_note or "",
                    "異常說明":  item.abnormal_note if getattr(item, "abnormal_flag", False) else "",
                },
            ))
    return rows'''

NEW_MALL_PM = '''def _fetch_mall_pm(db: Session, year: int, month: int, day: int) -> list[dict]:
    """商場週期保養：mall_pm_batch + mall_pm_batch_item（+ mall_pm_item_worklog 維修記錄子表）
    無維修記錄（子表無可解析「時間開始」）→ 排定日期口徑（原邏輯，人員=執行人員、工時=預估工時）。
    有維修記錄（子表）→ 改以子表「時間開始」實際日期歸戶，忽略排定日期（見 _group_pm_worklog_rows）。
    2026-07-14：修正排定日期與實際維修日期不一致（如颱風延期）時工作日誌顯示錯誤日期的問題。
    """
    rows = []
    target = _date(year, month, day)
    period_month = f"{year}/{month:02d}"
    sched_day    = f"{month:02d}/{day:02d}"

    batches = (
        db.query(MallPeriodicMaintenanceBatch)
        .filter(MallPeriodicMaintenanceBatch.period_month == period_month)
        .all()
    )
    if not batches:
        return rows
    batch_map = {b.ragic_id: b for b in batches}
    batch_ids = set(batch_map.keys())

    # 不再以 scheduled_date 篩選 SQL：需取得整批項目才能判斷是否有子表活動落在 target
    items = (
        db.query(MallPeriodicMaintenanceItem)
        .filter(MallPeriodicMaintenanceItem.batch_ragic_id.in_(batch_ids))
        .all()
    )
    if not items:
        return rows

    # 預載維修記錄子表（Sheet24 巢狀子表格），依項目分組、按子表項次排序
    item_ids = {item.ragic_id for item in items}
    wl_map: dict[str, list] = defaultdict(list)
    for wl in db.query(MallPMItemWorklog).filter(MallPMItemWorklog.item_ragic_id.in_(item_ids)).all():
        wl_map[wl.item_ragic_id].append(wl)
    for wls in wl_map.values():
        wls.sort(key=lambda w: w.seq_no)

    for item in items:
        batch = batch_map.get(item.batch_ragic_id)
        task = " ".join(filter(None, [item.task_name, item.location]))
        est  = item.estimated_minutes if item.estimated_minutes else None
        item_wls    = wl_map.get(item.ragic_id, [])
        dated_wls   = [wl for wl in item_wls if _parse_pm_datetime(wl.start_time)]
        detail_recs = _pm_detail_records_payload(item_wls)

        common = dict(
            source="mall_pm",
            category="例行維護",
            task=task or "(無說明)",
            est_min=est,
            remark=item.result_note or "",
            ragic_id=item.ragic_id,
            ragic_url=_ragic_url(_SOURCE_PATH["mall_pm"], item.ragic_id),
            detail_records=detail_recs,
            detail={
                "日誌編號":  (batch.journal_no if batch else "") or "",
                "保養月份":  (batch.period_month if batch else "") or "",
                "類別":      item.category or "",
                "頻率":      item.frequency or "",
                "區域":      item.location or "",
                "排定日期":  item.scheduled_date or "",
                "排定人員":  item.scheduler_name or "",
                "執行人員":  item.executor_name or "",
                "完成狀況":  "已完成" if item.is_completed else "未完成",
                "執行結果":  item.result_note or "",
                "異常說明":  item.abnormal_note if getattr(item, "abnormal_flag", False) else "",
            },
        )

        if dated_wls:
            # 有維修記錄（子表）→ 以子表「時間開始」實際日期歸戶，忽略排定日期
            groups = _group_pm_worklog_rows(dated_wls, target, item.executor_name or "")
            if not groups:
                continue   # 該日無子表活動 → 此項目不出現在本日日誌
            for g in groups:
                rows.append(_make_row(
                    person=g["person"],
                    start_time=g["start_time"],
                    end_time=g["end_time"],
                    work_min=g["work_min"],
                    **common,
                ))
        else:
            # 無維修記錄（或子表無可解析時間）→ 排定日期口徑（原邏輯）
            if item.scheduled_date != sched_day:
                continue
            wm = int(item.estimated_minutes) if item.estimated_minutes and item.estimated_minutes > 0 else None
            for person in _persons(item.executor_name):
                rows.append(_make_row(
                    person=person,
                    start_time=item.start_time or "",
                    end_time=item.end_time or "",
                    work_min=wm,
                    **common,
                ))
    return rows'''

assert data.count(OLD_MALL_PM) == 1, f"mall_pm anchor count={data.count(OLD_MALL_PM)}"
data = data.replace(OLD_MALL_PM, NEW_MALL_PM, 1)

# ── Patch 3: _fetch_full_bldg_pm ──────────────────────────────────────────────

OLD_FULL_BLDG_PM = '''def _fetch_full_bldg_pm(db: Session, year: int, month: int, day: int) -> list[dict]:
    """整棟保養：full_bldg_pm_batch + full_bldg_pm_batch_item（+ full_bldg_pm_item_worklog 維修記錄子表）"""
    rows = []
    period_month = f"{year}/{month:02d}"
    sched_day    = f"{month:02d}/{day:02d}"

    batches = (
        db.query(FullBldgPMBatch)
        .filter(FullBldgPMBatch.period_month == period_month)
        .all()
    )
    if not batches:
        return rows
    batch_map = {b.ragic_id: b for b in batches}
    batch_ids = set(batch_map.keys())

    items = (
        db.query(FullBldgPMItem)
        .filter(
            FullBldgPMItem.batch_ragic_id.in_(batch_ids),
            FullBldgPMItem.scheduled_date == sched_day,
        )
        .all()
    )
    if not items:
        return rows

    # 預載維修記錄子表（Sheet28 巢狀子表格），依項目分組、按子表項次排序
    item_ids = {item.ragic_id for item in items}
    wl_map: dict[str, list] = defaultdict(list)
    for wl in db.query(FullBldgPMItemWorklog).filter(FullBldgPMItemWorklog.item_ragic_id.in_(item_ids)).all():
        wl_map[wl.item_ragic_id].append(wl)
    for wls in wl_map.values():
        wls.sort(key=lambda w: w.seq_no)

    for item in items:
        batch = batch_map.get(item.batch_ragic_id)
        task = " ".join(filter(None, [item.task_name, item.location]))
        est  = item.estimated_minutes if item.estimated_minutes else None
        wm   = int(item.estimated_minutes) if item.estimated_minutes and item.estimated_minutes > 0 else None
        detail_recs = _pm_detail_records_payload(wl_map.get(item.ragic_id, []))
        for person in _persons(item.executor_name):
            rows.append(_make_row(
                source="full_bldg_pm",
                category="例行維護",
                task=task or "(無說明)",
                person=person,
                est_min=est,
                start_time=item.start_time or "",
                end_time=item.end_time or "",
                work_min=wm,
                remark=item.result_note or "",
                ragic_id=item.ragic_id,
                ragic_url=_ragic_url(_SOURCE_PATH["full_bldg_pm"], item.ragic_id),
                detail_records=detail_recs,
                detail={
                    "日誌編號":  (batch.journal_no if batch else "") or "",
                    "保養月份":  (batch.period_month if batch else "") or "",
                    "類別":      item.category or "",
                    "頻率":      item.frequency or "",
                    "區域":      item.location or "",
                    "排定日期":  item.scheduled_date or "",
                    "排定人員":  item.scheduler_name or "",
                    "執行人員":  item.executor_name or "",
                    "完成狀況":  "已完成" if item.is_completed else "未完成",
                    "執行結果":  item.result_note or "",
                    "異常說明":  item.abnormal_note if getattr(item, "abnormal_flag", False) else "",
                },
            ))
    return rows'''

NEW_FULL_BLDG_PM = '''def _fetch_full_bldg_pm(db: Session, year: int, month: int, day: int) -> list[dict]:
    """整棟保養：full_bldg_pm_batch + full_bldg_pm_batch_item（+ full_bldg_pm_item_worklog 維修記錄子表）
    無維修記錄（子表無可解析「時間開始」）→ 排定日期口徑（原邏輯，人員=執行人員、工時=預估工時）。
    有維修記錄（子表）→ 改以子表「時間開始」實際日期歸戶，忽略排定日期（見 _group_pm_worklog_rows）。
    2026-07-14：修正排定日期與實際維修日期不一致（如颱風延期）時工作日誌顯示錯誤日期的問題。
    """
    rows = []
    target = _date(year, month, day)
    period_month = f"{year}/{month:02d}"
    sched_day    = f"{month:02d}/{day:02d}"

    batches = (
        db.query(FullBldgPMBatch)
        .filter(FullBldgPMBatch.period_month == period_month)
        .all()
    )
    if not batches:
        return rows
    batch_map = {b.ragic_id: b for b in batches}
    batch_ids = set(batch_map.keys())

    # 不再以 scheduled_date 篩選 SQL：需取得整批項目才能判斷是否有子表活動落在 target
    items = (
        db.query(FullBldgPMItem)
        .filter(FullBldgPMItem.batch_ragic_id.in_(batch_ids))
        .all()
    )
    if not items:
        return rows

    # 預載維修記錄子表（Sheet28 巢狀子表格），依項目分組、按子表項次排序
    item_ids = {item.ragic_id for item in items}
    wl_map: dict[str, list] = defaultdict(list)
    for wl in db.query(FullBldgPMItemWorklog).filter(FullBldgPMItemWorklog.item_ragic_id.in_(item_ids)).all():
        wl_map[wl.item_ragic_id].append(wl)
    for wls in wl_map.values():
        wls.sort(key=lambda w: w.seq_no)

    for item in items:
        batch = batch_map.get(item.batch_ragic_id)
        task = " ".join(filter(None, [item.task_name, item.location]))
        est  = item.estimated_minutes if item.estimated_minutes else None
        item_wls    = wl_map.get(item.ragic_id, [])
        dated_wls   = [wl for wl in item_wls if _parse_pm_datetime(wl.start_time)]
        detail_recs = _pm_detail_records_payload(item_wls)

        common = dict(
            source="full_bldg_pm",
            category="例行維護",
            task=task or "(無說明)",
            est_min=est,
            remark=item.result_note or "",
            ragic_id=item.ragic_id,
            ragic_url=_ragic_url(_SOURCE_PATH["full_bldg_pm"], item.ragic_id),
            detail_records=detail_recs,
            detail={
                "日誌編號":  (batch.journal_no if batch else "") or "",
                "保養月份":  (batch.period_month if batch else "") or "",
                "類別":      item.category or "",
                "頻率":      item.frequency or "",
                "區域":      item.location or "",
                "排定日期":  item.scheduled_date or "",
                "排定人員":  item.scheduler_name or "",
                "執行人員":  item.executor_name or "",
                "完成狀況":  "已完成" if item.is_completed else "未完成",
                "執行結果":  item.result_note or "",
                "異常說明":  item.abnormal_note if getattr(item, "abnormal_flag", False) else "",
            },
        )

        if dated_wls:
            # 有維修記錄（子表）→ 以子表「時間開始」實際日期歸戶，忽略排定日期
            groups = _group_pm_worklog_rows(dated_wls, target, item.executor_name or "")
            if not groups:
                continue   # 該日無子表活動 → 此項目不出現在本日日誌
            for g in groups:
                rows.append(_make_row(
                    person=g["person"],
                    start_time=g["start_time"],
                    end_time=g["end_time"],
                    work_min=g["work_min"],
                    **common,
                ))
        else:
            # 無維修記錄（或子表無可解析時間）→ 排定日期口徑（原邏輯）
            if item.scheduled_date != sched_day:
                continue
            wm = int(item.estimated_minutes) if item.estimated_minutes and item.estimated_minutes > 0 else None
            for person in _persons(item.executor_name):
                rows.append(_make_row(
                    person=person,
                    start_time=item.start_time or "",
                    end_time=item.end_time or "",
                    work_min=wm,
                    **common,
                ))
    return rows'''

assert data.count(OLD_FULL_BLDG_PM) == 1, f"full_bldg_pm anchor count={data.count(OLD_FULL_BLDG_PM)}"
data = data.replace(OLD_FULL_BLDG_PM, NEW_FULL_BLDG_PM, 1)

with open(DST, "w", encoding="utf-8") as f:
    f.write(data)

print("OK, wrote", DST, len(data))
