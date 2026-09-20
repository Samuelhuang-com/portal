"""
週期採購 — 單號／批次號流水號的共用產生器

⚠️ 為什麼要有這個檔案（2026-09-20）
────────────────────────────────────────────────────────────────────────────
週採模組原本有 **7 處**各自用 `COUNT(*) + 1` 算流水號。這個寫法只要有任何一筆
被刪掉（或批次號被清成 NULL），號碼就會**倒退**去撞已經存在的號碼：

  · 欄位有 UNIQUE（request_no／po_no／receiving_no／payment_no）
      → IntegrityError → 500，而且是**永久性**的：這個月只要刪過一筆，
        之後每一次新增都必定失敗。畫面上只看得到一句 Internal Server Error，
        完全看不出跟刪除有關。
  · 欄位沒有 UNIQUE（close_batch_no／summary_batch_no／ragic_push_batch_no）
      → **不會報錯**，只是兩批不同的動作共用同一個批次號，批次號從此失去
        識別意義。比 500 難發現得多。

2026-09-20 端到端實測時真的撞上了：`PR-2026-09-` 底下只剩 003～007
（001、002 被刪過），`COUNT(*)+1` 算出 006，正好撞上還活著的那張單
（詳見 CHANGELOG [2.10.39]）。`ragic_push_batch_no` 那一支在 2026-08-09
也踩過同一類問題（取消拋轉把欄位清成 NULL → 計數退回 → 重推拿到一樣的批次號），
當時只換了計數來源，沒有改掉「用計數當號碼」這個根本寫法。

所以統一改成 **「既有號碼的最大流水號 + 1」**。

⚠️ 刪掉的號碼**刻意不回收**。單號是給人對帳用的，回收會讓同一個號碼先後指到
兩張不同的單據 —— 那比號碼中間有洞嚴重得多。

⚠️ 這裡沒有處理併發。兩個人同時按新增仍可能拿到同一個號，靠欄位的 UNIQUE
擋下（沒有 UNIQUE 的批次號本來就允許重複值）。這一點跟改版前一樣，不是這次
引入的；真要根治得改用資料庫 sequence 或加鎖，屬於另一個題目。
"""
from typing import Iterable, Optional

from sqlalchemy.orm import Session


def largest_suffix(values: Iterable[Optional[str]], prefix: str) -> int:
    """一堆號碼字串裡，「prefix 之後那段數字」的最大值；沒有就回 0。

    解析不出數字的值（手工補過的怪資料）直接跳過，不讓整支掛掉。
    """
    largest = 0
    for value in values:
        if not value or not value.startswith(prefix):
            continue
        tail = value[len(prefix):]
        if tail.isdigit():
            largest = max(largest, int(tail))
    return largest


def max_suffix(db: Session, column, prefix: str, *extra_filters) -> int:
    """資料庫裡符合 prefix 的既有號碼，其流水號的最大值。

    `column` 可以是單號欄位，也可以是會重複的批次號欄位 —— 兩者都只看
    「出現過哪些號碼」，所以不需要 DISTINCT，重複值不影響最大值。
    `extra_filters` 給需要再縮範圍的情況（例：稽核紀錄要限定 event_type）。
    """
    query = db.query(column).filter(column.like(f"{prefix}%"))
    for f in extra_filters:
        query = query.filter(f)
    return largest_suffix((row[0] for row in query.all()), prefix)


def next_no(db: Session, column, prefix: str, width: int, *extra_filters) -> str:
    """`prefix` ＋ 補零到 `width` 位的下一個流水號。"""
    return f"{prefix}{max_suffix(db, column, prefix, *extra_filters) + 1:0{width}d}"
