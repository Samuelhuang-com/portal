/**
 * cycle_po57_to_payment59.js  v1.3  (2026-09-30)
 *
 * Ragic 伺服器端 JavaScript Workflow ——「★週採採購單」(sheet 57) 的「拋轉請款單」按鈕
 * 把一張 57 週期採購單拋成一張「★週期請款單」(sheet 59)，並把請款單號寫回 57「請款單號」。
 *
 * 規則（Samuel 2026-09-28 裁示）：
 *   · 一張 57 → 一張 59（57 本來就是一家廠商一張）
 *   · 59 會科：固定「雜項購置」（主表單選必填；57 逐列的會計課目代碼對不上 59 選項）
 *   · 59 付款日期：依 57「1.付款條件」推算 —— 月結30/45/60天＝拋轉當月月底 + N 天；付現＝拋轉當天
 *   · 不檢查驗收；品項沒數量／沒單價 → 跳 Error，不建立請款單
 *   · 防重複：59 裡還找得到 57「請款單號」那張單，或 59 已有同一採購編號的請款單 → 擋下
 *     v1.2：57「請款單號」有值但那張 59 已被刪除 → 視為可重拋（新單號會覆蓋舊值）
 *   · 57 的「XX部 小計」列（料號空白）不直接複製；v1.1 起由本程式依部門重算，
 *     每個部門最後插一列「XX部 小計」（產品名稱＝「XX部 小計」、數量空白、擬定廠商金額＝部門小計）
 *
 * v1.3（Samuel 2026-09-30 裁示）59 子表新版型：
 *   品項列：單價(F)＝57 擬定廠商單價、廠商金額(G)＝57 擬定廠商金額、實際驗收數量(H)＝57 數量（預帶，驗收時人工改）
 *           實際收貨金額(I) 是 Ragic 公式 H7*F7，程式不寫
 *   部門小計列：產品名稱「XX部 小計」、廠商金額(G)＝部門廠商金額合計、收貨小計＝部門實際收貨金額合計（拋轉當下；之後人工改）
 *   59 主表「小計」＝I 加總；小計列沒有數量／單價，I＝0，不會重複計入
 *
 * （以下 v1.1 說明已不適用 —— 59 子表欄位已改版）
 * ⚠️ v1.1 前提：59 子表「擬定廠商金額(未稅)」G7 公式要改成
 *        IF(C7.RAW='', 0, IF(E11.RAW = "Yes", ROUND(F7/1.05), F7))
 *     （數量空白＝小計列 → 0），主表「小計」＝G7 加總才不會把部門小計重複算進去。
 *     程式存檔後會核對 59「小計」是否等於品項合計，不相等會在訊息裡警告。
 *
 * 59 必填欄位全部由本程式填入：申請部門、申請日期、事由、會科、付款種類、付款日期；
 * 總金額／大寫金額是 Ragic 公式，存檔前 recalculateAllFormulas() 算出。
 *
 * 安裝（57 設計模式）：
 *   1. JavaScript Workflow → 下拉選 57「★週採採購單」→ Installed Sheet Scope → 貼到最後面 → 儲存
 *   2. 表單設定 → 動作按鈕：把舊「拋轉請款單」刪除（或隱藏），新增 JS Workflow 按鈕
 *        名稱：拋轉請款單      動作：convertCyclePOToPayment({id})
 *
 * ⚠️ Ragic 伺服器端是 ES5：只能用 var／function。
 */

var PAY_VERSION = "v1.3";

var PO57P = {
  path: "/community-management-department/57",
  F_PO_NO: 1020773,      // 採購編號
  F_PERIOD: 1020774,     // 期別
  F_APPLICANT: 1020776,  // 申請人
  F_VENDOR: 1020778,     // 擬定廠商
  F_TERMS: 1020789,      // 1.付款條件（月結30天/月結45天/月結60天/付現）
  F_COMPANY: 1020793,    // 公司別
  F_CYCLE: 1020794,      // 週期名稱
  F_SOURCE_NO: 1020941,  // 來源請購單號
  F_PAY_NO: 1021009,     // 57「請款單號」（回寫 59 管請編號）
  SUB: 1020792,
  S_ITEM_CODE: "1020798",
  S_ITEM_NAME: "1020780",
  S_QTY: "1020781",
  S_UNIT: "1020782",
  S_NOTE: "1020783",
  S_AMOUNT57: "1020785",   // 擬定廠商金額（v1.3：直接拋到 59「廠商金額」）
  S_PRICE: "1020784",
  S_DEPT: "1020799"
};

var PAY59 = {
  path: "/community-management-department/59",
  F_NO: 1020944,          // 管請編號（自動編號）
  F_NO_ALT: 1020955,      // 付款編號（若自動編號設在這欄）
  F_DEPT: 1020945,        // 申請部門（必填，單選：營業/行銷/管理/資訊/執董室/財務）
  F_DATE: 1020946,        // 申請日期（必填）
  F_REASON: 1020947,      // 事由（必填，標題欄）
  F_PAYEE: 1020949,       // 受款者
  F_PAY_DATE: 1020950,    // 付款日期（必填）
  F_ACCOUNT: 1020956,     // 會科（必填，單選）
  F_PO_NO: 1020957,       // 採購編號
  F_APPLICANT: 1020959,   // 申請人
  F_PAY_TYPE: 1020960,    // 付款種類（必填：匯款/零用金/自動扣繳）
  F_TAX_INCL: 1020969,    // 項目金額為(含稅)：No＝子表金額是未稅
  F_NOTE: 1020986,        // 備註
  F_SUBTOTAL: 1020972,    // 小計（＝G7 加總，用來核對部門小計沒有被重複計入）
  SUB: 1021007,
  S_NAME: 1020963,
  S_QTY: 1020964,
  S_UNIT: 1020965,
  S_NOTE: 1020966,
  S_PRICE: 1020967,       // 單價（v1.3）
  S_AMOUNT: 1020968,      // 廠商金額（v1.3：＝57 擬定廠商金額；小計列＝部門合計）
  S_RECV_QTY: 1021011,    // 實際驗收數量（v1.3：預帶 57 數量，驗收時人工改）
  S_RECV_SUB: null        // ⚠️ v1.3「收貨小計」欄位代號：Ragic 建好後填入（null＝不寫）
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
function _taipei() { return new Date(new Date().getTime() + 8 * 3600 * 1000); }   // 讀 getUTC* 即台北時間
function _ymd(d) { return d.getUTCFullYear() + "/" + _p2(d.getUTCMonth() + 1) + "/" + _p2(d.getUTCDate()); }
function _payDate(terms, now) {
  var m = _pt(terms).match(/月結\s*(\d+)\s*天/);
  if (!m) { return _ymd(now); }                         // 付現或空白：當天
  var monthEnd = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 0));
  return _ymd(new Date(monthEnd.getTime() + parseInt(m[1], 10) * 86400000));
}
function _payFail(msg) { response.setStatus("ERROR"); response.setMessage(msg); }

function convertCyclePOToPayment(recordId) {
  var src = db.getAPIQuery(PO57P.path).getAPIEntry(recordId);
  if (!src) { return _payFail("找不到這張週期採購單（id=" + recordId + "）"); }

  var poNo = _pt(src.getFieldValue(PO57P.F_PO_NO));
  var vendor = _pt(src.getFieldValue(PO57P.F_VENDOR));
  var period = _pt(src.getFieldValue(PO57P.F_PERIOD));
  var company = _pt(src.getFieldValue(PO57P.F_COMPANY));
  var cycle = _pt(src.getFieldValue(PO57P.F_CYCLE));
  var terms = _pt(src.getFieldValue(PO57P.F_TERMS));
  var applicant = _pt(src.getFieldValue(PO57P.F_APPLICANT));
  var sourceNo = _pt(src.getFieldValue(PO57P.F_SOURCE_NO));

  // ── 防重複 ─────────────────────────────────────────────────────────
  var oldPayNo = PO57P.F_PAY_NO ? _pt(src.getFieldValue(PO57P.F_PAY_NO)) : "";
  var reissue = "";
  if (oldPayNo !== "") {
    // v1.2：確認記錄的那張 59 是否還在；已刪除就允許重拋
    var eq = db.getAPIQuery(PAY59.path);
    eq.addFilter(PAY59.F_NO, "=", oldPayNo);
    var still = eq.getAPIResultList();
    if (still && still.length > 0) {
      return _payFail("這張採購單已經拋轉過請款單（" + oldPayNo + "），而且該請款單仍存在，不能重複拋轉。" +
                      "若要重拋，請先刪除請款單 " + oldPayNo + " 再按一次。");
    }
    reissue = "（原請款單 " + oldPayNo + " 已不存在，本次為重新拋轉）";
  }
  var dq = db.getAPIQuery(PAY59.path);
  dq.addFilter(PAY59.F_PO_NO, "=", poNo);
  var dup = dq.getAPIResultList();
  if (dup && dup.length > 0) {
    return _payFail("週期請款單裡已經有採購編號 " + poNo + " 的請款單，不能重複拋轉。若要重拋，請先作廢那張請款單。");
  }
  if (vendor === "") { return _payFail("採購單沒有擬定廠商，無法拋轉請款單。"); }

  // ── 讀子表（跳過料號空白的部門小計列）＋檢核 ─────────────────────────
  var size = src.getSubtableSize(PO57P.SUB);
  var lines = [], problems = [], total = 0;
  for (var i = 0; i < size; i++) {
    var code = _pt(src.getSubtableFieldValue(PO57P.SUB, i, PO57P.S_ITEM_CODE));
    if (code === "") { continue; }
    var name = _pt(src.getSubtableFieldValue(PO57P.SUB, i, PO57P.S_ITEM_NAME));
    var qty = _pn(src.getSubtableFieldValue(PO57P.SUB, i, PO57P.S_QTY));
    var price = _pn(src.getSubtableFieldValue(PO57P.SUB, i, PO57P.S_PRICE));
    var label = "第 " + (i + 1) + " 列 " + code + " " + name;
    if (!qty) { problems.push(label + "：數量不可為 0 或空白"); }
    if (!price) { problems.push(label + "：單價不可為 0 或空白"); }
    var dept = _pt(src.getSubtableFieldValue(PO57P.SUB, i, PO57P.S_DEPT));
    var note = _pt(src.getSubtableFieldValue(PO57P.SUB, i, PO57P.S_NOTE));
    // v1.3：金額直接取 57「擬定廠商金額」
    var amount = _pn(src.getSubtableFieldValue(PO57P.SUB, i, PO57P.S_AMOUNT57));
    if (!amount) { problems.push(label + "：擬定廠商金額不可為 0 或空白"); amount = 0; }
    total += amount;
    lines.push({
      dept: dept, code: code,
      name: name, qty: qty, price: price, unit: _pt(src.getSubtableFieldValue(PO57P.SUB, i, PO57P.S_UNIT)),
      // 59 子表沒有部門／料號欄，放進品項備註保留追溯
      note: dept + "｜" + code + (note ? "｜" + note : ""),
      amount: Math.round(amount * 100) / 100
    });
  }
  if (lines.length === 0) { return _payFail("這張採購單沒有品項，無法拋轉請款單。"); }
  if (problems.length > 0) {
    return _payFail("檢核未通過，未建立請款單。請修正下列 " + problems.length + " 項後再按一次：\n" + problems.join("\n"));
  }

  // ── 建立 59 ───────────────────────────────────────────────────────
  var now = _taipei();
  var pay = db.getAPIQuery(PAY59.path).insertAPIEntry();
  pay.setFieldValue(PAY59.F_DEPT, PAY_DEFAULTS.dept);
  pay.setFieldValue(PAY59.F_DATE, _ymd(now));
  pay.setFieldValue(PAY59.F_REASON, period + " " + cycle + " 週期採購請款（" + company + "／" + vendor + "）採購單 " + poNo);
  pay.setFieldValue(PAY59.F_ACCOUNT, PAY_DEFAULTS.account);
  pay.setFieldValue(PAY59.F_PAY_TYPE, PAY_DEFAULTS.payType);
  pay.setFieldValue(PAY59.F_PAY_DATE, _payDate(terms, now));
  pay.setFieldValue(PAY59.F_PAYEE, vendor);
  pay.setFieldValue(PAY59.F_PO_NO, poNo);
  pay.setFieldValue(PAY59.F_TAX_INCL, "No");
  if (applicant) { pay.setFieldValue(PAY59.F_APPLICANT, applicant); }
  pay.setFieldValue(PAY59.F_NOTE, "由週期採購單 " + poNo + " 拋轉" + reissue + (sourceNo ? "（來源請購單 " + sourceNo + "）" : "") +
                    "；付款條件：" + (terms || "未填"));
  // v1.1：依部門排序，每個部門最後插一列「XX部 小計」
  lines.sort(function (a, b) {
    var da = a.dept || "\uffff", dbb = b.dept || "\uffff";
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
    pay.setSubtableFieldValue(PAY59.S_NAME, key, row.name);
    pay.setSubtableFieldValue(PAY59.S_AMOUNT, key, String(row.amount));
    if (row.subtotal) {
      // 收貨小計＝拋轉當下的實際收貨金額合計（實際驗收數量預帶 57 數量，所以＝部門廠商金額合計）
      if (PAY59.S_RECV_SUB) { pay.setSubtableFieldValue(PAY59.S_RECV_SUB, key, String(row.amount)); }
    } else {
      pay.setSubtableFieldValue(PAY59.S_PRICE, key, String(row.price));
      pay.setSubtableFieldValue(PAY59.S_RECV_QTY, key, String(row.qty));
      pay.setSubtableFieldValue(PAY59.S_QTY, key, String(row.qty));
      pay.setSubtableFieldValue(PAY59.S_UNIT, key, row.unit);
      pay.setSubtableFieldValue(PAY59.S_NOTE, key, row.note);
    }
  }
  pay.recalculateAllFormulas();   // 小計／營業稅／總計／總金額／大寫金額
  pay.save();

  // save() 後自動編號要重新讀一次才拿得到真正的號碼
  var saved = db.getAPIQuery(PAY59.path).getAPIEntry(pay.getRootNodeId());
  var payNo = _pt(saved.getFieldValue(PAY59.F_NO));
  if (payNo === "" || payNo.indexOf("{") >= 0) { payNo = _pt(saved.getFieldValue(PAY59.F_NO_ALT)); }
  if (payNo === "" || payNo.indexOf("{") >= 0) { payNo = "59/" + pay.getRootNodeId(); }

  // v1.1：核對 59「小計」＝品項合計（部門小計沒被重複計入）
  var itemTotal = Math.round(total * 100) / 100;
  var sub59 = _pn(saved.getFieldValue(PAY59.F_SUBTOTAL));
  var subWarn = "";
  if (sub59 !== null && Math.abs(sub59 - itemTotal) > 0.01) {
    subWarn = "\n⚠️ 59「小計」為 " + sub59 + "，但 57 擬定廠商金額合計為 " + itemTotal +
              "。請確認 59「實際收貨金額」公式為 H7*F7、「實際驗收數量」不是公式，以及 57 金額是否等於數量×單價。";
  }

  if (PO57P.F_PAY_NO) {
    src.setFieldValue(PO57P.F_PAY_NO, payNo);
    src.save();
  }

  response.setStatus("SUCCESS");
  response.setMessage("[" + PAY_VERSION + "] 已由採購單 " + poNo + " 建立週期請款單 " + payNo + reissue +
                      "：" + lines.length + " 項，未稅合計 " + (Math.round(total * 100) / 100) +
                      "，付款日期 " + _payDate(terms, now) + subWarn +
                      (PO57P.F_PAY_NO ? "" : "\n⚠️ 57 尚未設定「請款單號」欄位，單號未回寫。"));
}
