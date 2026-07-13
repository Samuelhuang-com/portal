// batch_generate_requests.js v1.0
// 功能：週期採購批次 → 為各適用單位產生請購單（含預載料號，數量預設0）
// 觸發位置：週期採購批次 / Action Button「產生各部門請購單」
// 輸入：批次記錄 (batch_no, cycle_id)
// 輸出：為每個適用部門新增一筆請購單，並預載料號主檔中的週期品
// 前置檢查：
//   1. 批次狀態必須為「開放」
//   2. 是否已產生請購 = false，避免重複
//   3. 週期設定的適用單位不可為空

var VERSION = "v1.0";
var ICON = "📋";

var batchNo = record["批次號"];
var cycleId = record["週期ID"];
var isGenerated = record["是否已產生請購"];
var batchStatus = record["狀態"];

if (batchStatus !== "開放") {
    return setErrorMessage(ICON + " [" + VERSION + "] 批次狀態非「開放」，無法產生請購單。");
}

if (isGenerated) {
    return setErrorMessage(ICON + " [" + VERSION + "] 此批次已產生過請購單（" + batchNo + "），請勿重複操作。");
}

// 取得週期設定的適用單位
var cycleRecords = getRecords("cycle_purchase_cycles", { "週期ID": cycleId });
if (!cycleRecords || cycleRecords.length === 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 找不到對應的週期設定。");
}
var applicableUnits = cycleRecords[0]["適用單位"];
if (!applicableUnits || applicableUnits.length === 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 週期設定的適用單位為空，無法產生請購單。");
}

// 取得所有週期採購料號（is_active=true, is_cycle_item=true）
var items = getRecords("cycle_purchase_items", {
    "是否啟用": true,
    "是否週期品": true
});
if (!items || items.length === 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 找不到有效的週期採購料號。");
}

var successCount = 0;
var units = applicableUnits.split ? applicableUnits.split(",") : applicableUnits;

for (var i = 0; i < units.length; i++) {
    var dept = units[i].trim();
    if (!dept) continue;

    var details = [];
    for (var j = 0; j < items.length; j++) {
        details.push({
            "統購料號": items[j]["料號"],
            "品名": items[j]["品名"],
            "單位": items[j]["單位"],
            "單價": 0,
            "請購數量": 0
        });
    }

    var requestData = {
        "批次號": batchNo,
        "請購部門": dept,
        "狀態": "待填",
        "請購明細": details
    };

    var newReq = createRecord("cycle_purchase_requests", requestData);
    if (newReq) successCount++;
}

// 更新批次：標記已產生請購
updateRecord("cycle_purchase_batches", batchNo, { "是否已產生請購": true });

console.log(ICON + " [" + VERSION + "] 共產生 " + successCount + " 張請購單。");
return setSuccessMessage(ICON + " 已為 " + successCount + " 個部門產生請購單（數量預設0）。");
