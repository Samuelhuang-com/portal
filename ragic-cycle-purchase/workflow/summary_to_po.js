// summary_to_po.js v1.0
// 功能：彙整單 → 轉採購單
// 觸發位置：週期採購彙整單 / Action Button「轉採購單」
// 輸入：彙整單記錄（可多筆選取同供應商）
// 輸出：依供應商產生採購單，明細為彙整單中的料號+調整量
// 前置檢查：
//   1. 彙整單狀態必須為「草稿」
//   2. 調整量不可為0（0表示不採購，需手動刪除或確認）

var VERSION = "v1.0";
var ICON = "🛒";

var summaryNo = record["彙整單號"];
var itemNo = record["料號"];
var supplierCode = record["供應商代碼"];
var adjustedQty = parseFloat(record["調整量"]) || 0;
var status = record["狀態"];
var adjustReason = record["調整原因"];
var demandQty = parseFloat(record["需求總量"]) || 0;

if (status !== "草稿") {
    return setErrorMessage(ICON + " [" + VERSION + "] 此彙整單已轉採購單（狀態：" + status + "），請勿重複操作。");
}

if (adjustedQty <= 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 調整量為0，請確認是否需要採購，或刪除此彙整記錄。");
}

// 若調整量與需求量不同，調整原因必填
if (adjustedQty !== demandQty && (!adjustReason || adjustReason.trim() === "")) {
    return setErrorMessage(ICON + " [" + VERSION + "] 調整量（" + adjustedQty + "）與需求量（" + demandQty + "）不同，請填寫調整原因。");
}

// 取得料號對照表中的單價
var mappings = getRecords("cycle_purchase_item_mapping", {
    "料號": itemNo,
    "供應商代碼": supplierCode
});
var unitPrice = mappings && mappings.length > 0 ? parseFloat(mappings[0]["單價"]) || 0 : 0;

// 建立採購單
var poData = {
    "彙整單號": summaryNo,
    "供應商代碼": supplierCode,
    "採購人員": currentUser(),
    "狀態": "草稿",
    "採購明細": [{
        "料號": itemNo,
        "訂購數量": adjustedQty,
        "單價": unitPrice,
    }]
};

var newPO = createRecord("cycle_purchase_po", poData);
if (!newPO) {
    return setErrorMessage(ICON + " [" + VERSION + "] 採購單建立失敗。");
}

// 更新彙整單狀態
updateRecord("cycle_purchase_summary", summaryNo, { "狀態": "已轉採購單" });

console.log(ICON + " [" + VERSION + "] 採購單已建立：" + newPO["採購單號"]);
return setSuccessMessage(ICON + " 採購單已建立：" + newPO["採購單號"]);
