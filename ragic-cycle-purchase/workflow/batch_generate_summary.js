// batch_generate_summary.js v1.0
// 功能：批次 → 彙整所有已核准請購單，依料號+供應商產生彙整單
// 觸發位置：週期採購批次 / Action Button「產生彙整單」
// 輸入：批次記錄
// 輸出：依料號+供應商對應新增彙整單記錄（需求總量=各請購單合計）
// 前置檢查：
//   1. 批次下至少有一張「已核准」請購單
//   2. 每個料號+供應商組合不可重複產生彙整

var VERSION = "v1.0";
var ICON = "📊";

var batchNo = record["批次號"];

// 取得此批次所有「已核准」的請購單
var requests = getRecords("cycle_purchase_requests", {
    "批次號": batchNo,
    "狀態": "已核准"
});

if (!requests || requests.length === 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 此批次下沒有「已核准」的請購單，無法產生彙整單。");
}

// 彙整各料號的需求數量 (key = 料號)
var qtyMap = {};
for (var i = 0; i < requests.length; i++) {
    var details = requests[i]["請購明細"] || [];
    for (var j = 0; j < details.length; j++) {
        var itemNo = details[j]["統購料號"];
        var qty = parseFloat(details[j]["請購數量"]) || 0;
        if (qty <= 0) continue;
        if (!qtyMap[itemNo]) {
            qtyMap[itemNo] = { total: 0, name: details[j]["品名"] };
        }
        qtyMap[itemNo].total += qty;
    }
}

if (Object.keys(qtyMap).length === 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 所有請購數量皆為0，無需產生彙整單。");
}

// 取得料號對應供應商
var createdCount = 0;
for (var itemNo in qtyMap) {
    var mappings = getRecords("cycle_purchase_item_mapping", { "料號": itemNo });
    if (!mappings || mappings.length === 0) {
        console.warn(ICON + " [" + VERSION + "] 料號 " + itemNo + " 無供應商對照，略過。");
        continue;
    }
    var supplierCode = mappings[0]["供應商代碼"];

    // 防止重複
    var existing = getRecords("cycle_purchase_summary", {
        "批次號": batchNo,
        "料號": itemNo
    });
    if (existing && existing.length > 0) {
        console.warn(ICON + " [" + VERSION + "] 料號 " + itemNo + " 彙整單已存在，略過。");
        continue;
    }

    createRecord("cycle_purchase_summary", {
        "批次號": batchNo,
        "料號": itemNo,
        "供應商代碼": supplierCode,
        "需求總量": qtyMap[itemNo].total,
        "調整量": qtyMap[itemNo].total,
        "狀態": "草稿"
    });
    createdCount++;
}

// 更新所有已核准請購單狀態為「已彙整」
for (var r = 0; r < requests.length; r++) {
    updateRecord("cycle_purchase_requests", requests[r]["請購單號"], { "狀態": "已彙整" });
}

console.log(ICON + " [" + VERSION + "] 彙整單產生完成，共 " + createdCount + " 筆。");
return setSuccessMessage(ICON + " 彙整單已產生 " + createdCount + " 筆，請購單狀態已更新為「已彙整」。");
