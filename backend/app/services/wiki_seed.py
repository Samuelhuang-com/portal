"""
知識庫範例資料 Seed
首次啟動時若 wiki_articles 為空，自動植入範例文章。
包含：10 篇 SOP（飯店集團日常作業）+ 5 篇開發者 Wiki
"""
import json
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.wiki import WikiArticle, _slugify


SAMPLE_ARTICLES = [
    # ─────────────────────────────────────────────────────────────────────────
    # 員工 SOP 知識庫（category=sop）
    # ─────────────────────────────────────────────────────────────────────────
    {
        "title": "冷氣異常故障排查 SOP",
        "category": "sop",
        "tags": ["空調", "設備保養", "緊急處理"],
        "body": """# 冷氣異常故障排查 SOP

## 適用範圍
飯店客房、大廳、商場公共區域的中央空調及分離式冷氣。

## 故障現象分類

### 1. 冷氣不冷（溫度偏高）
- **可能原因**：濾網阻塞、冷媒不足、壓縮機故障
- **初步檢查步驟**：
  1. 確認設定溫度是否正確（建議 22–25°C）
  2. 清潔或更換濾網（每月至少一次）
  3. 檢查室外機是否有雜物遮蔽
  4. 若以上均正常，通知工務報修

### 2. 冷氣異音
- **異音類型**：
  - **滴水聲** → 排水管阻塞，清通排水管
  - **噪音/震動** → 風扇葉片異物或鬆動，聯繫工務
  - **嗡嗡聲** → 電容器問題，立即停機通報

### 3. 遙控器無反應
1. 更換電池（使用 AA 鹼性電池）
2. 確認接收器無遮蔽物
3. 重設遙控器（長按 RESET 鍵 5 秒）

## 報修流程
1. 於 Portal → 工務報修 → 新增報修單
2. 填寫：樓層、房號、故障描述、發現時間
3. 緊急狀況（全樓停冷氣）：直接撥打工務急線 **#2001**

## 注意事項
- ❌ 禁止自行拆卸冷氣主機
- ✅ 報修前請先拍照存證，上傳至報修單附件
""",
        "summary": "飯店冷氣故障排查步驟：不冷、異音、遙控器失靈的處理方式與報修流程。",
    },
    {
        "title": "每日水電錶數值登錄作業 SOP",
        "category": "sop",
        "tags": ["日常作業", "數值登錄", "水電"],
        "body": """# 每日水電錶數值登錄作業 SOP

## 作業時間
- 每日 **07:00–08:00** 完成登錄
- 假日由值班工務人員執行

## 登錄範圍

| 類別 | 位置 | 頻率 |
|------|------|------|
| 全棟電錶 | B4F 電錶房 | 每日 |
| 商場空調電錶 | 各樓空調箱 | 每日 |
| 專櫃電錶 | 各專櫃配電盤 | 每日 |
| 專櫃水錶 | B1F 管道間 | 每週 |

## 登錄步驟

1. 攜帶**數值登錄表格**（紙本或 Portal 手機版）
2. 依照路線巡視各電錶、水錶
3. 記錄**當日讀數**（注意：整數位，不含小數）
4. 登入 Portal → 每日數值登錄表
5. 選擇對應日期，依序輸入各表讀數
6. 點擊**儲存** → 系統自動計算日用量與月累計

## 異常判斷
- 當日用量 **超出前 7 日平均值 30%** 以上 → 標記異常，通報主管
- 讀數**比昨日小**（不可能減少）→ 確認是否錶頭重置或讀錯

## 常見錯誤
> ⚠️ 忘記切換日期 → 資料會覆蓋前日，請務必確認日期正確
""",
        "summary": "每日水電錶數值登錄的時間、範圍、步驟與異常判斷標準。",
    },
    {
        "title": "緊急停電應變 SOP",
        "category": "sop",
        "tags": ["緊急處理", "電氣", "安全規範"],
        "body": """# 緊急停電應變 SOP

## 初步確認（3分鐘內完成）

1. **確認停電範圍**：是單一樓層、整棟、還是區域性停電
2. **確認緊急電源是否啟動**：檢查 B4F 發電機狀態燈
3. **聯繫台電**：查詢是否外部停電（台電客服 1911）

## 分級應變

### 🔴 全棟停電（含外電中斷）
1. 立即通報 **值班主管** 與 **工務主任**
2. 確認緊急照明、逃生指示燈正常
3. 電梯停止 → 派員至各樓層確認無受困者
4. 通知餐廳暫停明火烹調
5. 客房部門發送客房通知（道歉 + 預估恢復時間）

### 🟡 部分樓層停電（跳電）
1. 至 B4F 配電盤確認跳脫開關
2. 排除過載原因後，復歸開關
3. 若再次跳脫 → 不得強制復歸，立即聯繫工務

### 🟢 單一設備跳電
1. 確認設備電源線無損壞
2. 至就近配電箱復歸對應回路
3. 記錄跳電時間、原因、處理方式

## 復電後確認
- [ ] UPS 設備狀態正常
- [ ] 伺服器室溫度恢復正常
- [ ] 冰箱、冷凍庫溫度確認
- [ ] 電梯恢復正常運行
- [ ] 門禁系統重新上線
""",
        "summary": "緊急停電三級應變流程：全棟停電、部分樓層停電、單一設備跳電的處理步驟。",
    },
    {
        "title": "消防設備月巡檢 SOP",
        "category": "sop",
        "tags": ["消防", "安全規範", "巡檢", "設備保養"],
        "body": """# 消防設備月巡檢 SOP

## 巡檢頻率
- **滅火器**：每月目視檢查、每年更換
- **消防栓**：每月測試
- **偵煙器**：每季測試
- **灑水頭**：每半年外觀檢查

## 月巡檢清單

### 滅火器
- [ ] 壓力錶指針在綠色範圍
- [ ] 外殼無損傷、生鏽
- [ ] 插梢（保險別針）完整
- [ ] 標籤清晰可見（使用說明、有效期限）
- [ ] 固定架穩固

### 消防栓箱
- [ ] 箱門開關正常，無上鎖
- [ ] 水帶折疊整齊
- [ ] 水帶接頭無鏽蝕
- [ ] 瞄子（噴嘴）無損壞
- [ ] 啟動閥無漏水

## 異常記錄方式
1. 於 Portal → 保全巡檢 → 選擇對應樓層
2. 在「異常說明」欄位填入異常描述
3. 上傳現場照片
4. 標記「需工務處理」

## 注意事項
> ⚠️ 發現滅火器壓力不足，**立即更換備用品**，不可拖延。
> 消防設備缺失屬重大安全疏失，須當日回報主管。
""",
        "summary": "消防設備月巡檢清單：滅火器、消防栓、偵煙器的檢查項目與異常回報方式。",
    },
    {
        "title": "保養工單新增與完成確認 SOP",
        "category": "sop",
        "tags": ["設備保養", "報修", "工單"],
        "body": """# 保養工單新增與完成確認 SOP

## 新增工單

### 步驟
1. 登入 **Portal** → 選擇對應模組：
   - 客房保養 → 飯店管理 → 1. 飯店週期保養表
   - 商場設備 → 商場管理 → 商場例行維護
2. 點擊「新增保養單」
3. 填寫必填欄位：
   - **保養日期**：選擇實際執行日期
   - **設備名稱**：從下拉選單選擇
   - **保養類型**：例行 / 緊急 / 預防性
   - **執行人員**：選擇或輸入
4. 儲存後系統自動同步至 Ragic

### 注意
- 工單必須在**執行當天**建立，不可事後補填超過 3 天
- 緊急報修請使用「緊急」類型，系統會自動通報主管

## 完成確認

1. 進入工單詳情
2. 填寫「完成時間」與「實際工時」
3. 填寫「保養結果備註」（至少 10 字）
4. 點擊「標記完成」
5. 若有更換零件，點擊「新增用料記錄」

## 常見問題

**Q：工單同步失敗怎麼辦？**
A：等待 30 分鐘後重試；若仍失敗，在 Portal → 設定 → Ragic 連線 手動觸發同步。

**Q：可以修改已完成的工單嗎？**
A：已完成工單只有管理員可修改，請聯繫系統管理員。
""",
        "summary": "保養工單的新增步驟、完成確認流程與常見問題解答。",
    },
    {
        "title": "電梯月保養記錄 SOP",
        "category": "sop",
        "tags": ["電梯", "設備保養", "安全規範"],
        "body": """# 電梯月保養記錄 SOP

## 保養週期
- **月保養**：由認證電梯廠商執行（固定廠商：XX電梯）
- **季度大保養**：每季第一個月執行，含緊急電話測試
- **年度認證**：配合主管機關定期審驗

## 保養前準備
1. 確認廠商到場時間（通知前台、保全）
2. 於 Portal → 日曆 新增「電梯保養停用」事件
3. 在電梯入口張貼停用公告（至少提前 2 小時）

## 保養中配合事項
- 保安人員全程陪同監督
- 記錄廠商保養開始與結束時間
- 保養結束前進行**電梯功能確認測試**：
  - [ ] 各樓層停靠正常
  - [ ] 開關門順暢
  - [ ] 緊急呼叫鈕有人應答
  - [ ] 超重警報正常

## 保養後記錄
1. 取得廠商簽名的**保養記錄表**（掃描存入 Ragic）
2. Portal → 全棟例行維護 → 新增電梯保養記錄
3. 填寫：保養日期、廠商名稱、保養項目、發現問題與處置方式
""",
        "summary": "電梯月保養的週期、廠商陪同流程、功能測試清單與保養後記錄方式。",
    },
    {
        "title": "保全夜間巡檢路線與注意事項",
        "category": "sop",
        "tags": ["保全", "巡檢", "安全規範"],
        "body": """# 保全夜間巡檢路線與注意事項

## 巡檢時間表

| 次數 | 時間 | 重點區域 |
|------|------|---------|
| 第一巡 | 22:00 | 全棟外圍 + 1F 商場 |
| 第二巡 | 01:00 | B1F~B4F 停車場 + 機房 |
| 第三巡 | 04:00 | 各樓層走廊 + 逃生梯 |
| 第四巡 | 06:00 | 開店前商場全區 |

## 標準巡檢路線（第一巡）

```
大門廣場 → 1F 大廳 → 1F 商場（順時針）
→ B1F 停車場入口 → 機電房區域
→ 搭電梯至 RF 屋頂 → 逐層往下走逃生梯
→ 回到 1F 警衛室 填寫巡檢記錄
```

## 巡檢記錄方式
1. 登入 Portal → 保全巡檢 → 選擇對應班次
2. 逐項填寫各區域狀況（正常 / 異常）
3. 發現異常立即拍照，填入「異常說明」
4. 完成後點擊提交

## 緊急聯絡
- 消防 **119** / 警察 **110**
- 工務急線：**#2001**
- 值班主管：**#2010**

## 禁止事項
- ❌ 巡檢途中使用手機（緊急聯絡除外）
- ❌ 獨自進入封閉機房（需有第二人陪同）
- ❌ 發現可疑人物時自行處置（立即通報並等待支援）
""",
        "summary": "保全夜間四次巡檢的時間表、標準路線、記錄方式與緊急聯絡流程。",
    },
    {
        "title": "清潔外包廠商驗收 SOP",
        "category": "sop",
        "tags": ["清潔", "日常作業", "外包管理"],
        "body": """# 清潔外包廠商驗收 SOP

## 驗收時間
- 每日清晨清潔完成後（約 08:00）
- 由工務/管家部主管執行抽驗

## 驗收區域與標準

### 公共區域（必驗）
| 區域 | 驗收重點 |
|------|---------|
| 1F 大廳 | 地面光亮無水痕、玻璃門無指紋 |
| 電梯廂 | 鏡面無霧、地面乾淨、按鈕無污漬 |
| 廁所 | 無異味、馬桶內外清潔、紙巾補充充足 |
| 走廊 | 地毯吸塵徹底、牆腳無毛球 |

### 評分方式
- **A（優良）**：完全符合標準
- **B（合格）**：輕微瑕疵，當場口頭要求補做
- **C（不合格）**：明顯髒汙，書面通知要求重做 + 扣點

## 扣點制度
- 月累計 C 超過 3 次 → 書面警告
- 月累計 C 超過 5 次 → 罰款並要求換人

## 記錄方式
填寫驗收記錄表後，掃描上傳至 Ragic 清潔管理模組。
""",
        "summary": "清潔外包廠商每日驗收的時間、區域標準、評分方式與扣點制度。",
    },
    {
        "title": "客房報修快速處理流程",
        "category": "sop",
        "tags": ["報修", "客房", "緊急處理"],
        "body": """# 客房報修快速處理流程

## 報修分級

| 等級 | 描述 | 目標處理時間 |
|------|------|------------|
| P1（緊急）| 漏水、停電、無法入住 | 30 分鐘內回應 |
| P2（優先）| 空調故障、熱水無法使用 | 2 小時內完成 |
| P3（一般）| 燈泡更換、家具輕微損壞 | 24 小時內完成 |

## 前台收到報修

1. **聆聽並記錄**：房號、問題描述、住客聯絡方式
2. **立即分級**：依上表判斷等級
3. **通知工務**：
   - P1：電話直撥工務急線 #2001
   - P2/P3：於 Portal 新增報修單

## 工務處理完成後

1. 電話通知前台「已完成」
2. 前台致電住客確認
3. Portal 工單標記完成，備註：住客滿意度

## 住客安撫話術
> 「非常抱歉造成您的不便，我們的技術人員正在處理，預計 [時間] 前完成，感謝您的耐心等候。」

若處理時間超過預估：
> 「很抱歉需要更多時間，目前進度是 [說明]，我們預計在 [新時間] 前完成，並提供您 [補償方案]。」
""",
        "summary": "客房報修三級分類（P1/P2/P3）、前台流程、工務處理規範與住客安撫話術。",
    },
    {
        "title": "新進員工 Portal 系統使用導覽",
        "category": "sop",
        "tags": ["新人訓練", "日常作業"],
        "body": """# 新進員工 Portal 系統使用導覽

## 系統登入

1. 打開瀏覽器，前往 Portal 網址（詢問主管）
2. 帳號：員工編號（如：E001）
3. 初始密碼：生日後六碼（MMDDYY），**首次登入必須修改**

## 常用功能快速導覽

### 我的工作（建議每天第一件事）
- **Dashboard** → 查看今日待處理事項
- **行事曆** → 查看本週排程與保養計畫

### 報修作業
- 工務報修 → 大直工務部 / 商場工務報修
- 填寫：位置、故障描述、嚴重程度

### 巡檢記錄
- 依你的崗位選擇對應模組（保全 / 商場工務 / 飯店工務）
- 每次巡檢後當日完成登錄

### 知識庫
- **知識庫** → 搜尋 SOP、操作手冊
- 遇到不確定的情況，先查知識庫！

## 常見問題

**Q：忘記密碼怎麼辦？**
A：聯繫系統管理員 → 設定 → 使用者管理 → 重設密碼

**Q：找不到我負責的模組？**
A：主管需要在 設定 → 角色管理 中開通你的權限

## 緊急聯絡
- 系統問題：IT 分機 #2050
- 操作問題：詢問直屬主管或查閱知識庫
""",
        "summary": "新進員工 Portal 登入方式、常用功能導覽、巡檢記錄提交與密碼重設說明。",
    },

    # ─────────────────────────────────────────────────────────────────────────
    # 開發者技術 Wiki（category=dev）
    # ─────────────────────────────────────────────────────────────────────────
    {
        "title": "Portal 架構總覽與開發環境設定",
        "category": "dev",
        "tags": ["架構", "FastAPI", "React", "環境設定"],
        "body": """# Portal 架構總覽與開發環境設定

## 技術棧

| 層次 | 技術 | 版本 |
|------|------|------|
| 後端 | FastAPI | 0.111 |
| ORM | SQLAlchemy | 2.0（同步模式） |
| 資料庫 | SQLite（WAL 模式） | 3.x |
| 前端 | React + TypeScript | 18 + 5 |
| UI 元件 | Ant Design | 5 |
| 狀態管理 | Zustand（auth only）+ useState | — |
| 外部資料 | Ragic API（Basic Auth） | — |

## 啟動開發環境

```bash
# 後端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（另開終端）
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## 專案結構速查

```
portal/
├── backend/app/
│   ├── core/          # config, database, security, scheduler
│   ├── models/        # SQLAlchemy ORM 資料表
│   ├── routers/       # FastAPI 路由（每個模組一個檔案）
│   ├── schemas/       # Pydantic request/response 型別
│   ├── services/      # 業務邏輯（從 router 拆出）
│   └── main.py        # App 入口 + lifespan + router 掛載
└── frontend/src/
    ├── api/           # axios 封裝（每個模組一個檔案）
    ├── pages/         # React 頁面元件
    ├── components/    # 共用元件（Layout 等）
    ├── router/        # React Router v6 定義
    ├── stores/        # Zustand（只有 authStore）
    └── types/         # TypeScript 型別定義
```

## 重要規則（CLAUDE.md 摘要）
- API prefix 統一用 `/api/v1/`
- Ragic Basic Auth：直接用 API key，**不做 base64**
- 前端 API 呼叫：統一用 `@/api/` 下的封裝，**不在元件內直接用 axios**
- DB Session：永遠用 `Depends(get_db)`
""",
        "summary": "Portal 技術棧、啟動步驟、專案結構說明與核心開發規則摘要。",
    },
    {
        "title": "新增模組標準作業流程（後端 + 前端）",
        "category": "dev",
        "tags": ["架構", "開發流程", "FastAPI", "React"],
        "body": """# 新增模組標準作業流程（後端 + 前端）

## 後端（6 個步驟）

### 1. 建立 Model（`app/models/xxx.py`）
```python
from app.core.database import Base
from app.core.time import twnow
import uuid

class MyModel(Base):
    __tablename__ = "my_table"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=twnow)
```

### 2. 建立 Schema（`app/schemas/xxx.py`）
```python
class MyCreate(BaseModel):
    name: str

class MyOut(BaseModel):
    id: str
    name: str
    model_config = {"from_attributes": True}
```

### 3. 建立 Service（`app/services/xxx_service.py`）
業務邏輯從 router 拆出，保持 router 薄。

### 4. 建立 Router（`app/routers/xxx.py`）
```python
router = APIRouter()

@router.get("", response_model=List[MyOut])
def list_items(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return svc.list(db)
```

### 5. 在 `main.py` 掛載
```python
from app.routers import xxx
app.include_router(xxx.router, prefix=f"{API_PREFIX}/xxx", tags=["Xxx"])
```

### 6. 在 `lifespan` 加 import（讓 create_all 知道這個 table）
```python
import app.models.xxx  # noqa: F401
```

## 前端（5 個步驟）

1. **型別** → `src/types/xxx.ts`
2. **API 封裝** → `src/api/xxx.ts`（用 `apiClient`）
3. **頁面元件** → `src/pages/Xxx/index.tsx`
4. **Router** → `src/router/index.tsx` 加 `<Route path="xxx" element={<XxxPage />} />`
5. **Sidebar** → `MainLayout.tsx` 的 `menuItems` + `navLabels.ts`

## 文件更新（必須）
每次新增模組後，更新：
- `README.md` → 最後更新日期 + 最近變更
- `docs/CHANGELOG.md` → 版本記錄
- `docs/TECH_SPEC.md` → 技術規格表
""",
        "summary": "新增後端模組（Model→Schema→Service→Router→main.py）與前端模組的標準六步驟流程。",
    },
    {
        "title": "Ragic API 整合設計筆記",
        "category": "dev",
        "tags": ["Ragic", "API設計", "資料庫", "同步"],
        "body": """# Ragic API 整合設計筆記

## 認證方式

```python
# ⚠️ 重要：不做 base64，直接用 API key
headers = {"Authorization": f"Basic {settings.RAGIC_API_KEY}"}
```

## 標準 Ragic fetch 模式

```python
import httpx
from app.core.config import settings

async def fetch_ragic_sheet(path: str, server_url: str = None, account: str = None) -> dict:
    base_url = f"https://{server_url or settings.RAGIC_SERVER_URL}/{account or settings.RAGIC_ACCOUNT}"
    url = f"{base_url}/{path}"
    headers = {"Authorization": f"Basic {settings.RAGIC_API_KEY}"}

    async with httpx.AsyncClient(verify=settings.RAGIC_VERIFY_SSL, timeout=30) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
```

## 資料同步架構

```
APScheduler（每30分鐘）
    └─ _auto_sync()
        └─ sync_from_ragic()  ← 每個模組的 sync service
            ├─ fetch_ragic_sheet()  ← 抓 Ragic 資料
            ├─ upsert 到 SQLite      ← 比對 ragic_id
            └─ 回傳 {fetched, upserted, errors}
```

## 多 Server / Account 設定
部分 Sheet 在不同的 Ragic 帳號（`soutlet001` vs `intraragicapp`）：

```python
# config.py 設定
RAGIC_PM_SERVER_URL: str = "ap12.ragic.com"   # 不同 server
RAGIC_PM_JOURNAL_PATH: str = "periodic-maintenance/6"

# sync service 中使用
result = await fetch_ragic_sheet(
    path=settings.RAGIC_PM_JOURNAL_PATH,
    server_url=settings.RAGIC_PM_SERVER_URL,
    account=settings.RAGIC_PM_ACCOUNT,
)
```

## 常見踩坑

### 問題 1：Ragic 回傳 -1 key
Ragic 有時會在 JSON 中加入 `-1` key 作為 metadata，需要過濾：
```python
data = {k: v for k, v in raw.items() if k != "-1"}
```

### 問題 2：子表格欄位
Ragic 子表格（subtable）是巢狀 JSON，需要遞迴解析：
```python
subtable = record.get("1000123", {})  # 子表格 field id
for row in subtable.values():
    item_name = row.get("1000124", "")
```
""",
        "summary": "Ragic API 認證方式（不做 base64）、標準 fetch 模式、同步架構與常見踩坑。",
    },
    {
        "title": "SQLite WAL 模式與 OneDrive 環境注意事項",
        "category": "dev",
        "tags": ["SQLite", "資料庫", "部署", "除錯"],
        "body": """# SQLite WAL 模式與 OneDrive 環境注意事項

## 背景
Portal 的 SQLite 資料庫放在 OneDrive 同步資料夾中，這會導致：
- 多個行程同時讀寫時發生鎖定衝突
- OneDrive 的檔案系統監視器干擾 WAL 檔案

## WAL 模式設定（啟動時執行）

```python
# main.py lifespan
with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL"))
    conn.execute(text("PRAGMA busy_timeout=30000"))   # 30 秒等待鎖
    conn.execute(text("PRAGMA synchronous=NORMAL"))
    conn.commit()
```

## 關鍵 WAL 檔案
SQLite WAL 模式會產生兩個額外檔案：
- `portal.db-wal`：Write-Ahead Log
- `portal.db-shm`：Shared Memory

> ⚠️ 這兩個檔案是正常的，**不要刪除**

## 常見問題

### 問題：`database is locked`
**原因**：busy_timeout 太短，或另一個行程持有鎖太久

**解法**：
```python
PRAGMA busy_timeout=30000  # 提高到 30 秒
```

### 問題：OneDrive 自動備份衝突
**原因**：OneDrive 在備份 .db 時會鎖定檔案

**解法**：在 OneDrive 排除同步 `*.db-wal` 和 `*.db-shm` 檔案

### 問題：同步模式 vs 異步模式
本專案使用**同步 SQLAlchemy**（非 async），原因：
- `aiosqlite` 在 WAL 模式 + OneDrive 環境下不穩定
- APScheduler 的同步任務較易整合

> ❌ 禁止將同步模式改回 async（CLAUDE.md 規則）
""",
        "summary": "SQLite WAL 模式設定、OneDrive 環境的鎖定問題處理與同步/異步模式選擇說明。",
    },
    {
        "title": "JWT 認證架構與角色權限設計",
        "category": "dev",
        "tags": ["JWT", "認證", "API設計", "架構"],
        "body": """# JWT 認證架構與角色權限設計

## Token 結構

```python
# security.py
def create_access_token(subject: str, extra_claims: dict = {}) -> str:
    # ⚠️ subject 必須是純 UUID 字串（user.id）
    payload = {
        "sub": subject,           # user.id（UUID 字串）
        "email": extra_claims.get("email"),
        "roles": extra_claims.get("roles", []),
        "permissions": extra_claims.get("permissions", []),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

## 角色系統

| 角色 | 說明 | 特殊行為 |
|------|------|---------|
| `system_admin` | 最高管理員 | permissions=["*"]，全部通過 |
| 自訂角色 | 由管理員建立 | 需明確設定 permission_keys |

## 前端 Permission Guard

```tsx
// 細粒度權限守衛
function PermissionGuard({ permissionKey, children }) {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.roles?.includes('system_admin')
  const hasPermission = isAdmin ||
    user?.permissions?.includes('*') ||
    user?.permissions?.includes(permissionKey)

  return hasPermission ? children : <Forbidden403 />
}
```

## 後端 Dependency

```python
# dependencies.py
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # 解碼 JWT → 取 sub（user.id）→ 查 DB
    ...

def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)):
        if not any(r in user.role_names for r in roles):
            raise HTTPException(403, "權限不足")
        return user
    return dependency
```

## Token 刷新策略
- Access Token 有效期：30 分鐘
- Refresh Token 有效期：7 天
- 前端：每次 API 請求前檢查 Token 是否快過期（< 5 分鐘），自動刷新

## 常見錯誤
- `401 Unauthorized`：Token 過期或無效，前端會自動跳轉登入頁
- `403 Forbidden`：已登入但無對應 permission_key，前端顯示 403 提示頁
""",
        "summary": "Portal JWT Token 結構、角色系統、前端 PermissionGuard 與後端 Dependency 設計說明。",
    },
]


def seed_wiki_articles() -> None:
    """若 wiki_articles 為空，植入範例文章"""
    db: Session = SessionLocal()
    try:
        count = db.query(WikiArticle).count()
        if count > 0:
            return  # 已有資料，跳過

        import uuid
        for data in SAMPLE_ARTICLES:
            slug = _slugify(data["title"])
            # 確保 slug 唯一
            existing = db.query(WikiArticle).filter(WikiArticle.slug == slug).first()
            if existing:
                slug = f"{slug}-{uuid.uuid4().hex[:4]}"

            article = WikiArticle(
                title=data["title"],
                slug=slug,
                body=data["body"],
                summary=data.get("summary", ""),
                category=data["category"],
                tags=json.dumps(data.get("tags", []), ensure_ascii=False),
                author="系統預設",
                author_id="system",
                is_published=True,
            )
            db.add(article)

        db.commit()
        print(f"[Wiki] 範例資料植入完成：{len(SAMPLE_ARTICLES)} 篇文章")
    except Exception as e:
        db.rollback()
        print(f"[Wiki] 範例資料植入失敗：{e}")
    finally:
        db.close()
