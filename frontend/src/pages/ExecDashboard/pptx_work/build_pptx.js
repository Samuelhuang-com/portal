// build_pptx.js  — 工項工時 Dashboard Ragic 欄位對應簡報
"use strict";
const PptxGenJS = require("pptxgenjs");

// ── 色彩系統 ──────────────────────────────────────────────────────────────────
const C = {
  navy:    "1B3A5C",   // Portal 主色
  blue:    "4BA8E8",   // Portal 輔色
  darkBg:  "0F172A",   // 深色背景（標題頁）
  cardBg:  "1E293B",   // 深色卡片
  lightBg: "F0F4F8",   // 淺色頁面背景
  white:   "FFFFFF",
  offWhite:"F8FAFC",
  gold:    "F59E0B",   // 重點強調
  green:   "16A34A",
  red:     "DC2626",
  gray:    "64748B",
  lightGray:"E2E8F0",
  muted:   "94A3B8",
  teal:    "0D9488",
  purple:  "7C3AED",
};

// ── 陰影工廠（避免物件重用 Bug）─────────────────────────────────────────────
const mkShadow = () => ({ type:"outer", blur:8, offset:3, angle:135, color:"000000", opacity:0.12 });
const mkShadowLight = () => ({ type:"outer", blur:5, offset:2, angle:135, color:"000000", opacity:0.08 });

// ── 共用 Helper ────────────────────────────────────────────────────────────
function addSectionHeader(slide, title, pres) {
  slide.background = { color: C.lightBg };
  // 左側深藍色邊條
  slide.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.22, h:5.625, fill:{ color: C.navy } });
  slide.addText(title, {
    x:0.4, y:0.22, w:9.3, h:0.55,
    fontSize:22, bold:true, color:C.navy, fontFace:"Calibri",
    align:"left", margin:0,
  });
  // 底部裝飾線
  slide.addShape(pres.shapes.RECTANGLE, { x:0.4, y:0.82, w:9.2, h:0.04, fill:{ color: C.blue } });
}

function addScreenshotPlaceholder(slide, pres, x, y, w, h, label) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill:{ color:"E8F0F8" },
    line:{ color: C.blue, width:1.2, dashType:"dash" },
    shadow: mkShadowLight(),
  });
  // 模擬瀏覽器上方工具列
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h:0.22, fill:{ color: C.lightGray } });
  slide.addShape(pres.shapes.OVAL, { x:x+0.1, y:y+0.06, w:0.1, h:0.1, fill:{ color:"FC605B" } });
  slide.addShape(pres.shapes.OVAL, { x:x+0.24, y:y+0.06, w:0.1, h:0.1, fill:{ color:"FDBC40" } });
  slide.addShape(pres.shapes.OVAL, { x:x+0.38, y:y+0.06, w:0.1, h:0.1, fill:{ color:"34C749" } });
  slide.addText(`📷  ${label}`, {
    x:x+0.1, y:y+0.3, w:w-0.2, h:h-0.5,
    fontSize:13, color: C.blue, align:"center", valign:"middle",
    italic:true, fontFace:"Calibri",
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// 開始建立簡報
// ═══════════════════════════════════════════════════════════════════════════════
const pres = new PptxGenJS();
pres.layout  = "LAYOUT_16x9";
pres.author  = "維春集團 Portal";
pres.title   = "工項工時 Dashboard — Ragic 欄位對應說明";
pres.subject = "Dashboard KPI 計算邏輯與資料來源說明";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 1 — 封面
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  s.background = { color: C.darkBg };

  // 右側金色裝飾矩形
  s.addShape(pres.shapes.RECTANGLE, { x:7.5, y:0, w:2.5, h:5.625, fill:{ color:C.navy } });
  s.addShape(pres.shapes.RECTANGLE, { x:9.6, y:0, w:0.4, h:5.625, fill:{ color:C.gold } });

  // 主標題
  s.addText("工項工時 Dashboard", {
    x:0.6, y:1.3, w:7.0, h:0.9,
    fontSize:38, bold:true, color:C.white, fontFace:"Calibri",
    align:"left",
  });
  // 副標題
  s.addText("Ragic 欄位對應與 KPI 計算說明", {
    x:0.6, y:2.25, w:7.0, h:0.5,
    fontSize:18, color:C.blue, fontFace:"Calibri", align:"left",
  });
  // 分隔線
  s.addShape(pres.shapes.RECTANGLE, { x:0.6, y:2.8, w:4.0, h:0.05, fill:{ color:C.gold } });
  // 說明文字
  s.addText([
    { text:"簡報用途：", options:{ bold:true, breakLine:false } },
    { text:"說明工項工時 Dashboard 各項數字的計算來源，", options:{ breakLine:true } },
    { text:"以利主管確認數據正確性並進行決策討論。", options:{ breakLine:false } },
  ], {
    x:0.6, y:3.0, w:6.8, h:0.9,
    fontSize:13, color:C.muted, fontFace:"Calibri", align:"left",
  });
  // 日期與版本
  s.addText("2026-04-23  ｜  v1.38.3  ｜  維春集團管理 Portal", {
    x:0.6, y:4.9, w:8.0, h:0.4,
    fontSize:10, color:C.gray, fontFace:"Calibri",
  });
  // 右側文字
  s.addText([
    { text:"維春集團", options:{ bold:true, breakLine:true } },
    { text:"管理 Portal", options:{ breakLine:false } },
  ], {
    x:7.6, y:2.3, w:2.2, h:1.0,
    fontSize:14, color:C.white, fontFace:"Calibri", align:"center", valign:"middle",
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 2 — 目錄
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  s.background = { color: C.lightBg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.22, h:5.625, fill:{ color: C.navy } });
  s.addText("簡報目錄", {
    x:0.4, y:0.22, w:9.3, h:0.55,
    fontSize:24, bold:true, color:C.navy, fontFace:"Calibri", align:"left", margin:0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:0.82, w:9.2, h:0.04, fill:{ color: C.blue } });

  const items = [
    ["01", "系統資料來源總覽",      "三個 Ragic 資料庫的整合架構"],
    ["02", "樂群工務報修 欄位對應",  "Ragic 欄位 → Dashboard 數字"],
    ["03", "大直工務部 欄位對應",    "Ragic 欄位 → Dashboard 數字"],
    ["04", "房務保養 欄位對應",      "Ragic 欄位 → Dashboard 數字"],
    ["05", "工時計算邏輯",          "花費工時 → 工務處理天數 優先順序"],
    ["06", "人員統計邏輯",          "處理工務 欄位說明"],
    ["07", "Dashboard KPI 計算",   "6 大指標公式與來源"],
    ["08", "五大工項類別分類",       "關鍵字自動歸類規則"],
    ["09", "Dashboard 功能截圖",    "★工項類別分析 / 高階主管 Dashboard"],
  ];

  items.forEach(([no, title, desc], i) => {
    const row = Math.floor(i / 3);
    const col = i % 3;
    const x = 0.4 + col * 3.2;
    const y = 1.05 + row * 1.45;
    const w = 3.0;
    const h = 1.25;

    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w, h, fill:{ color: C.white }, shadow: mkShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w:0.12, h, fill:{ color: C.blue } });
    s.addText(no, {
      x:x+0.18, y:y+0.08, w:0.5, h:0.32,
      fontSize:14, bold:true, color:C.gold, fontFace:"Calibri", margin:0,
    });
    s.addText(title, {
      x:x+0.18, y:y+0.38, w:w-0.3, h:0.38,
      fontSize:11, bold:true, color:C.navy, fontFace:"Calibri", margin:0,
    });
    s.addText(desc, {
      x:x+0.18, y:y+0.75, w:w-0.3, h:0.4,
      fontSize:9, color:C.gray, fontFace:"Calibri", margin:0,
    });
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 3 — 系統資料來源總覽
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "01  系統資料來源總覽", pres);
  s.addText("三個 Ragic 系統整合進入同一 Dashboard，統一計算工時與人員指標", {
    x:0.4, y:0.92, w:9.2, h:0.3,
    fontSize:11, color:C.gray, fontFace:"Calibri",
  });

  // 三個來源卡片
  const srcs = [
    { title:"樂群工務報修", en:"Luqun Repair", color:C.navy,   ragic:"ap12.ragic.com\nsoutlet001 / Sheet 6", records:"工務報修案件", icon:"🔧" },
    { title:"大直工務部",   en:"Dazhi Repair", color:C.teal,   ragic:"ap12.ragic.com\nsoutlet001 / Sheet 8", records:"工務報修案件", icon:"🛠" },
    { title:"房務保養",     en:"Room Maint.",  color:C.purple, ragic:"ap12.ragic.com\nsoutlet001 / report2", records:"客房保養記錄", icon:"🏨" },
  ];

  srcs.forEach(({ title, en, color, ragic, records, icon }, i) => {
    const x = 0.4 + i * 3.1;
    const y = 1.35;
    const w = 2.9;
    const h = 2.5;

    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill:{ color: C.white }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h:0.14, fill:{ color } });

    s.addText(icon, { x:x+0.1, y:y+0.22, w:0.6, h:0.6, fontSize:28, align:"center" });
    s.addText(title, {
      x:x+0.1, y:y+0.22, w:w-0.2, h:0.4,
      fontSize:14, bold:true, color, fontFace:"Calibri", align:"center", margin:0,
    });
    s.addText(en, {
      x:x+0.1, y:y+0.62, w:w-0.2, h:0.25,
      fontSize:9, color:C.gray, fontFace:"Calibri", align:"center",
    });
    s.addShape(pres.shapes.RECTANGLE, { x:x+0.15, y:y+0.92, w:w-0.3, h:0.01, fill:{ color: C.lightGray } });
    s.addText("Ragic 路徑：", {
      x:x+0.15, y:y+1.0, w:w-0.3, h:0.22,
      fontSize:8, bold:true, color:C.gray, fontFace:"Calibri",
    });
    s.addText(ragic, {
      x:x+0.15, y:y+1.2, w:w-0.3, h:0.4,
      fontSize:8, color:C.muted, fontFace:"Calibri",
    });
    s.addText(`📋  ${records}`, {
      x:x+0.15, y:y+1.7, w:w-0.3, h:0.3,
      fontSize:9, color, fontFace:"Calibri", bold:true,
    });
    s.addShape(pres.shapes.RECTANGLE, { x:x+0.15, y:y+2.05, w:w-0.3, h:0.32, fill:{ color }, });
    s.addText("同步 → SQLite → API", {
      x:x+0.15, y:y+2.05, w:w-0.3, h:0.32,
      fontSize:9, color:C.white, fontFace:"Calibri", align:"center", valign:"middle",
    });
  });

  // 箭頭 + Dashboard 方塊
  s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:4.05, w:9.2, h:0.04, fill:{ color: C.lightGray } });
  s.addText("▼  統一整合進入 Portal Dashboard", {
    x:2.5, y:4.12, w:5, h:0.3,
    fontSize:10, color:C.gray, align:"center", italic:true, fontFace:"Calibri",
  });

  s.addShape(pres.shapes.RECTANGLE, { x:3.0, y:4.5, w:4.0, h:0.75, fill:{ color: C.navy }, shadow: mkShadow() });
  s.addText("★ 工項工時 Dashboard  ／  高階主管 Dashboard", {
    x:3.0, y:4.5, w:4.0, h:0.75,
    fontSize:12, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri",
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 4 — 樂群工務報修 欄位對應
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "02  樂群工務報修 — Ragic 欄位對應", pres);
  s.addText("Ragic：ap12.ragic.com / soutlet001 / luqun-public-works-repair-reporting-system", {
    x:0.4, y:0.9, w:9.2, h:0.25, fontSize:10, color:C.gray, fontFace:"Calibri",
  });

  // 截圖區 (左)
  addScreenshotPlaceholder(s, pres, 0.4, 1.22, 3.8, 3.8, "樂群 Ragic 表單截圖\n（請貼上實際截圖）");

  // 欄位對應表（右）
  const tableData = [
    [
      { text:"Dashboard 指標", options:{ bold:true, color:C.white, fill:{ color: C.navy }, align:"center" } },
      { text:"Ragic 欄位名稱", options:{ bold:true, color:C.white, fill:{ color: C.navy }, align:"center" } },
      { text:"說明", options:{ bold:true, color:C.white, fill:{ color: C.navy }, align:"center" } },
    ],
    ["⏱ 工時（主）",  "花費工時",      "單位：小時（HR），直接使用"],
    ["⏱ 工時（備）",  "工務處理天數",  "單位：天，× 24 = 小時（主欄位無值時使用）"],
    ["👤 人員",       "處理工務",      "執行維修的工務人員姓名"],
    ["📅 日期",       "發生時間",      "格式：YYYY/MM/DD HH:MM"],
    ["🔖 工項類別",   "標題 + 報修類型","關鍵字自動分類（詳見 Slide 08）"],
    ["📋 案件編號",   "報修編號",      "唯一識別碼，用於計算案件總數"],
    ["🏷 報修類型",   "報修類型",      "建築 / 衛廁 / 空調 / 消防…"],
    ["📌 樓層",       "發生樓層",      "2F / B1F / 10F…"],
    ["✅ 完成狀態",   "問題狀態",      "結案 / 已辦驗 / 已驗收 = 完成"],
  ];

  const rowFills = [null,"F8FAFC",C.white,"F8FAFC","FFF7ED","F8FAFC",C.white,"F8FAFC",C.white];

  s.addTable(tableData, {
    x:4.35, y:1.2, w:5.3, h:3.85,
    border:{ pt:0.5, color: C.lightGray },
    rowH:0.37,
    colW:[1.5, 1.6, 2.2],
    fontFace:"Calibri",
    fontSize:9.5,
    color:C.navy,
  });

  // 底部注意事項
  s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:5.1, w:9.2, h:0.38, fill:{ color:"FFF7ED" }, line:{ color:"F59E0B", width:0.8 } });
  s.addText("⚠️  注意：「報修同仁」（報修人）不作為人員統計用途，僅供記錄參考", {
    x:0.5, y:5.12, w:9.0, h:0.32,
    fontSize:10, color:"B45309", bold:true, fontFace:"Calibri",
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 5 — 大直工務部 欄位對應
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "03  大直工務部 — Ragic 欄位對應", pres);
  s.addText("Ragic：ap12.ragic.com / soutlet001 / lequn-public-works  (PAGEID: fV8)", {
    x:0.4, y:0.9, w:9.2, h:0.25, fontSize:10, color:C.gray, fontFace:"Calibri",
  });

  addScreenshotPlaceholder(s, pres, 0.4, 1.22, 3.8, 3.8, "大直 Ragic 表單截圖\n（請貼上實際截圖）");

  const tableData = [
    [
      { text:"Dashboard 指標", options:{ bold:true, color:C.white, fill:{ color: C.teal }, align:"center" } },
      { text:"Ragic 欄位名稱", options:{ bold:true, color:C.white, fill:{ color: C.teal }, align:"center" } },
      { text:"說明", options:{ bold:true, color:C.white, fill:{ color: C.teal }, align:"center" } },
    ],
    ["⏱ 工時（主）",  "花費工時",      "單位：小時（HR）"],
    ["⏱ 工時（備①）","工務處理天數",  "天 × 24 → 小時"],
    ["⏱ 工時（備②）","維修天數",      "天 × 24 → 小時（最後 fallback）"],
    ["👤 人員",       "處理工務",      "執行維修的工務人員"],
    ["📅 日期",       "報修日期",      "格式：YYYY/MM/DD"],
    ["🔖 工項類別",   "標題 + 類型",   "關鍵字自動分類"],
    ["📋 案件編號",   "報修單編號",    "唯一識別碼"],
    ["✅ 完成狀態",   "處理狀態",      "結案 / 已辦驗 / 已驗收 = 完成"],
  ];

  s.addTable(tableData, {
    x:4.35, y:1.2, w:5.3, h:3.85,
    border:{ pt:0.5, color: C.lightGray },
    rowH:0.41,
    colW:[1.5, 1.6, 2.2],
    fontFace:"Calibri", fontSize:9.5, color:C.navy,
  });

  // 差異說明
  s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:5.1, w:9.2, h:0.38, fill:{ color:"ECFDF5" }, line:{ color: C.green, width:0.8 } });
  s.addText("✔  大直特別說明：工時欄位有三層 fallback，確保每筆記錄都能取到有效工時數值", {
    x:0.5, y:5.12, w:9.0, h:0.32,
    fontSize:10, color:"15803D", bold:true, fontFace:"Calibri",
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 6 — 房務保養 欄位對應
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "04  房務保養 — Ragic 欄位對應", pres);
  s.addText("Ragic：ap12.ragic.com / soutlet001 / report2  ｜  資料表：room_maintenance_detail_records", {
    x:0.4, y:0.9, w:9.2, h:0.25, fontSize:10, color:C.gray, fontFace:"Calibri",
  });

  addScreenshotPlaceholder(s, pres, 0.4, 1.22, 3.8, 3.0, "房務保養 Ragic 表單截圖\n（請貼上實際截圖）");

  const tableData = [
    [
      { text:"Dashboard 指標", options:{ bold:true, color:C.white, fill:{ color: C.purple }, align:"center" } },
      { text:"Ragic 欄位名稱", options:{ bold:true, color:C.white, fill:{ color: C.purple }, align:"center" } },
      { text:"說明", options:{ bold:true, color:C.white, fill:{ color: C.purple }, align:"center" } },
    ],
    ["⏱ 工時",      "工時計算",    "格式：'22.00  分鐘'，÷ 60 → 小時"],
    ["👤 人員",      "保養人員",    "執行保養的房務人員"],
    ["📅 日期",      "保養日期",    "格式：YYYY/MM/DD"],
    ["🔖 工項類別",  "固定值",      "所有房務保養 = 每日巡檢"],
    ["📋 案件識別",  "ragic_id",   "Ragic 記錄 ID，唯一識別碼"],
    ["🏠 房號",      "房號",        "客房房號（501、602 等）"],
  ];

  s.addTable(tableData, {
    x:4.35, y:1.2, w:5.3, h:3.0,
    border:{ pt:0.5, color: C.lightGray },
    rowH:0.41,
    colW:[1.5, 1.6, 2.2],
    fontFace:"Calibri", fontSize:9.5, color:C.navy,
  });

  // 重要說明框
  s.addShape(pres.shapes.RECTANGLE, { x:4.35, y:4.32, w:5.3, h:0.75, fill:{ color:"F5F0FF" }, line:{ color: C.purple, width:0.8 } });
  s.addText([
    { text:"單位換算說明：", options:{ bold:true, breakLine:true } },
    { text:"Ragic 房務保養「工時計算」欄位儲存「分鐘」（例：22.00 分鐘）", options:{ breakLine:true } },
    { text:"→ 程式自動 ÷60 轉換為「小時」，再與樂群/大直工務工時統一加總", options:{} },
  ], {
    x:4.45, y:4.38, w:5.1, h:0.6,
    fontSize:9, color:"6D28D9", fontFace:"Calibri",
  });

  // 底部提示
  s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:5.1, w:9.2, h:0.38, fill:{ color:"E8F0F8" }, line:{ color: C.blue, width:0.8 } });
  s.addText("ℹ️  房務保養工項類別固定為「每日巡檢」，不進行關鍵字分類", {
    x:0.5, y:5.12, w:9.0, h:0.32,
    fontSize:10, color:C.navy, bold:true, fontFace:"Calibri",
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 7 — 工時計算邏輯
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "05  工時計算邏輯 — 優先順序", pres);
  s.addText("樂群 & 大直工務報修：同一套優先順序邏輯，確保每筆記錄都能取到有效工時", {
    x:0.4, y:0.9, w:9.2, h:0.28, fontSize:11, color:C.gray, fontFace:"Calibri",
  });

  // 流程圖區
  const steps = [
    { no:"①", field:"花費工時", unit:"小時（HR）", desc:"Ragic 欄位直接記載小時數\n→ 若此欄有值（> 0），直接使用", color:C.green, bg:"ECFDF5" },
    { no:"②", field:"工務處理天數", unit:"天 × 24 = 小時", desc:"Ragic 欄位記載天數\n→ 花費工時為空時使用，程式自動換算", color:"B45309", bg:"FFF7ED" },
    { no:"③", field:"維修天數（僅大直）", unit:"天 × 24 = 小時", desc:"大直系統專屬備用欄位\n→ 前兩者皆空時使用", color:C.gray, bg:"F8FAFC" },
  ];

  steps.forEach(({ no, field, unit, desc, color, bg }, i) => {
    const y = 1.3 + i * 1.25;
    // 連接線（非第一個）
    if (i > 0) {
      s.addShape(pres.shapes.RECTANGLE, { x:1.5, y:y-0.28, w:0.04, h:0.28, fill:{ color: C.lightGray } });
      s.addText("若上方欄位無值 ▼", {
        x:1.6, y:y-0.26, w:2.5, h:0.22,
        fontSize:8.5, color:C.muted, italic:true, fontFace:"Calibri",
      });
    }
    s.addShape(pres.shapes.RECTANGLE, { x:0.5, y, w:9.0, h:1.0, fill:{ color: bg }, line:{ color, width:1.0 }, shadow: mkShadowLight() });
    s.addShape(pres.shapes.RECTANGLE, { x:0.5, y, w:0.55, h:1.0, fill:{ color } });
    s.addText(no, {
      x:0.5, y, w:0.55, h:1.0,
      fontSize:20, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri",
    });
    s.addText(field, {
      x:1.15, y:y+0.08, w:2.5, h:0.38,
      fontSize:14, bold:true, color, fontFace:"Calibri", margin:0,
    });
    s.addText(`單位：${unit}`, {
      x:1.15, y:y+0.48, w:2.8, h:0.28,
      fontSize:9.5, color:C.gray, fontFace:"Calibri", italic:true,
    });
    s.addShape(pres.shapes.RECTANGLE, { x:4.0, y:y+0.1, w:0.03, h:0.8, fill:{ color: C.lightGray } });
    s.addText(desc, {
      x:4.1, y:y+0.12, w:5.2, h:0.8,
      fontSize:10, color:C.navy, fontFace:"Calibri", valign:"middle",
    });
  });

  // 公式說明框
  s.addShape(pres.shapes.RECTANGLE, { x:0.5, y:5.05, w:9.0, h:0.42, fill:{ color: C.navy }, shadow: mkShadow() });
  s.addText("📐  計算結果統一存入 work_hours 欄位（單位：小時），供所有 Dashboard KPI 計算使用", {
    x:0.5, y:5.05, w:9.0, h:0.42,
    fontSize:11, bold:true, color:C.white, fontFace:"Calibri", align:"center", valign:"middle",
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 8 — 人員統計邏輯
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "06  人員統計邏輯", pres);
  s.addText("所有人員相關指標（排名、占比、平均工時）都以「處理工務」欄位為唯一來源", {
    x:0.4, y:0.9, w:9.2, h:0.28, fontSize:11, color:C.gray, fontFace:"Calibri",
  });

  // 欄位說明 2欄
  const cols = [
    {
      title:"✅ 正確來源（唯一標準）",
      bg:"ECFDF5", border:C.green, titleColor:C.green,
      items:[
        ["樂群 / 大直", "「處理工務」欄位", "實際執行維修的工務人員"],
        ["房務保養",    "「保養人員」欄位", "執行客房保養的房務人員"],
      ]
    },
    {
      title:"❌ 已排除的欄位",
      bg:"FFF1F0", border:C.red, titleColor:C.red,
      items:[
        ["樂群 / 大直", "「報修同仁」", "填報需求的人，非執行人"],
        ["大直",        "「反應單位」", "部門/單位名稱，非個人"],
        ["任何系統",    "其他衍生欄位", "不得混用做人員統計"],
      ]
    },
  ];

  cols.forEach(({ title, bg, border, titleColor, items }, ci) => {
    const x = 0.4 + ci * 4.8;
    const w = 4.5;
    s.addShape(pres.shapes.RECTANGLE, { x, y:1.3, w, h:3.0, fill:{ color: bg }, line:{ color: border, width:1.2 }, shadow: mkShadow() });
    s.addText(title, {
      x:x+0.15, y:1.38, w:w-0.3, h:0.35,
      fontSize:12, bold:true, color: titleColor, fontFace:"Calibri", margin:0,
    });
    s.addShape(pres.shapes.RECTANGLE, { x:x+0.15, y:1.75, w:w-0.3, h:0.03, fill:{ color: border } });
    items.forEach(([src, field, desc], ri) => {
      const ry = 1.85 + ri * 0.68;
      s.addText(`[${src}]`, {
        x:x+0.15, y:ry, w:1.3, h:0.26,
        fontSize:9, bold:true, color: titleColor, fontFace:"Calibri", margin:0,
      });
      s.addText(field, {
        x:x+1.5, y:ry, w:w-1.65, h:0.26,
        fontSize:10, bold:true, color:C.navy, fontFace:"Calibri", margin:0,
      });
      s.addText(desc, {
        x:x+1.5, y:ry+0.28, w:w-1.65, h:0.28,
        fontSize:8.5, color:C.gray, fontFace:"Calibri", margin:0,
      });
    });
  });

  // 計算公式
  s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:4.42, w:9.2, h:0.88, fill:{ color: C.white }, shadow: mkShadow(), line:{ color: C.blue, width:0.8 } });
  s.addText("人員統計計算邏輯", {
    x:0.6, y:4.5, w:8.8, h:0.26,
    fontSize:11, bold:true, color:C.navy, fontFace:"Calibri", margin:0,
  });
  s.addText([
    { text:"• 人員去重：", options:{ bold:true } },
    { text:"distinct(處理工務)，「未指定」不計入排名   ", options:{} },
    { text:"• 人員排名：", options:{ bold:true } },
    { text:"group by 處理工務 → sum(工時) → 降冪排列", options:{} },
  ], {
    x:0.6, y:4.78, w:8.8, h:0.42,
    fontSize:10, color:C.navy, fontFace:"Calibri",
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 9 — Dashboard KPI 計算說明
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "07  Dashboard KPI 計算說明", pres);
  s.addText("以下為「高階主管 Dashboard」第一層 Hero KPI 的計算公式", {
    x:0.4, y:0.9, w:9.2, h:0.28, fontSize:11, color:C.gray, fontFace:"Calibri",
  });

  const kpis = [
    { no:"KPI 1", title:"本期總工時", color:C.navy, formula:"SUM(work_hours)，所有篩選條件內記錄的工時加總", src:"花費工時 / 工務處理天數×24", unit:"HR（小時）" },
    { no:"KPI 2", title:"案件/工項數", color:C.teal, formula:"COUNT(distinct ragic_id)，篩選條件內的唯一案件數", src:"ragic_id（唯一識別碼）", unit:"筆" },
    { no:"KPI 3", title:"平均人工時",  color:C.green, formula:"總工時 ÷ COUNT(distinct 處理工務)", src:"花費工時 + 處理工務", unit:"HR/人" },
    { no:"KPI 4", title:"工時最高類別",color:"B45309", formula:"GROUP BY 工項類別 → SUM(工時) → MAX", src:"標題/報修類型（關鍵字分類）", unit:"類別名稱 + 占比%" },
    { no:"KPI 5", title:"工時最高人員",color:C.purple, formula:"GROUP BY 處理工務 → SUM(工時) → MAX", src:"處理工務", unit:"姓名 + 占比%" },
    { no:"KPI 6", title:"環比變化",    color:C.red, formula:"(本期工時 - 上期工時) ÷ 上期工時 × 100%", src:"與上月 or 去年同期比較", unit:"%" },
  ];

  kpis.forEach(({ no, title, color, formula, src, unit }, i) => {
    const row = Math.floor(i / 3);
    const col = i % 3;
    const x = 0.4 + col * 3.2;
    const y = 1.28 + row * 2.1;
    const w = 3.0;
    const h = 1.95;

    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill:{ color:C.white }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h:0.12, fill:{ color } });
    s.addShape(pres.shapes.RECTANGLE, { x, y:y+0.12, w:0.08, h:h-0.12, fill:{ color } });

    s.addText(no, {
      x:x+0.15, y:y+0.15, w:1.0, h:0.22,
      fontSize:8.5, bold:true, color, fontFace:"Calibri", margin:0,
    });
    s.addText(title, {
      x:x+0.15, y:y+0.36, w:w-0.25, h:0.3,
      fontSize:12, bold:true, color:C.navy, fontFace:"Calibri", margin:0,
    });
    s.addShape(pres.shapes.RECTANGLE, { x:x+0.15, y:y+0.68, w:w-0.25, h:0.02, fill:{ color: C.lightGray } });
    s.addText([
      { text:"公式：", options:{ bold:true, color:C.navy } },
      { text:formula, options:{ color:C.gray } },
    ], {
      x:x+0.15, y:y+0.73, w:w-0.25, h:0.55,
      fontSize:8.5, fontFace:"Calibri",
    });
    s.addText([
      { text:"來源欄位：", options:{ bold:true, color } },
      { text:src, options:{ color:C.gray } },
    ], {
      x:x+0.15, y:y+1.33, w:w-0.25, h:0.3,
      fontSize:8, fontFace:"Calibri",
    });
    s.addShape(pres.shapes.RECTANGLE, { x:x+w-0.72, y:y+h-0.35, w:0.62, h:0.28, fill:{ color } });
    s.addText(unit, {
      x:x+w-0.72, y:y+h-0.35, w:0.62, h:0.28,
      fontSize:8, color:C.white, bold:true, align:"center", valign:"middle", fontFace:"Calibri",
    });
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 10 — 五大工項類別分類邏輯
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "08  五大工項類別分類邏輯", pres);
  s.addText("程式依據案件「標題 + 報修類型」欄位關鍵字自動歸類，優先順序由上至下", {
    x:0.4, y:0.9, w:9.2, h:0.28, fontSize:11, color:C.gray, fontFace:"Calibri",
  });

  const cats = [
    { name:"緊急事件", priority:"① 最優先", color:C.red,    bg:"FFF1F0", keywords:"緊急、急修、突發、火警、停電", example:"緊急漏電、突發管線爆裂" },
    { name:"每日巡檢", priority:"②",        color:C.purple, bg:"F5F0FF", keywords:"巡檢、巡視、例巡、日巡", example:"每日例行巡檢、巡視設備" },
    { name:"例行維護", priority:"③",        color:"B45309", bg:"FFF7ED", keywords:"例行、定期、保養、維護、月保、季保", example:"定期設備保養、例行維護作業" },
    { name:"上級交辦", priority:"④",        color:C.teal,   bg:"ECFDF5", keywords:"交辦、上級、主管指示、指派、院長", example:"主管交辦工程、院長指示修繕" },
    { name:"現場報修", priority:"⑤ 預設",   color:C.blue,   bg:"E8F0F8", keywords:"（以上皆不符合時，歸入此類）", example:"一般工務報修案件（多數資料）" },
  ];

  cats.forEach(({ name, priority, color, bg, keywords, example }, i) => {
    const y = 1.28 + i * 0.83;
    s.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:9.2, h:0.75, fill:{ color: bg }, line:{ color, width:0.8 } });
    s.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:1.1, h:0.75, fill:{ color } });
    s.addText([
      { text:priority+"\n", options:{ fontSize:8, breakLine:true } },
      { text:name, options:{ fontSize:13, bold:true } },
    ], {
      x:0.4, y, w:1.1, h:0.75,
      color:C.white, fontFace:"Calibri", align:"center", valign:"middle",
    });
    s.addText("關鍵字：", {
      x:1.6, y:y+0.06, w:1.2, h:0.28,
      fontSize:9.5, bold:true, color:C.navy, fontFace:"Calibri", margin:0,
    });
    s.addText(keywords, {
      x:2.75, y:y+0.06, w:6.6, h:0.28,
      fontSize:9.5, color, bold:true, fontFace:"Calibri", margin:0,
    });
    s.addText("例：", {
      x:1.6, y:y+0.4, w:0.6, h:0.26,
      fontSize:8.5, bold:true, color:C.gray, fontFace:"Calibri", margin:0,
    });
    s.addText(example, {
      x:2.2, y:y+0.4, w:7.2, h:0.26,
      fontSize:8.5, color:C.gray, italic:true, fontFace:"Calibri", margin:0,
    });
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 11 — ★工項類別分析 Dashboard 功能說明
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "09-A  ★工項類別分析 Dashboard", pres);
  s.addText("路由：/work-category-analysis  ｜  位置：左側選單 → 樂群工務報修 / 大直工務部", {
    x:0.4, y:0.9, w:9.2, h:0.28, fontSize:10, color:C.gray, fontFace:"Calibri",
  });

  // 左欄：功能說明
  const features = [
    ["📊 Dashboard Tab",  "5 類別趨勢折線圖（全年月趨勢 / 單月日趨勢）"],
    ["📅 每日累計表（B）","1~31 日 × 5 類別 + 星期 + TOTAL + % "],
    ["📆 每月累計表（C）","1~12 月 × 5 類別 + TOTAL + % "],
    ["🧑‍💼 人員工時%（D）","各工項類別下各人員工時佔比（%）"],
    ["🔍 五維篩選",       "年度 / 月份 / 來源 / 類別 / 人員"],
  ];

  features.forEach(([title, desc], i) => {
    const y = 1.28 + i * 0.73;
    s.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:4.5, h:0.63, fill:{ color: C.white }, shadow: mkShadowLight() });
    s.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:0.08, h:0.63, fill:{ color: C.blue } });
    s.addText(title, { x:0.58, y:y+0.05, w:4.2, h:0.26, fontSize:10.5, bold:true, color:C.navy, fontFace:"Calibri", margin:0 });
    s.addText(desc, { x:0.58, y:y+0.32, w:4.2, h:0.26, fontSize:9, color:C.gray, fontFace:"Calibri", margin:0 });
  });

  // 右欄：截圖預留
  addScreenshotPlaceholder(s, pres, 5.1, 1.22, 4.5, 4.0, "★工項類別分析 Dashboard 截圖\n（請貼上實際截圖）");
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 12 — 高階主管 Dashboard 功能說明
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "09-B  高階主管 Dashboard", pres);
  s.addText("路由：/exec-dashboard  ｜  位置：左側選單 → 樂群工務報修 / 大直工務部", {
    x:0.4, y:0.9, w:9.2, h:0.28, fontSize:10, color:C.gray, fontFace:"Calibri",
  });

  const layers = [
    {
      no:"第一層", title:"Hero KPI 區", color: C.navy, bg:"E8F0F8",
      items:["本期總工時（超大數字）","人均工時","最高工時類別","最高工時人員","最高工時來源","環比變化 ↑↓"],
    },
    {
      no:"第二層", title:"決策圖表區", color: C.teal, bg:"ECFDF5",
      items:["工項類別趨勢（折線圖）","類別占比（Donut）","人員排名（橫柱圖）","類別×人員（Stacked Bar）","來源別分析","人力集中度"],
    },
    {
      no:"第三層", title:"明細分析表格", color: C.purple, bg:"F5F0FF",
      items:["每日累計工時表","每月累計工時表","人員工時佔比表","人員排名詳細表（可排序）"],
    },
  ];

  layers.forEach(({ no, title, color, bg, items }, i) => {
    const x = 0.4 + i * 3.15;
    const y = 1.28;
    const w = 2.95;
    const h = 4.1;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill:{ color: bg }, line:{ color, width:1.0 }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h:0.42, fill:{ color } });
    s.addText([
      { text:no+"  ", options:{ fontSize:9 } },
      { text:title, options:{ fontSize:12, bold:true } },
    ], {
      x:x+0.1, y, w:w-0.2, h:0.42,
      color:C.white, fontFace:"Calibri", align:"center", valign:"middle",
    });
    items.forEach((item, ri) => {
      s.addText("▸  " + item, {
        x:x+0.18, y:y+0.52+ri*0.56, w:w-0.28, h:0.46,
        fontSize:9.5, color:C.navy, fontFace:"Calibri",
        bullet:false,
      });
      if (ri < items.length-1) {
        s.addShape(pres.shapes.RECTANGLE, { x:x+0.18, y:y+0.97+ri*0.56, w:w-0.28, h:0.02, fill:{ color: C.lightGray } });
      }
    });
  });

  // 決策提示說明
  s.addShape(pres.shapes.RECTANGLE, { x:0.4, y:5.1, w:9.2, h:0.38, fill:{ color:"FFF7ED" }, line:{ color: C.gold, width:0.8 } });
  s.addText("💡  自動決策提示：集中度 > 70% 🔴 / 現場報修 > 40% 🟡 / 環比 ±25% 🟡 / 分布正常 🟢", {
    x:0.5, y:5.12, w:9.0, h:0.32,
    fontSize:10, color:"92400E", bold:true, fontFace:"Calibri",
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 13 — 數據驗證清單
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  addSectionHeader(s, "10  數據驗證方式", pres);
  s.addText("如何確認 Dashboard 數字與 Ragic 原始資料一致", {
    x:0.4, y:0.9, w:9.2, h:0.28, fontSize:11, color:C.gray, fontFace:"Calibri",
  });

  const checks = [
    { step:"01", title:"觸發 Ragic → DB 同步",   color:C.blue,
      detail:"POST /api/v1/luqun-repair/sync\nPOST /api/v1/dazhi-repair/sync",
      tip:"同步完成後，DB 才會反映 Ragic 最新資料" },
    { step:"02", title:"確認人員清單（處理工務）",  color:C.teal,
      detail:"GET /api/v1/work-category-analysis/persons?year=2026",
      tip:"回傳值應為「處理工務」欄位的人員姓名，而非報修人" },
    { step:"03", title:"對帳特定案件工時",          color:C.purple,
      detail:"GET /api/v1/luqun-repair/raw-fields\n→ 確認 fields 清單含「花費工時」",
      tip:"比對 Ragic 單筆記錄的花費工時 與 API 統計值" },
    { step:"04", title:"查詢 Dashboard 主統計",    color:C.navy,
      detail:"GET /api/v1/work-category-analysis/stats?year=2026&month=4",
      tip:"kpi.total_hours = Σ(花費工時)，kpi.top_person = 處理工務工時最高者" },
    { step:"05", title:"期望值驗算範例",            color:C.green,
      detail:"圖中案件：花費工時=159.67 HR，工務處理天數=6.65 天\n→ 159.67÷24=6.65（換算一致）",
      tip:"API 應統計 159.67 HR（優先使用花費工時）" },
  ];

  checks.forEach(({ step, title, color, detail, tip }, i) => {
    const y = 1.28 + i * 0.79;
    s.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:9.2, h:0.72, fill:{ color: C.white }, shadow: mkShadowLight() });
    s.addShape(pres.shapes.RECTANGLE, { x:0.4, y, w:0.7, h:0.72, fill:{ color } });
    s.addText(step, {
      x:0.4, y, w:0.7, h:0.72,
      fontSize:16, bold:true, color:C.white, align:"center", valign:"middle", fontFace:"Calibri",
    });
    s.addText(title, {
      x:1.2, y:y+0.05, w:8.2, h:0.26,
      fontSize:11, bold:true, color:C.navy, fontFace:"Calibri", margin:0,
    });
    s.addText(detail, {
      x:1.2, y:y+0.32, w:5.5, h:0.34,
      fontSize:8.5, color, fontFace:"Consolas",
    });
    s.addShape(pres.shapes.RECTANGLE, { x:6.8, y:y+0.08, w:2.7, h:0.58, fill:{ color:"F8FAFC" }, line:{ color: C.lightGray, width:0.5 } });
    s.addText("💡 " + tip, {
      x:6.85, y:y+0.1, w:2.6, h:0.52,
      fontSize:8, color:C.gray, fontFace:"Calibri",
    });
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Slide 14 — 結尾
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  const s = pres.addSlide();
  s.background = { color: C.darkBg };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.4, h:5.625, fill:{ color: C.gold } });
  s.addShape(pres.shapes.RECTANGLE, { x:9.6, y:0, w:0.4, h:5.625, fill:{ color: C.navy } });

  s.addText("資料欄位對應摘要", {
    x:0.7, y:1.0, w:8.6, h:0.65,
    fontSize:28, bold:true, color:C.white, fontFace:"Calibri", align:"center",
  });

  const summary = [
    ["人員欄位",  "處理工務",                          "樂群 / 大直共用"],
    ["工時欄位",  "花費工時（HR）→ 工務處理天數×24", "優先順序"],
    ["工項類別",  "標題 + 報修類型 → 關鍵字分類",     "5 大類別"],
    ["房務保養",  "保養人員 / 工時計算÷60",            "固定歸入每日巡檢"],
  ];

  s.addTable(
    [
      summary.map(r => ({ text: r[0], options:{ bold:true, color:C.white, fill:{ color: C.navy }, align:"center" } })),
      summary.map(r => ({ text: r[1], options:{ bold:true, color:C.gold,  fill:{ color:"1E293B" } } })),
      summary.map(r => ({ text: r[2], options:{ color:C.muted, fill:{ color:"1E293B" } } })),
    ],
    { x:0.7, y:1.85, w:8.6, h:1.6, border:{ pt:0.5, color:"334155" }, fontFace:"Calibri", fontSize:10, rowH:0.5 }
  );

  s.addText("Dashboard 數據如有疑問，請以 Ragic 明細表「花費工時」欄位進行對帳", {
    x:0.7, y:3.65, w:8.6, h:0.4,
    fontSize:13, color:C.muted, fontFace:"Calibri", align:"center", italic:true,
  });
  s.addText("維春集團管理 Portal  ｜  2026-04-23", {
    x:0.7, y:4.9, w:8.6, h:0.35,
    fontSize:10, color:C.gray, fontFace:"Calibri", align:"center",
  });
}

// ── 輸出 ──────────────────────────────────────────────────────────────────────
pres.writeFile({ fileName: "/sessions/brave-eloquent-franklin/mnt/outputs/Dashboard_Ragic欄位對應說明.pptx" })
  .then(() => console.log("✅  簡報已產生：Dashboard_Ragic欄位對應說明.pptx"))
  .catch(err => { console.error("❌  產生失敗：", err); process.exit(1); });
