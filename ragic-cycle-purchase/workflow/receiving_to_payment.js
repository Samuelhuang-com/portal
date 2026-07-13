// receiving_to_payment.js v1.0
// 功能：驗收單完成後，產生請款單（異常驗收需授權）
// 觸發位置：週期採購驗收單 / Action Button「產生請款單」
// 輸入：驗收單記錄
// 輸出：新增請款單，費用分攤明細須手動填寫
// 前置檢查：
//   1. 驗收狀態必須為「驗收完成」或授權放行的「驗收異常」
//   2. 驗收異常時自動寫入異常紀錄
//   3. 不可重複產生請款單

var VERSION = "v1.0";
var ICON = "💰";

var recvNo = record["驗收單號"];
var poNo = record["採購單號"];
var status = record["狀態"];
var details = record["驗收明細"] || [];

if (status === "待驗收") {
    return setErrorMessage(ICON + " [" + VERSION + "] 驗收尚未完成，無法產生請款單。");
}

if (status === "驗收異常") {
    // 寫入異常紀錄
    createRecord("cycle_purchase_audit", {
        "關聯類型": "驗收單",
        "關聯單號": recvNo,
        "事件類型": "驗收差異",
        "說明": "驗收異常授權放行產生請款單",
        "操作人員": currentUser(),
        "建立時間": new Date().toISOString()
    });
}

// 確認未重複產生
var existing = getRecords("cycle_purchase_payment", { "驗收單號": recvNo });
if (existing && existing.length > 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 此驗收單已建立請款單（" + existing[0]["請款單號"] + "），請勿重複操作。");
}

// 計算驗收總金額（從採購單取單價）
var po = getRecord("cycle_purchase_po", poNo);
var totalAmount = 0;
if (po) {
    var poDetails = po["採購明細"] || [];
    for (var i = 0; i < details.length; i++) {
        for (var j = 0; j < poDetails.length; j++) {
            if (details[i]["料號"] === poDetails[j]["料號"]) {
                totalAmount += (parseFloat(details[i]["驗收數量"]) || 0) * (parseFloat(poDetails[j]["單價"]) || 0);
                break;
            }
        }
    }
}

var paymentData = {
    "驗收單號": recvNo,
    "發票金額": totalAmount,
    "狀態": "草稿"
};

var newPayment = createRecord("cycle_purchase_payment", paymentData);
if (!newPayment) {
    return setErrorMessage(ICON + " [" + VERSION + "] 請款單建立失敗。");
}

console.log(ICON + " [" + VERSION + "] 請款單已建立：" + newPayment["請款單號"] + "，金額：" + totalAmount);
return setSuccessMessage(ICON + " 請款單已建立：" + newPayment["請款單號"] + "，請財務人員填寫發票資訊與費用分攤。");
