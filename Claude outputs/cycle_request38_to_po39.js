/**
 * cycle_request38_to_po39.js  DRAFT  (2026-11-25)
 *
 * 台中版：Ragic 伺服器端 JavaScript Workflow ——「★週期請購單」(taichung-public-form/38)
 * 的「拋轉週期採購單」按鈕，把一張週期請購單拋轉成「★週採採購單」(taichung-public-form/39)。
 *
 * 由 cycle_request58_to_po57.js v1.1（樂群）改寫：
 *   - 路徑與欄位代號全部改為台中 38 / 39 的代號（見下方 CP38、PO39）
 *   - 防重複：新增「來源請購單號」欄位（39 的 1022773）精確比對，並保留 Portal備註 like 比對
 *   - 其餘檢核邏輯與依廠商拆單、部門排序、部門小計列，與樂群版相同
 *
 * 草稿狀態：尚未在 Ragic 測試，請先用測試單驗證後再使用。
 *
 * 安裝（Ragic 設計模式，taichung-public-form/38）：
 *   1. 表單設定 → JavaScript 工作流程 → 貼上本檔全部內容 → 儲存
 *      （2026-11-19 實測：41 的版本必須貼在「Installed sheet scope」，貼在全域不生效；
 *        請依 38 實際測試結果選擇）
 *   2. 表單設定 → 動作按鈕 → 新增「JavaScript 動作」
 *        名稱：拋轉週期採購單      呼叫：convertCycleRequestToPO({id})
 *
 * ⚠️ Ragic 伺服器端是 ES5（Rhino）：只能用 var／function，不可用箭頭函式、let/const、樣板字串。
 */

var CP38 = {
  path: "/taichung-public-form/38",
  F_DOC_NO: 1022685,     // 編號（樂管購yyyyMM00000）
  F_PURPOSE: 1022692,    // 說明（開頭是期別 yyyy-MM）
  F_APPLICANT: 1022689,  // 申請人
  F_COMPANY: 1022737,    // 公司別
  F_CYCLE: 1022738,      // 週期名稱
  F_BATCH: 1022739,      // 拋轉批次號（CPSUM-yyyyMM-公司-NNNN）
  SUB: 1022743,          // 子表 key
  S_ITEM_CODE: "1022694",     // 料號
  S_ITEM_NAME: "1022695",     // 產品名稱
  S_QTY: "1022696",           // 數量
  S_UNIT: "1022697",          // 單位
  S_NOTE: "1022698",          // 品項備註
  S_PRICE: "1022699",         // 單價
  S_AMOUNT: "1022700",        // 金額（公式；小計列為人工輸入的小計）
  S_DEPT: "1022702",          // 部門
  S_VENDOR: "1022705",        // 擬定廠商
  S_SUMMARY_ID: "1022709"     // Portal彙整列ID
};

var PO39 = {
  path: "/taichung-public-form/39",
  F_NO: 1022744,         // 採購編號（樂管週採00000，由 Ragic 自動編號）
  F_PERIOD: 1022745,     // 期別（必填）
  F_APPLICANT: 1022752,  // 申請人
  F_PURPOSE: 1022748,    // 用途說明（必填）
  F_VENDOR: 1022746,     // 擬定廠商（必填，文字）
  F_COMPANY: 1022768,    // 公司別
  F_CYCLE: 1022769,      // 週期名稱
  F_BATCH: 1022770,      // 拋轉批次號
  F_PUSHED_AT: 1022771,  // 拋轉時間
  F_NOTE: 1022772,       // Portal備註
  F_SOURCE: 1022773,     // 來源請購單號（防重複用）
  S_ITEM_CODE: 1022754,  // 料號
  S_ITEM_NAME: 1022755,  // 產品名稱
  S_QTY: 1022756,        // 數量
  S_UNIT: 1022757,       // 單位
  S_NOTE: 1022758,       // 品項備註
  S_PRICE: 1022759,      // 擬定廠商單價（小計列的小計金額也放這裡）
  S_DEPT: 1022761,       // 部門
  S_SUMMARY_ID: 1022763  // Portal彙整列ID
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
  var d = new Date();
  return d.getFullYear() + "/" + _pad(d.getMonth() + 1) + "/" + _pad(d.getDate()) + " " +
         _pad(d.getHours()) + ":" + _pad(d.getMinutes()) + ":" + _pad(d.getSeconds());
}
function _fail(msg) {
  response.setStatus("ERROR");
  response.setMessage(msg);
}
function _same(a, b) { return Math.abs(Math.round(a * 100) - Math.round(b * 100)) <= 1; }  // 容許 0.01 捨入誤差

function convertCycleRequestToPO(recordId) {
  var src = db.getAPIQuery(CP38.path).getAPIEntry(recordId);
  if (!src) { return _fail("找不到這張週期請購單（id=" + recordId + "）"); }

  var docNo = _trim(src.getFieldValue(CP38.F_DOC_NO));
  var purpose = _trim(src.getFieldValue(CP38.F_PURPOSE));
  var company = _trim(src.getFieldValue(CP38.F_COMPANY));
  var cycleName = _trim(src.getFieldValue(CP38.F_CYCLE));
  var batchNo = _trim(src.getFieldValue(CP38.F_BATCH));
  var applicant = _trim(src.getFieldValue(CP38.F_APPLICANT));

  // 期別：說明開頭的 yyyy-MM；抓不到就從批次號 CPSUM-yyyyMM-… 推
  var period = "";
  var m = purpose.match(/^(\d{4}-\d{2})/);
  if (m) { period = m[1]; }
  else {
    var b = batchNo.match(/-(\d{4})(\d{2})-/);
    if (b) { period = b[1] + "-" + b[2]; }
  }
  if (!period) { return _fail("無法判斷期別：說明欄要以 yyyy-MM 開頭（例如「2026-09 客廁備品週採…」）"); }

  // ── ⑤ 防重複：來源請購單號精確比對，另以 Portal備註 like 再擋一次 ─────
  var dupQ = db.getAPIQuery(PO39.path);
  dupQ.addFilter(PO39.F_SOURCE, "=", docNo);
  var dup = dupQ.getAPIResultList();
  var dupQ2 = db.getAPIQuery(PO39.path);
  dupQ2.addFilter(PO39.F_NOTE, "like", docNo);
  var dup2 = dupQ2.getAPIResultList();
  var dupCount = Math.max((dup ? dup.length : 0), (dup2 ? dup2.length : 0));
  if (dupCount > 0) {
    return _fail("這張請購單 " + docNo + " 已經拋轉過採購單（" + dupCount + " 張），不能重複拋轉。" +
                 "若要重拋，請先把那幾張採購單作廢／刪除。");
  }

  // ── 讀子表：品項列與「XX部 小計」列分開收 ─────────────────────────────
  var size = src.getSubtableSize(CP38.SUB);
  var lines = [];
  var problems = [];
  var deptItemSum = {};      // 部門 → 品項金額加總（用 38 上的金額欄）
  var deptSubtotal = {};     // 部門 → 38 上人工輸入的小計
  for (var i = 0; i < size; i++) {
    var code = _trim(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_ITEM_CODE));
    var dept = _trim(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_DEPT));
    var amount = _num(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_AMOUNT));
    var rowNo = "第 " + (i + 1) + " 列";

    if (code === "") {
      // 料號空白：部門小計列（部門以「 小計」結尾）或整列空白
      if (dept.slice(-SUBTOTAL_SUFFIX.length) === SUBTOTAL_SUFFIX) {
        var sd = _trim(dept.slice(0, dept.length - SUBTOTAL_SUFFIX.length));
        if (amount === null) {   // 金額欄空白時，退回看單價欄（Portal 會把小計同時放在單價）
          amount = _num(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_PRICE));
        }
        if (deptSubtotal[sd] !== undefined) { problems.push(rowNo + "：「" + dept + "」重複出現"); }
        deptSubtotal[sd] = amount;
      }
      continue;
    }

    var name = _trim(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_ITEM_NAME));
    var qty = _num(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_QTY));
    var price = _num(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_PRICE));
    var vendor = _trim(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_VENDOR));
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
      code: code, name: name, qty: qty, price: price, vendor: vendor, dept: dept,
      unit: _trim(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_UNIT)),
      note: _trim(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_NOTE)),
      sid: _trim(src.getSubtableFieldValue(CP38.SUB, i, CP38.S_SUMMARY_ID))
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

    var po = db.getAPIQuery(PO39.path).insertAPIEntry();
    po.setFieldValue(PO39.F_PERIOD, period);
    po.setFieldValue(PO39.F_PURPOSE, period + " " + cycleName + " 週期採購（" + company + "／" + vendorName + "）");
    po.setFieldValue(PO39.F_VENDOR, vendorName);
    if (applicant) { po.setFieldValue(PO39.F_APPLICANT, applicant); }
    po.setFieldValue(PO39.F_COMPANY, company);
    po.setFieldValue(PO39.F_CYCLE, cycleName);
    po.setFieldValue(PO39.F_BATCH, batchNo);
    po.setFieldValue(PO39.F_PUSHED_AT, pushedAt);
    po.setFieldValue(PO39.F_NOTE, "由週期請購單 " + docNo + " 拋轉（依廠商拆單）");
    po.setFieldValue(PO39.F_SOURCE, docNo);

    // 子表 key 用負數；Ragic 依「絕對值大的排前面」，所以第一列拿最大的絕對值
    var total = rows.length;
    for (var r = 0; r < total; r++) {
      var key = -(total - r);
      var row = rows[r];
      if (row.subtotal) {
        // 小計列：料號空白；小計金額放在「擬定廠商單價」，數量留空
        po.setSubtableFieldValue(PO39.S_DEPT, key, row.dept);
        po.setSubtableFieldValue(PO39.S_PRICE, key, _fmt(row.amount));
      } else {
        po.setSubtableFieldValue(PO39.S_ITEM_CODE, key, row.code);
        po.setSubtableFieldValue(PO39.S_ITEM_NAME, key, row.name);
        po.setSubtableFieldValue(PO39.S_QTY, key, String(row.qty));
        po.setSubtableFieldValue(PO39.S_UNIT, key, row.unit);
        po.setSubtableFieldValue(PO39.S_NOTE, key, row.note);
        po.setSubtableFieldValue(PO39.S_PRICE, key, _fmt(row.price));
        po.setSubtableFieldValue(PO39.S_DEPT, key, row.dept);
        po.setSubtableFieldValue(PO39.S_SUMMARY_ID, key, row.sid);
      }
    }
    po.recalculateAllFormulas();
    po.save();
    created.push(vendorName + "：" + _trim(po.getFieldValue(PO39.F_NO)) + "（" + items.length + " 項）");
  }

  response.setStatus("SUCCESS");
  response.setMessage("已由 " + docNo + " 拋轉 " + created.length + " 張採購單：\n" + created.join("\n"));
}
