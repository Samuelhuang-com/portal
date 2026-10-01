/**
 * 廠商資料表 (community-management-department/15) 前置工作流程：重複建檔檢查  v1.0  2026-10-01
 *
 * 規則
 *  1. 統一編號（統編／身分證字號／流水號共用這一欄）：不可和其他筆相同；空白跳過
 *  2. 名稱：去掉空白與「股份有限公司／有限公司／(股)公司」後，不可和其他筆相同
 *  3. 修改既有資料時，只有該欄「有變動」才檢查（既有重複資料照樣可以改其他欄位）
 *  4. 排除自己這一筆
 *
 * 安裝：設計模式 → JavaScript 工作流程 → 前置工作流程 → 表單選「廠商資料表」→ 貼到最後面
 */
(function () {
  var VER = 'v1.0';
  var PATH = '/community-management-department/15';
  var F_CODE = 1004254;   // 廠商編號
  var F_NAME = 1004248;   // 名稱
  var F_TAX  = 1004250;   // 統一編號
  var CHECK_NAME = true;  // 不要檢查名稱就改成 false

  function normTax(v) { return (v == null ? '' : String(v)).replace(/[\s\-]/g, '').toUpperCase(); }
  function normName(v) {
    return (v == null ? '' : String(v)).replace(/\s/g, '')
      .replace(/[()（）]/g, '').replace(/股份有限公司|有限公司|股公司$|公司$/g, '');
  }
  function changed(fid, normFn) {
    var nv = normFn(param.getNewValue(fid));
    return nv && nv !== normFn(param.getOldValue(fid)) ? nv : '';
  }

  var selfId = param.getNewNodeId(F_NAME);   // 新增時為負值
  var taxNew = changed(F_TAX, normTax);
  var nameNew = CHECK_NAME ? changed(F_NAME, normName) : '';
  if (!taxNew && !nameNew) return;

  var q = db.getAPIQuery(PATH);
  q.setLimitSize(5000);
  var list = q.getAPIResultList();
  var msgs = [];

  for (var i = 0; i < list.length; i++) {
    var e = list[i];
    if (e.getRootNodeId() == selfId) continue;
    var who = e.getFieldValue(F_CODE) + ' ' + e.getFieldValue(F_NAME);
    if (taxNew && normTax(e.getFieldValue(F_TAX)) === taxNew)
      msgs.push('統一編號「' + taxNew + '」已存在：' + who);
    if (nameNew && normName(e.getFieldValue(F_NAME)) === nameNew)
      msgs.push('名稱與既有廠商相同：' + who);
  }

  if (msgs.length) {
    response.setStatus('INVALID');
    response.setMessage('[' + VER + '] 重複建檔，無法存檔：\n' + msgs.join('\n') +
      '\n請改用既有廠商資料，或先修正舊資料。');
  }
})();
