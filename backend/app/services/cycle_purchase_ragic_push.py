"""
週期採購 —「彙整單 →  Ragic 週採請購單」的推送客戶端

═══════════════════════════════════════════════════════════════════════════
2026-09-18：拋轉目標由 sheet 57「週採採購單」改為 sheet 58「★週採請購單」
═══════════════════════════════════════════════════════════════════════════

Samuel 2026-09-18 裁示：「我下錯任務，指到 Ragic 採購單，應該是請購單。」
彙整單的下一步是**請購單**（由 Ragic 內建簽核流程簽核），不是採購單。
sheet 57 自此**停用**——程式裡不再有任何地方指向它，既有已拋轉的列保留原本的
單號與網址（那些 Ragic 單據還在，不要去動）。

目標表單：
    https://ap12.ragic.com/soutlet001/community-management-department/58
    表單名稱「★週採請購單」，是樂群**比價式請購單**的原樣複製：
      · 主表有 廠商(一)(二)(三) 三組比價欄
      · 子表有 單價/金額 ×3 組 ＋ 擬定廠商 ＋ 勾選
      · Ragic **內建簽核流程已啟用**（approval.enable=true、toLockEntry=true）
      · 已有「拋轉採購單」「拋轉請款單」兩個動作鈕

⚠️ 跟 sheet 57 完全不同的三件事（欄位代號整批換過，見 config.py RAGIC_CP_*）：

1. **部門與會計課目在子表逐列**（2026-09-20 起，0919 會議結論）。
   Ragic 端把原本的「單價(二)/金額(二)/單價(三)/金額(三)」四欄改名成
   會計課目／部門／本月預算／上月累計預算，並清掉殘留公式、型態改回文字，
   所以 Portal 可以**直接送部門名稱**（「工務部」），不必再做七選一對照。
   ⚠️ 欄位代號是沿用舊的（1020828～1020831），不是新建。
   主表的「部門」「會科」退化成表頭，在 Ragic 仍是必填，送
   `RAGIC_CP_SUMMARY_HEADER_DEPT` / `..._ACCOUNT_CODE` 餵飽它；設成空字串就不送。
   ⚠️ 表頭「部門」那個選單**沒有開放自訂選項**，只吃七個字串之一，
      不能送「多部門」這種說明文字。
   因此拆單粒度回到 **一張單 = 一公司 ＋ 一期別 ＋ 一廠商**
   （2026-09-18～19 曾短暫加過部門那一層，已移除）。

2. **主表「會科」是必填＋單選**（34 個會計科目）。Portal 彙整列沒有會科資料
   （只有料號主檔上的 account_code_id，且主檔目前是暫定的 CPAC-001~004，
   名稱與 Ragic 這 34 個完全對不上）。2026-09-18 Samuel 裁示**固定填「雜項購置」**
   （config.py `RAGIC_CP_SUMMARY_ACCOUNT_CODE`），之後由採購在 Ragic 手動改。

3. **廠商要填兩個地方**。Portal 一張單只有一家廠商，但這張表是比價式的：
       主表「廠商(一)」(1020818)  ← 連結廠商資料表 sheet 15，送廠商名稱
       子表「擬定廠商」(1020832)  ← 同一個名稱
       子表「勾選」    (1020835)  ← 送 "Yes"
   為什麼三個都要送：子表的「單價(選定)」「金額(選定)」是公式
       IF(L5.RAW=F4.RAW, F5, IF(L5.RAW=H4.RAW, H5, IF(L5.RAW=J4.RAW, J5)))
   靠「擬定廠商 == 廠商(一)」比對出來，而主表的「全案小計」(N5 加總)、
   「全案總計」又依賴那兩欄。少送擬定廠商 → 全案金額整片是空的，
   而且 Ragic 照樣回 SUCCESS。廠商(二)(三) 與對應的單價欄一律留空。
   （2026-09-18 Samuel 裁示：廠商(一)＋子表擬定廠商＋勾選，三個都送。）

⚠️ **金額欄位全部是 Ragic 公式，Portal 一律不送**（沿用 2026-09-15 裁示）：
     子表「金額(一)」  = C5*F5（數量 × 單價(一)）
     主表「小計(一)」  = G5（子表金額(一) 加總）
     主表「稅(一)」    = F10*0.05（未稅外加 5%）
     主表「總計(一)」  = F10+F11
     主表「全案小計」  = N5、「全案總計」= M10+M11
   自己算容易因為四捨五入跟 Ragic 差一元，而且之後有人在 Ragic 手改數量時，
   Portal 帶進去的死值不會跟著變，反而會變成錯的。
   同理「項次」是 $SEQ 自動序號、「編號」是自動編號（樂管購{yyyyMM}{00000}），
   兩個都不送。

   ⚠️⚠️ **但是：Ragic 的公式在 API 寫入時預設「不會執行」**（2026-09-15 在 sheet 57
   實測過，整張單的金額全部是空字串）。必須在 query string 帶 **`doFormula=true`**
   才會算，`doDefaultValue=true` 則是讓「項次」的 $SEQ 與其他預設值生效。
   兩個參數缺一，單子就會是一張沒有金額的空殼，而且 API 回的是 status=SUCCESS，
   **不會有任何錯誤**——這是最容易漏掉、又最難發現的坑。

⚠️ **子表列的順序與 key 的大小相反**：Ragic 是由「負數 key 的絕對值大的先排」，
   送 -1=A、-2=B 進去，出來會是 項次1=B、項次2=A。所以 build_payload() 是用
   `-(總列數 - index)` 產生 key，讓第一列拿到最大的絕對值。純排版問題，不影響金額。

⚠️ ~~子表「單價(一)」沒有單價的列絕對不能送~~ → **2026-09-25 Samuel 裁示改為照送**：
   請購單金額是採購在 Ragic 上填的，沒單價的列送空白單價、空白金額（該部門小計也留空）。
   前提是 Ragic sheet 58 子表「單價(一)」已改成非必填；若仍必填，Ragic API 會**整筆退**
   （不是跳過該列），會出現在 failed 清單，不會靜默成功。
   呼叫端（cycle_purchase_summary_service）仍會濾掉「沒有廠商」「調整量 0」
   「沒有部門別的歷史列」並列進未拋轉清單。

⚠️ **主表「申請人」(1020808) 在 Ragic 端是唯讀欄（預設值 $USERNAME）**——
   2026-09-18 實測：唯讀屬性擋的只是 UI 編輯，**API 照樣寫得進去**
   （送 "Samuel" 就存 "Samuel"，沒有被 $USERNAME 蓋掉），所以照送。
   另外主表「請購人」(1020860) 是**必填**，送該部門的承辦人姓名；部門沒設承辦人
   時退回 `RAGIC_CP_SUMMARY_APPLICANT`（Samuel），總比讓整張單被退掉好。

✅ **2026-09-18 實測結果（樂管購20260900001，兩列子表）**，這份對應是驗過的：
     必填全過（部門=工務／會科=雜項購置／申請日期／說明／請購人）
     小計(一) 5251、稅(一) 262.55、總計(一) 5513.55
     全案小計 5251、全案總計 5513.55  ← 證明子表擬定廠商＋勾選的做法是對的
     子表 金額 3480／1771、項次 1／2 順序正確
     簽核狀態(1020813) = "N"（未送簽）—— 拋進去的單**不會自動送簽**，
     要有人在 Ragic 按送出簽核，這一段目前不在 Portal 的範圍內。
     ragicId 回 **0**（第一筆），再次確認不能用 `a or b or ""` 取值。

欄位代號全部放在 app/core/config.py 的 RAGIC_CP_* 設定值，不寫死在這裡；
Ragic 端若重建表單，只要改 .env／config 預設值即可，不用動程式。
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
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

# ───────────────────────────────────────────────────────────────────────────
# 廠商防呆：拋轉前先問 Ragic「你認得這個廠商嗎」
# ───────────────────────────────────────────────────────────────────────────
#
# ⚠️ 2026-09-20 實測踩到（CHANGELOG [2.10.40]／[2.10.41]）：
# 主表「廠商(一)」是 **L（連結到「廠商資料表」）** 型態，只吃廠商資料表裡
# **完全相符**的既有名稱。Portal 送「北金」，Ragic 只認
# 「北金文具印刷有限公司」—— 對不上時 Ragic **靜默丟掉那一欄、照樣回
# SUCCESS**，單子上的廠商欄是空的，而 API 回應完全看不出來。
#
# 好消息是 Ragic 的表單定義裡直接帶著這一欄的**可接受值清單**
# （`fields.fid<廠商欄位ID>.options`，實測 175 筆），所以我們可以在送出前
# 就比對，把對不上的列擋在 `not_pushed`，而不是推完才發現。
#
# ⚠️ **拿不到清單時「放行」而不是「擋下」**（fail open）：
#    取定義是額外的一次呼叫，它失敗不代表廠商有問題。為了一個輔助檢查而讓
#    整批拋轉停擺，比原本的行為更糟。拿不到時回 None，呼叫端就跳過這道檢查
#    並在 warnings 說明。這是刻意的取捨，要改成 fail closed 只需改這裡的回傳。

_VENDOR_OPTION_CACHE: dict[str, Any] = {"values": None, "fetched_at": 0.0}
_VENDOR_OPTION_TTL = 600  # 秒。表單定義很少變，但也不該整個行程都不更新。


def fetch_accepted_vendor_names(force: bool = False) -> set[str] | None:
    """Ragic 主表「廠商(一)」目前接受哪些值（＝廠商資料表裡的名稱）。

    Returns:
        名稱集合；**取不到時回 None**（代表「這次無法檢查」，不是「沒有任何廠商」）。
        兩者一定要分得出來 —— 回空集合的話呼叫端會把每一家都當成對不上。
    """
    import time

    now = time.time()
    if (not force and _VENDOR_OPTION_CACHE["values"] is not None
            and now - _VENDOR_OPTION_CACHE["fetched_at"] < _VENDOR_OPTION_TTL):
        return _VENDOR_OPTION_CACHE["values"]

    url = _sheet_url()
    try:
        resp = httpx.get(
            url,
            headers={"Authorization": f"Basic {settings.RAGIC_API_KEY}"},
            params={"api": "", "v": "3", "def": "true"},
            timeout=settings.RAGIC_CP_SUMMARY_TIMEOUT,
            verify=settings.RAGIC_VERIFY_SSL,
        )
        resp.raise_for_status()
        fields = (resp.json() or {}).get("fields") or {}
        field = fields.get(f"fid{settings.RAGIC_CP_F_VENDOR}") or {}
        options = field.get("options")
        if not isinstance(options, list):
            logger.warning(
                "[cycle_purchase_ragic_push] 廠商欄位定義裡沒有 options，跳過廠商檢查"
            )
            return None
        values = {str(o.get("v")) for o in options if o.get("v") is not None}
        if not values:
            return None
        _VENDOR_OPTION_CACHE["values"] = values
        _VENDOR_OPTION_CACHE["fetched_at"] = now
        return values
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[cycle_purchase_ragic_push] 取不到 Ragic 廠商清單，這次跳過廠商檢查：%s", exc
        )
        return None


def vendor_rejection_reason(vendor_name: str | None, accepted: set[str] | None) -> str | None:
    """這個廠商名稱送進 Ragic 會不會被丟掉？會的話回一句人看得懂的理由。

    accepted 是 None（查不到清單）時一律回 None —— 不能因為查不到就把所有
    廠商都判成錯的。
    """
    if accepted is None:
        return None
    name = (vendor_name or "").strip()
    if not name:
        return "缺供應商"
    if name in accepted:
        return None

    # 給個「你是不是想找這個」的提示：Ragic 那邊通常是同一家的全名。
    near = [v for v in accepted if name in v or v in name]
    if near:
        hint = "、".join(sorted(near)[:3])
        return (
            f"廠商「{name}」不是 Ragic 廠商資料表裡的名稱，送過去會被 Ragic 丟掉"
            f"（單子上的廠商欄會是空的）。Ragic 那邊的寫法可能是：{hint}。"
            f"請到「週採 → 供應商主檔」用「對應合約廠商」接上，再按「自合約模組同步」。"
        )
    return (
        f"廠商「{name}」在 Ragic 廠商資料表裡完全找不到，送過去會被 Ragic 丟掉"
        f"（單子上的廠商欄會是空的）。請先在 Ragic 廠商資料表建檔，"
        f"再跑一次廠商同步。"
    )


def build_payload(document: dict[str, Any]) -> dict[str, Any]:
    """把一份「單一廠商 ＋ 單一部門」的彙整文件轉成 Ragic API 的 JSON payload。

    抽成獨立函式是為了可以在沒有網路的情況下單獨測試欄位對應
    （見 backend/tests/test_cycle_purchase_ragic_push.py）。
    """
    s = settings
    vendor_name = _text(document.get("vendor_name"))

    payload: dict[str, Any] = {
        # ── Ragic 端必填 ────────────────────────────────────────────────
        # 表頭的「部門」「會科」只是為了餵飽必填，實際歸屬看子表逐列；
        # 設定成空字串就不送（Ragic 端若已取消必填就這樣設）。
        s.RAGIC_CP_F_APPLY_DATE: _text(document.get("apply_date")),
        s.RAGIC_CP_F_PURPOSE:    _text(document.get("purpose")),
        s.RAGIC_CP_F_REQUESTER:  _text(document.get("requester") or s.RAGIC_CP_SUMMARY_APPLICANT),
        # ── 廠商：主表只填廠商(一)，(二)(三) 留空（週採不比價）────────────
        s.RAGIC_CP_F_VENDOR:     vendor_name,
        # ── 其他 ────────────────────────────────────────────────────────
        s.RAGIC_CP_F_APPLICANT:  _text(document.get("applicant") or s.RAGIC_CP_SUMMARY_APPLICANT),
        s.RAGIC_CP_F_COMPANY:    _text(document.get("company")),
        s.RAGIC_CP_F_CYCLE:      _text(document.get("cycle_name")),
        s.RAGIC_CP_F_BATCH:      _text(document.get("batch_no")),
        s.RAGIC_CP_F_PUSHED_AT:  _text(document.get("pushed_at")),
        s.RAGIC_CP_F_NOTE:       _text(document.get("portal_note")),
        # 小計／稅／總計／全案小計／全案總計 是 Ragic 公式，刻意不送（見檔頭）
    }

    # ⚠️ 用 "key in document" 判斷，不能用 `or`：
    #    document 明確給空字串＝「這張單不要送表頭的部門／會科」，
    #    用 `or` 會掉回 config 預設值，等於關不掉。
    header_dept = _text(
        document["header_dept"]
        if "header_dept" in document
        else s.RAGIC_CP_SUMMARY_HEADER_DEPT
    )
    header_acct = _text(
        document["account_code"]
        if "account_code" in document
        else s.RAGIC_CP_SUMMARY_ACCOUNT_CODE
    )
    if header_dept:
        payload[s.RAGIC_CP_F_DEPT] = header_dept
    if header_acct:
        payload[s.RAGIC_CP_F_ACCOUNT] = header_acct

    lines = document.get("lines", [])
    total = len(lines)
    rows: dict[str, dict[str, str]] = {}
    for idx, line in enumerate(lines):
        # ⚠️ key 用 -(總列數 - index)，讓第一列拿到絕對值最大的負號。
        #    Ragic 是「絕對值大的排前面」，直接用 -1、-2… 會讓明細整個反序。
        key = f"-{total - idx}"

        # ── 部門小計列（2026-09-20 新增）──────────────────────────────────
        # 只填部門與金額，其餘一律留空 —— 一眼看得出不是品項，
        # Ragic 端也靠「料號為空」把它排除在小計／全案小計的加總之外。
        if line.get("is_subtotal"):
            rows[key] = {
                s.RAGIC_CP_SF_DEPT:   _text(line.get("department_name")),
                s.RAGIC_CP_SF_AMOUNT: _num(line.get("amount")),
            }
            continue

        rows[key] = {
            s.RAGIC_CP_SF_ITEM_NAME:  _text(line.get("item_name")),
            s.RAGIC_CP_SF_QTY:        _num(line.get("qty")),
            s.RAGIC_CP_SF_UNIT:       _text(line.get("unit")),
            s.RAGIC_CP_SF_NOTE:       _text(line.get("note")),
            s.RAGIC_CP_SF_PRICE:      _num(line.get("unit_price")),
            # ⚠️ 2026-09-20：金額改成**由 Portal 送**。
            #    Ragic 端原本是公式欄（數量×單價），但公式欄寫不進值，
            #    「部門小計列」的金額就放不進去（小計列沒有數量與單價）。
            #    Samuel 裁示把 Ragic 那個公式拿掉，改由 Portal 逐列算好送。
            #    代價：採購在 Ragic 手動改數量，金額不會自己跟著變。
            s.RAGIC_CP_SF_AMOUNT:     _num(line.get("amount")),
            # 2026-09-20 新增：部門與會計課目逐列帶（Ragic 端已把這兩欄改成自由文字）
            s.RAGIC_CP_SF_DEPT:       _text(line.get("department_name")),
            s.RAGIC_CP_SF_ACCOUNT:    _text(line.get("account_name")),
            # 擬定廠商＋勾選：全案小計／全案總計的公式靠這兩欄才算得出來，見檔頭第 3 點
            s.RAGIC_CP_SF_VENDOR:     vendor_name,
            s.RAGIC_CP_SF_CHOSEN:     "Yes",
            s.RAGIC_CP_SF_ITEM_CODE:  _text(line.get("item_code")),
            s.RAGIC_CP_SF_SUMMARY_ID: _text(line.get("summary_id")),
            # 項次($SEQ) 是 Ragic 自己算的，不送；
            # 本月預算／上月累計預算是人工填的，Portal 不碰
        }
    payload[f"_subtable_{settings.RAGIC_CP_SUBTABLE}"] = rows
    return payload


def push_summary_document(document: dict[str, Any]) -> dict[str, Any]:
    """把**一家廠商 ＋ 一個部門**的彙整文件推送到 Ragic，回傳這一張單的識別資訊。

    Args:
        document: 由 cycle_purchase_summary_service._build_vendor_documents() 組好的
            單一文件：
            {
                "batch_no": "CPSUM-202609-春大直-0001",
                "cycle_name": "工程備品週採",
                "period_label": "2026-09",
                "company": "春大直",
                "vendor_id": 3,
                "vendor_name": "茂忠",
                "department_names": ["工務部", "管理部"],   # 這張單涵蓋的部門（顯示用）
                "header_dept": "管理",            # Ragic 主表「部門」表頭固定值
                "account_code": "雜項購置",       # Ragic 主表「會科」表頭固定值
                "requester": "劉佳佳",            # Ragic 主表「請購人」（單一部門時＝該部門承辦人）
                "purpose": "2026-09 工程備品週採 匯總請購（春大直／茂忠）",
                "applicant": "Samuel",
                "apply_date": "2026/09/18",
                "pushed_at": "2026/09/18 21:30:00",
                "portal_note": "由 Portal 週期採購模組自動產生，明細請勿手動修改",
                "lines": [
                    {"item_code": "CH-E0301001", "item_name": "…",
                     "department_name": "工務部",        # 子表逐列的部門
                     "account_name": "6238 清潔費",       # 子表逐列的會計課目
                     "qty": 1, "unit": "個", "note": None,
                     "unit_price": Decimal("290.0000"), "summary_id": 137},
                    …
                ],
            }

    Returns:
        {"ragic_record_id": str, "ragic_no": str, "ragic_record_url": str,
         "is_stub": bool, "message": str}
        ragic_record_id 是 Ragic 的內部 _ragicId；ragic_no 是表單上的「編號」
        （樂管購20260900001），對帳時人看的是後者。

    Raises:
        RagicPushError: 連線失敗、HTTP 非 2xx、或 Ragic 回傳 status != SUCCESS。
    """
    batch_no = document.get("batch_no", "UNKNOWN")
    vendor_name = document.get("vendor_name") or "—"
    dept_name = document.get("department_name") or "—"
    label = f"{vendor_name}／{dept_name}"

    # 關閉開關：Ragic 端維護中或測試環境不想真的寫入時，設 RAGIC_CP_SUMMARY_ENABLED=false
    # 就會退回舊的 stub 行為（Portal 端狀態照常更新，但不碰 Ragic）。
    if not settings.RAGIC_CP_SUMMARY_ENABLED:
        logger.warning(
            "[cycle_purchase_ragic_push] RAGIC_CP_SUMMARY_ENABLED=false，"
            "batch_no=%s %s 改走 stub，未真正寫入 Ragic", batch_no, label,
        )
        return {
            "ragic_record_id": f"STUB-{batch_no}",
            "ragic_no": "",
            "ragic_record_url": "",
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
            #    少了它們 Ragic 照樣回 SUCCESS，但小計／稅／總計／子表金額／
            #    項次會全部是空的，變成一張沒有金額的空殼單。
            params={"api": "", "v": "3", "doFormula": "true", "doDefaultValue": "true"},
            json=payload,
            timeout=settings.RAGIC_CP_SUMMARY_TIMEOUT,
            verify=settings.RAGIC_VERIFY_SSL,
        )
    except Exception as exc:  # noqa: BLE001 — httpx 的例外種類很多，一律轉成自己的錯誤
        logger.error(
            "[cycle_purchase_ragic_push] 連線 Ragic 失敗：batch_no=%s %s url=%s err=%s",
            batch_no, label, url, exc,
        )
        raise RagicPushError(f"連線 Ragic 失敗（{label}）：{exc}") from exc

    if resp.status_code >= 400:
        logger.error(
            "[cycle_purchase_ragic_push] Ragic 回 HTTP %s：batch_no=%s %s body=%s",
            resp.status_code, batch_no, label, resp.text[:500],
        )
        raise RagicPushError(
            f"Ragic 回 HTTP {resp.status_code}（{label}）：{resp.text[:300]}"
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
            f"Ragic 回傳的不是 JSON（{label}），"
            f"最常見原因是這把 API Key 對該表單沒有新增權限：{resp.text[:200]}"
        ) from exc

    status = str(data.get("status", "")).upper()
    if status != "SUCCESS":
        msg = data.get("msg") or data.get("message") or str(data)[:300]
        logger.error(
            "[cycle_purchase_ragic_push] Ragic 回報失敗：batch_no=%s %s resp=%s",
            batch_no, label, str(data)[:500],
        )
        raise RagicPushError(f"Ragic 拒絕寫入（{label}）：{msg}")

    record = data.get("data") or {}
    # ⚠️ 不可以寫 `data.get("ragicId") or record.get("_ragicId") or ""`
    #    ——Ragic 的第一筆記錄 ragicId 就是 **0**，0 在 Python 是 falsy，
    #    整串 or 會一路掉到 ""，第一張單的記錄 ID 就這樣不見了。
    #    （2026-09-15 用 sheet 57 的第一張單實測到，ragicId 真的回 0。）
    raw_id = data.get("ragicId")
    if raw_id is None:
        raw_id = record.get("_ragicId")
    ragic_record_id = "" if raw_id is None else str(raw_id)

    ragic_no = _text(record.get(settings.RAGIC_CP_F_DOC_NO) or record.get("編號"))

    # 空殼防呆：帶了 doFormula 還是算不出金額，代表 Ragic 端的公式被動過或
    # 參數被擋掉。這種單在 Ragic 看起來是正常的一張單，只是金額全空，
    # 不主動檢查的話沒有人會發現。
    #
    # ⚠️ 2026-09-20 起看的是**全案小計（1020810 = O5）**，不是「小計」。
    #    原因有兩個：
    #      1. 舊的「小計 1020838」那一組已經被刪掉，`record.get()` 永遠是 None，
    #         這個防呆因此**每推一張單都誤報**。
    #      2. 現在還掛在表單上的「小計 1020840」是比價版型的殘留，公式是 `L5`
    #         （子表「上月累計預算」欄，整欄都空），**恆為字串 "0"** ——
    #         "0" 是 truthy，看它反而會被騙過去，等於防呆失效。
    grand_sub = _text(record.get(settings.RAGIC_CP_F_GRAND_SUB))
    grand_total = _text(record.get(settings.RAGIC_CP_F_GRAND_TOTAL))
    if not grand_sub:
        # 全案小計＝子表「金額2(選定)」的加總，而金額2 是
        # `IF(擬定廠商 = 廠商(一), …)`。所以它空白最常見的原因是**廠商對不上**
        # （2026-09-20 起拋轉前已有廠商防呆擋這件事，走到這裡代表防呆沒攔到），
        # 其次才是 doFormula 沒生效或公式被改壞。
        logger.warning(
            "[cycle_purchase_ragic_push] ⚠️ %s 寫入成功但「全案小計」是空的——"
            "最常見是子表『擬定廠商』沒對到主表『廠商(一)』（廠商名稱與 Ragic "
            "廠商資料表不一致），其次是 doFormula 沒生效或公式被改動",
            ragic_no or ragic_record_id,
        )
    elif not grand_total:
        logger.warning(
            "[cycle_purchase_ragic_push] ⚠️ %s 的「全案小計」有值但「全案總計」是空的——"
            "請確認 Ragic 端『全案總計 = M10+M11』與『營業稅』的公式還在",
            ragic_no or ragic_record_id,
        )

    logger.info(
        "[cycle_purchase_ragic_push] 已寫入 Ragic：batch_no=%s %s ragicId=%s 單號=%s 明細=%d 列",
        batch_no, label, ragic_record_id, ragic_no or "—", len(document.get("lines", [])),
    )

    # 單筆網址用 Ragic 的內部 _ragicId，不是表單上的編號
    # （2026-09-15 在 sheet 57 實測 .../57/2 開出來就是 樂管週採00003）。
    # 在這裡組好一起回傳，service 存進 ragic_record_url，前端就不用再拼一次網址。
    ragic_record_url = f"{_sheet_url()}/{ragic_record_id}" if ragic_record_id else ""

    return {
        "ragic_record_id": ragic_record_id,
        "ragic_no": ragic_no,
        "ragic_record_url": ragic_record_url,
        "is_stub": False,
        "message": f"已寫入 Ragic 週採請購單 {ragic_no or ragic_record_id}",
    }
