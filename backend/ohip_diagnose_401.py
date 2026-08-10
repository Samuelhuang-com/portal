"""
OHIP 換 token 401 對照診斷 — 找出「Failed to authenticate application」的真正原因

背景：`ohip_connectivity_test.py` 在 POST /oauth/v1/tokens 收到
      HTTP 401 "Failed to authenticate application"。
      這個訊息本身沒有鑑別度，可能是 x-app-key、client_id/secret、
      或 Application 剛註冊尚未生效（propagation）任一種。

做法：發 5 組**只有一個變數不同**的對照請求，比對回應。
      哪一組的錯誤訊息與其他組不同，問題就在那個變數上。

安全：
  - 只發 POST /oauth/v1/tokens（換 token），不碰任何業務資料
  - 螢幕上只印長度與字元類型，**不印任何憑證明文**
  - 故意用錯的憑證只會被拒絕，不會鎖帳號（OHIP 無登入鎖定機制）

用法：
    cd backend
    python ohip_diagnose_401.py
"""
from __future__ import annotations

import base64
import os
import re
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

GATEWAY = os.getenv("OHIP_GATEWAY_URL", "").rstrip("/")
APP_KEY = os.getenv("OHIP_APP_KEY", "")
CLIENT_ID = os.getenv("OHIP_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("OHIP_CLIENT_SECRET", "")
SCOPE = os.getenv("OHIP_SCOPE", "urn:opc:hgbu:ws:__myscopes__")

TOKEN_URL = f"{GATEWAY}/oauth/v1/tokens"
TIMEOUT = 45

BAD = "0" * 32  # 明顯錯誤的對照值


# ── 連線前置檢查 ─────────────────────────────────────────────────────────────
# 2026-08-06 實測踩到：同一台機器前幾分鐘還能通，之後 DNS 解析失敗噴滿頁 traceback。
# 那是網路層問題（斷線／VPN／DNS），不是程式或憑證問題，但原始 traceback 完全看不出來。

def preflight() -> bool:
    """先確認 gateway 的網域解析得到，解析不到就直接給人話。"""
    import socket
    from urllib.parse import urlparse

    host = urlparse(GATEWAY).hostname
    if not host:
        print(f"❌ OHIP_GATEWAY_URL 格式不正確：{GATEWAY!r}")
        return False
    try:
        socket.getaddrinfo(host, 443)
        return True
    except socket.gaierror:
        print(f"""
❌ 連不到 OHIP：DNS 解析失敗（無法解析 {host}）

   這是**網路層**問題，與憑證、程式無關。依序檢查：

   1. 網路是否斷線 —— 開瀏覽器隨便連一個網站試試
   2. VPN 是否斷開 —— 若公司網路需要 VPN 才能連外，重新連線
   3. DNS 是否正常 —— 在 cmd 執行：
          nslookup {host}
      解析不到就是 DNS 或防火牆的問題，找 IT 確認
   4. 公司防火牆是否擋掉 *.oraclecloud.com

   確認網路恢復後重跑本腳本即可，不需要改任何設定。
""")
        return False
    except Exception as e:
        print(f"❌ 網域檢查失敗：{type(e).__name__}: {e}")
        return False


def describe(name: str, val: str) -> None:
    """只描述特徵，不印明文"""
    if not val:
        print(f"  {name:<20} ❌ 空值")
        return
    if re.fullmatch(r"[0-9a-fA-F]+", val):
        kind = "純 hex"
    elif re.fullmatch(r"[0-9a-fA-F-]+", val):
        kind = "hex + dash（UUID 形式）"
    elif re.fullmatch(r"[0-9a-zA-Z._~-]+", val):
        kind = "英數"
    else:
        kind = "含特殊字元"
    flags = []
    if val != val.strip():
        flags.append("⚠️ 頭尾有空白")
    if val[:1] in "\"'":
        flags.append("⚠️ 被引號包住")
    if "<" in val or ">" in val:
        flags.append("⚠️ 還是佔位符")
    print(f"  {name:<20} 長度 {len(val):>3}｜{kind}｜尾碼 …{val[-4:]}"
          + ("｜" + " ".join(flags) if flags else ""))


def attempt(label: str, app_key: str, cid: str, secret: str,
            send_scope: bool = True, creds_in_body: bool = False) -> None:
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if app_key:
        headers["x-app-key"] = app_key

    data = {"grant_type": "client_credentials"}
    if send_scope:
        data["scope"] = SCOPE

    if creds_in_body:
        data["client_id"] = cid
        data["client_secret"] = secret
    else:
        basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
        headers["Authorization"] = f"Basic {basic}"

    try:
        r = requests.post(TOKEN_URL, headers=headers, data=data, timeout=TIMEOUT)
    except Exception as e:
        print(f"  {label:<34} 連線失敗：{type(e).__name__}")
        return

    body = (r.text or "").strip().replace("\n", " ")[:120]
    rid = r.headers.get("X-Request-Id") or r.headers.get("x-request-id") or "—"
    mark = "✅" if r.status_code == 200 else "  "
    print(f"{mark} {label:<34} HTTP {r.status_code}｜{body}")
    print(f"    X-Request-Id: {rid}")


def main() -> None:
    print("=" * 78)
    print("OHIP 換 token 401 對照診斷")
    print(f"Token URL: {TOKEN_URL}")
    print("=" * 78)

    print("\n[憑證特徵檢查]（不顯示明文）")
    describe("OHIP_APP_KEY", APP_KEY)
    describe("OHIP_CLIENT_ID", CLIENT_ID)
    describe("OHIP_CLIENT_SECRET", CLIENT_SECRET)
    print("\n  對照：Developer Portal 上 Application Key 的遮罩是 28 個 * + 尾碼 0b95。")
    print("        若上面 APP_KEY 的長度不是 32，很可能複製時多帶了字元，請重新 Copy。")

    if not all([GATEWAY, APP_KEY, CLIENT_ID, CLIENT_SECRET]):
        print("\n❌ 有欄位是空的，先補齊 backend/.env 再跑。")
        return

    if not preflight():
        return

    print("\n[對照測試] 每組只改一個變數，比對錯誤訊息差異\n")

    attempt("1 基準（現有設定）", APP_KEY, CLIENT_ID, CLIENT_SECRET)
    attempt("2 app-key 故意錯", BAD, CLIENT_ID, CLIENT_SECRET)
    attempt("3 client secret 故意錯", APP_KEY, CLIENT_ID, BAD)
    attempt("4 基準 + 不帶 scope", APP_KEY, CLIENT_ID, CLIENT_SECRET, send_scope=False)
    attempt("5 基準 + 憑證改放 body", APP_KEY, CLIENT_ID, CLIENT_SECRET, creds_in_body=True)

    print("\n" + "=" * 78)
    print("怎麼讀這份結果")
    print("=" * 78)
    print("""
  ・第 4 或 5 組回 200
        → 只是傳法問題，照那組改 ohip_connectivity_test.py 即可。

  ・1、2、3 組訊息**完全一樣**
        → 這個錯誤訊息沒有鑑別度，Gateway 在驗 app-key 就擋掉了，
          根本還沒驗到 client credentials。最可能是 Application 剛註冊
          **尚未 propagate**（OHIP 已知行為，需數十分鐘到數小時）。
          → 先等一段時間再跑一次基準組。

  ・第 2 組訊息與第 1 組**不同**（例如變成 403 或別的字串）
        → 代表 Gateway 認得你的 app-key，問題出在 client_id / client_secret。
          → 回 Environments → HANNS-GLORYS-Client → Manage 重新 Copy secret。

  ・第 3 組訊息與第 1 組**不同**
        → 代表 client secret 是被實際驗證的，你目前這組是對的，
          問題反而在 app-key 或訂閱關聯。

  ・全部都連線失敗
        → 公司防火牆擋掉了對外 HTTPS，換一台機器或開白名單。

  把 X-Request-Id 記下來 —— 若最後要開 Oracle 服務單，這是必要資訊。
""")


if __name__ == "__main__":
    main()
