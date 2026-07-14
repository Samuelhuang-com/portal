import hashlib, sys

def patch_file(path, sha_expected, sheet_tag, images_const, server_var, account_var):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != sha_expected:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)

    # Patch A: add images_fallback_used counter next to items_with_images
    OLD_A = "    items_with_images = 0\n"
    assert data.count(OLD_A) == 1, f"{path}: OLD_A count={data.count(OLD_A)}"
    NEW_A = "    items_with_images = 0\n    images_fallback_used = 0   # 2026-07-14 新增：見下方欄位 key 備援偵測邏輯\n"
    data = data.replace(OLD_A, NEW_A, 1)

    # Patch B: add a seen-keys set right before the main for-loop
    OLD_B = "        for item_ragic_id, raw in raw_data.items():\n"
    assert data.count(OLD_B) == 1, f"{path}: OLD_B count={data.count(OLD_B)}"
    NEW_B = (
        "        # 2026-07-14 新增：CK*_IMAGES 欄位 key 若猜錯，同一個錯誤 key 每筆項目都會\n"
        "        # 觸發備援邏輯，這個 set 只用來讓警告訊息在整次同步只出現一次（依 fallback_key 去重）。\n"
        "        _images_fallback_keys_seen: set[str] = set()\n"
        "        for item_ragic_id, raw in raw_data.items():\n"
    )
    data = data.replace(OLD_B, NEW_B, 1)

    # Patch C: defensive images extraction with fallback key detection
    OLD_C = f'''                    images = parse_images(
                        full_record.get({images_const}),
                        server={server_var},
                        account={account_var},
                    )'''
    assert data.count(OLD_C) == 1, f"{path}: OLD_C count={data.count(OLD_C)}"
    NEW_C = f'''                    raw_images_val = full_record.get({images_const})
                    if not raw_images_val:
                        # 2026-07-14 新增：{images_const}（中文欄位 label）當時是「新增」而非「實測驗證」
                        # （對照同檔案其餘 CK*L_* 常數皆有明確實測驗證標記），實際欄位 key 是否正確
                        # 從未被證實過。使用者回報 Ragic 記錄明明有圖檔，Drawer 卻始終不顯示附圖，
                        # 懷疑是這裡的欄位 key 猜錯。加入備援：若設定的 key 抓不到值，改在 full_record
                        # 全部 key 中尋找任何含「圖片／附件／照片／相片／image／upload」關鍵字的欄位
                        # 當備援來源，並記錄一次警告方便從 log 找出真正的欄位 key 以便日後修正常數。
                        fallback_key = next(
                            (k for k in full_record.keys()
                             if isinstance(k, str) and k != {images_const}
                             and any(c in k for c in ("圖片", "附件", "照片", "相片", "image", "upload"))
                             and full_record.get(k)),
                            None,
                        )
                        if fallback_key:
                            raw_images_val = full_record.get(fallback_key)
                            images_fallback_used += 1
                            if fallback_key not in _images_fallback_keys_seen:
                                _images_fallback_keys_seen.add(fallback_key)
                                logger.warning(
                                    f"[{sheet_tag}] {images_const}=\\"{{{images_const}}}\\" 抓不到資料，"
                                    f"改用偵測到的備援欄位 \\"{{fallback_key}}\\"（item={{item_id}} 首次觸發）；"
                                    f"建議確認 Ragic 實際欄位名稱後更新此常數，避免長期依賴備援邏輯"
                                )
                    images = parse_images(
                        raw_images_val,
                        server={server_var},
                        account={account_var},
                    )'''
    data = data.replace(OLD_C, NEW_C, 1)

    # Patch D: include images_fallback_used in the final summary log line
    OLD_D = f'''            f"worklogs={{worklog_upserted}}, items_with_images={{items_with_images}}, "
            f"errors={{len(errors)}}, unmatched_batches={{len(unmatched_journal_nos)}}"
        )'''
    assert data.count(OLD_D) == 1, f"{path}: OLD_D count={data.count(OLD_D)}"
    NEW_D = f'''            f"worklogs={{worklog_upserted}}, items_with_images={{items_with_images}}, "
            f"images_fallback_used={{images_fallback_used}}, "
            f"errors={{len(errors)}}, unmatched_batches={{len(unmatched_journal_nos)}}"
        )'''
    data = data.replace(OLD_D, NEW_D, 1)

    # Patch E: include images_fallback_used in the returned dict
    OLD_E = '''        "items_with_images": items_with_images,
        "old_style_removed": len(old_style),'''
    assert data.count(OLD_E) == 1, f"{path}: OLD_E count={data.count(OLD_E)}"
    NEW_E = '''        "items_with_images": items_with_images,
        "images_fallback_used": images_fallback_used,
        "old_style_removed": len(old_style),'''
    data = data.replace(OLD_E, NEW_E, 1)

    dst = path.replace(".py", "_tmp_v40.py")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(data)
    print(f"OK wrote {dst} bytes={len(data)}")


patch_file(
    "backend/app/services/full_building_maintenance_sync.py",
    "057e88ce1359d0b2c32e38a43bcc08b530fa9bb192d47a89369f89a5fc0459cc",
    "FullBldgPMSync][Sheet28Items",
    "CK28L_IMAGES",
    "FULL_BLDG_PM_SERVER_URL",
    "FULL_BLDG_PM_ACCOUNT",
)

patch_file(
    "backend/app/services/mall_periodic_maintenance_sync.py",
    "bbe2664a17052ecfb00f3130c4ccc766a979026498b4c13eab320777a455e958",
    "MallPMSync][Sheet24Items",
    "CK24L_IMAGES",
    "MALL_PM_SERVER_URL",
    "MALL_PM_ACCOUNT",
)
