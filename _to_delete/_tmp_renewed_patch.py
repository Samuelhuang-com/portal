import io
def patch(path, pairs):
    s = io.open(path, encoding='utf-8', newline='').read()
    n0 = len(s)
    for old, new in pairs:
        c = s.count(old)
        assert c == 1, (path, c, old[:80])
        s = s.replace(old, new)
    io.open(path, 'w', encoding='utf-8', newline='').write(s)
    print(path, n0, '->', len(s))

# ── service ──
SVC = 'backend/app/services/contract_service.py'
helper = '''    @staticmethod
    def mark_source_renewed(db: Session, contract: Contract) -> Optional[str]:
        """
        新合約轉為「生效中」時，把它的續約來源（renewed_from_contract_id）改為「已續約」。
        （2026-09-30 使用者裁示：原合約在「新合約生效」那一刻才變更，
          不在按下複製續約時變更——複製出來的草稿可能被拒絕或刪除，不能誤傷原合約。）

        只有來源合約目前是「生效中／即將到期」才會改；草稿、審核中、已終止、已續約都不動。
        不自行 commit，由呼叫端與新合約的狀態變更同一個交易提交。

        Returns:
            被改成「已續約」的來源合約編號；未變更時回傳 None
        """
        src_id = getattr(contract, "renewed_from_contract_id", None)
        if not src_id or contract.contract_status != "生效中":
            return None
        src = db.query(Contract).filter(Contract.contract_id == src_id).first()
        if not src or src.contract_status not in ("生效中", "即將到期"):
            return None
        src.contract_status = "已續約"
        src.updated_at = datetime.now()
        return src.contract_id

    @staticmethod
    def get_renewal_chain(db: Session, contract_id: str) -> List[Contract]:'''
patch(SVC, [
    ('''    @staticmethod
    def get_renewal_chain(db: Session, contract_id: str) -> List[Contract]:''', helper),
    # update_contract：手動把狀態改成生效中也要連動
    ('''        # 更新欄位
        update_data = contract_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(contract, key, value)
''', '''        # 更新欄位
        old_status = contract.contract_status
        update_data = contract_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(contract, key, value)

        # 手動把續約新合約改成「生效中」→ 原合約轉「已續約」
        if old_status != "生效中" and contract.contract_status == "生效中":
            ContractService.mark_source_renewed(db, contract)
'''),
    ('''        now = datetime.now()
        contract.contract_status = "生效中"
        contract.approved_by = approver
        contract.approved_at = now
        contract.approval_comment = comment
        contract.updated_at = now
        db.commit()''', '''        now = datetime.now()
        contract.contract_status = "生效中"
        contract.approved_by = approver
        contract.approved_at = now
        contract.approval_comment = comment
        contract.updated_at = now
        ContractService.mark_source_renewed(db, contract)   # 續約新合約生效 → 原合約「已續約」
        db.commit()'''),
    ('''            Contract.end_date <= deadline,
            Contract.contract_status != "已終止",''', '''            Contract.end_date <= deadline,
            Contract.contract_status.notin_(["已終止", "已續約"]),'''),
    ('status: 狀態篩選（草稿/簽訂中/生效中/已結束/已終止）', 'status: 狀態篩選（草稿/簽訂中/生效中/已結束/已終止/已續約）'),
])

# ── router ──
RT = 'backend/app/routers/contract.py'
s = io.open(RT, encoding='utf-8', newline='').read()
cnt = s.count('Contract.contract_status.notin_(["已終止"])')
assert cnt == 3, cnt
s = s.replace('Contract.contract_status.notin_(["已終止"])', 'Contract.contract_status.notin_(["已終止", "已續約"])')
io.open(RT, 'w', encoding='utf-8', newline='').write(s)
patch(RT, [
    ('''    if all_approved and contract and contract.contract_status == "審核中":
        contract.contract_status = "生效中"
        contract.approved_by = reviewer
        contract.approved_at = now
        contract.approval_comment = body.comment
        contract.updated_at = now
''', '''    renewed_source_id = None
    if all_approved and contract and contract.contract_status == "審核中":
        contract.contract_status = "生效中"
        contract.approved_by = reviewer
        contract.approved_at = now
        contract.approval_comment = body.comment
        contract.updated_at = now
        # 續約新合約生效 → 原合約「已續約」（2026-09-30）
        renewed_source_id = ContractService.mark_source_renewed(db, contract)
'''),
    ('''        "status": "已核准",
        "contract_promoted": all_approved,
    }''', '''        "status": "已核准",
        "contract_promoted": all_approved,
        "renewed_source_id": renewed_source_id,
    }'''),
])

# ── model comment ──
patch('backend/app/models/contract.py', [
    ('comment="合約狀態（草稿/審核中/生效中/即將到期/已終止）"', 'comment="合約狀態（草稿/審核中/生效中/即將到期/已終止/已續約）"'),
])

# ── frontend ──
patch('frontend/src/pages/Contract/index.tsx', [
    ("""  '已終止': 'error',
}""", """  '已終止': 'error',
  '已續約': 'purple',   // 被複製續約的新合約取代（新合約生效時自動設定）
}"""),
    ('''              <Option value="已終止">已終止</Option>''', '''              <Option value="已終止">已終止</Option>
              <Option value="已續約">已續約</Option>'''),
    ("['草稿','審核中','生效中','即將到期','已終止'].map(s =>", "['草稿','審核中','生效中','即將到期','已終止','已續約'].map(s =>"),
])
patch('frontend/src/pages/Contract/CompareContracts.tsx', [
    ("即將到期: 'warning', 已終止: 'error',", "即將到期: 'warning', 已終止: 'error', 已續約: 'purple',"),
])
patch('frontend/src/pages/Contract/Manual/content.ts', [
    ('''              + '這個關聯就是第 5-4 節「上下層級」看到的續約家族樹。',
          },''', '''              + '這個關聯就是第 5-4 節「上下層級」看到的續約家族樹。',
          },
          {
            t: 'p',
            text:
              '**原合約的狀態會自動改成「已續約」**，但時間點是**新合約變成「生效中」的那一刻**'
              + '（審核全部通過，或手動把新合約狀態改成生效中），**不是按下複製續約的時候**——'
              + '剛複製出來的新合約還是草稿，可能被拒絕或刪掉，這段期間原合約維持原狀態照常運作。'
              + '只有原合約當時是「生效中／即將到期」才會被改；「已續約」的合約不會再出現在到期預警、'
              + '到期提醒、合約行事曆、廠商金額統計與預算分析的合約金額裡，避免新舊兩版重複計算。',
          },'''),
])
