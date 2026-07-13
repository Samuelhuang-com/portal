// po_to_receiving.js v1.0
// 功能：採購單到貨後，產生驗收單
// 觸發位置：週期採購採購單 / Action Button「產生驗收單」
// 輸入：採購單記錄
// 輸出：新增驗收單（含採購明細複製為驗收明細，驗收數量預設0）
// 前置檢查：
//   1. 採購單狀態為「已發出」或「部分到貨」
//   2. 此次不重複產生相同採購單的驗收單（每次到貨可產生一張）

var VERSION = "v1.0";
var ICON = "📦";

var poNo = record["採購單號"];
var status = record["狀態"];
var details = record["採購明細"] || [];

if (status !== "已發出" && status !== "部分到貨") {
    return setErrorMessage(ICON + " [" + VERSION + "] 採購單狀態（" + status + "）不符合，需為「已發出」或「部分到貨」。");
}

if (details.length === 0) {
    return setErrorMessage(ICON + " [" + VERSION + "] 採購單無明細，無法產生驗收單。");
}

// 複製採購明細為驗收明細，驗收數量設為訂購數量（讓驗收人員核實）
var recvDetails = [];
for (var i = 0; i < details.length; i++) {
    recvDetails.push({
        "料號": details[i]["料號"],
        "驗收數量": details[i]["訂購數量"],
        "發票數量": 0
    });
}

var today = new Date().toISOString().split("T")[0];
var recvData = {
    "採購單號": poNo,
    "驗收日期": today,
    "狀態": "待驗收",
    "驗收明細": recvDetails
};

var newRecv = createRecord("cycle_purchase_receiving", recvData);
if (!newRecv) {
    return setErrorMessage(ICON + " [" + VERSION + "] 驗收單建立失敗。");
}

// 更新採購單狀態
updateRecord("cycle_purchase_po", poNo, { "狀態": "部分到貨" });

console.log(ICON + " [" + VERSION + "] 驗收單已建立：" + newRecv["驗收單號"]);
return setSuccessMessage(ICON + " 驗收單已建立：" + newRecv["驗收單號"] + "，請驗收人員確認數量與發票。");
