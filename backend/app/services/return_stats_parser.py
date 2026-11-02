"""
退件統計：Ragic 原始紀錄解析與狀態判定（規格 §3.4、§4）

純函式，不碰資料庫，方便單元測試。
"""
import re
from datetime import date

PROFILE_STANDARD = "standard_v1"   # 簽署日期N
PROFILE_DATE_LAYER = "date_layer_v1"  # 日期N（部分表單的工作流時間戳）
PROFILE_SEAL = "seal_v1"             # 用印申請單：主管簽名N／簽名日期N，無回應欄位

OTHER_ROLES = ["出納簽核", "財務簽核", "財務主管"]
REJECT_WORDS = ["退件", "退回", "駁回"]
WITHDRAW_WORDS = ["退簽"]
AGREE_WORDS = ["同意"]
SIG_PREFIX = "data:image"
_SLOT_RE = re.compile(r"^簽核主管(\d*)$")


def as_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return "；".join(str(x) for x in v if x not in (None, ""))
    if isinstance(v, str) and v.startswith(SIG_PREFIX):
        return "（簽名圖）"
    return str(v)


def parse_date(s) -> date | None:
    """'2026/03/04' / '2026-03-04' → date；無法解析回傳 None。"""
    if not s:
        return None
    nums = re.findall(r"\d+", str(s))
    if len(nums) < 3:
        return None
    try:
        return date(int(nums[0]), int(nums[1]), int(nums[2]))
    except ValueError:
        return None


_BB_TAG_RE = re.compile(
    r"\[/?(?:br|size|font|b|i|u|p|div|span|color|align|center|h[1-6])(?:=[^\]]*)?\]", re.IGNORECASE)
_HTML_BR_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def html_to_text(s) -> str:
    """
    Ragic 的富文字欄位（事由等）內容是 HTML／BBCode 標記，例如 [br][/br]、[size=18px]、<br>。
    轉為純文字：換行標記變成換行，其餘標記移除，常見 HTML 實體還原。
    """
    if not s:
        return ""
    t = str(s)
    t = _HTML_BR_RE.sub("\n", t)
    t = re.sub(r"\[/?br\]", "\n", t, flags=re.IGNORECASE)
    t = _BB_TAG_RE.sub("", t)
    t = re.sub(r"</?\s*(p|div|li)\b[^>]*>", "\n", t, flags=re.IGNORECASE)
    t = _HTML_TAG_RE.sub("", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    lines = [ln.rstrip() for ln in t.replace("\r\n", "\n").split("\n")]
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def parse_amount(s) -> int | None:
    t = re.sub(r"[^\d.\-]", "", as_text(s))
    if not t:
        return None
    try:
        return int(float(t))
    except ValueError:
        return None


def _date_field(profile: str, sfx: str) -> str:
    return f"日期{sfx}" if profile == PROFILE_DATE_LAYER else f"簽署日期{sfx}"


def _parse_seal_steps(raw: dict) -> list[dict]:
    """用印申請單：簽核格為「主管簽名N」（簽名圖）＋「簽名日期N」，沒有回應欄位，也沒有主管姓名。"""
    suffixes = set()
    for k in raw:
        m = re.match(r"^主管簽名(\d*)$", k)
        if m:
            suffixes.add(m.group(1))
    steps = []
    for sfx in sorted(suffixes, key=lambda s: int(s) if s else 0):
        sig = as_text(raw.get(f"主管簽名{sfx}"))
        date_txt = as_text(raw.get(f"簽名日期{sfx}"))
        if sig or date_txt:
            steps.append({"role_field": f"主管簽名{sfx}", "approver_text": sig,
                          "sign_date": parse_date(date_txt), "remark": None})
    for i, st in enumerate(steps, start=1):
        st["step_no"] = i
        st["is_inferred_last"] = False
    return steps


CODE_AGREE = "A"      # 同意（Ragic 步驟狀態 F）
CODE_REJECT = "REJ"   # 拒絕簽核（Ragic UI 顯示「拒絕簽核」，使用者稱為退簽）
CODE_PENDING = "N"    # 尚未處理


def steps_from_approval(lst: list) -> list[dict]:
    """
    Ragic 清單 API 加上 approval=true 時的 _approval_steps（2026-11-02 探測確認）。
    每一步：_signer 簽核人、_signer_comment 備註、_step_response 代碼、_step_actionTime 時間。
    """
    steps = []
    for i, s in enumerate(lst or [], start=1):
        steps.append({
            "step_no": i,
            "role_field": as_text(s.get("_step_name")),
            "approver_text": as_text(s.get("_signer")),
            "sign_date": parse_date((s.get("_step_actionTime") or "")[:10]),
            "remark": (s.get("_signer_comment") or None),
            "code": (as_text(s.get("_step_response")) or "").strip().upper(),
            "is_inferred_last": False,
        })
    return steps


def parse_steps(raw: dict, profile: str = PROFILE_STANDARD) -> list[dict]:
    """依簽核主管N 的 N 排序，同步對應簽署日期N、回應N。"""
    if profile == PROFILE_SEAL:
        return _parse_seal_steps(raw)
    suffixes = set()
    for k in raw:
        m = _SLOT_RE.match(k)
        if m:
            suffixes.add(m.group(1))
    steps = []
    for sfx in sorted(suffixes, key=lambda s: int(s) if s else 0):
        name = as_text(raw.get(f"簽核主管{sfx}"))
        date_txt = as_text(raw.get(_date_field(profile, sfx)))
        remark = as_text(raw.get(f"回應{sfx}"))
        if name or date_txt or remark:
            steps.append({
                "role_field": f"簽核主管{sfx}",
                "approver_text": name,
                "sign_date": parse_date(date_txt),
                "remark": remark or None,
            })
    for role in OTHER_ROLES:
        name = as_text(raw.get(role))
        if name:
            steps.append({"role_field": role, "approver_text": name,
                          "sign_date": None, "remark": None})
    for i, st in enumerate(steps, start=1):
        st["step_no"] = i
        st["is_inferred_last"] = False
    return steps


def infer_last(ragic_status: str, steps: list[dict]) -> int | None:
    """規則（使用者裁示）：只看簽核狀態 F，取簽署日期最晚的簽核主管格；同日多格全部標示。"""
    if (ragic_status or "").upper() != "F":
        return None
    dated = [s for s in steps if s["role_field"].startswith("簽核主管") and s["sign_date"]]
    if not dated:
        return None
    latest = max(s["sign_date"] for s in dated)
    last_nos = []
    for s in dated:
        if s["sign_date"] == latest:
            s["is_inferred_last"] = True
            last_nos.append(s["step_no"])
    return last_nos[0] if last_nos else None


def classify_approval(steps: list[dict]) -> tuple[str, str]:
    """依 approval=true 的步驟代碼判定（2026-11-02 裁示：REJ＝退簽）。"""
    rej = [s for s in steps if s.get("code") == CODE_REJECT]
    if rej:
        s = rej[0]
        return "withdrawn", f"第{s['step_no']}步（{s['approver_text'] or '—'}）拒絕簽核"
    if any(s.get("code") != CODE_AGREE for s in steps):
        return "pending", "尚有簽核步驟未處理"
    return "approved", "所有簽核步驟皆為同意"


def classify(ragic_status: str, steps: list[dict]) -> tuple[str, str]:
    """回傳 (outcome, outcome_reason)。判定只看簽核狀態與「回應」文字（不看事由等欄位）。"""
    st = (ragic_status or "").strip().upper()
    remarks = [(s["step_no"], s["remark"] or "") for s in steps if s["remark"]]

    if st == "REJ":
        return "rejected", "簽核狀態=REJ"
    for no, text in remarks:
        for w in WITHDRAW_WORDS:
            if w in text:
                return "withdrawn", f"第{no}步回應含「{w}」"
    for no, text in remarks:
        for w in REJECT_WORDS:
            if w in text:
                return "rejected", f"第{no}步回應含「{w}」"
    if st == "F":
        for no, text in remarks:
            if any(w in text for w in AGREE_WORDS):
                return "approved", f"簽核狀態=F（第{no}步回應含「同意」）"
        return "approved", "簽核狀態=F"
    for no, text in remarks:
        for w in AGREE_WORDS:
            if w in text:
                return "agreed", f"第{no}步回應含「{w}」，尚未完成"
    if st == "N" or st == "":
        return "pending", "簽核狀態=N（待審）"
    return "unknown", f"簽核狀態={st}，無法判定"


def rejection_note(outcome: str, steps: list[dict]) -> str:
    # approval 來源：退簽的原因就是拒絕簽核那一步的備註
    if outcome == "withdrawn" and any(s.get("code") for s in steps):
        for s in steps:
            if s.get("code") == CODE_REJECT:
                return s.get("remark") or ""
        return ""
    """
    退件原因（使用者 2026-11-02 裁示）：取「被判定那一步」的備註。
    - withdrawn：第一個回應含「退簽」的步驟的備註
    - rejected ：第一個回應含「退件／退回／駁回」的步驟的備註
    - 其他（含只有簽核狀態=REJ、沒有備註可對應）：回傳空字串，不推測步驟
    """
    if outcome == "withdrawn":
        words = WITHDRAW_WORDS
    elif outcome == "rejected":
        words = REJECT_WORDS
    else:
        return ""
    for s in steps:
        t = s["remark"] or ""
        if any(w in t for w in words):
            return t
    return ""


def parse_record(raw: dict, profile: str = PROFILE_STANDARD) -> dict:
    """將一筆 Ragic 原始 dict 轉為統一結構（規格 §3.5）。"""
    status = as_text(raw.get("簽核狀態") or raw.get("狀態")).strip().upper()
    approval = raw.get("_approval_steps")
    if isinstance(approval, list) and approval:
        steps = steps_from_approval(approval)
        last_no = None
        outcome, reason = classify_approval(steps)
    else:
        steps = parse_steps(raw, profile)
        last_no = infer_last(status, steps)
        outcome, reason = classify(status, steps)
    last_date = max((s["sign_date"] for s in steps if s["sign_date"]), default=None)
    return {
        "applicant": as_text(raw.get("申請人") or raw.get("請款人")) or None,
        "apply_date": parse_date(as_text(raw.get("申請日期") or raw.get("填單日期"))),
        "amount": parse_amount(raw.get("總計") or raw.get("應付(繳)款") or raw.get("總金額")),
        "purpose": html_to_text(as_text(raw.get("事由") or raw.get("說明") or raw.get("主旨"))) or None,
        "ragic_status": status or None,
        "submitter": as_text(raw.get("送出簽核人") or raw.get("送出簽核人姓名")) or None,
        "next_approver": as_text(raw.get("下一位簽核人")) or None,
        "outcome": outcome,
        "outcome_reason": reason,
        "inferred_last_step": last_no,
        "last_sign_date": last_date,
        "steps": steps,
    }
