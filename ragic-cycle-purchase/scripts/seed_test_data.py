"""
seed_test_data.py v1.0
測試資料產生器：產生週期、批次、請購單（含明細）、驗收單測試資料
預設 dry_run=True，不會實際寫入 Ragic
"""
import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from ragic_client import RagicClient

VERSION = "v1.0"
ICON = "🌱"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SAMPLE_ITEMS = [
    {"料號": "ITEM001", "品名": "衛生紙", "單位": "箱", "預設數量": 10, "MOQ": 5},
    {"料號": "ITEM002", "品名": "洗手乳", "單位": "瓶", "預設數量": 20, "MOQ": 10},
    {"料號": "ITEM003", "品名": "咖啡豆", "單位": "包", "預設數量": 5,  "MOQ": 2},
]

SAMPLE_DEPARTMENTS = ["行政部", "業務部", "IT部"]


def seed_cycle(client: RagicClient) -> dict:
    logger.info(f"{ICON} [{VERSION}] 產生測試週期設定...")
    data = {
        "週期名稱": "2026年06月_每月週期",
        "週期頻率": "每月",
        "開放起始日": "2026-06-01",
        "截止日": "2026-06-10",
        "適用單位": ",".join(SAMPLE_DEPARTMENTS),
        "狀態": "啟用"
    }
    result = client.create_record("cycle-purchase/cycles", data)
    logger.info(f"{ICON} 週期設定：{result}")
    return result


def seed_batch(client: RagicClient, cycle_id: str = "CYCLE001") -> dict:
    logger.info(f"{ICON} [{VERSION}] 產生測試批次...")
    data = {
        "週期ID": cycle_id,
        "批次名稱": "2026年06月批次",
        "開放日期": "2026-06-01",
        "截止日期": "2026-06-10",
        "是否已產生請購": False,
        "狀態": "開放"
    }
    result = client.create_record("cycle-purchase/batches", data)
    logger.info(f"{ICON} 批次：{result}")
    return result


def seed_requests(client: RagicClient, batch_no: str = "BATCH001") -> list:
    logger.info(f"{ICON} [{VERSION}] 產生測試請購單（共 {len(SAMPLE_DEPARTMENTS)} 張）...")
    results = []
    for dept in SAMPLE_DEPARTMENTS:
        details = []
        for item in SAMPLE_ITEMS:
            details.append({
                "統購料號": item["料號"],
                "品名": item["品名"],
                "單位": item["單位"],
                "單價": 100,
                "請購數量": 0
            })
        data = {
            "批次號": batch_no,
            "請購部門": dept,
            "公司別": "C001",
            "狀態": "待填",
            "請購明細": details
        }
        result = client.create_record("cycle-purchase/requests", data)
        logger.info(f"{ICON} 請購單({dept})：{result}")
        results.append(result)
    return results


def seed_receiving(client: RagicClient, po_no: str = "PO001") -> dict:
    logger.info(f"{ICON} [{VERSION}] 產生測試驗收單...")
    details = []
    for item in SAMPLE_ITEMS:
        details.append({
            "料號": item["料號"],
            "驗收數量": 5,
            "發票數量": 5
        })
    data = {
        "採購單號": po_no,
        "驗收日期": "2026-06-15",
        "狀態": "待驗收",
        "驗收明細": details
    }
    result = client.create_record("cycle-purchase/receiving", data)
    logger.info(f"{ICON} 驗收單：{result}")
    return result


def main():
    parser = argparse.ArgumentParser(description=f"Ragic 週期採購測試資料產生器 {VERSION}")
    parser.add_argument("--dry-run", action="store_true", default=True, help="僅模擬，不寫入（預設）")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="實際寫入 Ragic（謹慎使用）")
    args = parser.parse_args()

    logger.info(f"{ICON} [{VERSION}] 開始產生測試資料 | dry_run={args.dry_run}")

    client = RagicClient(dry_run=args.dry_run)

    seed_cycle(client)
    seed_batch(client)
    seed_requests(client)
    seed_receiving(client)

    logger.info(f"{ICON} [{VERSION}] 測試資料產生完成")


if __name__ == "__main__":
    main()
