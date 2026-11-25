/**
 * cycle_po39_to_claim40.js  DRAFT  (2026-11-25)
 *
 * 台中版：Ragic 伺服器端 JavaScript Workflow ——「★週採採購單」(taichung-public-form/39)
 * 的「拋轉 週期請款」按鈕，把一張採購單拋轉成「★週期請款單」(taichung-public-form/40)。
 *
 * 規則：
 *   - 一張 39 採購單 → 一張 40 請款單（39 已依廠商拆單，所以不再拆）
 *   - 只拋品項列；39 的「XX部 小計」列（料號空白）不拋
 *   - 品項金額 = 數量 × 單價（39 的「擬定廠商單價」）
 *   - 40 的「週期採購單號」（1022778）記下 39 的採購編號；39 的「請款單號」（1022749）回寫 40 的管請編號
 *   - 防重複：40 已有相同「週期採購單號」，或 39 的「請款單號」已有值，就擋下
 *
 * ⚠️ 草稿狀態：尚未在 Ragic 測試。以下假設請你確認（都標在程式的 ASSUME 註解）：
 *   A1  40 的「申請部門」「會科」「受款者」的選項必須含有我們送的值，否則 Ragic 會退回
 *   A2  40 的「小計」「營業稅」「總計」若是公式，會由 recalculateAllFormulas 算出；若不是，程式會補值
 *   A3  40 沒有「料號」欄位，料號併入「品項備註」前面
 *   A4  「付款種類」「項目金額為(含稅)」「收貨人」「付款條件」不送，保留空白
 *   A5  回寫 39 的請款單號失敗不影響拋轉（40 已建立），會在回傳訊息中提示
 *
 * 安裝（Ragic 設計模式，taichung-public-form/39）：
 *   1. 表單設定 → JavaScript 工作流程 → 貼上本檔全部內容 → 儲存
 *      （依 2026-11-19 實測經驗，請確認貼在 Installed sheet scope；全域是否生效請實測）
 *   2. 表單設定 → 動作按鈕 → 「拋轉 週期請款」呼叫：convertPOToClaim({id})
 *
 * ⚠️ Ragic 伺服器端是 ES5（Rhino）：只能用 var／function，不可用箭頭函式、let/const、樣板字串。
 */

var PO39 = {
  path: "/taichung-public-form/39",
  F_NO: 1022744,         // 採購編號（台中週採00000）
  F_PERIOD: 1022745,     // 期別
  F_APPLICANT: 1022752,  // 申請人
  F_PURPOSE: 1022748,    // 用途說明
  F_VENDOR: 1022746,     // 擬定廠商
  F_CLAIM_NO: 1022749,   // 請款單號（回寫）
  F_SOURCE: 1022773,     // 來源請購單號
  SUB: 1022774,
  S_ITEM_CODE: 1022754,  // 料號
  S_ITEM_NAME: 1022755,  // 產品名稱
  S_QTY: 1022756,        // 數量
  S_UNIT: 1022757,       // 單位
  S_NOTE: 1022758,       // 品項備註
  S_PRICE: 1022759,      // 擬定廠商單價（小計列的小計金額也放這裡）
  S_AMOUNT: 1022760,     // 擬定廠商金額
  S_DEPT: 1022761,       // 部門
  S_ACCOUNT: 1022762     // 會計課目
};

var CL40 = {
  path: "/taichung-public-form/40",
  F_CLAIM_NO: 1022776,   // 管請編號（台中請yyyyMMdd000，自動）
  F_DEPT: 1022775,       // 申請部門  ASSUME A1
  F_ACCOUNT: 1022779,    // 會科      ASSUME A1
  F_PO_LINK: 1022778,    // 週期採購單號（記 39 採購編號）
  F_APPLY_DATE: 1022782, // 申請日期
  F_APPLICANT: 1022783,  // 申請人
  F_PURPOSE: 1022785,    // 事由
  F_PAYEE: 1022804,      // 受款者   ASSUME A1
  F_SUBTOTAL: 1022799,   // 小計
  F_TAX: 1022800,        // 營業稅
  F_TOTAL: 1022802,      // 總計
  SUB: 1022835,
  S_NAME: 1022788,       // 產品名稱
  S_QTY: 1022789,        // 數量
  S_UNIT: 1022790,       // 單位
  S_NOTE: 1022791,       // 品項備註（料號併入此欄前面）
  S_PRICE: 1022792,      // 單價
  S_AMOUNT: 1022793      // 廠商金額
};

var TAX_RATE = 0.05;

function _trim(v) { return (v === null || v === undefined) ? "" : String(v).replace(/^\s+|\s+$/g, ""); }
function _num(v) {
  var s = _trim(v).replace(/[,$\s]/g, "");
  if (s === "") { return null; }
  var n = parseFloat(s);
  return isNaN(n) ? null : n;
}
function _fmt(n) { return String(Math.round(n * 100) / 100); }
function _pad(n) { return (n < 10 ? "0" : "") + n; }
function _today() {
  var d = new Date();
  return d.getFullYear() + "/" + _pad(d.getMonth() + 1) + "/" + _pad(d.getDate());
}
function _fail(msg) {
  response.setStatus("ERROR");
  response.setMessage(msg);
}

function convertPOToClaim(recordId) {
  var src = db.getAPIQuery(PO39.path).getAPIEntry(recordId);
  if (!src) { return _fail("找不到這張採購單（id=" + recordId + "）"); }

  var poNo = _trim(src.getFieldValue(PO39.F_NO));
  var existingClaim = _trim(src.getFieldValue(PO39.F_CLAIM_NO));
  var vendor = _trim(src.getFieldValue(PO39.F_VENDOR));
  var applicant = _trim(src.getFieldValue(PO39.F_APPLICANT));
  var purpose = _trim(src.getFieldValue(PO39.F_PURPOSE));

  // ── 防重複 ─────────────────────────────────────────────────────────
  if (existingClaim !== "") {
    return _fail("這張採購單 " + poNo + " 已經拋轉過請款單（" + existingClaim + "），不能重複拋轉。");
  }
  var dupQ = db.getAPIQuery(CL40.path);
  dupQ.addFilter(CL40.F_PO_LINK, "=", poNo);
  var dup = dupQ.getAPIResultList();
  if (dup && dup.length > 0) {
    return _fail("這張採購單 " + poNo + " 已有 " + dup.length + " 張請款單，不能重複拋轉。");
  }

  // ── 讀品項列（跳過部門小計列：料號空白） ───────────────────────────
  var size = src.getSubtableSize(PO39.SUB);
  var lines = [];
  var problems = [];
  var firstDept = "";
  var firstAccount = "";
  for (var i = 0; i < size; i++) {
    var code = _trim(src.getSubtableFieldValue(PO39.SUB, i, PO39.S_ITEM_CODE));
    if (code === "") { continue; }   // 小計列或空白列
    var name = _trim(src.getSubtableFieldValue(PO39.SUB, i, PO39.S_ITEM_NAME));
    var qty = _num(src.getSubtableFieldValue(PO39.SUB, i, PO39.S_QTY));
    var price = _num(src.getSubtableFieldValue(PO39.SUB, i, PO39.S_PRICE));
    var dept = _trim(src.getSubtableFieldValue(PO39.SUB, i, PO39.S_DEPT));
    var acc = _trim(src.getSubtableFieldValue(PO39.SUB, i, PO39.S_ACCOUNT));
    var label = "第 " + (i + 1) + " 列 " + code + " " + name;
    if (qty === null || qty === 0) { problems.push(label + "：數量不可為 0 或空白"); }
    if (price === null || price === 0) { problems.push(label + "：單價不可為 0 或空白"); }
    if (firstDept === "" && dept !== "") { firstDept = dept; }
    if (firstAccount === "" && acc !== "") { firstAccount = acc; }
    lines.push({
      code: code, name: name, qty: qty || 0, price: price || 0,
      unit: _trim(src.getSubtableFieldValue(PO39.SUB, i, PO39.S_UNIT)),
      note: _trim(src.getSubtableFieldValue(PO39.SUB, i, PO39.S_NOTE))
    });
  }
  if (lines.length === 0) { return _fail("這張採購單沒有品項，無法拋轉請款單。"); }
  if (vendor === "") { problems.push("採購單沒有擬定廠商（受款者必填）"); }
  if (problems.length > 0) {
    return _fail("檢核未通過，未拋轉請款單。請修正下列 " + problems.length + " 項後再按一次：\n" + problems.join("\n"));
  }

  // ── 建立請款單 ─────────────────────────────────────────────────────
  var cl = db.getAPIQuery(CL40.path).insertAPIEntry();
  cl.setFieldValue(CL40.F_PO_LINK, poNo);
  cl.setFieldValue(CL40.F_APPLY_DATE, _today());
  if (applicant) { cl.setFieldValue(CL40.F_APPLICANT, applicant); }
  if (purpose) { cl.setFieldValue(CL40.F_PURPOSE, purpose); }
  if (firstDept) { cl.setFieldValue(CL40.F_DEPT, firstDept); }        // ASSUME A1
  if (firstAccount) { cl.setFieldValue(CL40.F_ACCOUNT, firstAccount); } // ASSUME A1
  cl.setFieldValue(CL40.F_PAYEE, vendor);                              // ASSUME A1

  var subtotal = 0;
  var total = lines.length;
  for (var r = 0; r < total; r++) {
    var key = -(total - r);
    var it = lines[r];
    var amt = it.qty * it.price;
    subtotal += amt;
    cl.setSubtableFieldValue(CL40.S_NAME, key, it.name);
    cl.setSubtableFieldValue(CL40.S_QTY, key, String(it.qty));
    cl.setSubtableFieldValue(CL40.S_UNIT, key, it.unit);
    cl.setSubtableFieldValue(CL40.S_NOTE, key, (it.code ? "料號 " + it.code + "；" : "") + it.note); // A3
    cl.setSubtableFieldValue(CL40.S_PRICE, key, _fmt(it.price));
    cl.setSubtableFieldValue(CL40.S_AMOUNT, key, _fmt(amt));
  }

  cl.recalculateAllFormulas();
  // ASSUME A2：若 40 的合計欄是公式，recalculate 已算好；若是空白，這裡補值
  if (_num(cl.getFieldValue(CL40.F_SUBTOTAL)) === null) { cl.setFieldValue(CL40.F_SUBTOTAL, _fmt(subtotal)); }
  if (_num(cl.getFieldValue(CL40.F_TAX)) === null) { cl.setFieldValue(CL40.F_TAX, _fmt(Math.round(subtotal * TAX_RATE))); }
  if (_num(cl.getFieldValue(CL40.F_TOTAL)) === null) {
    cl.setFieldValue(CL40.F_TOTAL, _fmt(subtotal + Math.round(subtotal * TAX_RATE)));
  }
  cl.save();

  var claimNo = _trim(cl.getFieldValue(CL40.F_CLAIM_NO));

  // ── 回寫 39 的請款單號（失敗不影響已建立的請款單） ─────────────────
  var writeBackMsg = "";
  try {
    src.setFieldValue(PO39.F_CLAIM_NO, claimNo);
    src.save();
  } catch (e) {
    writeBackMsg = "\n（注意：請款單已建立，但回寫採購單的「請款單號」失敗，請手動填入 " + claimNo + "）";
  }

  response.setStatus("SUCCESS");
  response.setMessage("已由採購單 " + poNo + " 拋轉請款單 " + claimNo + "（" + lines.length + " 項，小計 " + _fmt(subtotal) + "）" + writeBackMsg);
}
