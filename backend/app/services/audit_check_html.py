"""
稽核檢查「查核評語」富文字（2026-10-04）

查核評語改用前端原生 contentEditable 編輯器，存的是 HTML。這支負責：
  - sanitize_html()  白名單清理（只留排版用的標籤與 style），存檔前必跑
  - html_to_text()   轉純文字：判斷是否空白（計分／分母）、缺失彙整、Excel、上期待補正帶入
  - html_to_runs()   轉成「段落 → 帶格式的文字片段」，給 Word 匯出照欄位內顏色排版
舊資料是純文字（含換行），三個函式都相容：沒有標籤就當純文字處理。

只用標準庫 html.parser，不加相依套件。
"""
from __future__ import annotations

import html as _html
import re
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

ALLOWED_TAGS = {
    "b", "strong", "i", "em", "u", "s", "strike", "del", "span", "font", "br",
    "p", "div", "ul", "ol", "li", "sub", "sup", "blockquote",
}
BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "blockquote"}
VOID_TAGS = {"br"}
DROP_CONTENT = {"script", "style", "head", "title", "iframe", "object", "noscript"}
ALLOWED_STYLE = {
    "color", "background-color", "font-size", "font-weight", "font-style",
    "text-decoration", "text-decoration-line", "text-align",
}
_TAG_RE = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
_SAFE_VALUE = re.compile(r"^[#\w\s.,%()\-]+$")


def is_html(s: Optional[str]) -> bool:
    return bool(s and _TAG_RE.search(s))


def _clean_style(style: str) -> str:
    out = []
    for decl in (style or "").split(";"):
        if ":" not in decl:
            continue
        k, v = decl.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k in ALLOWED_STYLE and v and _SAFE_VALUE.match(v) and "url" not in v.lower() and "expression" not in v.lower():
            out.append(f"{k}: {v}")
    return "; ".join(out)


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: List[str] = []
        self.drop_depth = 0
        self.open_stack: List[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in DROP_CONTENT:
            self.drop_depth += 1
            return
        if self.drop_depth or tag not in ALLOWED_TAGS:
            return
        keep = []
        for k, v in attrs:
            k = (k or "").lower()
            if k == "style":
                st = _clean_style(v or "")
                if st:
                    keep.append(f'style="{_html.escape(st, quote=True)}"')
            elif tag == "font" and k in ("color", "size") and v and _SAFE_VALUE.match(v):
                keep.append(f'{k}="{_html.escape(v, quote=True)}"')
        attr_s = (" " + " ".join(keep)) if keep else ""
        if tag in VOID_TAGS:
            self.out.append(f"<{tag}>")
        else:
            self.out.append(f"<{tag}{attr_s}>")
            self.open_stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in DROP_CONTENT:
            self.drop_depth = max(0, self.drop_depth - 1)
            return
        if self.drop_depth or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        if tag in self.open_stack:
            while self.open_stack:
                t = self.open_stack.pop()
                self.out.append(f"</{t}>")
                if t == tag:
                    break

    def handle_data(self, data):
        if not self.drop_depth:
            self.out.append(_html.escape(data, quote=False))

    def result(self) -> str:
        while self.open_stack:
            self.out.append(f"</{self.open_stack.pop()}>")
        return "".join(self.out)


def sanitize_html(s: Optional[str]) -> str:
    """白名單清理。純文字（舊資料或手機貼上）→ 轉義後換行改 <br>。內容實質空白時回空字串。"""
    if not s:
        return ""
    if not is_html(s):
        text = s.strip()
        return _html.escape(text, quote=False).replace("\r\n", "\n").replace("\n", "<br>") if text else ""
    p = _Sanitizer()
    p.feed(s)
    p.close()
    cleaned = p.result()
    return cleaned if html_to_text(cleaned).strip() else ""


# ── 轉純文字 ──────────────────────────────────────────────────────────────
class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.drop = 0
        self.lists: List[List[int]] = []   # [是否有序, 目前編號]

    def _nl(self):
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in DROP_CONTENT:
            self.drop += 1
        elif tag == "br":
            self.parts.append("\n")
        elif tag in ("ul", "ol"):
            self._nl()
            self.lists.append([1 if tag == "ol" else 0, 0])
        elif tag == "li":
            self._nl()
            if self.lists and self.lists[-1][0]:
                self.lists[-1][1] += 1
                self.parts.append(f"{self.lists[-1][1]}. ")
            else:
                self.parts.append("• ")
        elif tag in BLOCK_TAGS:
            self._nl()

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in DROP_CONTENT:
            self.drop = max(0, self.drop - 1)
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            self._nl()
        elif tag in BLOCK_TAGS:
            self._nl()

    def handle_data(self, data):
        if not self.drop:
            self.parts.append(data.replace("\xa0", " "))


def html_to_text(s: Optional[str]) -> str:
    if not s:
        return ""
    if not is_html(s):
        return s.strip()
    p = _Text()
    p.feed(s)
    p.close()
    text = "".join(p.parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── 轉 Word 段落 / 片段 ──────────────────────────────────────────────────
_NAMED = {
    "black": "000000", "white": "FFFFFF", "red": "FF0000", "blue": "0000FF", "green": "008000",
    "yellow": "FFFF00", "orange": "FFA500", "purple": "800080", "gray": "808080", "grey": "808080",
}
_FONT_SIZE_PT = {1: 8, 2: 10, 3: 12, 4: 14, 5: 18, 6: 24, 7: 36}
_KEYWORD_PT = {"x-small": 8, "small": 10, "medium": 12, "large": 14, "x-large": 18, "xx-large": 24, "xxx-large": 36}


def parse_color(v: Optional[str]) -> Optional[str]:
    """'#cf1322' / '#f00' / 'rgb(207, 19, 34)' / 'red' → 'CF1322'；透明或無法辨識 → None。"""
    if not v:
        return None
    v = v.strip().lower()
    if v in ("transparent", "inherit", "initial", "none"):
        return None
    if v in _NAMED:
        return _NAMED[v]
    m = re.match(r"^#([0-9a-f]{6})$", v)
    if m:
        return m.group(1).upper()
    m = re.match(r"^#([0-9a-f]{3})$", v)
    if m:
        return "".join(ch * 2 for ch in m.group(1)).upper()
    m = re.match(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)$", v)
    if m:
        if m.group(4) is not None and float(m.group(4)) == 0:
            return None
        return "".join(f"{min(255, int(x)):02X}" for x in m.groups()[:3])
    return None


def _parse_size(v: Optional[str]) -> Optional[float]:
    if not v:
        return None
    v = v.strip().lower()
    if v in _KEYWORD_PT:
        return float(_KEYWORD_PT[v])
    m = re.match(r"^([\d.]+)\s*(px|pt)?$", v)
    if not m:
        return None
    n = float(m.group(1))
    return n * 0.75 if (m.group(2) or "px") == "px" else n


Run = Tuple[str, Dict[str, object]]


class _Runs(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paras: List[Dict[str, object]] = [{"align": None, "runs": []}]
        self.stack: List[Tuple[str, Dict[str, object]]] = []
        self.lists: List[List[int]] = []
        self.drop = 0

    def _fmt(self) -> Dict[str, object]:
        f: Dict[str, object] = {}
        for _t, d in self.stack:
            f.update(d)
        return f

    def _new_para(self, align=None):
        cur = self.paras[-1]
        if cur["runs"]:
            self.paras.append({"align": align, "runs": []})
        elif align:
            cur["align"] = align

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in DROP_CONTENT:
            self.drop += 1
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        style = {}
        for decl in a.get("style", "").split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                style[k.strip().lower()] = v.strip()
        d: Dict[str, object] = {}
        if tag in ("b", "strong") or style.get("font-weight", "") in ("bold", "bolder", "600", "700", "800", "900"):
            d["bold"] = True
        if style.get("font-weight") in ("normal", "400"):
            d["bold"] = False
        if tag in ("i", "em") or style.get("font-style") == "italic":
            d["italic"] = True
        deco = style.get("text-decoration", "") + " " + style.get("text-decoration-line", "")
        if tag == "u" or "underline" in deco:
            d["underline"] = True
        if tag in ("s", "strike", "del") or "line-through" in deco:
            d["strike"] = True
        if tag == "sub":
            d["sub"] = True
        if tag == "sup":
            d["sup"] = True
        col = parse_color(style.get("color") or (a.get("color") if tag == "font" else None))
        if col:
            d["color"] = col
        bg = parse_color(style.get("background-color"))
        if bg:
            d["bg"] = bg
        size = _parse_size(style.get("font-size"))
        if tag == "font" and a.get("size", "").strip().isdigit():
            size = float(_FONT_SIZE_PT.get(int(a["size"]), 12))
        if size:
            d["size"] = size

        align = style.get("text-align") if style.get("text-align") in ("left", "center", "right", "justify") else None
        if tag == "br":
            self.paras.append({"align": self.paras[-1]["align"], "runs": []})
            return
        if tag in ("ul", "ol"):
            self._new_para()
            self.lists.append([1 if tag == "ol" else 0, 0])
        elif tag == "li":
            self._new_para(align)
            if self.lists and self.lists[-1][0]:
                self.lists[-1][1] += 1
                prefix = f"{self.lists[-1][1]}. "
            else:
                prefix = "• "
            self.paras[-1]["runs"].append((prefix, self._fmt()))
        elif tag in BLOCK_TAGS:
            self._new_para(align)
        self.stack.append((tag, d))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in DROP_CONTENT:
            self.drop = max(0, self.drop - 1)
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        if tag in ("ul", "ol") and self.lists:
            self.lists.pop()
        if tag in BLOCK_TAGS:
            self._new_para()

    def handle_data(self, data):
        if self.drop or not data:
            return
        data = data.replace("\xa0", " ")
        if not data.strip() and not self.paras[-1]["runs"]:
            return
        self.paras[-1]["runs"].append((data, self._fmt()))


def html_to_runs(s: Optional[str]) -> List[Dict[str, object]]:
    """回傳 [{'align': None|'center'..., 'runs': [(text, fmt), ...]}, ...]；純文字依換行分段。"""
    if not s:
        return []
    if not is_html(s):
        return [{"align": None, "runs": [(line, {})] if line else []} for line in s.strip().split("\n")]
    p = _Runs()
    p.feed(s)
    p.close()
    paras = p.paras
    while paras and not paras[-1]["runs"]:
        paras.pop()
    while paras and not paras[0]["runs"]:
        paras.pop(0)
    return paras
