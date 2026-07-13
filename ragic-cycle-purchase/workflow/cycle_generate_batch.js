// cycle_generate_batch.js v1.0
// 功能：週期採購週期設定 → 自動產生批次
// 觸發位置：週期採購週期設定 / Action Button「產生批次」
// 輸入：週期設定記錄 (cycle_id, cycle_name, frequency, open_date, close_date, applicable_units)
// 輸出：新增一筆週期採購批次記錄
// 前置檢查：
//   1. 狀態必須為「啟用」
//   2. 同一週期同一期間不可重複產生批次

var VERSION = "v1.0";
var ICON = "🔄";

// 取得目前週期設定欄位
var cycleId = record["週期ID"];
var cycleName = record["週期名稱"];
var openDate = record["開放起始日"];
var closeDate = record["截止日"];
var status = record["狀態"];

if (status !== "啟用") {
    return setErrorMessage(ICON + " [" + VERSION + "] 此週期狀態非啟用，無法產生批次。");
}

if (!openDate || !closeDate) {
    return setErrorMessage(ICON + " [" + VERSION + "] 請填寫開放起始日與截止日。");
}

// 防止重複產生：查詢是否已有相同週期+相同日期的批次
var existing = getRecords("cycle_purchase_batches", {
    "週期ID": cycleId,
    "開放日期": openDate
});

if (existing && existing.length > 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 此週期此期間已存在批次（" + existing[0]["批次號"] + "），請勿重複產生。");
}

// 新增批次記錄
var batchData = {
    "週期ID": cycleId,
    "批次名稱": cycleName + "_" + openDate,
    "開放日期": openDate,
    "截止日期": closeDate,
    "是否已產生請購": false,
    "狀態": "開放"
};

var newBatch = createRecord("cycle_purchase_batches", batchData);

if (!newBatch) {
    return setErrorMessage(ICON + " [" + VERSION + "] 批次產生失敗，請聯絡系統管理員。");
}

console.log(ICON + " [" + VERSION + "] 批次產生成功：" + newBatch["批次號"]);
return setSuccessMessage(ICON + " 批次已產生：" + newBatch["批次號"]);
