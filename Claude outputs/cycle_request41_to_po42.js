/**
 * cycle_request41_to_po42.js  v1.5  (2026-11-20)
 *
 * Ragic 伺服器端 JavaScript Workflow ——日曜「★週期請購單」(freed-management-division/41) 的「拋轉採購單」按鈕
 * 把一張週期請購單拋轉成「★週採採購單」(freed-management-division/42)：
 *
 *   ① 同一廠商合併成同一張採購單（依子表「擬定廠商」分組；一家廠商一張 42）
 *   ② 每張採購單內，相同部門排在一起，部門最後插一列「XX部 小計」
 *   ③ 數量／單價／廠商一律讀 41 目前內容（含採購在 Ragic 補填的單價）
 *   ④ 不檢查 41 簽核狀態（比照春大直版裁示）
 *   ⑤ 防重複：同一張 41 已經拋過（42 的 Portal備註含該請購單編號）就擋下
 *   ⑥ 檢核（任何一項有誤 → 跳 Error、**一張 42 都不建立**）：
 *        a. 品項列的數量、單價、金額不可為 0 或空白
 *        b. 品項列金額必須 = 數量 × 單價
 *        c. 41 上的「XX部 小計」列（人工輸入）必須等於該部門品項金額加總；
 *           有品項的部門一定要有小計列，小計列的部門也一定要有品項
 *   ⑦ 採購編號：由 Ragic 自動編號產生；建立後以新記錄 ID 重新讀取，讀到的若仍是未展開的占位字串會在訊息中警告
 *   ⑧ 回寫 41「對應週期採購單號」（1022456）：依廠商對應，只寫品項列；寫入後重新讀取核對
 *
 * v1.5 變更：
 *   - 回寫修正：改用 src.getSubtableRootNodeId(子表, 列索引) 取得既有列的內部 ID 再寫入（與春大直 v1.7 相同做法），
 *     v1.4 的列索引寫入會失敗（0/3）。
 *   - 申請人：41「申請人」為空時，改用 41「請購人」帶入 42「申請人」。
 *     ⚠️ 申請人在 Ragic 是人員下拉欄，值必須與 Ragic 使用者選項完全一致，否則會被靜默丟棄。
 *
 * 與春大直版（cycle_request58_to_po57.js）的差異：
 *   - 來源表單 41、目標表單 42，欄位代號全部依 41／42 實際表單定義
 *   - 41 沒有「期別」欄，期別由說明開頭的 yyyy-MM 取得（抓不到再從拋轉批次號推）
 *   - 42 的「擬定廠商」為文字表頭欄；子表擬定廠商單價為必填
 *
 * 安裝（Ragic 設計模式）：
 *   1. 表單 41 → 表單設定 → JavaScript 工作流程 → 下拉選「Installed sheet scope」→ 貼上本檔全部內容 → 儲存
 *      （實測：放在 Installed sheet scope 才會成功；全域 JavaScript／Post-workflow 不生效）
 *   2. 表單 41 → 動作按鈕 → 新增「JavaScript 動作」
 *        名稱：拋轉採購單      呼叫：convertCycleRequestToPO({id})
 *      原本那顆內建「拋轉採購單」請刪除或改名，避免按錯。
 *
 * ⚠️ Ragic 伺服器端是 ES5（Rhino）：只能用 var／function，不可用箭頭函式、let/const、樣板字串。
 * ⚠️ 本版尚未在正式表單實際拋轉驗證，請先用一張測試單確認。
 */

// 回寫 41「對應週期採購單號」開關（v1.5 起使用 getSubtableRootNodeId 寫入，已與春大直版相同做法）
var WRITEBACK_41 = true;

var CP41 = {
  path: "/freed-management-division/41",
  F_DOC_NO: 1022431,     // 編號
  F_APPLICANT: 1022435,  // 申請人（人員下拉欄）
  F_PURPOSE: 1022438,    // 說明（開頭是期別 yyyy-MM）
  F_REQUESTER: 1022467,  // 請購人（必填）
  F_COMPANY: 1022483,    // 公司別
  F_CYCLE: 1022484,      // 週期名稱
  F_BATCH: 1022485,      // 拋轉批次號（CPSUM-yyyyMM-公司-NNNN）
  SUB: 1022489,          // 子表容器
  S_ITEM_CODE: "1022440",
  S_ITEM_NAME: "1022441",
  S_QTY: "1022442",
  S_UNIT: "1022443",
  S_NOTE: "1022444",
  S_PRICE: "1022445",    // 單價
  S_AMOUNT: "1022446",   // 金額（公式；小計列為人工輸入的小計）
  S_DEPT: "1022448",     // 部門
  S_VENDOR: "1022451",   // 擬定廠商
  S_SUMMARY_ID: "1022455", // Portal彙整列ID
  S_LINK_PO: "1022456"   // 對應週期採購單號（回寫用）
};

var PO42 = {
  path: "/freed-management-division/42",
  F_NO: 1022551,         // 採購編號（標題欄；由 Ragic 自動編號）
  F_PERIOD: 1022552,     // 期別（必填）
  F_VENDOR: 1022553,     // 擬定廠商（必填，文字）
  F_APPLICANT: 1022559,  // 申請人（人員下拉欄）
  F_PURPOSE: 1022555,    // 用途說明（必填）
  F_COMPANY: 1022575,    // 公司別
  F_CYCLE: 1022576,      // 週期名稱
  F_BATCH: 1022577,      // 拋轉批次號
  F_PUSHED_AT: 1022578,  // 拋轉時間
  F_NOTE: 1022579,       // Portal備註（寫入來源請購單編號，兼防重複）
  SUB: 1022581,          // 子表容器
  S_ITEM_CODE: 1022561,
  S_ITEM_NAME: 1022562,
  S_QTY: 1022563,
  S_UNIT: 1022564,
  S_NOTE: 1022565,
  S_PRICE: 1022566,      // 擬定廠商單價（必填）
  S_AMOUNT: 1022567,     // 擬定廠商金額
  S_DEPT: 1022568,
  S_ACCOUNT: 1022569,    // 會計課目（本版不寫入）
  S_SUMMARY_ID: 1022570
};

var SUBTOTAL_SUFFIX = " 小計";

function _trim(v) { return (v === null || v === undefined) ? "" : String(v).replace(/^\s+|\s+$/g, ""); }
function _num(v) {
  var s = _trim(v).replace(/[,$\s]/g, "");
  if (s === "") { return null; }
  var n = parseFloat(s);
  return isNaN(n) ? null : n;
}
function _fmt(n) {  // 金額到小數 2 位、去掉多餘的 0
  var r = Math.round(n * 100) / 100;
  return String(r);
}
function _pad(n) { return (n < 10 ? "0" : "") + n; }
function _nowText() {
  // Ragic 伺服器是 UTC，一律換算成台北時間（UTC+8）
  var d = new Date(new Date().getTime() + 8 * 3600 * 1000);
  return d.getUTCFullYear() + "/" + _pad(d.getUTCMonth() + 1) + "/" + _pad(d.getUTCDate()) + " " +
         _pad(d.getUTCHours()) + ":" + _pad(d.getUTCMinutes()) + ":" + _pad(d.getUTCSeconds());
}
function _fail(msg) {
  response.setStatus("ERROR");
  response.setMessage(msg);
}
function _same(a, b) { return Math.abs(Math.round(a * 100) - Math.round(b * 100)) <= 1; }  // 容許 0.01 捨入誤差
function _isPlaceholder(s) { return s === "" || s.indexOf("{") >= 0; }  // 未展開的自動編號占位字串

// 讀不到記錄時的診斷訊息：列出 id 型別、路徑與表單 41 可讀取的筆數
function _notFoundMessage(recordId) {
  var msg = "找不到這張週期請購單（id=" + recordId + "，型別=" + typeof recordId +
            "，路徑=" + CP41.path + "）";
  if (recordId === 0 || recordId === "0" || recordId === "" || recordId === null || recordId === undefined) {
    msg += "。id 為 0 代表這是尚未儲存的新增記錄，請先儲存後，在已儲存的記錄頁面再按一次。";
  }
  try {
    var list = db.getAPIQuery(CP41.path).getAPIResultList();
    msg += "。表單 41 目前可讀取筆數：" + (list ? list.length : 0);
  } catch (e) {
    msg += "。無法讀取表單 41 的筆數（" + e + "）";
  }
  return msg;
}

function convertCycleRequestToPO(recordId) {
  var src = db.getAPIQuery(CP41.path).getAPIEntry(recordId);
  if (!src) { return _fail(_notFoundMessage(recordId)); }

  var docNo = _trim(src.getFieldValue(CP41.F_DOC_NO));
  var purpose = _trim(src.getFieldValue(CP41.F_PURPOSE));
  var company = _trim(src.getFieldValue(CP41.F_COMPANY));
  var cycleName = _trim(src.getFieldValue(CP41.F_CYCLE));
  var batchNo = _trim(src.getFieldValue(CP41.F_BATCH));
  // v1.5：41「申請人」為空時改用「請購人」
  var applicant = _trim(src.getFieldValue(CP41.F_APPLICANT)) || _trim(src.getFieldValue(CP41.F_REQUESTER));

  // 期別：說明開頭的 yyyy-MM；抓不到就從批次號 CPSUM-yyyyMM-… 推
  var period = "";
  var m = purpose.match(/^(\d{4}-\d{2})/);
  if (m) { period = m[1]; }
  else {
    var b = batchNo.match(/-(\d{4})(\d{2})-/);
    if (b) { period = b[1] + "-" + b[2]; }
  }
  if (!period) { return _fail("無法判斷期別：說明欄要以 yyyy-MM 開頭（例如「2026-09 客廁備品週採…」）"); }

  // ── ⑤ 防重複 ────────────────────────────────────────────────────────
  var dupQ = db.getAPIQuery(PO42.path);
  dupQ.addFilter(PO42.F_NOTE, "like", docNo);
  var dup = dupQ.getAPIResultList();
  if (dup && dup.length > 0) {
    return _fail("這張請購單 " + docNo + " 已經拋轉過採購單（" + dup.length + " 張），不能重複拋轉。" +
                 "若要重拋，請先把那幾張採購單作廢／刪除。");
  }

  // ── 讀子表：品項列與「XX部 小計」列分開收 ─────────────────────────────
  var size = src.getSubtableSize(CP41.SUB);
  var lines = [];
  var problems = [];
  var deptItemSum = {};      // 部門 → 品項金額加總（用 41 上的金額欄）
  var deptSubtotal = {};     // 部門 → 41 上人工輸入的小計
  for (var i = 0; i < size; i++) {
    var code = _trim(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_ITEM_CODE));
    var dept = _trim(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_DEPT));
    var amount = _num(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_AMOUNT));
    var rowNo = "第 " + (i + 1) + " 列";

    if (code === "") {
      // 料號空白：部門小計列（部門以「 小計」結尾）或整列空白
      if (dept.slice(-SUBTOTAL_SUFFIX.length) === SUBTOTAL_SUFFIX) {
        var sd = _trim(dept.slice(0, dept.length - SUBTOTAL_SUFFIX.length));
        if (amount === null) {   // 金額欄空白時，退回看單價欄（小計可能同時放在單價）
          amount = _num(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_PRICE));
        }
        if (deptSubtotal[sd] !== undefined) { problems.push(rowNo + "：「" + dept + "」重複出現"); }
        deptSubtotal[sd] = amount;
      }
      continue;
    }

    var name = _trim(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_ITEM_NAME));
    var qty = _num(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_QTY));
    var price = _num(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_PRICE));
    var vendor = _trim(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_VENDOR));
    var label = rowNo + " " + code + " " + name;

    // a. 數量／單價／金額不可為 0 或空白
    if (qty === null || qty === 0) { problems.push(label + "：數量不可為 0 或空白"); }
    if (price === null || price === 0) { problems.push(label + "：單價不可為 0 或空白"); }
    if (amount === null || amount === 0) { problems.push(label + "：金額不可為 0 或空白"); }
    // b. 金額 = 數量 × 單價
    if (qty && price && amount && !_same(amount, qty * price)) {
      problems.push(label + "：金額 " + _fmt(amount) + " ≠ 數量 " + qty + " × 單價 " + price + " = " + _fmt(qty * price));
    }
    if (vendor === "") { problems.push(label + "：沒有擬定廠商"); }
    if (dept === "") { problems.push(label + "：沒有部門"); }

    if (dept !== "") { deptItemSum[dept] = (deptItemSum[dept] || 0) + (amount || 0); }
    lines.push({
      idx: i,
      code: code, name: name, qty: qty, price: price, vendor: vendor, dept: dept,
      unit: _trim(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_UNIT)),
      note: _trim(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_NOTE)),
      sid: _trim(src.getSubtableFieldValue(CP41.SUB, i, CP41.S_SUMMARY_ID))
    });
  }
  if (lines.length === 0) { return _fail("這張請購單沒有品項，無法拋轉採購單。"); }

  // c. 部門小計（人工輸入）必須正確
  var d;
  for (d in deptItemSum) {
    if (!deptItemSum.hasOwnProperty(d)) { continue; }
    if (deptSubtotal[d] === undefined) {
      problems.push("「" + d + SUBTOTAL_SUFFIX + "」列不存在（品項金額合計 " + _fmt(deptItemSum[d]) + "）");
    } else if (deptSubtotal[d] === null) {
      problems.push("「" + d + SUBTOTAL_SUFFIX + "」金額空白，應為 " + _fmt(deptItemSum[d]));
    } else if (!_same(deptSubtotal[d], deptItemSum[d])) {
      problems.push("「" + d + SUBTOTAL_SUFFIX + "」輸入 " + _fmt(deptSubtotal[d]) +
                    "，但該部門品項金額合計為 " + _fmt(deptItemSum[d]) +
                    "（差 " + _fmt(deptSubtotal[d] - deptItemSum[d]) + "）");
    }
  }
  for (d in deptSubtotal) {
    if (deptSubtotal.hasOwnProperty(d) && deptItemSum[d] === undefined) {
      problems.push("「" + d + SUBTOTAL_SUFFIX + "」沒有對應的品項（部門名稱是否打錯？）");
    }
  }

  if (problems.length > 0) {
    return _fail("檢核未通過，未拋轉任何採購單。請修正下列 " + problems.length + " 項後再按一次：\n" + problems.join("\n"));
  }

  // ── ① 依廠商分組 ───────────────────────────────────────────────────
  var groups = {};
  var vendorOrder = [];
  for (var j = 0; j < lines.length; j++) {
    var v = lines[j].vendor;
    if (!groups[v]) { groups[v] = []; vendorOrder.push(v); }
    groups[v].push(lines[j]);
  }
  vendorOrder.sort();

  var pushedAt = _nowText();
  var created = [];
  var warnings = [];
  var poNoByVendor = {};    // 廠商 → 採購編號（僅當編號已正確產生時才記錄）
  for (var k = 0; k < vendorOrder.length; k++) {
    var vendorName = vendorOrder[k];
    var items = groups[vendorName];

    // ── ② 部門排序＋部門小計 ─────────────────────────────────────────
    items.sort(function (a, b) {
      var da = a.dept || "￿", dbb = b.dept || "￿";
      if (da !== dbb) { return da < dbb ? -1 : 1; }
      return a.code < b.code ? -1 : (a.code > b.code ? 1 : 0);
    });
    var rows = [];
    var curDept = null, running = 0;
    for (var n = 0; n < items.length; n++) {
      var it = items[n];
      if (curDept !== null && it.dept !== curDept && curDept !== "") {
        rows.push({ subtotal: true, dept: curDept + SUBTOTAL_SUFFIX, amount: running });
        running = 0;
      }
      curDept = it.dept;
      rows.push(it);
      running += it.qty * it.price;
    }
    if (curDept !== null && curDept !== "") {
      rows.push({ subtotal: true, dept: curDept + SUBTOTAL_SUFFIX, amount: running });
    }

    var po = db.getAPIQuery(PO42.path).insertAPIEntry();
    po.setFieldValue(PO42.F_PERIOD, period);
    po.setFieldValue(PO42.F_PURPOSE, period + " " + cycleName + " 週期採購（" + company + "／" + vendorName + "）");
    po.setFieldValue(PO42.F_VENDOR, vendorName);
    if (applicant) { po.setFieldValue(PO42.F_APPLICANT, applicant); }
    po.setFieldValue(PO42.F_COMPANY, company);
    po.setFieldValue(PO42.F_CYCLE, cycleName);
    po.setFieldValue(PO42.F_BATCH, batchNo);
    po.setFieldValue(PO42.F_PUSHED_AT, pushedAt);
    po.setFieldValue(PO42.F_NOTE, "由週期請購單 " + docNo + " 拋轉（依廠商拆單）");

    // 子表 key 用負數；Ragic 依「絕對值大的排前面」，所以第一列拿最大的絕對值
    var total = rows.length;
    for (var r = 0; r < total; r++) {
      var key = -(total - r);
      var row = rows[r];
      if (row.subtotal) {
        // 小計列：料號空白；小計金額放在「擬定廠商單價」（必填欄），數量留空
        //   → 42 的「擬定廠商金額」若是公式會算成 0，不會重複計入「小計」
        po.setSubtableFieldValue(PO42.S_DEPT, key, row.dept);
        po.setSubtableFieldValue(PO42.S_PRICE, key, _fmt(row.amount));
      } else {
        po.setSubtableFieldValue(PO42.S_ITEM_CODE, key, row.code);
        po.setSubtableFieldValue(PO42.S_ITEM_NAME, key, row.name);
        po.setSubtableFieldValue(PO42.S_QTY, key, String(row.qty));
        po.setSubtableFieldValue(PO42.S_UNIT, key, row.unit);
        po.setSubtableFieldValue(PO42.S_NOTE, key, row.note);
        po.setSubtableFieldValue(PO42.S_PRICE, key, _fmt(row.price));
        po.setSubtableFieldValue(PO42.S_DEPT, key, row.dept);
        po.setSubtableFieldValue(PO42.S_SUMMARY_ID, key, row.sid);
      }
    }
    po.recalculateAllFormulas();
    po.save();

    // ⑦ 以新記錄 ID 重新讀取採購編號（save 之後自動編號才會展開）
    var newId = po.getRootNodeId();
    var rr = db.getAPIQuery(PO42.path).getAPIEntry(newId);
    var savedNo = rr ? _trim(rr.getFieldValue(PO42.F_NO)) : "";
    if (_isPlaceholder(savedNo)) {
      warnings.push("⚠️ " + vendorName + "：採購編號未展開（讀到「" + savedNo + "」），請檢查 42 的自動編號格式設定");
    } else {
      poNoByVendor[vendorName] = savedNo;
    }
    created.push(vendorName + "：" + (savedNo || "（編號未知）") + "（" + items.length + " 項）");
  }

  // ── ⑧ 回寫 41「對應週期採購單號」（依既有列的內部 ID 寫入）──────────────
  var wbMsg = "";
  if (!WRITEBACK_41) {
    wbMsg = "\n⚠️ 未回寫 41「對應週期採購單號」（回寫功能已停用），請依上方採購編號手動補填";
  } else {
    try {
      var wbCount = 0;
      for (var w = 0; w < lines.length; w++) {
        var target = poNoByVendor[lines[w].vendor];
        if (target) {
          var nodeId = src.getSubtableRootNodeId(CP41.SUB, lines[w].idx);
          src.setSubtableFieldValue(CP41.S_LINK_PO, nodeId, target);
          wbCount++;
        }
      }
      src.save();
      // 重新讀取 41 核對
      var chk = db.getAPIQuery(CP41.path).getAPIEntry(recordId);
      var okCount = 0;
      for (var c = 0; c < lines.length; c++) {
        var want = poNoByVendor[lines[c].vendor];
        if (want && _trim(chk.getSubtableFieldValue(CP41.SUB, lines[c].idx, CP41.S_LINK_PO)) === want) { okCount++; }
      }
      wbMsg = "\n回寫 41「對應週期採購單號」：" + okCount + "/" + wbCount + " 列核對成功";
      if (okCount < wbCount) { wbMsg += "（⚠️ 有列未寫入，請手動補填）"; }
    } catch (e) {
      wbMsg = "\n⚠️ 回寫 41「對應週期採購單號」失敗：" + e + "（採購單已建立，請手動補填）";
    }
  }

  response.setStatus("SUCCESS");
  response.setMessage("已由 " + docNo + " 拋轉 " + created.length + " 張採購單：\n" + created.join("\n") +
                      (warnings.length ? "\n" + warnings.join("\n") : "") + wbMsg);
}

/*
 * 欄位 ID 依表單 41（★週期請購單）與表單 42（★週採採購單）的設計模式實際讀取結果，2026-11-19。
 * 表單 41 子表容器 1022489；表單 42 子表容器 1022581。
 */
