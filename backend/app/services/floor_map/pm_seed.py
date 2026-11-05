"""
樓層巡檢圖 — 例行維護類模組的點位清單與草稿寫入（2026-11-04）

模組：商場例行維護（mall_periodic_maintenance）、全棟例行維護（mall_full_building_maintenance）
來源（Samuel 提供，以 Excel 內容為準）：
  myDoc/平面圖/樓層巡檢圖_點位清單_商場例行維護_2026-11春週保-002_v2.xlsx（34 項）
  myDoc/平面圖/樓層巡檢圖_點位清單_全棟例行維護_2026-棟週保202611-003.xlsx（54 項）
本檔資料由 Excel 以程式轉出，請勿手改單列；清單改版時重新轉出並另開 migration。

裁示（docs/SPEC_floor_map_periodic_maintenance.md）：
  - 子項 source_ref＝保養項目名稱（空白正規化）；同一批次內同名者依項次排序加「 #1」「 #2」
  - 子項樓層：「全區／各樓層」＝該模組全部樓層；「戶外」＝1F；「B1中控室」＝B1F
  - 2026-11-05 起點位以「母項」為單位（PM_PARENTS）：每個母項在子項出現過的每一層各一點；
    子項停用記在 floor_map_disabled_sources（不再停用點位）
  - 位置一律「待定位」排在圖左上，上線後在畫面上拖曳定位
  - 只在該模組一筆點位都沒有時寫入（含已停用的點），可重跑、不會重複；
    既有子項點位由 convert_child_points 轉成母項點位（沿用已拖曳過的位置）
"""
from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from app.core.time import twnow

TABLE = "floor_map_points"

# 模組全部樓層（「全區」「各樓層」展開用；同時是工具列樓層順序）
PM_FLOORS: dict[str, list[str]] = {
    "mall_periodic_maintenance":      ["4f", "3f", "2f", "1f", "b1f", "b2f", "b3f", "b4f"],
    "mall_full_building_maintenance": ["rf", "4f", "3f", "2f", "1f", "b1f", "b2f", "b3f", "b4f"],
}

# source_ref, 類別, Excel 樓層原文, 樓層
PM_ITEMS: dict[str, list[tuple[str, str, str, tuple[str, ...]]]] = {
    "mall_periodic_maintenance": [
        ('1F商場水洗機房→保養', '水電', '1F', ('1f',)),  # 1.1
        ('3F商場靜電機房→保養', '水電', '3F', ('3f',)),  # 2.1
        ('商場辦公室室內送風機排水→巡檢保養', '空調', 'B1F', ('b1f',)),  # 3.1
        ('空調箱保養(R-21 . R-22 . R-23)', '空調', '2F', ('2f',)),  # 4.1
        ('空調箱保養(R-24 . R-25 . R-34)', '空調', '2F、3F', ('2f', '3f',)),  # 4.2
        ('空調箱保養(R-26 . R-27 . R-33)', '空調', '2F、3F', ('2f', '3f',)),  # 4.3
        ('空調箱保養(R-31 . H-41 . H-42)', '空調', '3F、4F', ('3f', '4f',)),  # 4.4
        ('預冷空調箱(PAH-R21)', '空調', '2F', ('2f',)),  # 4.5
        ('商場空調箱x13→更換濾網', '照明', '2、3、4F', ('2f', '3f', '4f',)),  # 4.6
        ('商場送風機x7 #1', '空調', '1F', ('1f',)),  # 5.1
        ('商場送風機x7 #2', '空調', '1F', ('1f',)),  # 5.2
        ('更換商場送風機濾網x7(中島區) #1', '空調', '1F', ('1f',)),  # 5.3
        ('更換商場送風機濾網x7(中島區) #2', '空調', '1F', ('1f',)),  # 5.4
        ('更換迴風網x6', '空調', 'B1F', ('b1f',)),  # 5.5
        ('更換迴風網x5', '空調', 'B1F', ('b1f',)),  # 5.6
        ('B4~3F照明設定與調整', '照明', 'B1中控室', ('b1f',)),  # 6.1
        ('給排水設備', '水電', 'B4F', ('b4f',)),  # 7.1
        ('電氣感應設備', '水電', 'B1F', ('b1f',)),  # 7.2
        ('五金及固定配件', '水電', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 7.3
        ('安全及設施維護', '水電', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 7.4
        ('各樓層後勤通道', '油漆', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 8.1
        ('廁所動線', '油漆', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 8.2
        ('公共區域', '油漆', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 8.3
        ('後場區域(辦公室/回收區/卸貨區/梯廳/員休室/會議室)', '油漆', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 8.4
        ('地磚整平', '整體', '戶外', ('1f',)),  # 9.1
        ('固定桌椅檢查保養', '整體', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 9.2
        ('傘架收放測試保養', '整體', '戶外', ('1f',)),  # 9.3
        ('水霧系統測試保養', '整體', 'B1F', ('b1f',)),  # 9.4
        ('照明設備檢查保養', '整體', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 9.5
        ('電力設備(電箱)附載檢查', '整體', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 9.6
        ('停車場招牌燈箱*2戶外指引牌*4 懸掛式招牌*2(小後苑廊道)', '', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 10.1
        ('春大直LOGO燈字招牌*2 館內燈箱指引牌*6', '', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 10.2
        ('不鏽鋼除鏽保養', '其它', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 11.1
        ('門扇→巡檢保養', '其它', '全區', ('4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 11.2
    ],
    "mall_full_building_maintenance": [
        ('全館Timer定時器時間及減壓閥校正', '水電', 'B1F中控室', ('b1f',)),  # 1
        ('1F / RF 落水頭清潔', '水電', '1F / RF', ('1f', 'rf',)),  # 2
        ('各樓層配電盤接點鎖螺絲安全檢查→巡檢', '水電', '各樓層', ('rf', '4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 3
        ('WP1 沉水式馬達x2 + 控制盤x1', '水電', 'B4F', ('b4f',)),  # 4
        ('WP2 沉水式馬達x2 + 控制盤x1', '水電', 'B4F', ('b4f',)),  # 5
        ('WP3 沉水式馬達x2 + 控制盤x1', '水電', 'B4F', ('b4f',)),  # 6
        ('SP1 沉水式馬達x2 + 控制盤x1', '水電', 'B4F', ('b4f',)),  # 7
        ('SP2 沉水式馬達x2 + 控制盤x1', '水電', 'B4F', ('b4f',)),  # 8
        ('SP3 沉水式馬達x2 + 控制盤x1', '水電', 'B4F', ('b4f',)),  # 9
        ('汙水管道通管保養', '水電', 'B4F', ('b4f',)),  # 10
        ('地上型抽水馬達x2', '水電', 'B4F', ('b4f',)),  # 11
        ('自動控制盤x1(變頻器x2)目測及溫度偵測', '水電', 'B4F', ('b4f',)),  # 12
        ('澆灌系統自動控制盤x2→校對時間', '水電', 'B4F', ('b4f',)),  # 13
        ('噴頭系統維護測試', '水電', 'B4F', ('b4f',)),  # 14
        ('雨水坑內澆灌沉水馬達x2', '水電', 'B4F', ('b4f',)),  # 15
        ('雨水坑自動控制盤x2', '水電', 'B4F', ('b4f',)),  # 16
        ('冷卻馬達x3，清洗、保養、加藥、檢測', '水電', 'RF', ('rf',)),  # 17
        ('冷卻水塔x3，清洗、保養、加藥、檢測', '水電', 'RF', ('rf',)),  # 18
        ('上蓄水塔/下蓄水塔 共4座清洗', '水電', 'RF', ('rf',)),  # 19
        ('設備保養-油脂截流攔污機', '水電', 'B2F', ('b2f',)),  # 20
        ('油泥抽除', '水電', 'B2F', ('b2f',)),  # 21
        ('油泥清運', '水電', 'B2F', ('b2f',)),  # 22
        ('抽排風扇設備維護運轉測試', '水電', 'B2F', ('b2f',)),  # 23
        ('發電機x2→工程人員無載測試運轉', '水電', 'B1F', ('b1f',)),  # 24
        ('發電機x2', '水電', 'B1F', ('b1f',)),  # 25
        ('台電高壓機房 #1', '水電', 'B1F', ('b1f',)),  # 26
        ('台電高壓機房 #2', '水電', 'B1F', ('b1f',)),  # 27
        ('UPS巡檢', '水電', 'B1F', ('b1f',)),  # 28
        ('冰水主機x6(商場CH-R1~R3, 飯店CH-H1~H3)', '空調', 'B4F', ('b4f',)),  # 29
        ('冷卻水泵x8(商場CWP-R1~R4, 飯店CWP-H1~H4)', '空調', 'B4F', ('b4f',)),  # 30
        ('冰水循環泵x8(商場SCP-R1~R4, 飯店SCP-H1~H4)', '空調', 'B4F', ('b4f',)),  # 31
        ('冰水泵x8(商場CHP-R1~R4, 飯店CHP-H1~H4)', '空調', 'B4F', ('b4f',)),  # 32
        ('區域泵x8(商場SCHP-R1~R4, 飯店SCHP-H1~H4)', '空調', 'B4F', ('b4f',)),  # 33
        ('泵補控制盤x6(商場x3, 飯店x3)', '空調', 'B4F', ('b4f',)),  # 34
        ('冰水主機Y型過濾器清洗保養(商場x3)', '空調', 'B4F', ('b4f',)),  # 35
        ('進風', '空調', 'B1、B2、B3、B4F', ('b1f', 'b2f', 'b3f', 'b4f',)),  # 36
        ('排風', '空調', 'B1、B2、B3、B4F', ('b1f', 'b2f', 'b3f', 'b4f',)),  # 37
        ('導流風扇運轉正常測試', '空調', 'B1、B2、B3、B4F', ('b1f', 'b2f', 'b3f', 'b4f',)),  # 38
        ('室內機x1', '空調', 'B1F', ('b1f',)),  # 39
        ('室外機x5', '空調', 'B1F', ('b1f',)),  # 40
        ('戶外景觀/公區/停車場燈具→保養', '照明', 'B1F', ('b1f',)),  # 41
        ('消防機組(整套含馬達)測試運轉+檢測控盤', '消防', 'B4F', ('b4f',)),  # 42
        ('灑水機組(整套含馬達)測試運轉+檢測控盤', '消防', 'B4F', ('b4f',)),  # 43
        ('泡沫機組(整套含馬達)測試運轉+檢測控盤', '消防', 'B4F', ('b4f',)),  # 44
        ('泡沫原液桶x1 原液量測量', '消防', 'B4F', ('b4f',)),  # 45
        ('消防栓箱及滅火器清潔', '消防', 'B4F', ('b4f',)),  # 46
        ('頂樓消防系統', '消防', 'B4F', ('b4f',)),  # 47
        ('鐡捲門測試', '消防', 'B4F', ('b4f',)),  # 48
        ('緊急廣播測試', '消防', 'B4F', ('b4f',)),  # 49
        ('年度能源申報', '申報', 'B4F', ('b4f',)),  # 50
        ('商場扶梯x4', '整體', '全區', ('rf', '4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 51
        ('商場客.貨x4', '整體', '全區', ('rf', '4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 52
        ('倉庫整理、盤點（含工具）', '整體', '全區', ('rf', '4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 53
        ('工務耗材庫存管理每月盤點出單', '整體', '全區', ('rf', '4f', '3f', '2f', '1f', 'b1f', 'b2f', 'b3f', 'b4f',)),  # 54
    ],
}

# 子項 → 母項名稱（2026-11-05；商場取自 Ragic Sheet35「項目母項名稱」、全棟取自 Sheet28，
# 母項名稱空白者＝子項名稱，Samuel 裁示）。執行時優先用資料庫 parent_name（Ragic 同步值），
# 沒有值才用這份對照；兩者都沒有＝子項自成一個母項。
PM_PARENTS: dict[str, dict[str, str]] = {
    "mall_periodic_maintenance": {
        '1F商場水洗機房→保養': '1F商場水洗機房→保養',
        '3F商場靜電機房→保養': '3F商場靜電機房→保養',
        '商場辦公室室內送風機排水→巡檢保養': '商場辦公室室內送風機排水→巡檢保養',
        '空調箱保養(R-21 . R-22 . R-23)': '1F~3F空調→保養',
        '空調箱保養(R-24 . R-25 . R-34)': '1F~3F空調→保養',
        '空調箱保養(R-26 . R-27 . R-33)': '1F~3F空調→保養',
        '空調箱保養(R-31 . H-41 . H-42)': '1F~3F空調→保養',
        '預冷空調箱(PAH-R21)': '1F~3F空調→保養',
        '商場空調箱x13→更換濾網': '1F~3F空調→保養',
        '商場送風機x7 #1': '1F空調→保養(中島區)',
        '商場送風機x7 #2': '1F空調→保養(中島區)',
        '更換商場送風機濾網x7(中島區) #1': '1F空調→保養(中島區)',
        '更換商場送風機濾網x7(中島區) #2': '1F空調→保養(中島區)',
        '更換迴風網x6': '1F空調→保養(中島區)',
        '更換迴風網x5': '1F空調→保養(中島區)',
        'B4~3F照明設定與調整': 'B4~3F照明設定與調整',
        '給排水設備': '客厠配件維護(戶外.1F.2F.3F)',
        '電氣感應設備': '客厠配件維護(戶外.1F.2F.3F)',
        '五金及固定配件': '客厠配件維護(戶外.1F.2F.3F)',
        '安全及設施維護': '客厠配件維護(戶外.1F.2F.3F)',
        '各樓層後勤通道': '公區壁面批土補漆',
        '廁所動線': '公區壁面批土補漆',
        '公共區域': '公區壁面批土補漆',
        '後場區域(辦公室/回收區/卸貨區/梯廳/員休室/會議室)': '公區壁面批土補漆',
        '地磚整平': '戶外廣場維護保養',
        '固定桌椅檢查保養': '戶外廣場維護保養',
        '傘架收放測試保養': '戶外廣場維護保養',
        '水霧系統測試保養': '戶外廣場維護保養',
        '照明設備檢查保養': '戶外廣場維護保養',
        '電力設備(電箱)附載檢查': '戶外廣場維護保養',
        '停車場招牌燈箱*2戶外指引牌*4 懸掛式招牌*2(小後苑廊道)': '燈箱招牌維護含底座',
        '春大直LOGO燈字招牌*2 館內燈箱指引牌*6': '燈箱招牌維護含底座',
        '不鏽鋼除鏽保養': '門扇→保養',
        '門扇→巡檢保養': '門扇→保養',
    },
    "mall_full_building_maintenance": {
        '全館Timer定時器時間及減壓閥校正': '全館Timer定時器時間及減壓閥校正',
        '1F / RF 落水頭清潔': '1F / RF 落水頭清潔',
        '各樓層配電盤接點鎖螺絲安全檢查→巡檢': '各樓層配電盤接點鎖螺絲安全檢查→巡檢',
        'WP1 沉水式馬達x2 + 控制盤x1': '廢水系統→保養',
        'WP2 沉水式馬達x2 + 控制盤x1': '廢水系統→保養',
        'WP3 沉水式馬達x2 + 控制盤x1': '廢水系統→保養',
        'SP1 沉水式馬達x2 + 控制盤x1': '汙水系統→保養',
        'SP2 沉水式馬達x2 + 控制盤x1': '汙水系統→保養',
        'SP3 沉水式馬達x2 + 控制盤x1': '汙水系統→保養',
        '汙水管道通管保養': '汙水管道通管保養',
        '地上型抽水馬達x2': '揚水泵馬達巡檢→測試運轉',
        '自動控制盤x1(變頻器x2)目測及溫度偵測': '揚水泵馬達巡檢→測試運轉',
        '澆灌系統自動控制盤x2→校對時間': '雨水池/ 給水閥/噴灌設備→保養',
        '噴頭系統維護測試': '雨水池/ 給水閥/噴灌設備→保養',
        '雨水坑內澆灌沉水馬達x2': '雨水池/ 給水閥/噴灌設備→保養',
        '雨水坑自動控制盤x2': '雨水池/ 給水閥/噴灌設備→保養',
        '冷卻馬達x3，清洗、保養、加藥、檢測': 'RF水塔→保養',
        '冷卻水塔x3，清洗、保養、加藥、檢測': 'RF水塔→保養',
        '上蓄水塔/下蓄水塔 共4座清洗': '上蓄水塔/下蓄水塔 共4座清洗',
        '設備保養-油脂截流攔污機': 'B2商場截油槽(大)+飯店截油槽(小)→保養',
        '油泥抽除': 'B2商場截油槽(大)+飯店截油槽(小)→保養',
        '油泥清運': 'B2商場截油槽(大)+飯店截油槽(小)→保養',
        '抽排風扇設備維護運轉測試': 'B2商場截油槽(大)+飯店截油槽(小)→保養',
        '發電機x2→工程人員無載測試運轉': '電氣設備→保養',
        '發電機x2': '電氣設備→保養',
        '台電高壓機房 #1': '電氣設備→保養',
        '台電高壓機房 #2': '電氣設備→保養',
        'UPS巡檢': '電氣設備→保養',
        '冰水主機x6(商場CH-R1~R3, 飯店CH-H1~H3)': '冰水機房',
        '冷卻水泵x8(商場CWP-R1~R4, 飯店CWP-H1~H4)': '冰水機房',
        '冰水循環泵x8(商場SCP-R1~R4, 飯店SCP-H1~H4)': '冰水機房',
        '冰水泵x8(商場CHP-R1~R4, 飯店CHP-H1~H4)': '冰水機房',
        '區域泵x8(商場SCHP-R1~R4, 飯店SCHP-H1~H4)': '冰水機房',
        '泵補控制盤x6(商場x3, 飯店x3)': '冰水機房',
        '冰水主機Y型過濾器清洗保養(商場x3)': '冰水機房',
        '進風': 'B1~B4進排風→設定與調整',
        '排風': 'B1~B4進排風→設定與調整',
        '導流風扇運轉正常測試': 'B1~B4進排風→設定與調整',
        '室內機x1': '全棟分離式空調(B1行政辦公室)→保養',
        '室外機x5': '全棟分離式空調(B1行政辦公室)→保養',
        '戶外景觀/公區/停車場燈具→保養': '戶外景觀/公區/停車場燈具→保養',
        '消防機組(整套含馬達)測試運轉+檢測控盤': '消防設備→巡檢保養',
        '灑水機組(整套含馬達)測試運轉+檢測控盤': '消防設備→巡檢保養',
        '泡沫機組(整套含馬達)測試運轉+檢測控盤': '消防設備→巡檢保養',
        '泡沫原液桶x1 原液量測量': '消防設備→巡檢保養',
        '消防栓箱及滅火器清潔': '消防設備→巡檢保養',
        '頂樓消防系統': '消防設備→巡檢保養',
        '鐡捲門測試': '消防設備→巡檢保養',
        '緊急廣播測試': '消防設備→巡檢保養',
        '年度能源申報': '年度能源申報',
        '商場扶梯x4': '客貨梯/扶梯保養',
        '商場客.貨x4': '客貨梯/扶梯保養',
        '倉庫整理、盤點（含工具）': '倉庫整理、盤點（含工具）',
        '工務耗材庫存管理每月盤點出單': '工務耗材庫存管理每月盤點出單',
    },
}

UNCATEGORIZED = "未分類"
PENDING_NOTE = "待定位：請用「編輯點位」拖到正確位置（拖過即視為已校正）"
CONVERT_TAG = "fmappm2"   # 子項點位 → 母項點位 轉換／母項草稿的寫入標記（created_by 含此字串）


def normalize_name(name: str | None) -> str:
    """保養項目名稱正規化：去頭尾、連續空白合併成一個（Ragic 與畫面顯示的空白可能不同）"""
    return " ".join((name or "").split())


# ── 子項／母項查詢（點位清單）──────────────────────────────────────────────────
def child_floors(module: str) -> dict[str, tuple[str, ...]]:
    """子項 → 樓層（點位清單）"""
    return {ref: floors for ref, _c, _t, floors in PM_ITEMS.get(module, [])}


def child_category(module: str) -> dict[str, str]:
    return {ref: cat for ref, cat, _t, _f in PM_ITEMS.get(module, [])}


def parent_of(module: str, child_ref: str) -> str | None:
    """點位清單的子項 → 母項名稱；不在清單＝None"""
    return PM_PARENTS.get(module, {}).get(child_ref)


def static_parents(module: str) -> list[dict[str, Any]]:
    """
    點位清單的母項：[{ref, category, floors, children}]，依清單順序。
    floors＝所有子項樓層的聯集（依模組樓層順序）；category＝第一個子項的類別。
    """
    order = PM_FLOORS.get(module, [])
    out: dict[str, dict[str, Any]] = {}
    for ref, cat, _txt, floors in PM_ITEMS.get(module, []):
        p = parent_of(module, ref) or ref
        g = out.setdefault(p, {"ref": p, "category": cat, "floors": set(), "children": []})
        g["floors"].update(floors)
        g["children"].append(ref)
    for g in out.values():
        g["floors"] = [f for f in order if f in g["floors"]]
    return list(out.values())


def static_groups(module: str) -> list[dict[str, Any]]:
    """點位清單的資料來源（GroupMeta，母項層級）"""
    return [
        {"source_ref": g["ref"], "label": g["ref"], "system": g["category"] or UNCATEGORIZED, "shared_label": ""}
        for g in static_parents(module)
    ]


def pending_xy(i: int) -> tuple[float, float]:
    """待定位排列：圖左上，每欄 13 點，超過往右另起一欄（座標維持 0～1）"""
    col, row = divmod(i, 13)
    return round(0.04 + 0.07 * col, 3), round(0.07 + 0.065 * row, 3)


_COLS = (
    "module", "floor_key", "x", "y", "label", "equipment_code", "source_ref", "placement", "note",
    "sort_order", "is_active", "created_by", "updated_by", "created_at", "updated_at",
)
_tbl = sa.table(TABLE, sa.column("attrs", sa.JSON(none_as_null=True)), *(sa.column(c) for c in _COLS))
DISABLED_TABLE = "floor_map_disabled_sources"


def _parent_rows(module: str, tag: str, positions: dict[tuple[str, str], tuple[float, float]] | None = None
                 ) -> list[dict[str, Any]]:
    """母項點位列：每個母項在子項出現過的每一層各一點；positions 有值者沿用位置（已校正）"""
    now, rows = twnow(), []
    per_floor: dict[str, int] = {}
    order = 0
    for g in static_parents(module):
        for fk in g["floors"]:
            pos = (positions or {}).get((g["ref"], fk))
            if pos:
                (x, y), placement, note = pos, "confirmed", None
            else:
                i = per_floor.get(fk, 0)
                per_floor[fk] = i + 1
                (x, y), placement, note = pending_xy(i), "pending", PENDING_NOTE
            rows.append({
                "module": module, "floor_key": fk, "x": x, "y": y, "label": g["ref"][:100],
                "equipment_code": None, "source_ref": g["ref"], "placement": placement,
                "attrs": None, "note": note, "sort_order": order, "is_active": True,
                "created_by": tag, "updated_by": tag, "created_at": now, "updated_at": now,
            })
            order += 1
    return rows


def seed_pm_points(conn, module: str, tag: str) -> int:
    """
    模組一筆點位都沒有時寫入母項點位（全部待定位）；已有任何點位（含已停用）就不動。回傳寫入筆數。
    2026-11-05 起寫入的是母項點位（原為子項點位，見 convert_child_points）。
    """
    if module not in PM_ITEMS:
        return 0
    n = conn.execute(sa.text(f"SELECT COUNT(*) FROM {TABLE} WHERE module = :m"), {"m": module}).scalar() or 0
    if n:
        return 0
    rows = _parent_rows(module, f"{tag}:{CONVERT_TAG}")
    if rows:
        conn.execute(_tbl.insert(), rows)
    return len(rows)


def convert_child_points(conn, module: str, tag: str) -> dict[str, int]:
    """
    既有環境：子項點位 → 母項點位（2026-11-05 Samuel 裁示；可重跑）。
      1. 已轉換過（任何點位 created_by 含 fmappm2）或沒有點位 → 不做事
      2. 點位清單的子項中「有點位、但全部已停用」者 → 寫入 floor_map_disabled_sources（子項停用）
      3. 每個母項在子項樓層聯集各建一點；該層已有拖曳過（confirmed）的子項點位 → 沿用第一個的位置，否則待定位
      4. 原子項點位全部停用（保留資料列，不硬刪）
    不在點位清單的點（畫面上手動新增的）不動。
    """
    stat = {"disabled_children": 0, "parent_points": 0, "retired_child_points": 0}
    if module not in PM_ITEMS:
        return stat
    rows = [dict(r) for r in conn.execute(sa.text(
        f"SELECT id, floor_key, x, y, source_ref, placement, is_active, created_by, sort_order "
        f"FROM {TABLE} WHERE module = :m ORDER BY sort_order, id"
    ), {"m": module}).mappings().all()]
    if not rows or any(CONVERT_TAG in (r["created_by"] or "") for r in rows):
        return stat

    floors = child_floors(module)
    children = set(floors)
    old = [r for r in rows if r["source_ref"] in children]
    if not old:
        return stat

    # 2. 子項停用
    by_ref: dict[str, list[dict]] = {}
    for r in old:
        by_ref.setdefault(r["source_ref"], []).append(r)
    disabled = [ref for ref, rs in by_ref.items() if not any(x["is_active"] for x in rs)]
    now = twnow()
    for ref in disabled:
        conn.execute(sa.text(
            f"INSERT INTO {DISABLED_TABLE} (module, source_ref, disabled_by, disabled_at) "
            f"VALUES (:m, :r, :t, :n) ON CONFLICT (module, source_ref) DO NOTHING"
        ), {"m": module, "r": ref, "t": tag, "n": now})
    stat["disabled_children"] = len(disabled)

    # 3. 母項點位（沿用已校正子項的位置）
    positions: dict[tuple[str, str], tuple[float, float]] = {}
    for r in old:
        if r["placement"] != "confirmed":
            continue
        key = (parent_of(module, r["source_ref"]) or r["source_ref"], r["floor_key"])
        positions.setdefault(key, (float(r["x"]), float(r["y"])))
    new_rows = _parent_rows(module, f"{tag}:{CONVERT_TAG}", positions)
    if new_rows:
        conn.execute(_tbl.insert(), new_rows)
    stat["parent_points"] = len(new_rows)

    # 4. 原子項點位停用
    ids = [r["id"] for r in old if r["is_active"]]
    if ids:
        conn.execute(
            sa.text(f"UPDATE {TABLE} SET is_active = false, updated_by = :t, updated_at = :n WHERE id IN :ids")
            .bindparams(sa.bindparam("ids", expanding=True)),
            {"t": f"{tag}:{CONVERT_TAG}:retired", "n": now, "ids": ids},
        )
    stat["retired_child_points"] = len(ids)
    return stat


def ensure_pm_columns(conn) -> None:
    """
    開發環境（start-dev.bat 不跑 alembic）保底：補 Alembic fmappm2 的欄位與資料表（PostgreSQL，可重跑）。
    與 migration 內容相同。
    """
    insp = sa.inspect(conn)
    if insp.has_table("mall_pm_batch_item"):
        conn.execute(sa.text("ALTER TABLE mall_pm_batch_item ADD COLUMN IF NOT EXISTS parent_name VARCHAR(200)"))
        conn.execute(sa.text("ALTER TABLE mall_pm_batch_item ADD COLUMN IF NOT EXISTS schedule_end_date VARCHAR(10)"))
    if insp.has_table("full_bldg_pm_batch_item"):
        conn.execute(sa.text("ALTER TABLE full_bldg_pm_batch_item ADD COLUMN IF NOT EXISTS schedule_end_date VARCHAR(10)"))
    conn.execute(sa.text(
        f"CREATE TABLE IF NOT EXISTS {DISABLED_TABLE} ("
        "id SERIAL PRIMARY KEY, module VARCHAR(50) NOT NULL, source_ref VARCHAR(200) NOT NULL, "
        "disabled_by VARCHAR(100), disabled_at TIMESTAMP NOT NULL DEFAULT now())"
    ))
    conn.execute(sa.text(
        f"CREATE UNIQUE INDEX IF NOT EXISTS ux_floor_map_disabled_sources ON {DISABLED_TABLE} (module, source_ref)"
    ))
