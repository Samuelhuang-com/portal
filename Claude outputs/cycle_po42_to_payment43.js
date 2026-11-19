/**
 * cycle_po42_to_payment43.js  v1.0  (2026-11-19)
 *
 * Ragic 伺服器端 JavaScript Workflow ——日曜「★週採採購單」(freed-management-division/42) 的「拋轉請款單」按鈕
 * 把一張 42 採購單拋成一張「★週期請款單」(freed-management-division/43)，並把請款單號寫回 42「請款單號」。
 *
 * 規則（沿用春大直 v1.3 的裁示，欄位代號依日曜 42／43 表單）：
 *   · 一張 42 → 一張 43（42 本來就是一家廠商一張）
 *   · 43 會科：固定「雜項購置」（主表單選必填）
 *   · 43 付款日期：依 42「1.付款條件」推算 —— 月結30/45/60天＝拋轉當月月底 + N 天；付現＝拋轉當天
 *   · 不檢查驗收；品項沒數量／沒單價／沒金額 → 跳 Error，不建立請款單
 *   · 防重複：42「請款單號」有值且那張 43 仍存在 → 擋下；43 已有同一採購編號的請款單 → 擋下
 *     42「請款單號」有值但那張 43 已被刪除 → 視為可重拋
 *   · 42 的「XX部 小計」列（料號空白）不直接複製；由本程式依部門重算，每部門最後插一列「XX部 小計」
 *   · 43 子表：廠商金額＝42「擬定廠商金額」；實際驗收數量預帶 42 數量（驗收時人工改）；
 *     實際收貨金額為 43 的公式欄位，本程式不寫；部門小計列的廠商金額＝部門合計
 *   · 43 主表「小計」＝品項合計，存檔後核對，不相等會在結果訊息中警告
 *
 * 編號：拋轉時自行產生「管請」＋yyyyMM＋5 位流水號（例：管請20261100001），流水號接在目前 43 同月份最大號之後，
 *       寫入 43「管請編號」（1022491），存檔後讀回確認。
 *
 * 安裝（Ragic 設計模式，表單 42）：
 *   1. JavaScript 工作流程 → 下拉選 42「★週採採購單」→ Installed sheet scope → 貼上本檔全部內容 → 儲存
 *      （實測：放在 Installed sheet scope 才會成功）
 *   2. 表單設定 → 動作按鈕：新增 JavaScript 動作
 *        名稱：拋轉請款單      呼叫：convertCyclePOToPayment({id})
 *
 * ⚠️ Ragic 伺服器端是 ES5：只能用 var／function。
 * ⚠️ 43「申請部門」的選項未確認，預設送「管理」；若 Ragic 拒收，請告知正確選項。
 * ⚠️ 43「管請編號」是否接受程式寫入尚待實測；若被 Ragic 自動編號覆蓋，結果訊息會顯示實際存下的號碼。
 */

var PAY_VERSION = "v1.0";
var PAY_NO_PREFIX = "管請";

var PO42P = {
  path: "/freed-management-division/42",
  F_PO_NO: 1022551,      // 採購編號
  F_PERIOD: 1022552,     // 期別
  F_VENDOR: 1022553,     // 擬定廠商
  F_APPLICANT: 1022559,  // 申請人
  F_TERMS: 1022573,      // 1.付款條件（月結30天／月結45天／月結60天／付現）
  F_COMPANY: 1022575,    // 公司別
  F_CYCLE: 1022576,      // 週期名稱
  F_SOURCE_NO: 1022580,  // 來源請購單號
  F_PAY_NO: 1022556,     // 請款單號（回寫 43 管請編號）
  SUB: 1022581,
  S_ITEM_CODE: "1022561",
  S_ITEM_NAME: "1022562",
  S_QTY: "1022563",
  S_UNIT: "1022564",
  S_NOTE: "1022565",
  S_PRICE: "1022566",    // 擬定廠商單價
  S_AMOUNT: "1022567",   // 擬定廠商金額
  S_DEPT: "1022568"      // 部門
};

var PAY43 = {
  path: "/freed-management-division/43",
  F_NO: 1022491,         // 管請編號（拋轉時寫入「管請」＋流水號）
  F_NO_ALT: 1022492,     // 付款編號（備用讀回）
  F_DEPT: 1022490,       // 申請部門（必填）
  F_PERIOD_PO: 1022493,  // 週期採購單號
  F_ACCOUNT: 1022494,    // 會科（必填）
  F_PO_NO: 1022495,      // 採購編號
  F_DATE: 1022497,       // 申請日期（必填）
  F_APPLICANT: 1022498,  // 申請人
  F_PAY_TYPE: 1022499,   // 付款種類（必填）
  F_REASON: 1022500,     // 事由（必填）
  F_TAX_INCL: 1022511,   // 項目金額為(含稅)：No＝子表金額是未稅
  F_SUBTOTAL: 1022514,   // 小計（＝品項合計，用來核對部門小計沒有重複計入）
  F_PAYEE: 1022519,      // 受款者
  F_PAY_DATE: 1022523,   // 付款日期（必填）
  F_NOTE: 1022525,       // 備註
  SUB: 1022550,          // 子表容器（項次 subtable key）
  S_NAME: "1022503",     // 產品名稱
  S_QTY: "1022504",
  S_UNIT: "1022505",
  S_NOTE: "1022506",
  S_PRICE: "1022507",    // 單價
  S_AMOUNT: "1022508",   // 廠商金額
  S_RECV_QTY: "1022509", // 實際驗收數量（預帶 42 數量）
  S_RECV_SUB: null       // 實際收貨金額為公式欄位（1022510），本程式不寫
};

var PAY_DEFAULTS = {
  dept: "管理",
  account: "雜項購置",
  payType: "匯款"
};

function _pt(v) { return (v === null || v === undefined) ? "" : String(v).replace(/^\s+|\s+$/g, ""); }
function _pn(v) {
  var s = _pt(v).replace(/[,$\s]/g, "");
  if (s === "") { return null; }
  var n = parseFloat(s);
  return isNaN(n) ? null : n;
}
function _p2(n) { return (n < 10 ? "0" : "") + n; }
function _padN(n, width) {
  var s = String(n);
  while (s.length < width) { s = "0" + s; }
  return s;
}
function _taipei() { return new Date(new Date().getTime() + 8 * 3600 * 1000); }   // 讀 getUTC* 即台北時間
function _ymd(d) { return d.getUTCFullYear() + "/" + _p2(d.getUTCMonth() + 1) + "/" + _p2(d.getUTCDate()); }
function _ym(d) { return String(d.getUTCFullYear()) + _p2(d.getUTCMonth() + 1); }   // yyyyMM
function _payDate(terms, now) {
  var m = _pt(terms).match(/月結\s*(\d+)\s*天/);
  if (!m) { return _ymd(now); }                         // 付現或空白：當天
  var monthEnd = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 0));
  return _ymd(new Date(monthEnd.getTime() + parseInt(m[1], 10) * 86400000));
}
function _payFail(msg) { response.setStatus("ERROR"); response.setMessage(msg); }

// 取得 43 同月份「管請」＋yyyyMM 的最大流水號（沒有則回傳 0）
function _maxPaySerial(prefix) {
  var max = 0;
  var q = db.getAPIQuery(PAY43.path);
  q.addFilter(PAY43.F_NO, "like", prefix);
  var list = q.getAPIResultList();
  for (var i = 0; list && i < list.length; i++) {
    var no = _pt(list[i].getFieldValue(PAY43.F_NO));
    if (no.indexOf(prefix) === 0) {
      var s = parseInt(no.slice(prefix.length), 10);
      if (!isNaN(s) && s > max) { max = s; }
    }
  }
  return max;
}

function convertCyclePOToPayment(recordId) {
  var src = db.getAPIQuery(PO42P.path).getAPIEntry(recordId);
  if (!src) { return _payFail("找不到這張週期採購單（id=" + recordId + "）"); }

  var poNo = _pt(src.getFieldValue(PO42P.F_PO_NO));
  var vendor = _pt(src.getFieldValue(PO42P.F_VENDOR));
  var period = _pt(src.getFieldValue(PO42P.F_PERIOD));
  var company = _pt(src.getFieldValue(PO42P.F_COMPANY));
  var cycle = _pt(src.getFieldValue(PO42P.F_CYCLE));
  var terms = _pt(src.getFieldValue(PO42P.F_TERMS));
  var applicant = _pt(src.getFieldValue(PO42P.F_APPLICANT));
  var sourceNo = _pt(src.getFieldValue(PO42P.F_SOURCE_NO));

  // ── 防重複 ─────────────────────────────────────────────────────────
  var oldPayNo = _pt(src.getFieldValue(PO42P.F_PAY_NO));
  var reissue = "";
  if (oldPayNo !== "") {
    var eq = db.getAPIQuery(PAY43.path);
    eq.addFilter(PAY43.F_NO, "=", oldPayNo);
    var still = eq.getAPIResultList();
    if (still && still.length > 0) {
      return _payFail("這張採購單已經拋轉過請款單（" + oldPayNo + "），而且該請款單仍存在，不能重複拋轉。" +
                      "若要重拋，請先刪除請款單 " + oldPayNo + " 再按一次。");
    }
    reissue = "（原請款單 " + oldPayNo + " 已不存在，本次為重新拋轉）";
  }
  var dq = db.getAPIQuery(PAY43.path);
  dq.addFilter(PAY43.F_PO_NO, "=", poNo);
  var dup = dq.getAPIResultList();
  if (dup && dup.length > 0) {
    return _payFail("週期請款單裡已經有採購編號 " + poNo + " 的請款單，不能重複拋轉。若要重拋，請先作廢那張請款單。");
  }
  if (vendor === "") { return _payFail("採購單沒有擬定廠商，無法拋轉請款單。"); }

  // ── 讀子表（跳過料號空白的部門小計列）＋檢核 ─────────────────────────
  var size = src.getSubtableSize(PO42P.SUB);
  var lines = [], problems = [], total = 0;
  for (var i = 0; i < size; i++) {
    var code = _pt(src.getSubtableFieldValue(PO42P.SUB, i, PO42P.S_ITEM_CODE));
    if (code === "") { continue; }
    var name = _pt(src.getSubtableFieldValue(PO42P.SUB, i, PO42P.S_ITEM_NAME));
    var qty = _pn(src.getSubtableFieldValue(PO42P.SUB, i, PO42P.S_QTY));
    var price = _pn(src.getSubtableFieldValue(PO42P.SUB, i, PO42P.S_PRICE));
    var label = "第 " + (i + 1) + " 列 " + code + " " + name;
    if (!qty) { problems.push(label + "：數量不可為 0 或空白"); }
    if (!price) { problems.push(label + "：單價不可為 0 或空白"); }
    var dept = _pt(src.getSubtableFieldValue(PO42P.SUB, i, PO42P.S_DEPT));
    var note = _pt(src.getSubtableFieldValue(PO42P.SUB, i, PO42P.S_NOTE));
    var amount = _pn(src.getSubtableFieldValue(PO42P.SUB, i, PO42P.S_AMOUNT));
    if (!amount) { problems.push(label + "：擬定廠商金額不可為 0 或空白"); amount = 0; }
    total += amount;
    lines.push({
      dept: dept, code: code,
      name: name, qty: qty, price: price, unit: _pt(src.getSubtableFieldValue(PO42P.SUB, i, PO42P.S_UNIT)),
      // 43 子表沒有部門／料號欄，放進品項備註保留追溯
      note: dept + "｜" + code + (note ? "｜" + note : ""),
      amount: Math.round(amount * 100) / 100
    });
  }
  if (lines.length === 0) { return _payFail("這張採購單沒有品項，無法拋轉請款單。"); }
  if (problems.length > 0) {
    return _payFail("檢核未通過，未建立請款單。請修正下列 " + problems.length + " 項後再按一次：\n" + problems.join("\n"));
  }

  // ── 建立 43 ───────────────────────────────────────────────────────
  var now = _taipei();
  var payPrefix = PAY_NO_PREFIX + _ym(now);
  var paySerial = _maxPaySerial(payPrefix) + 1;
  var payNoWanted = payPrefix + _padN(paySerial, 5);

  var pay = db.getAPIQuery(PAY43.path).insertAPIEntry();
  pay.setFieldValue(PAY43.F_NO, payNoWanted);
  pay.setFieldValue(PAY43.F_DEPT, PAY_DEFAULTS.dept);
  pay.setFieldValue(PAY43.F_DATE, _ymd(now));
  pay.setFieldValue(PAY43.F_REASON, period + " " + cycle + " 週期採購請款（" + company + "／" + vendor + "）採購單 " + poNo);
  pay.setFieldValue(PAY43.F_ACCOUNT, PAY_DEFAULTS.account);
  pay.setFieldValue(PAY43.F_PAY_TYPE, PAY_DEFAULTS.payType);
  pay.setFieldValue(PAY43.F_PAY_DATE, _payDate(terms, now));
  pay.setFieldValue(PAY43.F_PAYEE, vendor);
  pay.setFieldValue(PAY43.F_PO_NO, poNo);
  pay.setFieldValue(PAY43.F_PERIOD_PO, poNo);
  pay.setFieldValue(PAY43.F_TAX_INCL, "No");
  if (applicant) { pay.setFieldValue(PAY43.F_APPLICANT, applicant); }
  pay.setFieldValue(PAY43.F_NOTE, "由週期採購單 " + poNo + " 拋轉" + reissue + (sourceNo ? "（來源請購單 " + sourceNo + "）" : "") +
                    "；付款條件：" + (terms || "未填"));

  // 依部門排序，每個部門最後插一列「XX部 小計」
  lines.sort(function (a, b) {
    var da = a.dept || "￿", dbb = b.dept || "￿";
    if (da !== dbb) { return da < dbb ? -1 : 1; }
    return a.code < b.code ? -1 : (a.code > b.code ? 1 : 0);
  });
  var rows = [], curDept = null, running = 0;
  for (var q = 0; q < lines.length; q++) {
    if (curDept !== null && lines[q].dept !== curDept && curDept !== "") {
      rows.push({ subtotal: true, name: curDept + " 小計", amount: Math.round(running * 100) / 100 });
      running = 0;
    }
    curDept = lines[q].dept;
    rows.push(lines[q]);
    running += lines[q].amount;
  }
  if (curDept !== null && curDept !== "") {
    rows.push({ subtotal: true, name: curDept + " 小計", amount: Math.round(running * 100) / 100 });
  }

  var n = rows.length;
  for (var r = 0; r < n; r++) {
    var key = -(n - r);          // 負數 key：絕對值大的排前面
    var row = rows[r];
    pay.setSubtableFieldValue(PAY43.S_NAME, key, row.name);
    pay.setSubtableFieldValue(PAY43.S_AMOUNT, key, String(row.amount));
    if (!row.subtotal) {
      pay.setSubtableFieldValue(PAY43.S_PRICE, key, String(row.price));
      pay.setSubtableFieldValue(PAY43.S_RECV_QTY, key, String(row.qty));
      pay.setSubtableFieldValue(PAY43.S_QTY, key, String(row.qty));
      pay.setSubtableFieldValue(PAY43.S_UNIT, key, row.unit);
      pay.setSubtableFieldValue(PAY43.S_NOTE, key, row.note);
    }
  }
  pay.recalculateAllFormulas();   // 小計／營業稅／總計／總金額／大寫金額
  pay.save();

  // save() 後自動編號要重新讀一次才拿得到真正的號碼
  var saved = db.getAPIQuery(PAY43.path).getAPIEntry(pay.getRootNodeId());
  var payNo = _pt(saved.getFieldValue(PAY43.F_NO));
  if (payNo === "" || payNo.indexOf("{") >= 0) { payNo = payNoWanted; }

  // 核對 43「小計」＝品項合計（部門小計沒被重複計入）
  var itemTotal = Math.round(total * 100) / 100;
  var sub43 = _pn(saved.getFieldValue(PAY43.F_SUBTOTAL));
  var subWarn = "";
  if (sub43 !== null && Math.abs(sub43 - itemTotal) > 0.01) {
    subWarn = "\n⚠️ 43「小計」為 " + sub43 + "，但 42 擬定廠商金額合計為 " + itemTotal +
              "。請確認 43「實際收貨金額」公式與「實際驗收數量」設定，以及 42 金額是否等於數量×單價。";
  }

  if (payNo !== payNoWanted) {
    subWarn += "\n⚠️ 43 管請編號實際存為 " + payNo + "，與程式產生的 " + payNoWanted + " 不同，請檢查該欄位是否為自動編號。";
  }

  src.setFieldValue(PO42P.F_PAY_NO, payNo);
  src.save();

  response.setStatus("SUCCESS");
  response.setMessage("[" + PAY_VERSION + "] 已由採購單 " + poNo + " 建立週期請款單 " + payNo + reissue +
                      "：" + lines.length + " 項，未稅合計 " + itemTotal +
                      "，付款日期 " + _payDate(terms, now) + subWarn);
}
