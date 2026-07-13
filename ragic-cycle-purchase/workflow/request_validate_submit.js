// request_validate_submit.js v1.0
// 功能：請購單送出前驗證，驗證通過後狀態改為「已送出」
// 觸發位置：週期採購請購單 / Before Submit
// 輸入：請購單記錄
// 輸出：更新狀態為「已送出」；驗證失敗則阻止送出
// 前置檢查：
//   1. 批次截止日未逾期
//   2. 請購數量不可有空白（必須填 0 表示不購）
//   3. 若批次已關閉則不可送出

var VERSION = "v1.0";
var ICON = "✅";

var requestNo = record["請購單號"];
var batchNo = record["批次號"];
var status = record["狀態"];
var details = record["請購明細"] || [];

if (status === "已送出" || status === "簽核中" || status === "已核准") {
    return setErrorMessage(ICON + " [" + VERSION + "] 此請購單已送出，請勿重複操作。");
}

// 檢查批次狀態
var batches = getRecords("cycle_purchase_batches", { "批次號": batchNo });
if (!batches || batches.length === 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 找不到對應批次。");
}
var batch = batches[0];

if (batch["狀態"] === "關閉" || batch["狀態"] === "完成") {
    return setErrorMessage(ICON + " [" + VERSION + "] 批次已關閉，無法送出請購單。請申請補填。");
}

var today = new Date().toISOString().split("T")[0];
if (batch["截止日期"] < today) {
    return setErrorMessage(ICON + " [" + VERSION + "] 批次已逾截止日（" + batch["截止日期"] + "），請申請補填。");
}

// 檢查請購明細：不允許空白數量
for (var i = 0; i < details.length; i++) {
    var qty = details[i]["請購數量"];
    if (qty === null || qty === undefined || qty === "") {
        return setErrorMessage(ICON + " [" + VERSION + "] 第 " + (i + 1) + " 筆料號「" + details[i]["品名"] + "」請購數量不可為空白（填0表示不購）。");
    }
}

// 驗證通過，更新狀態
record["狀態"] = "已送出";
record["送出時間"] = today;

console.log(ICON + " [" + VERSION + "] 請購單 " + requestNo + " 驗證通過，已送出。");
return true;
