/**
 * cycle_request58_to_po57.js  v1.7  (2026-09-28)
 *
 * Ragic 伺服器端 JavaScript Workflow ——「★週期請購單」(sheet 58) 的「拋轉採購單」按鈕
 * 把一張週期請購單拋轉成「★週採採購單」(sheet 57)：
 *
 *   ① 同一廠商合併成同一張採購單（依子表「擬定廠商」分組；一家廠商一張 57）
 *   ② 每張採購單內，相同部門排在一起，部門最後插一列「XX部 小計」
 *   ③ 數量／單價／廠商一律讀 58 目前內容（含採購在 Ragic 補填的單價）
 *   ④ 不檢查 58 簽核狀態（Samuel 2026-09-28 裁示）
 *   ⑤ 防重複：同一張 58 已經拋過（57 的 Portal備註含該請購單編號）就擋下
 *   ⑥ v1.1 檢核（任何一項有誤 → 跳 Error、**一張 57 都不建立**）：
 *        a. 品項列的數量、單價、金額不可為 0 或空白
 *        b. 品項列金額必須 = 數量 × 單價
 *        d. v1.7 品項列的會計課目不可空白
 *        c. 58 上的「XX部 小計」列（人工輸入）必須等於該部門品項金額加總；
 *           有品項的部門一定要有小計列，小計列的部門也一定要有品項
 *
 * 57 小計列的淺橘色底色：Workflow 無法設定樣式，請在 57 設計模式對子表欄位設定
 *   條件式格式「部門 包含 小計 → 底色淺橘」（比照 58 的設定）。
 *
 * 安裝（Ragic 設計模式，sheet 58）：
 *   1. 表單設定 → JavaScript 工作流程 → 「全域 Javascript」貼上本檔全部內容 → 儲存
 *   2. 表單設定 → 動作按鈕 → 新增「JavaScript 動作」
 *        名稱：拋轉採購單      呼叫：convertCycleRequestToPO({id})
 *      原本那顆內建「拋轉採購單」（轉到 sheet 23）請刪除或改名，避免按錯。
 *
 * ⚠️ Ragic 伺服器端是 ES5（Rhino）：只能用 var／function，不可用箭頭函式、let/const、樣板字串。
 */

var CP58 = {
  path: "/community-management-department/58",
  F_DOC_NO: 1020805,     // 編號（樂管購yyyyMM00000）
  F_PURPOSE: 1020809,    // 說明（開頭是期別 yyyy-MM）
  F_APPLICANT: 1020808,  // 申請人
  F_COMPANY: 1020875,    // 公司別
  F_CYCLE: 1020876,      // 週期名稱
  F_BATCH: 1020877,      // 拋轉批次號（CPSUM-yyyyMM-公司-NNNN）
  SUB: 1020873,
  S_ITEM_CODE: "1020880",
  S_ITEM_NAME: "1020822",
  S_QTY: "1020823",
  S_UNIT: "1020824",
  S_NOTE: "1020825",
  S_PRICE: "1020826",
  S_AMOUNT: "1020827",   // 金額（公式；小計列為人工輸入的小計）
  S_DEPT: "1020829",
  S_ACCOUNT: "1020828",  // 會計課目
  S_VENDOR: "1020832",
  S_SUMMARY_ID: "1020881",
  // v1.3：58 子表「對應週期採購單號」欄位代號（回寫每個料號拋到哪張 57；null＝不回寫）
  S_PO_NO: "1020942"
};

var PO57 = {
  path: "/community-management-department/57",
  F_PERIOD: 1020774,     // 期別（必填）
  F_APPLICANT: 1020776,  // 申請人
  F_PURPOSE: 1020777,    // 用途說明（必填）
  F_VENDOR: 1020778,     // 擬定廠商（必填，文字）
  F_COMPANY: 1020793,    // 公司別
  F_CYCLE: 1020794,      // 週期名稱
  F_BATCH: 1020795,      // 拋轉批次號
  F_PUSHED_AT: 1020796,  // 拋轉時間
  F_NOTE: 1020797,       // Portal備註（寫入來源請購單編號，兼防重複）
  // v1.2：57 主表「來源請購單號」欄位代號（Ragic 建好欄位後填入；null＝不寫）
  F_SOURCE_NO: 1020941,  // 57 主表「來源請購單號」
  S_ITEM_NAME: 1020780,
  S_QTY: 1020781,
  S_UNIT: 1020782,
  S_NOTE: 1020783,
  S_PRICE: 1020784,      // 擬定廠商單價（必填）
  S_ITEM_CODE: 1020798,
  S_DEPT: 1020799,
  S_SUMMARY_ID: 1020800,
  // v1.6：57 子表「會計課目」欄位代號（Ragic 建好後填入；null＝不寫）
  S_ACCOUNT: 1020943
};

var SUBTOTAL_SUFFIX = " 小計";
var SCRIPT_VERSION = "v1.7";

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
  // v1.4：Ragic 伺服器是 UTC，一律換算成台北時間（UTC+8）
  var d = new Date(new Date().getTime() + 8 * 3600 * 1000);
  return d.getUTCFullYear() + "/" + _pad(d.getUTCMonth() + 1) + "/" + _pad(d.getUTCDate()) + " " +
         _pad(d.getUTCHours()) + ":" + _pad(d.getUTCMinutes()) + ":" + _pad(d.getUTCSeconds());
}
function _fail(msg) {
  response.setStatus("ERROR");
  response.setMessage(msg);
}
function _same(a, b) { return Math.abs(Math.round(a * 100) - Math.round(b * 100)) <= 1; }  // 容許 0.01 捨入誤差

function convertCycleRequestToPO(recordId) {
  var src = db.getAPIQuery(CP58.path).getAPIEntry(recordId);
  if (!src) { return _fail("找不到這張週期請購單（id=" + recordId + "）"); }

  var docNo = _trim(src.getFieldValue(CP58.F_DOC_NO));
  var purpose = _trim(src.getFieldValue(CP58.F_PURPOSE));
  var company = _trim(src.getFieldValue(CP58.F_COMPANY));
  var cycleName = _trim(src.getFieldValue(CP58.F_CYCLE));
  var batchNo = _trim(src.getFieldValue(CP58.F_BATCH));
  var applicant = _trim(src.getFieldValue(CP58.F_APPLICANT));

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
  var dupQ = db.getAPIQuery(PO57.path);
  dupQ.addFilter(PO57.F_NOTE, "like", docNo);
  var dup = dupQ.getAPIResultList();
  if (dup && dup.length > 0) {
    return _fail("這張請購單 " + docNo + " 已經拋轉過採購單（" + dup.length + " 張），不能重複拋轉。" +
                 "若要重拋，請先把那幾張採購單作廢／刪除。");
  }

  // ── 讀子表：品項列與「XX部 小計」列分開收 ─────────────────────────────
  var size = src.getSubtableSize(CP58.SUB);
  var lines = [];
  var problems = [];
  var deptItemSum = {};      // 部門 → 品項金額加總（用 58 上的金額欄）
  var deptSubtotal = {};     // 部門 → 58 上人工輸入的小計
  for (var i = 0; i < size; i++) {
    var code = _trim(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_ITEM_CODE));
    var dept = _trim(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_DEPT));
    var amount = _num(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_AMOUNT));
    var rowNo = "第 " + (i + 1) + " 列";

    if (code === "") {
      // 料號空白：部門小計列（部門以「 小計」結尾）或整列空白
      if (dept.slice(-SUBTOTAL_SUFFIX.length) === SUBTOTAL_SUFFIX) {
        var sd = _trim(dept.slice(0, dept.length - SUBTOTAL_SUFFIX.length));
        if (amount === null) {   // 金額欄空白時，退回看單價欄（Portal 會把小計同時放在單價）
          amount = _num(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_PRICE));
        }
        if (deptSubtotal[sd] !== undefined) { problems.push(rowNo + "：「" + dept + "」重複出現"); }
        deptSubtotal[sd] = amount;
      }
      continue;
    }

    var name = _trim(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_ITEM_NAME));
    var qty = _num(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_QTY));
    var price = _num(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_PRICE));
    var vendor = _trim(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_VENDOR));
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
    // v1.7：會計課目不可空白
    if (_trim(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_ACCOUNT)) === "") {
      problems.push(label + "：沒有會計課目");
    }

    if (dept !== "") { deptItemSum[dept] = (deptItemSum[dept] || 0) + (amount || 0); }
    lines.push({
      code: code, name: name, qty: qty, price: price, vendor: vendor, dept: dept,
      unit: _trim(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_UNIT)),
      note: _trim(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_NOTE)),
      sid: _trim(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_SUMMARY_ID)),
      rowIdx: i,
      acct: _trim(src.getSubtableFieldValue(CP58.SUB, i, CP58.S_ACCOUNT))
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

    var po = db.getAPIQuery(PO57.path).insertAPIEntry();
    po.setFieldValue(PO57.F_PERIOD, period);
    po.setFieldValue(PO57.F_PURPOSE, period + " " + cycleName + " 週期採購（" + company + "／" + vendorName + "）");
    po.setFieldValue(PO57.F_VENDOR, vendorName);
    if (applicant) { po.setFieldValue(PO57.F_APPLICANT, applicant); }
    po.setFieldValue(PO57.F_COMPANY, company);
    po.setFieldValue(PO57.F_CYCLE, cycleName);
    po.setFieldValue(PO57.F_BATCH, batchNo);
    po.setFieldValue(PO57.F_PUSHED_AT, pushedAt);
    po.setFieldValue(PO57.F_NOTE, "由週期請購單 " + docNo + " 拋轉（依廠商拆單）");
    if (PO57.F_SOURCE_NO) { po.setFieldValue(PO57.F_SOURCE_NO, docNo); }

    // 子表 key 用負數；Ragic 依「絕對值大的排前面」，所以第一列拿最大的絕對值
    var total = rows.length;
    for (var r = 0; r < total; r++) {
      var key = -(total - r);
      var row = rows[r];
      if (row.subtotal) {
        // 小計列：料號空白；小計金額放在「擬定廠商單價」（必填欄），數量留空
        //   → 57 的「擬定廠商金額」若是 C5*F5 會算成 0，不會重複計入「小計」
        po.setSubtableFieldValue(PO57.S_DEPT, key, row.dept);
        po.setSubtableFieldValue(PO57.S_PRICE, key, _fmt(row.amount));
      } else {
        po.setSubtableFieldValue(PO57.S_ITEM_CODE, key, row.code);
        po.setSubtableFieldValue(PO57.S_ITEM_NAME, key, row.name);
        po.setSubtableFieldValue(PO57.S_QTY, key, String(row.qty));
        po.setSubtableFieldValue(PO57.S_UNIT, key, row.unit);
        po.setSubtableFieldValue(PO57.S_NOTE, key, row.note);
        po.setSubtableFieldValue(PO57.S_PRICE, key, _fmt(row.price));
        po.setSubtableFieldValue(PO57.S_DEPT, key, row.dept);
        po.setSubtableFieldValue(PO57.S_SUMMARY_ID, key, row.sid);
        if (PO57.S_ACCOUNT) { po.setSubtableFieldValue(PO57.S_ACCOUNT, key, row.acct); }
      }
    }
    po.recalculateAllFormulas();
    po.save();
    // v1.5：save() 後 entry 上的自動編號仍是樣板「樂管週採{0,number,00000}」，
    //       必須用 rootNodeId 重新讀一次才拿得到真正的採購編號
    var poNo = _trim(db.getAPIQuery(PO57.path).getAPIEntry(po.getRootNodeId()).getFieldValue(1020773));
    if (CP58.S_PO_NO) {
      for (var w = 0; w < items.length; w++) {
        var nodeId = src.getSubtableRootNodeId(CP58.SUB, items[w].rowIdx);
        src.setSubtableFieldValue(CP58.S_PO_NO, nodeId, poNo);
      }
    }
    created.push(vendorName + "：" + poNo + "（" + items.length + " 項）");
  }

  if (CP58.S_PO_NO) { src.save(); }   // 回寫 58 子表「對應週期採購單號」
  response.setStatus("SUCCESS");
  response.setMessage("[" + SCRIPT_VERSION + "] 已由 " + docNo + " 拋轉 " + created.length + " 張採購單：\n" + created.join("\n"));
}
