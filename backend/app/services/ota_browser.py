"""
OTA 口碑分析 — 瀏覽器層（Selenium 生命週期與反偵測）

建立日期：2026-08-22
規格書：`docs/SPEC_ota_reviews.md` §3.3、§6.5

═══════════════════════════════════════════════════════════════════════════
⚠️ R1：Booking 需要可見視窗，而 Windows Service 沒有互動式桌面
═══════════════════════════════════════════════════════════════════════════
原型工具（`ota_review_gui.py` 第 273-275 行）對 Booking 刻意**不加 headless**，
因為 Booking 對無頭瀏覽器的偵測比其他站嚴格。

但 Portal 若以 Windows Service（LocalSystem）執行，沒有互動式桌面 session，
開可見視窗的 `webdriver.Chrome()` 會直接失敗。

本模組把這件事做成**可自我診斷**的流程，而不是等出事再查：

    OTA_BROWSER_MODE = "auto"（預設）
        1. 先用 headless=new + undetected-chromedriver 試
        2. 抓不到評論卡 → 自動改開可見視窗重試一次
        3. 可見視窗也開不起來 → 拋出 HeadlessBlockedError，
           訊息直接寫明「請改用 ota_scraper_cli.py + Windows 工作排程器」

    OTA_BROWSER_MODE = "headless"   伺服器排程用：失敗就失敗，不做無謂重試
    OTA_BROWSER_MODE = "visible"    本機工作排程器用：一律開可見視窗

也就是說：**第一次跑排程就會告訴你 R1 過不過**，不需要另外做探針。

═══════════════════════════════════════════════════════════════════════════
套件相依
═══════════════════════════════════════════════════════════════════════════
`selenium` 與 `undetected-chromedriver` 是 2026-08-22 新增的相依
（見 `backend/requirements.txt` 與 `docs/TECH_SPEC.md`）。

⚠️ **一律在函式內 import**，不在模組層 import。
   沒裝這兩個套件的環境（例如只跑 API 不跑爬蟲的機器）仍然要能
   `import app.main` 成功，否則整個 Portal 起不來。
"""
from __future__ import annotations

import logging
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from app.core.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# 頁面「看起來有東西」的最低 HTML 長度。低於此值多半是 app shell。
MIN_HTML_LENGTH = 9000

# ⭐ **最可靠的攔截判定訊號：可見文字長度**（2026-08-22 實測得出）
#
# Expedia 的驗證頁：HTML **121,540 字元**，可見文字只有 **63 字元**。
#     <title>身分驗證</title>
#     <h2>請協助我們維護網路安全</h2>
#     點擊以下方格以完成身分驗證。
#
# 關鍵字比對在這裡兩次都失敗：
#   · 初版搜整份 HTML（含 script）→ 把正常頁面誤判成被擋
#   · 改成大頁面只認 <title> → 「身分驗證」不在特徵清單裡，變成漏判
#
# 關鍵字清單永遠追不上各站的用詞（何況還有多語系）。
# 但「一個真實的評論頁不可能只有幾十個字的可見文字」是**結構性事實**，
# 不管哪一站、哪一種語言都成立。
MIN_VISIBLE_TEXT = 200

# 特徵字仍然保留 —— 命中就能給出更精準的訊息（「被要求驗證」而不是「頁面異常」）。
# 但它現在是**輔助**，不是主要判準。
BLOCK_MARKERS = (
    "captcha",
    "are you a robot",
    "unusual traffic",
    "access denied",
    "verify you are human",
    "請驗證",
    "驗證您是人類",
    "身分驗證",           # ← Expedia 實測
    "維護網路安全",       # ← Expedia 實測
    "安全性驗證",
    "人機驗證",
)


class ScraperError(RuntimeError):
    """擷取失敗的基底例外。"""


class CaptchaError(ScraperError):
    """被要求人機驗證或被擋。⚠️ 不要重試。"""


class HeadlessBlockedError(ScraperError):
    """
    無頭模式被擋，且可見視窗也開不起來 —— 這就是規格書 §3.3 的 R1 成真。

    例外訊息會直接寫明退路，不要只寫「失敗」。
    """


class BrowserUnavailableError(ScraperError):
    """selenium / undetected-chromedriver 沒裝，或 Chrome 不存在。"""


@dataclass
class FetchResult:
    html: str
    mode: str          # "headless" / "visible"
    warnings: list[str]


# 用來剝掉 <script> / <style> —— 攔截頁的訊息不會藏在腳本裡，
# 但正常頁面的腳本裡**很容易**出現 "captcha"（例如登入表單的 recaptcha 載入器）
_RE_SCRIPT_STYLE = re.compile(
    r"<(script|style|noscript)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_RE_TAGS = re.compile(r"<[^>]+>")
_RE_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# 頁面大到這個程度，就不可能是純攔截頁 —— 除非特徵出現在標題裡
LARGE_PAGE_CHARS = 50_000


def visible_text(html: str, limit: int = 400_000) -> str:
    """
    取出可見文字：剝掉 `<script>` / `<style>` / `<noscript>` 與所有標籤。

    ⚠️ 一定要先剝 script —— OTA 頁面動輒數百 KB 內嵌 JS，
       不剝的話「HTML 很長」與「頁面有內容」會被混為一談。
    """
    if not html:
        return ""
    stripped = _RE_TAGS.sub(" ", _RE_SCRIPT_STYLE.sub(" ", html[:limit]))
    return " ".join(stripped.split())


def has_block_marker(html: str) -> bool:
    """
    可見文字或 `<title>` 裡有明確的驗證字樣。

    ⚠️ 只看**可見文字**，不看 `<script>` —— 正常頁面的腳本裡很容易出現
       "captcha"（登入表單的 recaptcha 載入器），那不代表被擋。

    這是「我們知道原因」的訊號，用來給出比「頁面異常」更有用的訊息。
    判定本身不依賴它（見 `looks_blocked`）。
    """
    if not html:
        return False
    title = " ".join(_RE_TITLE.findall(html)[:1]).lower()
    text = visible_text(html).lower()
    return any(marker in title or marker in text[:3000] for marker in BLOCK_MARKERS)


def looks_blocked(html: str) -> bool:
    """
    頁面是否為 CAPTCHA／攔截頁。

    ⭐ **主要判準是「可見文字長度」，不是關鍵字**。

    2026-08-22 為了這件事改了兩次，兩次都錯在同一個地方 ——
    以為關鍵字比對可以判斷：

      1. 初版搜**整份 HTML（含 script）**→ Expedia 頁面內嵌的 recaptcha
         載入器讓一份**完整抓到的頁面**被誤判成被擋
      2. 改成大頁面只認 `<title>` → Expedia 的驗證頁標題是「身分驗證」，
         不在特徵清單裡，於是從誤判變成**漏判**

    關鍵字清單永遠追不上各站的用詞（何況多語系）。真正可靠的是結構：

        Expedia 驗證頁：HTML 121,540 字元，**可見文字只有 63 字元**

    一個真實的評論頁不可能只有幾十個字的可見文字 —— 這是結構性事實，
    不管哪一站、哪一種語言都成立。

    ⚠️ 特徵字仍然檢查，但只是為了**給出更精準的訊息**
       （「被要求驗證」比「頁面異常」有用）。判定本身不依賴它。
    """
    if not html:
        return True

    text = visible_text(html)

    # 主要判準：可見文字太少 → 不是真實內容頁
    if len(text) < MIN_VISIBLE_TEXT:
        return True

    # 輔助：內容夠多但明確寫著驗證字樣（例如驗證頁上還帶了一堆說明）
    return has_block_marker(html)


def looks_empty(html: str) -> bool:
    """頁面是否短到不可能有內容（多半是 app shell）。"""
    return not html or len(html) < MIN_HTML_LENGTH


# 從 uc 的錯誤訊息裡撈出實際安裝的 Chrome 主版號
_RE_BROWSER_VERSION = re.compile(r"Current browser version is (\d+)")


def detect_chrome_major() -> int | None:
    """
    偵測本機安裝的 Chrome 主版號。

    ⚠️ 2026-08-22 實測：`undetected-chromedriver` 的自動版本偵測會抓錯 ——
       本機 Chrome 是 151，它卻下載了 152 的 chromedriver，然後
       `session not created: This version of ChromeDriver only supports
       Chrome version 152 / Current browser version is 151`。

       所以主動偵測後用 `version_main=` 明確指定，不靠它自己猜。

    回傳 None 代表偵測不到（交給 uc 自己猜，並在失敗時用錯誤訊息回推重試）。
    """
    # Windows：登錄檔最可靠，不必找 chrome.exe 在哪
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"Software\Google\Chrome\BLBeacon") as key:
                    version, _ = winreg.QueryValueEx(key, "version")
                    return int(str(version).split(".")[0])
            except OSError:
                continue
    except ImportError:
        pass        # 非 Windows

    # Linux / macOS：問 chrome 自己
    import shutil
    import subprocess
    for name in ("google-chrome", "chromium", "chromium-browser",
                 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        path = shutil.which(name) or (name if name.startswith("/") else None)
        if not path:
            continue
        try:
            out = subprocess.run([path, "--version"], capture_output=True,
                                 text=True, timeout=10).stdout
            m = re.search(r"(\d+)\.", out)
            if m:
                return int(m.group(1))
        except Exception:       # noqa: BLE001
            continue
    return None


def _make_options(headless: bool):
    """
    每次嘗試都建一份**全新的** Options。

    ⚠️ 不可重複使用同一個 Options 物件：`undetected_chromedriver` 會就地
       修改傳進去的 options，用過之後再拿去給原生 selenium 會帶著殘留設定。
    """
    from selenium.webdriver.chrome.options import Options

    options = Options()
    if headless:
        # headless=new（Chrome 109+ 的新版無頭），舊版 --headless 特徵更明顯
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1200")
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--lang=zh-TW")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return options


def _hide_webdriver(driver) -> None:
    """把 navigator.webdriver 藏起來（原型工具有這段，保留）。"""
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
        )
    except Exception:           # noqa: BLE001 —— 失敗只是少一層偽裝，不該中斷
        logger.debug("[OTA] 無法注入 navigator.webdriver 偽裝腳本")


def _try_undetected(headless: bool) -> object | None:
    """
    用 undetected-chromedriver 啟動。失敗回 None（呼叫端退回原生 selenium）。

    版本對不上時，從錯誤訊息回推正確主版號再重試一次 —— 這是最常見的失敗，
    而且訊息裡就寫著答案（`Current browser version is 151`），
    沒有理由讓使用者自己去讀 stacktrace。
    """
    try:
        import undetected_chromedriver as uc
    except ImportError:
        # ⚠️ warning 不用 info：Booking 用原生 selenium 過得去，
        #    但各站偵測強度差很多，缺這個套件是很可能的失敗原因。
        logger.warning(
            "[OTA] ⚠️ 未安裝 undetected-chromedriver，改用原生 selenium。"
            "偵測較嚴的站（Tripadvisor／Expedia）很可能被擋。"
            "請執行：cd backend && pip install -r requirements.txt"
        )
        return None

    major = detect_chrome_major()
    if major:
        logger.info("[OTA] 偵測到 Chrome 主版號 %s，明確指定給 undetected-chromedriver", major)

    for attempt, version_main in enumerate((major, None), start=1):
        try:
            return uc.Chrome(options=_make_options(headless),
                             version_main=version_main, use_subprocess=True)
        except Exception as exc:        # noqa: BLE001 —— uc 失敗原因五花八門
            text = str(exc)
            m = _RE_BROWSER_VERSION.search(text)
            if m and attempt == 1:
                fixed = int(m.group(1))
                logger.warning(
                    "[OTA] chromedriver 版本對不上（本機 Chrome %s），用它重試一次", fixed)
                try:
                    return uc.Chrome(options=_make_options(headless),
                                     version_main=fixed, use_subprocess=True)
                except Exception as exc2:       # noqa: BLE001
                    logger.warning("[OTA] 指定版本 %s 仍失敗：%s", fixed, str(exc2)[:200])
                    return None
            logger.warning("[OTA] undetected-chromedriver 啟動失敗：%s", text[:200])
            if attempt == 2:
                return None
    return None


def _build_driver(headless: bool):
    """
    建立 driver。優先用 undetected-chromedriver，退回原生 selenium。

    ⚠️ 套件在函式內 import：沒裝爬蟲相依的環境仍要能 import app.main。
    """
    try:
        import selenium  # noqa: F401
    except ImportError as exc:
        raise BrowserUnavailableError(
            "未安裝 selenium。請執行：pip install -r backend/requirements.txt"
        ) from exc

    driver = _try_undetected(headless)
    if driver is not None:
        _hide_webdriver(driver)
        return driver

    # ── 退回原生 selenium ──────────────────────────────────────────────
    # ⚠️ 2026-08-22 移除 excludeSwitches 與 useAutomationExtension。
    #    這兩個是舊版 Chrome 的反偵測寫法（原型工具留下來的），
    #    新版 chromedriver 已經**不接受**它們，會直接啟動失敗：
    #        invalid argument: unrecognized chrome option: excludeSwitches
    #    現代等價做法是 `--disable-blink-features=AutomationControlled`
    #    （已在 _make_options）＋ CDP 注入隱藏 navigator.webdriver。
    try:
        from selenium import webdriver
        driver = webdriver.Chrome(options=_make_options(headless))
        _hide_webdriver(driver)
        return driver
    except Exception as exc:            # noqa: BLE001
        raise BrowserUnavailableError(f"無法啟動 Chrome：{exc}") from exc


@contextmanager
def browser(headless: bool) -> Iterator[Any]:
    """driver 生命週期。⚠️ 一定要 quit，否則會留下殭屍 chrome 行程吃記憶體。"""
    driver = None
    try:
        driver = _build_driver(headless)
        driver.set_page_load_timeout(settings.OTA_FETCH_TIMEOUT)
        yield driver
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:           # noqa: BLE001 —— quit 失敗不該蓋掉原本的錯誤
                logger.warning("[OTA] driver.quit() 失敗，可能留下殘留行程")

            # ⚠️ Windows 上 `undetected_chromedriver` 會在直譯器關閉時由
            #    `Chrome.__del__` 再 quit 一次，印出一段嚇人的 traceback：
            #
            #        Exception ignored in: <function Chrome.__del__ ...>
            #        OSError: [WinError 6] 控制代碼無效。
            #
            #    行程其實已經正常結束了（我們上面自己 quit 過），
            #    那只是重複清理踩到已關閉的 handle。但它長得跟真的錯誤
            #    一模一樣，會讓人以為擷取失敗了 —— 實測 2026-08-23 就是
            #    在一次**成功**的同步後面看到它。
            #
            #    把 `__del__` 換成 no-op：清理我們自己做完了，不需要它。
            try:
                type(driver).__del__ = lambda self: None
            except Exception:           # noqa: BLE001 —— 純粹是消雜訊，失敗無所謂
                pass


def resolve_modes(prefer_visible: bool) -> list[bool]:
    """
    依設定決定要試哪些模式，回傳 headless 旗標的清單（依序嘗試）。

    | OTA_BROWSER_MODE | prefer_visible=False | prefer_visible=True |
    |------------------|----------------------|---------------------|
    | auto（預設）      | [headless, visible]  | [visible, headless] |
    | headless         | [headless]           | [headless]          |
    | visible          | [visible]            | [visible]           |

    ⚠️ **auto 模式一律兩種都會試**，只是順序不同。
       「headless 失敗就換可見視窗」對每一站都成立，不該由 parser 決定 ——
       2026-08-22 實測 Tripadvisor 被 headless 擋掉，而它當時
       `prefer_visible=False`，**連退一步的機會都沒有**就直接失敗。

    `prefer_visible` 現在只決定**先試哪一個**，是純粹的效率考量：

      - Booking      實測 headless 就過 → False，先試 headless（快）
      - Tripadvisor  實測 headless 必被擋 → True，直接開可見視窗，
                     省下每次白試一輪 headless 的十幾秒

    ⚠️ 伺服器（無桌面 session）上開可見視窗會**快速失敗**而不是逾時，
       所以就算把 prefer_visible 設成 True，在伺服器上也只是多幾秒，
       之後仍會退回 headless。
    """
    mode = (settings.OTA_BROWSER_MODE or "auto").strip().lower()
    if mode == "headless":
        return [True]
    if mode == "visible":
        return [False]
    return [False, True] if prefer_visible else [True, False]


def fetch_static(url: str) -> tuple[str, bool]:
    """
    先用 requests 試一次（成本最低，不開瀏覽器）。

    回傳 `(html, needs_browser)`。`requests` 已在 requirements（OHIP 用），
    不是新增相依。
    """
    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.5",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        response = session.get(url, timeout=25, allow_redirects=True)
    except Exception as exc:            # noqa: BLE001
        logger.info("[OTA] 靜態抓取失敗（%s），改用瀏覽器", exc)
        return "", True

    html = response.text
    needs_browser = (
        response.status_code in (202, 403, 429)
        or looks_empty(html)
        or looks_blocked(html)
    )
    return html, needs_browser


def wait_ready(driver, timeout: int = 18) -> None:
    """等頁面載出實質內容（或等到攔截頁出現，那樣也算「載完了」）。"""
    from selenium.webdriver.support.ui import WebDriverWait

    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.page_source) > 12_000 or looks_blocked(d.page_source)
        )
    except Exception:                   # noqa: BLE001 —— 逾時就用當下的內容繼續判斷
        logger.info("[OTA] 等待頁面內容逾時，改用當下 page_source 判斷")
    time.sleep(1.5)


def assert_usable(html: str) -> None:
    """
    把「空頁」與「被擋」轉成明確的例外，不要讓它們流進 parser。

    ⚠️ **順序很重要，先判空頁再判被擋**（2026-08-22 修正）。

    `looks_empty` 看 **HTML 長度**、`looks_blocked` 看 **可見文字長度**，
    而未渲染的 app shell **兩者都會命中**：

        <div id="root"></div>   → HTML 很短、可見文字也是 0

    先判被擋的話，一個單純還沒渲染的頁面會回報「被要求驗證」——
    使用者會去查站方擋不擋人，實際上只是要多等一下或換網址。

    分工（依「訊息對使用者有多少幫助」排序）：

      | 情況 | 例外 | 訊息 |
      |------|------|------|
      | 有明確驗證字樣（不論長短） | `CaptchaError` | 「被要求驗證」—— 我們知道原因，直接講 |
      | HTML 就很短、也沒有驗證字樣 | `ScraperError` | 「還沒渲染完或版面改版」 |
      | HTML 長但可見文字極少 | `CaptchaError` | Expedia 實測：121,540 字元 HTML、63 字元可見文字 |

    ⚠️ **有特徵字時優先報 CaptchaError**，即使頁面很短。
       一個 171 字元、寫著「Please complete the CAPTCHA」的頁面，
       報「內容過短，可能還沒渲染完」是把已知的答案藏起來。
    """
    if has_block_marker(html):
        raise CaptchaError("OTA 要求人機驗證或拒絕自動讀取，請稍後再試（不重試）")
    if looks_empty(html):
        raise ScraperError(
            f"頁面內容過短（{len(html)} 字元），可能是還沒渲染完或版面已改版"
        )
    if looks_blocked(html):
        raise CaptchaError(
            f"頁面沒有實質內容，多半是驗證頁（不重試）"
            f"——HTML {len(html):,} 字元，但可見文字只有 "
            f"{len(visible_text(html)):,} 字元"
        )


def headless_blocked_message(url: str, last_error: Exception | None = None,
                             browser_started: bool = True) -> str:
    """
    兩種模式都失敗時的訊息。

    ⚠️⚠️ **2026-08-24 大改：這則訊息原本在猜，而且會把人帶錯方向。**

       舊版不管實際發生什麼，一律寫死：

           「本機器多半沒有互動式桌面 session（例如以 Windows Service 執行）」

       它從來沒有驗證過這件事，而且**把真正的例外整個丟掉**。
       實測踩到：使用者就坐在桌面前、Chrome 開得好好的，
       真正的原因是新寫的 TripComParser 少點一顆「全部 447 則評論」按鈕，
       解析結果 0 筆 —— 然後畫面叫他去查 Windows Service。

       **「瀏覽器開不起來」和「瀏覽器開了但解析不到」是兩件完全不同的事，
       修法也完全不同。** 訊息必須先講事實（真正的例外），
       再依「瀏覽器有沒有啟動成功」給出對的方向。

    ⚠️ 這與本模組其他地方的原則一致：`assert_usable()` 也是先分辨
       「短頁面」「有驗證字樣」「HTML 長但沒有可見文字」才報對應的錯，
       不是統一報一句「失敗」。
    """
    detail = f"{type(last_error).__name__}: {last_error}" if last_error else "（沒有捕捉到例外）"

    if not browser_started:
        cause = (
            "無頭與可見視窗**都啟動不了瀏覽器** —— 這是規格書 §3.3 的 R1。\n"
            "常見原因：以 Windows Service／LocalSystem 執行（沒有互動式桌面 session）、\n"
            "或 chromedriver 與已安裝的 Chrome 版本對不上。\n"
            "\n"
            "兩條退路（擇一）：\n"
            "  1. 用 Windows 工作排程器「以登入使用者身分」執行：\n"
            "     cd backend && python -m app.services.ota_scraper_cli\n"
            "     並把 .env 的 OTA_BROWSER_MODE 設為 visible\n"
            "  2. 改用 CSV 匯入（Portal →口碑分析 → OTA 來源設定 → CSV 匯入）"
        )
    else:
        cause = (
            "⚠️ **瀏覽器有啟動成功，是「開了頁面但解析不到評論」** ——\n"
            "   所以這**不是** R1，跟 Windows Service／桌面 session 無關。\n"
            "\n"
            "依可能性排序：\n"
            "  1. **少了一步互動**：有些站要先點「全部 N 則評論」「顯示所有評語」\n"
            "     才會出現評論列表。詳情頁上看得到的可能是結構完全不同的摘要輪播。\n"
            "  2. **OTA 改版**，selector 失效（定義在 ota_parser.py 頂端的常數區）\n"
            "  3. 內容還沒渲染完（SPA 載入較慢）\n"
            "\n"
            "先跑診斷看是哪一種：\n"
            "  cd backend && python -m app.services.ota_scraper_cli \\\n"
            "      --diagnose \"<網址>\" --platform <平台代碼>"
        )

    return (
        f"{cause}\n"
        f"\n"
        f"最後一次的實際錯誤：{detail}\n"
        f"來源：{url}"
    )
