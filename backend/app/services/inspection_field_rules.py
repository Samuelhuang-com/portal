"""
整棟巡檢 — item 欄位分類規則（四個樓層共用）

為什麼需要這支：
  各樓層 sync 的 `_extract_check_items()` 是**動態欄位偵測** —— 只排除四個場次
  metadata（巡檢人員／開始巡檢時間／巡檢結束時間／工時計算），Ragic Sheet 上其餘
  所有欄位一律當成「設備巡檢項目」寫進 `*_inspection_item`。

  於是「拍照」「拍照1」「拍照2」「異常說明」「建立日期」「建立年份」「月份」
  也都變成了 item，而 `_normalize_result_status()` 對「非空但不在對照表裡」的值
  一律判成 abnormal，檔名與日期就被畫成紅色的「異常」Tag。

  這支模組把「這個 item 到底是什麼」集中判斷，避免四支 router 各寫一份、
  然後某天有人只改了其中一支。

⚠️ 前端 `FloorInspectionList.tsx` 有一份**等價**的規則（同樣的正規表達式），
   兩邊必須一起改，否則會出現「明細列表把檔名當成異常狀態顯示成紅色 Tag」
   或「附圖區空白」。

⚠️ 為什麼用「名稱規則 + 值規則」而不是寫死清單：
   Ragic 上的附件欄位命名沒有統一（拍照 / 拍照1 / 拍照2 / 照片 / 附件…），
   寫死一份清單的話，Sheet 上新增一個「拍照3」就會靜默漏掉 ——
   而症狀只是「多一個紅色異常 Tag」，沒有人會發現。
   值規則（副檔名）是名稱規則的保險：欄位叫什麼都好，值長得像檔名就是附件。
"""
import re

# ── 附件／圖片欄位 ────────────────────────────────────────────────────────────
# 允許結尾帶數字：拍照、拍照1、拍照2、照片3…
IMAGE_FIELD_RE = re.compile(r"^(拍照|照片|相片|圖片|圖檔|附件|附圖|上傳圖片)\s*\d*$")

# 值看起來是檔名（多檔以換行／逗號／分號分隔，任一段像檔名就算）
FILE_VALUE_RE = re.compile(r"\.(jpe?g|png|gif|bmp|webp|heic|heif|pdf)\s*$", re.IGNORECASE)

# ── 附註／系統欄位（不是巡檢結果，不該套狀態色，也不該算異常）────────────────
META_FIELD_RE = re.compile(r"^(異常說明|備註|說明|建立日期|建立年份|建立時間|年份|月份)\s*\d*$")


def is_image_field(item_name: str, result_raw: str = "") -> bool:
    """這個 item 是不是附件／圖片欄位？名稱像、或值像檔名，都算。"""
    if IMAGE_FIELD_RE.match((item_name or "").strip()):
        return True
    value = (result_raw or "").strip()
    if not value:
        return False
    return any(
        FILE_VALUE_RE.search(part.strip())
        for part in re.split(r"[\n,;]", value)
        if part.strip()
    )


def is_meta_field(item_name: str) -> bool:
    """這個 item 是不是附註／系統欄位（非巡檢結果）？"""
    return bool(META_FIELD_RE.match((item_name or "").strip()))


def is_equipment_field(item_name: str, result_raw: str = "") -> bool:
    """這個 item 是不是真正的設備巡檢項目？"""
    return not is_image_field(item_name, result_raw) and not is_meta_field(item_name)


# ── 附件值拆檔 ────────────────────────────────────────────────────────────────
# ⚠️ 為什麼不能直接把整個值丟給 ragic_data_service.parse_images()：
#    Ragic 的附件欄位回傳的是 **list**，而各 sync 的 `_stringify()` 用
#    `" ".join(...)` 把它壓成一個字串：
#        'vciuvASVNw@1000013624.jpg 13biGm4LjV@1000013623.jpg'
#    parse_images 只認得換行／逗號／分號分隔，會把整串當成**單一檔名**，
#    組出一個同時包含兩個檔名的壞連結 —— 畫面上就是「兩張圖變一張破圖」。
#
#    這裡用副檔名把 token 切開。刻意不改 parse_images 本身：那支被多個模組共用，
#    把空白加進分隔字元會影響「檔名本身含空白」的模組。
# HTML（<a>／<img>）或純 URL 一律原樣交給 parse_images，不可自行切斷
_HTML_OR_URL_RE = re.compile(r"[<>]|^https?://|^//")

# 純檔名清單的分隔字元：空白、換行、逗號、分號
_ATTACHMENT_SEP_RE = re.compile(r"[\s,;]+")


def split_attachment_value(raw: str) -> list[str]:
    """把一個附件欄位的值拆成個別檔名。

    HTML / 純 URL 不拆（交給 parse_images 自己解析），其餘依空白、換行、
    逗號、分號切開。⚠️ 若 Ragic 端出現「檔名本身含空白」的附件，這裡會拆錯 ——
    但目前四個 Sheet 的附件都是 `<10碼ID>@<數字>.jpg` 這種手機上傳的檔名，
    沒有空白；真的出現時再改，不要為了假想情境把規則寫複雜。
    """
    value = (raw or "").strip()
    if not value:
        return []
    if _HTML_OR_URL_RE.search(value):
        return [value]
    return [p for p in _ATTACHMENT_SEP_RE.split(value) if p]


# ── 欄位型別判定：狀態型 vs 量測/程度型 ──────────────────────────────────────
#
# 問題：`_normalize_result_status()` 的預設分支是「非空但不在對照表裡 → abnormal」。
#       但有些欄位的值域**根本不是狀態**：
#           水位檢查 / 水位狀態 / 膨脹水箱水位 / 油箱油量充足 …  → 高 / 中 / 低
#           電瓶電壓                                        → 靜置12.4V~12.7V …
#       這些值被當成異常，四個樓層合計虛報 262 筆。
#
# ⚠️ 為什麼看「欄位」而不是看「值」：
#       另有一類**混合型**欄位 —— 正常×26 + `查修表` / `低水位` / `高水位`×1
#       （隔熱材是否完好、液位顯示正常(浮球)、液位未超限或接近滿槽、
#         液位、浮球感測器正常）。這些欄位的正常值就是「正常」，冒出別的值
#       **是真的異常訊號**。若改成「值不認得就當記錄值」，這 4 筆真訊號會被藏起來。
#
#       判準因此是：**一個欄位在整份資料裡若從未出現過任何已知狀態值
#       （正常／異常／待處理…），它就是量測/程度型**；只要出現過一次，
#       它就是狀態型，不認得的值仍然判異常。
#
# ⚠️ 必須用**整份資料**判定，不可只看單筆 Row。只看一筆的話，
#    「隔熱材是否完好」那筆值為 `查修表` 的場次會被誤判成量測型，
#    同一個欄位在不同場次得到不同型別，統計就再也對不起來了。

MEASURE_STATUS = "measure"


def build_measure_fields(
    rows: dict,
    check_items: list,
    known_status_values: set,
    stringify,
) -> set:
    """掃描整份 Ragic 資料，找出「從未出現過已知狀態值」的欄位。

    Args:
        rows:                fetch_all() 的回傳（{ragic_id: {欄位: 值}}）
        check_items:         動態偵測到的欄位清單
        known_status_values: RESULT_STATUS_MAP 的 key 集合
        stringify:           該 sync 的 _stringify（各檔一份，行為一致）

    Returns:
        量測/程度型欄位名稱的集合。
    """
    candidates = {
        name for name in check_items
        if not is_image_field(name) and not is_meta_field(name)
    }
    seen_status: set = set()
    has_value: set = set()

    for row in rows.values():
        if not isinstance(row, dict):
            continue
        for name in candidates:
            if name in seen_status:
                continue
            value = stringify(row.get(name, ""))
            if not value:
                continue
            # 名稱不像附件、但值是檔名的欄位（值規則）——不列入型別判定，
            # 它會被 is_equipment_field() 以值規則排除在 KPI 之外。
            if is_image_field(name, value):
                continue
            has_value.add(name)
            if value in known_status_values:
                seen_status.add(name)

    # 有值、但從頭到尾沒出現過任何已知狀態值 → 量測/程度型
    return has_value - seen_status
