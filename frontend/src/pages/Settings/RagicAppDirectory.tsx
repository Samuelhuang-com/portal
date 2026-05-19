/**
 * Ragic 應用程式對應表
 * 路徑：/settings/ragic-app-directory
 *
 * 顯示 235 筆 Ragic 應用程式，前兩欄為可編輯的 Portal 對應資訊：
 *   - Portal 名稱（portal_name）
 *   - Portal 超連結（portal_url）
 * 其餘欄位為靜態參考資料（序號、模組、應用程式名稱、URL、類型、備註）。
 */

import React, { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  EditOutlined,
  ExportOutlined,
  LinkOutlined,
  SaveOutlined,
} from '@ant-design/icons'
import apiClient from '@/api/client'
import { menuItems } from '@/components/Layout/MainLayout'

const { Title, Text, Link } = Typography

// ── 靜態資料：219 筆 Ragic 應用程式 ─────────────────────────────────────────
interface RagicApp {
  itemNo: number
  module: string
  name: string
  url: string
  type: string
  note: string
  // 可編輯的 portal 欄位（由後端載入後合併）
  portalName: string
  portalUrl: string
  // 本地 DB 表（靜態推導，不存 DB）
  localTable: string
}

const RAGIC_APPS_STATIC: Omit<RagicApp, 'portalName' | 'portalUrl' | 'localTable'>[] = [
  { itemNo: 1,   module: '例行抄表/設備檢查', name: '全棟電錶ACB123',                      url: 'https://ap12.ragic.com/soutlet001/hotel-routine-inspection/11',                  type: '表單/作業', note: '' },
  { itemNo: 2,   module: '例行抄表/設備檢查', name: '商場空調箱電錶-2',                     url: 'https://ap12.ragic.com/soutlet001/hotel-routine-inspection/12',                  type: '表單/作業', note: '' },
  { itemNo: 3,   module: '例行抄表/設備檢查', name: '專櫃水錶',                             url: 'https://ap12.ragic.com/soutlet001/hotel-routine-inspection/15',                  type: '表單/作業', note: '' },
  { itemNo: 4,   module: '例行抄表/設備檢查', name: '專櫃電錶',                             url: 'https://ap12.ragic.com/soutlet001/hotel-routine-inspection/14',                  type: '表單/作業', note: '' },
  { itemNo: 5,   module: '保全巡檢',          name: '保全巡檢 - 1F ~ 3F (夜間巡檢)',        url: 'https://ap12.ragic.com/soutlet001/security-patrol/2',                            type: '表單/作業', note: '' },
  { itemNo: 6,   module: '保全巡檢',          name: '保全巡檢 - 1F 閉店巡檢',               url: 'https://ap12.ragic.com/soutlet001/security-patrol/6',                            type: '表單/作業', note: '' },
  { itemNo: 7,   module: '保全巡檢',          name: '保全巡檢 - 1F 開店準備',               url: 'https://ap12.ragic.com/soutlet001/security-patrol/9',                            type: '表單/作業', note: '' },
  { itemNo: 8,   module: '保全巡檢',          name: '保全巡檢 - 1F夜間巡檢 (飯店大廳)',     url: 'https://ap12.ragic.com/soutlet001/security-patrol/5',                            type: '表單/作業', note: '' },
  { itemNo: 9,   module: '保全巡檢',          name: '保全巡檢 - 4F (夜間巡檢)',             url: 'https://ap12.ragic.com/soutlet001/security-patrol/4',                            type: '表單/作業', note: '' },
  { itemNo: 10,  module: '保全巡檢',          name: '保全巡檢 - 5F ~ 10F (夜間巡檢)',       url: 'https://ap12.ragic.com/soutlet001/security-patrol/3',                            type: '表單/作業', note: '' },
  { itemNo: 11,  module: '保全巡檢',          name: '保全巡檢總表',                         url: 'https://ap12.ragic.com/soutlet001/security-patrol/10',                           type: '報表/清單', note: '' },
  { itemNo: 12,  module: '保全巡檢',          name: '保全工時表',                           url: 'https://ap12.ragic.com/soutlet001/security-patrol/8',                            type: '報表/清單', note: '' },
  { itemNo: 13,  module: '保全巡檢',          name: '保全每日巡檢 - B1F~B4F夜間巡檢',       url: 'https://ap12.ragic.com/soutlet001/security-patrol/1',                            type: '表單/作業', note: '' },
  { itemNo: 14,  module: '保全巡檢',          name: '巡檢紀錄',                             url: 'https://ap12.ragic.com/soutlet001/security-patrol/23',                           type: '報表/清單', note: '' },
  { itemNo: 15,  module: '保全巡檢',          name: '巡檢結果表',                           url: 'https://ap12.ragic.com/soutlet001/security-patrol/12',                           type: '報表/清單', note: '' },
  { itemNo: 16,  module: '保全巡檢',          name: '巡檢項目設定表',                       url: 'https://ap12.ragic.com/soutlet001/security-patrol/11',                           type: '設定主檔',  note: '' },
  { itemNo: 17,  module: '保全巡檢',          name: '巡檢點主檔',                           url: 'https://ap12.ragic.com/soutlet001/security-patrol/22',                           type: '設定主檔',  note: '' },
  { itemNo: 18,  module: '保全巡檢',          name: '首頁',                                 url: 'https://ap12.ragic.com/soutlet001/security-patrol/7',                            type: '入口頁',    note: '' },
  { itemNo: 19,  module: '共用表單',          name: '出差申請單',                           url: 'https://ap12.ragic.com/soutlet001/public-form/19',                               type: '表單/作業', note: '' },
  { itemNo: 20,  module: '共用表單',          name: '忘打卡申請單',                         url: 'https://ap12.ragic.com/soutlet001/public-form/9',                                type: '表單/作業', note: '' },
  { itemNo: 21,  module: '共用表單',          name: '用印申請表',                           url: 'https://ap12.ragic.com/soutlet001/public-form/21',                               type: '表單/作業', note: '' },
  { itemNo: 22,  module: '共用表單',          name: '維春自由公告',                         url: 'https://ap12.ragic.com/soutlet001/public-form/42',                               type: '表單/作業', note: '' },
  { itemNo: 23,  module: '共用表單',          name: '維春自由商場共用簽呈',                 url: 'https://ap12.ragic.com/soutlet001/public-form/43',                               type: '表單/作業', note: '' },
  { itemNo: 24,  module: '共用表單',          name: '維春自由簽呈',                         url: 'https://ap12.ragic.com/soutlet001/public-form/22',                               type: '表單/作業', note: '' },
  { itemNo: 25,  module: '共用表單',          name: '調 班 單',                             url: 'https://ap12.ragic.com/soutlet001/public-form/17',                               type: '其他',      note: '' },
  { itemNo: 26,  module: '共用表單',          name: '資產異動單',                           url: 'https://ap12.ragic.com/soutlet001/public-form/44',                               type: '表單/作業', note: '' },
  { itemNo: 27,  module: '共用表單',          name: '資訊報修單',                           url: 'https://ap12.ragic.com/soutlet001/public-form/36',                               type: '其他',      note: '' },
  { itemNo: 28,  module: '共用表單（群組）',  name: '出差申請單',                           url: 'https://ap12.ragic.com/soutlet001/public-form-for-group-use/7',                  type: '表單/作業', note: '' },
  { itemNo: 29,  module: '共用表單（群組）',  name: '忘打卡申請單',                         url: 'https://ap12.ragic.com/soutlet001/public-form-for-group-use/5',                  type: '表單/作業', note: '' },
  { itemNo: 30,  module: '共用表單（群組）',  name: '維春商場簽呈',                         url: 'https://ap12.ragic.com/soutlet001/public-form-for-group-use/8',                  type: '表單/作業', note: '' },
  { itemNo: 31,  module: '共用表單（群組）',  name: '維春自由商場共用簽呈',                 url: 'https://ap12.ragic.com/soutlet001/public-form-for-group-use/12',                 type: '表單/作業', note: '' },
  { itemNo: 32,  module: '共用表單（群組）',  name: '調 班 單',                             url: 'https://ap12.ragic.com/soutlet001/public-form-for-group-use/6',                  type: '其他',      note: '' },
  { itemNo: 33,  module: '共用表單（群組）',  name: '資訊報修單',                           url: 'https://ap12.ragic.com/soutlet001/public-form-for-group-use/10',                 type: '其他',      note: '' },
  { itemNo: 34,  module: '原澄/上澄簽核',    name: '一般文件 上澄',                        url: 'https://ap12.ragic.com/soutlet001/decantation/17',                               type: '表單/作業', note: '上澄' },
  { itemNo: 35,  module: '原澄/上澄簽核',    name: '一般文件 原澄',                        url: 'https://ap12.ragic.com/soutlet001/decantation/15',                               type: '表單/作業', note: '原澄' },
  { itemNo: 36,  module: '原澄/上澄簽核',    name: '上澄簽呈',                             url: 'https://ap12.ragic.com/soutlet001/decantation/7',                                type: '表單/作業', note: '上澄' },
  { itemNo: 37,  module: '原澄/上澄簽核',    name: '原澄簽呈',                             url: 'https://ap12.ragic.com/soutlet001/decantation/6',                                type: '表單/作業', note: '原澄' },
  { itemNo: 38,  module: '原澄/上澄簽核',    name: '用印申請表',                           url: 'https://ap12.ragic.com/soutlet001/decantation/20',                               type: '表單/作業', note: '' },
  { itemNo: 39,  module: '原澄/上澄簽核',    name: '請款單 上澄',                          url: 'https://ap12.ragic.com/soutlet001/decantation/1',                                type: '表單/作業', note: '上澄' },
  { itemNo: 40,  module: '原澄/上澄簽核',    name: '請款單 原澄',                          url: 'https://ap12.ragic.com/soutlet001/decantation/3',                                type: '表單/作業', note: '原澄' },
  { itemNo: 41,  module: '原澄/上澄簽核',    name: '請購單 上澄',                          url: 'https://ap12.ragic.com/soutlet001/decantation/2',                                type: '表單/作業', note: '上澄' },
  { itemNo: 42,  module: '原澄/上澄簽核',    name: '請購單 原澄',                          url: 'https://ap12.ragic.com/soutlet001/decantation/4',                                type: '表單/作業', note: '原澄' },
  { itemNo: 43,  module: '原澄/上澄簽核',    name: '預支證明單 上澄',                      url: 'https://ap12.ragic.com/soutlet001/decantation/18',                               type: '表單/作業', note: '上澄' },
  { itemNo: 44,  module: '原澄/上澄簽核',    name: '預支證明單 原澄',                      url: 'https://ap12.ragic.com/soutlet001/decantation/19',                               type: '表單/作業', note: '原澄' },
  { itemNo: 45,  module: '原澄/上澄請款',    name: '請款單 上澄',                          url: 'https://ap12.ragic.com/soutlet001/clear-the-excess-boardroom-interior/1',        type: '表單/作業', note: '上澄' },
  { itemNo: 46,  module: '原澄/上澄請款',    name: '請款單 原澄',                          url: 'https://ap12.ragic.com/soutlet001/clear-the-excess-boardroom-interior/3',        type: '表單/作業', note: '原澄' },
  { itemNo: 47,  module: '原澄/上澄財務清算', name: '應付憑單 上澄',                       url: 'https://ap12.ragic.com/soutlet001/clearance-financial-office/4',                 type: '表單/作業', note: '上澄' },
  { itemNo: 48,  module: '原澄/上澄財務清算', name: '應付憑單 原澄',                       url: 'https://ap12.ragic.com/soutlet001/clearance-financial-office/3',                 type: '表單/作業', note: '原澄' },
  { itemNo: 49,  module: '原澄/上澄財務清算', name: '請款單 上澄',                         url: 'https://ap12.ragic.com/soutlet001/clearance-financial-office/1',                 type: '表單/作業', note: '上澄' },
  { itemNo: 50,  module: '原澄/上澄財務清算', name: '請款單 原澄',                         url: 'https://ap12.ragic.com/soutlet001/clearance-financial-office/2',                 type: '表單/作業', note: '原澄' },
  { itemNo: 51,  module: '商場工務每日巡檢', name: '商場工務每日巡檢 - 1F',                url: 'https://ap12.ragic.com/soutlet001/mall-facility-inspection/5',                   type: '表單/作業', note: '' },
  { itemNo: 52,  module: '商場工務每日巡檢', name: '商場工務每日巡檢 - 1F ~ 3F',           url: 'https://ap12.ragic.com/soutlet001/mall-facility-inspection/4',                   type: '表單/作業', note: '' },
  { itemNo: 53,  module: '商場工務每日巡檢', name: '商場工務每日巡檢 - 3F',                url: 'https://ap12.ragic.com/soutlet001/mall-facility-inspection/3',                   type: '表單/作業', note: '' },
  { itemNo: 54,  module: '商場工務每日巡檢', name: '商場工務每日巡檢 - 4F',                url: 'https://ap12.ragic.com/soutlet001/mall-facility-inspection/2',                   type: '表單/作業', note: '' },
  { itemNo: 55,  module: '商場工務每日巡檢', name: '商場工務每日巡檢 - B1F ~ B4F',         url: 'https://ap12.ragic.com/soutlet001/mall-facility-inspection/7',                   type: '表單/作業', note: '' },
  { itemNo: 56,  module: '封存巡檢資料',     name: '全棟電錶ACB123',                       url: 'https://ap12.ragic.com/soutlet001/archive-old-data/9',                           type: '表單/作業', note: '' },
  { itemNo: 57,  module: '封存巡檢資料',     name: '商場空調箱電錶-2',                     url: 'https://ap12.ragic.com/soutlet001/archive-old-data/10',                          type: '表單/作業', note: '' },
  { itemNo: 58,  module: '封存巡檢資料',     name: '工務巡檢總表',                         url: 'https://ap12.ragic.com/soutlet001/archive-old-data/6',                           type: '報表/清單', note: '' },
  { itemNo: 59,  module: '封存巡檢資料',     name: '飯店巡檢 1F(封存)',                    url: 'https://ap12.ragic.com/soutlet001/archive-old-data/18',                          type: '封存資料',  note: '歷史封存' },
  { itemNo: 60,  module: '封存巡檢資料',     name: '飯店巡檢 2F(封存)',                    url: 'https://ap12.ragic.com/soutlet001/archive-old-data/17',                          type: '封存資料',  note: '歷史封存' },
  { itemNo: 61,  module: '封存巡檢資料',     name: '飯店巡檢 4F(封存)',                    url: 'https://ap12.ragic.com/soutlet001/archive-old-data/16',                          type: '封存資料',  note: '歷史封存' },
  { itemNo: 62,  module: '封存巡檢資料',     name: '飯店巡檢 RF(封存)',                    url: 'https://ap12.ragic.com/soutlet001/archive-old-data/14',                          type: '封存資料',  note: '歷史封存' },
  { itemNo: 63,  module: '封存巡檢資料',     name: '飯店巡檢4F -10F(封存)',                url: 'https://ap12.ragic.com/soutlet001/archive-old-data/15',                          type: '封存資料',  note: '歷史封存' },
  { itemNo: 64,  module: '封存巡檢資料',     name: '飯店巡檢結果表',                       url: 'https://ap12.ragic.com/soutlet001/archive-old-data/8',                           type: '報表/清單', note: '' },
  { itemNo: 65,  module: '封存巡檢資料',     name: '飯店巡檢總表(封存)',                   url: 'https://ap12.ragic.com/soutlet001/archive-old-data/13',                          type: '封存資料',  note: '歷史封存' },
  { itemNo: 66,  module: '封存巡檢資料',     name: '飯店巡檢項目設定表',                   url: 'https://ap12.ragic.com/soutlet001/archive-old-data/7',                           type: '設定主檔',  note: '' },
  { itemNo: 67,  module: '工務/保養報表',    name: '客房保養總表',                         url: 'https://ap12.ragic.com/soutlet001/report2/1',                                    type: '報表/清單', note: '' },
  { itemNo: 68,  module: '工務/保養報表',    name: '客房保養表明細',                       url: 'https://ap12.ragic.com/soutlet001/report2/2',                                    type: '報表/清單', note: '' },
  { itemNo: 69,  module: '工務/保養報表',    name: '工務工時表',                           url: 'https://ap12.ragic.com/soutlet001/report2/3',                                    type: '報表/清單', note: '' },
  { itemNo: 70,  module: '工務/保養報表',    name: '工務工時表 多版本表單',                url: 'https://ap12.ragic.com/soutlet001/report2/4',                                    type: '報表/清單', note: '' },
  { itemNo: 71,  module: '整棟工務每日巡檢', name: '整棟工務每日巡檢 - B1F',               url: 'https://ap12.ragic.com/soutlet001/full-building-inspection/4',                   type: '表單/作業', note: '' },
  { itemNo: 72,  module: '整棟工務每日巡檢', name: '整棟工務每日巡檢 - B2F',               url: 'https://ap12.ragic.com/soutlet001/full-building-inspection/3',                   type: '表單/作業', note: '' },
  { itemNo: 73,  module: '整棟工務每日巡檢', name: '整棟工務每日巡檢 - B4F',               url: 'https://ap12.ragic.com/soutlet001/full-building-inspection/2',                   type: '表單/作業', note: '' },
  { itemNo: 74,  module: '整棟工務每日巡檢', name: '整棟工務每日巡檢 - RF',                url: 'https://ap12.ragic.com/soutlet001/full-building-inspection/1',                   type: '表單/作業', note: '' },
  { itemNo: 75,  module: '春大直報修系統',   name: '春大直 - 前端報修',                   url: 'https://ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/1', type: '表單/作業', note: '前台/前端使用' },
  { itemNo: 76,  module: '春大直報修系統',   name: '春大直 - 前端驗收',                   url: 'https://ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/3', type: '表單/作業', note: '前台/前端使用、驗收流程' },
  { itemNo: 77,  module: '春大直報修系統',   name: '春大直 - 報修清單總表',               url: 'https://ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/6', type: '報表/清單', note: '' },
  { itemNo: 78,  module: '春大直報修系統',   name: '春大直 - 後勤維護',                   url: 'https://ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/2', type: '表單/作業', note: '後勤使用' },
  { itemNo: 79,  module: '春大直報修系統',   name: '春大直 - 管理結案',                   url: 'https://ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/4', type: '其他',      note: '' },
  { itemNo: 80,  module: '春大直報修系統',   name: '春大直 - 財務註記',                   url: 'https://ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/5', type: '表單/作業', note: '財務補註' },
  { itemNo: 81,  module: '商場主管室',       name: '用印申請表',                           url: 'https://ap12.ragic.com/soutlet001/lequn-executive-office/2',                     type: '表單/作業', note: '' },
  { itemNo: 82,  module: '商場主管室',       name: '維春商場簽呈',                         url: 'https://ap12.ragic.com/soutlet001/lequn-executive-office/11',                    type: '表單/作業', note: '' },
  { itemNo: 83,  module: '商場主管室',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-executive-office/9',                     type: '表單/作業', note: '' },
  { itemNo: 84,  module: '商場主管室',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-executive-office/10',                    type: '表單/作業', note: '' },
  { itemNo: 85,  module: '商場工務報修',     name: '工程報修單',                           url: 'https://ap12.ragic.com/soutlet001/lequn-public-works/2',                         type: '其他',      note: '' },
  { itemNo: 86,  module: '商場工務報修',     name: '工程報修單 查閱',                      url: 'https://ap12.ragic.com/soutlet001/lequn-public-works/7',                         type: '查閱頁',    note: '唯讀查閱' },
  { itemNo: 87,  module: '商場工務報修',     name: '工程維修單',                           url: 'https://ap12.ragic.com/soutlet001/lequn-public-works/4',                         type: '其他',      note: '' },
  { itemNo: 88,  module: '商場工務報修',     name: '工程維修單 房務部查閱用',              url: 'https://ap12.ragic.com/soutlet001/lequn-public-works/8',                         type: '查閱頁',    note: '唯讀查閱、房務部查閱' },
  { itemNo: 89,  module: '商場工務報修',     name: '工程維修單-飯店驗收',                  url: 'https://ap12.ragic.com/soutlet001/lequn-public-works/26',                        type: '表單/作業', note: '驗收流程' },
  { itemNo: 90,  module: '商場工務報表中心', name: '4.1 飯店報修狀態表',                   url: 'https://ap12.ragic.com/soutlet001/report/query?id=3&tabPath=Report',             type: '其他',      note: '' },
  { itemNo: 91,  module: '商場工務報表中心', name: '4.3 報修類型一覽表',                   url: 'https://ap12.ragic.com/soutlet001/report/query?id=5&tabPath=Report',             type: '報表/清單', note: '' },
  { itemNo: 92,  module: '商場工務報表中心', name: '4.4 客房報修表',                       url: 'https://ap12.ragic.com/soutlet001/report/query?id=6&tabPath=Report',             type: '其他',      note: '' },
  { itemNo: 93,  module: '商場工務報表中心', name: '報表中心',                             url: 'https://ap12.ragic.com/soutlet001/reportCenter',                                 type: '入口頁',    note: '' },
  { itemNo: 94,  module: '商場工務報表中心', name: '新報表',                               url: 'https://ap12.ragic.com/soutlet001/report?menuSetIndex=3',                        type: '入口頁',    note: '' },
  { itemNo: 95,  module: '商場工務報表中心', name: '飯店報修一覽表',                       url: 'https://ap12.ragic.com/soutlet001/report/query?id=4&tabPath=Report',             type: '報表/清單', note: '' },
  { itemNo: 96,  module: '商場工務部',       name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-public-works-department/4',              type: '表單/作業', note: '' },
  { itemNo: 97,  module: '商場工務部',       name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/lequn-public-works-department/5',              type: '表單/作業', note: '' },
  { itemNo: 98,  module: '商場工務部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-public-works-department/2',              type: '表單/作業', note: '' },
  { itemNo: 99,  module: '商場工務部',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-public-works-department/1',              type: '表單/作業', note: '' },
  { itemNo: 100, module: '商場工務部',       name: '預支證明單',                           url: 'https://ap12.ragic.com/soutlet001/lequn-public-works-department/3',              type: '表單/作業', note: '' },
  { itemNo: 101, module: '商場營業/一般文件', name: '採購單',                              url: 'https://ap12.ragic.com/soutlet001/new-tab/11',                                   type: '表單/作業', note: '' },
  { itemNo: 102, module: '商場營業/一般文件', name: '檔期活動提案書',                      url: 'https://ap12.ragic.com/soutlet001/new-tab/6',                                    type: '表單/作業', note: '' },
  { itemNo: 103, module: '商場營業/一般文件', name: '營業一般文件',                        url: 'https://ap12.ragic.com/soutlet001/new-tab/4',                                    type: '表單/作業', note: '' },
  { itemNo: 104, module: '商場營業/一般文件', name: '用印申請單',                          url: 'https://ap12.ragic.com/soutlet001/new-tab/9',                                    type: '表單/作業', note: '' },
  { itemNo: 105, module: '商場營業/一般文件', name: '設櫃提案書',                          url: 'https://ap12.ragic.com/soutlet001/new-tab/5',                                    type: '表單/作業', note: '' },
  { itemNo: 106, module: '商場營業/一般文件', name: '請款單',                              url: 'https://ap12.ragic.com/soutlet001/new-tab/8',                                    type: '表單/作業', note: '' },
  { itemNo: 107, module: '商場營業/一般文件', name: '請購單',                              url: 'https://ap12.ragic.com/soutlet001/new-tab/10',                                   type: '表單/作業', note: '' },
  { itemNo: 108, module: '商場營業/一般文件', name: '預支證明單',                          url: 'https://ap12.ragic.com/soutlet001/new-tab/12',                                   type: '表單/作業', note: '' },
  { itemNo: 109, module: '商場行銷部',       name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-marketing-department/14',                type: '表單/作業', note: '' },
  { itemNo: 110, module: '商場行銷部',       name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/lequn-marketing-department/11',                type: '表單/作業', note: '' },
  { itemNo: 111, module: '商場行銷部',       name: '行銷提案書',                           url: 'https://ap12.ragic.com/soutlet001/lequn-marketing-department/2',                 type: '表單/作業', note: '' },
  { itemNo: 112, module: '商場行銷部',       name: '設計項目需求申請單',                   url: 'https://ap12.ragic.com/soutlet001/lequn-marketing-department/3',                 type: '表單/作業', note: '' },
  { itemNo: 113, module: '商場行銷部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-marketing-department/13',                type: '表單/作業', note: '' },
  { itemNo: 114, module: '商場行銷部',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-marketing-department/12',                type: '表單/作業', note: '' },
  { itemNo: 115, module: '商場行銷部',       name: '預支證明單',                           url: 'https://ap12.ragic.com/soutlet001/lequn-marketing-department/15',                type: '表單/作業', note: '' },
  { itemNo: 116, module: '商場財務部',       name: '應付憑單',                             url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/7',                   type: '表單/作業', note: '' },
  { itemNo: 117, module: '商場財務部',       name: '應付憑單-請款單',                      url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/10',                  type: '表單/作業', note: '' },
  { itemNo: 118, module: '商場財務部',       name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/11',                  type: '表單/作業', note: '' },
  { itemNo: 119, module: '商場財務部',       name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/5',                   type: '表單/作業', note: '' },
  { itemNo: 120, module: '商場財務部',       name: '維春商場簽呈',                         url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/12',                  type: '表單/作業', note: '' },
  { itemNo: 121, module: '商場財務部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/6',                   type: '表單/作業', note: '' },
  { itemNo: 122, module: '商場財務部',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/9',                   type: '表單/作業', note: '' },
  { itemNo: 123, module: '商場財務部',       name: '預支證明單',                           url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/14',                  type: '表單/作業', note: '' },
  { itemNo: 124, module: '商場車務管理',     name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-traffic-management/10',                  type: '表單/作業', note: '' },
  { itemNo: 125, module: '商場車務管理',     name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/lequn-traffic-management/7',                   type: '表單/作業', note: '' },
  { itemNo: 126, module: '商場車務管理',     name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-traffic-management/5',                   type: '表單/作業', note: '' },
  { itemNo: 127, module: '商場車務管理',     name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/lequn-traffic-management/6',                   type: '表單/作業', note: '' },
  { itemNo: 128, module: '社區管理部',       name: '廠商資料表',                           url: 'https://ap12.ragic.com/soutlet001/community-management-department/15',           type: '其他',      note: '' },
  { itemNo: 129, module: '社區管理部',       name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/community-management-department/23',           type: '表單/作業', note: '' },
  { itemNo: 130, module: '社區管理部',       name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/community-management-department/27',           type: '表單/作業', note: '' },
  { itemNo: 131, module: '社區管理部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/community-management-department/24',           type: '表單/作業', note: '' },
  { itemNo: 132, module: '社區管理部',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/community-management-department/22',           type: '表單/作業', note: '' },
  { itemNo: 133, module: '社區管理部',       name: '預支證明單',                           url: 'https://ap12.ragic.com/soutlet001/community-management-department/37',           type: '表單/作業', note: '' },
  { itemNo: 134, module: '自由主管室',       name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/free-executive-office/10',                     type: '表單/作業', note: '' },
  { itemNo: 135, module: '自由主管室',       name: '維春自由簽呈',                         url: 'https://ap12.ragic.com/soutlet001/free-executive-office/12',                     type: '表單/作業', note: '' },
  { itemNo: 136, module: '自由主管室',       name: '薪資建議單',                           url: 'https://ap12.ragic.com/soutlet001/free-executive-office/3',                      type: '其他',      note: '' },
  { itemNo: 137, module: '自由主管室',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/free-executive-office/8',                      type: '表單/作業', note: '' },
  { itemNo: 138, module: '自由主管室',       name: '請款單(副總簽允)',                      url: 'https://ap12.ragic.com/soutlet001/free-executive-office/11',                     type: '表單/作業', note: '' },
  { itemNo: 139, module: '自由主管室',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/free-executive-office/9',                      type: '表單/作業', note: '' },
  { itemNo: 140, module: '自由營業部',       name: '專櫃名單',                             url: 'https://ap12.ragic.com/soutlet001/free-business-division/6',                     type: '其他',      note: '' },
  { itemNo: 141, module: '自由營業部',       name: '專櫃活動花車擺放申請單',               url: 'https://ap12.ragic.com/soutlet001/free-business-division/14',                    type: '表單/作業', note: '' },
  { itemNo: 142, module: '自由營業部',       name: '專櫃製作物申請單',                     url: 'https://ap12.ragic.com/soutlet001/free-business-division/13',                    type: '表單/作業', note: '' },
  { itemNo: 143, module: '自由營業部',       name: '檔期專櫃條件總表',                     url: 'https://ap12.ragic.com/soutlet001/free-business-division/9',                     type: '報表/清單', note: '' },
  { itemNo: 144, module: '自由營業部',       name: '檔期活動提案書',                       url: 'https://ap12.ragic.com/soutlet001/free-business-division/8',                     type: '表單/作業', note: '' },
  { itemNo: 145, module: '自由營業部',       name: '營業一般文件',                         url: 'https://ap12.ragic.com/soutlet001/free-business-division/15',                    type: '表單/作業', note: '' },
  { itemNo: 146, module: '自由營業部',       name: '用印申請表',                           url: 'https://ap12.ragic.com/soutlet001/free-business-division/22',                    type: '表單/作業', note: '' },
  { itemNo: 147, module: '自由營業部',       name: '設櫃提案書',                           url: 'https://ap12.ragic.com/soutlet001/free-business-division/11',                    type: '表單/作業', note: '' },
  { itemNo: 148, module: '自由營業部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/free-business-division/12',                    type: '表單/作業', note: '' },
  { itemNo: 149, module: '自由營業部',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/free-business-division/21',                    type: '表單/作業', note: '' },
  { itemNo: 150, module: '自由管理處',       name: '廠商資料表-管理部',                    url: 'https://ap12.ragic.com/soutlet001/freed-management-division/20',                 type: '其他',      note: '' },
  { itemNo: 151, module: '自由管理處',       name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/freed-management-division/31',                 type: '表單/作業', note: '' },
  { itemNo: 152, module: '自由管理處',       name: '用印申請表',                           url: 'https://ap12.ragic.com/soutlet001/freed-management-division/7',                  type: '表單/作業', note: '' },
  { itemNo: 153, module: '自由管理處',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/freed-management-division/8',                  type: '表單/作業', note: '' },
  { itemNo: 154, module: '自由管理處',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/freed-management-division/19',                 type: '表單/作業', note: '' },
  { itemNo: 155, module: '自由管理處',       name: '請購單(舊版停用)',                      url: 'https://ap12.ragic.com/soutlet001/freed-management-division/9',                  type: '表單/作業', note: '舊版停用' },
  { itemNo: 156, module: '自由管理處',       name: '預支證明單',                           url: 'https://ap12.ragic.com/soutlet001/freed-management-division/16',                 type: '表單/作業', note: '' },
  { itemNo: 157, module: '自由管理部',       name: '參照',                                 url: 'https://ap12.ragic.com/soutlet001/free-management-department/17',                type: '其他',      note: '' },
  { itemNo: 158, module: '自由管理部',       name: '廠商折抵申請',                         url: 'https://ap12.ragic.com/soutlet001/free-management-department/19',                type: '其他',      note: '' },
  { itemNo: 159, module: '自由管理部',       name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/free-management-department/9',                 type: '表單/作業', note: '' },
  { itemNo: 160, module: '自由管理部',       name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/free-management-department/12',                type: '表單/作業', note: '' },
  { itemNo: 161, module: '自由管理部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/free-management-department/8',                 type: '表單/作業', note: '' },
  { itemNo: 162, module: '自由管理部',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/free-management-department/10',                type: '表單/作業', note: '' },
  { itemNo: 163, module: '自由管理部',       name: '預支證明單',                           url: 'https://ap12.ragic.com/soutlet001/free-management-department/11',                type: '表單/作業', note: '' },
  { itemNo: 164, module: '自由行銷部',       name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/marketing/41',                                 type: '表單/作業', note: '' },
  { itemNo: 165, module: '自由行銷部',       name: '用印申請表',                           url: 'https://ap12.ragic.com/soutlet001/marketing/38',                                 type: '表單/作業', note: '' },
  { itemNo: 166, module: '自由行銷部',       name: '維春自由簽呈',                         url: 'https://ap12.ragic.com/soutlet001/marketing/45',                                 type: '表單/作業', note: '' },
  { itemNo: 167, module: '自由行銷部',       name: '行銷提案書',                           url: 'https://ap12.ragic.com/soutlet001/marketing/5',                                  type: '表單/作業', note: '' },
  { itemNo: 168, module: '自由行銷部',       name: '行銷提案書(上澄)',                      url: 'https://ap12.ragic.com/soutlet001/marketing/30',                                 type: '表單/作業', note: '上澄' },
  { itemNo: 169, module: '自由行銷部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/marketing/32',                                 type: '表單/作業', note: '' },
  { itemNo: 170, module: '自由行銷部',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/marketing/40',                                 type: '表單/作業', note: '' },
  { itemNo: 171, module: '自由行銷部',       name: '預支證明單',                           url: 'https://ap12.ragic.com/soutlet001/marketing/31',                                 type: '表單/作業', note: '' },
  { itemNo: 172, module: '自由設計部',       name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/free-design-department/6',                     type: '表單/作業', note: '' },
  { itemNo: 173, module: '自由設計部',       name: '每月製作物請款單',                     url: 'https://ap12.ragic.com/soutlet001/free-design-department/4',                     type: '表單/作業', note: '' },
  { itemNo: 174, module: '自由設計部',       name: '每月製作物請款單 (健豪)',               url: 'https://ap12.ragic.com/soutlet001/free-design-department/3',                     type: '表單/作業', note: '' },
  { itemNo: 175, module: '自由設計部',       name: '設計提案書',                           url: 'https://ap12.ragic.com/soutlet001/free-design-department/5',                     type: '表單/作業', note: '' },
  { itemNo: 176, module: '自由設計部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/free-design-department/1',                     type: '表單/作業', note: '' },
  { itemNo: 177, module: '自由設計部',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/free-design-department/2',                     type: '表單/作業', note: '' },
  { itemNo: 178, module: '自由財務部',       name: '應付憑單',                             url: 'https://ap12.ragic.com/soutlet001/free-finance-department/6',                    type: '表單/作業', note: '' },
  { itemNo: 179, module: '自由財務部',       name: '應付憑單 票貼',                        url: 'https://ap12.ragic.com/soutlet001/free-finance-department/16',                   type: '表單/作業', note: '' },
  { itemNo: 180, module: '自由財務部',       name: '應付憑單-請款單',                      url: 'https://ap12.ragic.com/soutlet001/free-finance-department/19',                   type: '表單/作業', note: '' },
  { itemNo: 181, module: '自由財務部',       name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/free-finance-department/27',                   type: '表單/作業', note: '' },
  { itemNo: 182, module: '自由財務部',       name: '維春自由簽呈',                         url: 'https://ap12.ragic.com/soutlet001/free-finance-department/28',                   type: '表單/作業', note: '' },
  { itemNo: 183, module: '自由財務部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/free-finance-department/15',                   type: '表單/作業', note: '' },
  { itemNo: 184, module: '自由財務部',       name: '資金調撥單',                           url: 'https://ap12.ragic.com/soutlet001/free-finance-department/17',                   type: '表單/作業', note: '' },
  { itemNo: 185, module: '自由財務部',       name: '預支證明單',                           url: 'https://ap12.ragic.com/soutlet001/free-finance-department/25',                   type: '表單/作業', note: '' },
  { itemNo: 186, module: '自由資訊部',       name: '出差申請單',                           url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/8',             type: '表單/作業', note: '' },
  { itemNo: 187, module: '自由資訊部',       name: '小額支出證明單',                       url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/59',            type: '其他',      note: '' },
  { itemNo: 188, module: '自由資訊部',       name: '廠商資料表-資訊部',                    url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/24',            type: '其他',      note: '' },
  { itemNo: 189, module: '自由資訊部',       name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/33',            type: '表單/作業', note: '' },
  { itemNo: 190, module: '自由資訊部',       name: '測試',                                 url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/63',            type: '其他',      note: '' },
  { itemNo: 191, module: '自由資訊部',       name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/28',            type: '表單/作業', note: '' },
  { itemNo: 192, module: '自由資訊部',       name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/22',            type: '表單/作業', note: '' },
  { itemNo: 193, module: '自由資訊部',       name: '請款單 (資訊簡化)',                    url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/58',            type: '表單/作業', note: '' },
  { itemNo: 194, module: '自由資訊部',       name: '請款單 財務列印',                      url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/31',            type: '表單/作業', note: '' },
  { itemNo: 195, module: '自由資訊部',       name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/department-of-free-information/23',            type: '表單/作業', note: '' },
  { itemNo: 196, module: '資訊部',           name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/joy-group-it-department/12',                   type: '表單/作業', note: '' },
  { itemNo: 197, module: '資訊部',           name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/joy-group-it-department/15',                   type: '表單/作業', note: '' },
  { itemNo: 198, module: '資訊部',           name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/joy-group-it-department/14',                   type: '表單/作業', note: '' },
  { itemNo: 199, module: '資訊部',           name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/joy-group-it-department/11',                   type: '表單/作業', note: '' },
  { itemNo: 200, module: '資訊部',           name: '部門會辦單 (試作中)',                   url: 'https://ap12.ragic.com/soutlet001/joy-group-it-department/37',                   type: '表單/作業', note: '試作中' },
  { itemNo: 201, module: '週期保養',         name: '商場週期保養日誌(主管排定)',             url: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/13',                      type: '表單/作業', note: '主管排程' },
  { itemNo: 202, module: '週期保養',         name: '商場週期保養日誌(主表單)',               url: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/12',                      type: '其他',      note: '主表' },
  { itemNo: 203, module: '週期保養',         name: '商場週期保養日誌(同仁執行)',             url: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/18',                      type: '表單/作業', note: '執行端' },
  { itemNo: 204, module: '週期保養',         name: '客房保養表',                           url: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/4',                       type: '表單/作業', note: '' },
  { itemNo: 205, module: '週期保養',         name: '飯店週期保養表(主管排定)',               url: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/7',                       type: '表單/作業', note: '主管排程' },
  { itemNo: 206, module: '週期保養',         name: '飯店週期保養表(主表單)',                 url: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/6',                       type: '表單/作業', note: '主表' },
  { itemNo: 207, module: '週期保養',         name: '飯店週期保養表(同仁執行)',               url: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/8',                       type: '表單/作業', note: '執行端' },
  { itemNo: 208, module: '週期保養',         name: '飯店週期保養表(同仁執行) - 子表: 項目',  url: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/11',                      type: '子表',      note: '子表、執行端' },
  { itemNo: 209, module: '集團專案',         name: '採購單',                               url: 'https://ap12.ragic.com/soutlet001/happy-group-project/5',                        type: '表單/作業', note: '' },
  { itemNo: 210, module: '集團專案',         name: '用印申請單',                           url: 'https://ap12.ragic.com/soutlet001/happy-group-project/4',                        type: '表單/作業', note: '' },
  { itemNo: 211, module: '集團專案',         name: '請款單',                               url: 'https://ap12.ragic.com/soutlet001/happy-group-project/1',                        type: '表單/作業', note: '' },
  { itemNo: 212, module: '集團專案',         name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/happy-group-project/2',                        type: '表單/作業', note: '' },
  { itemNo: 213, module: '集團專案',         name: '請購單',                               url: 'https://ap12.ragic.com/soutlet001/happy-group-project/6',                        type: '表單/作業', note: '' },
  { itemNo: 214, module: '集團專案',         name: '預支證明單',                           url: 'https://ap12.ragic.com/soutlet001/happy-group-project/7',                        type: '表單/作業', note: '' },
  { itemNo: 215, module: '飯店工務每日巡檢', name: '飯店工務每日巡檢 - 1F',                url: 'https://ap12.ragic.com/soutlet001/main-project-inspection/21',                   type: '表單/作業', note: '' },
  { itemNo: 216, module: '飯店工務每日巡檢', name: '飯店工務每日巡檢 - 2F',                url: 'https://ap12.ragic.com/soutlet001/main-project-inspection/20',                   type: '表單/作業', note: '' },
  { itemNo: 217, module: '飯店工務每日巡檢', name: '飯店工務每日巡檢 - 4F',                url: 'https://ap12.ragic.com/soutlet001/main-project-inspection/19',                   type: '表單/作業', note: '' },
  { itemNo: 218, module: '飯店工務每日巡檢', name: '飯店工務每日巡檢 - 4F - 10F',          url: 'https://ap12.ragic.com/soutlet001/main-project-inspection/18',                   type: '表單/作業', note: '' },
  { itemNo: 219, module: '飯店工務每日巡檢', name: '飯店工務每日巡檢 - RF',                url: 'https://ap12.ragic.com/soutlet001/main-project-inspection/17',                   type: '表單/作業', note: '' },
  // ── 核准請購單（9 部門，Master+Detail 雙層同步）─────────────────────────────
  { itemNo: 220, module: '核准請購單',       name: '執董室請購單（清單）',                url: 'https://ap12.ragic.com/soutlet001/lequn-executive-office/10',                   type: '報表/清單', note: 'Portal同步' },
  { itemNo: 221, module: '核准請購單',       name: '執董室請購單（內頁）',                url: 'https://ap12.ragic.com/soutlet001/lequn-executive-office/2',                    type: '表單/作業', note: 'Portal同步' },
  { itemNo: 222, module: '核准請購單',       name: '行銷部請購單（清單）',                url: 'https://ap12.ragic.com/soutlet001/lequn-marketing-department/12',               type: '報表/清單', note: 'Portal同步' },
  { itemNo: 223, module: '核准請購單',       name: '行銷部請購單（內頁）',                url: 'https://ap12.ragic.com/soutlet001/lequn-marketing-department/9',                type: '表單/作業', note: 'Portal同步' },
  { itemNo: 224, module: '核准請購單',       name: '管理部請購單（清單）',                url: 'https://ap12.ragic.com/soutlet001/community-management-department/22',           type: '報表/清單', note: 'Portal同步' },
  { itemNo: 225, module: '核准請購單',       name: '管理部請購單（內頁）',                url: 'https://ap12.ragic.com/soutlet001/community-management-department/31',           type: '表單/作業', note: 'Portal同步' },
  { itemNo: 226, module: '核准請購單',       name: '工務部請購單（清單）',                url: 'https://ap12.ragic.com/soutlet001/lequn-public-works-department/1',              type: '報表/清單', note: 'Portal同步' },
  { itemNo: 227, module: '核准請購單',       name: '工務部請購單（內頁）',                url: 'https://ap12.ragic.com/soutlet001/lequn-public-works-department/60',             type: '表單/作業', note: 'Portal同步' },
  { itemNo: 228, module: '核准請購單',       name: '專案請購單（清單）',                  url: 'https://ap12.ragic.com/soutlet001/happy-group-project/2',                       type: '報表/清單', note: 'Portal同步' },
  { itemNo: 229, module: '核准請購單',       name: '專案請購單（內頁）',                  url: 'https://ap12.ragic.com/soutlet001/happy-group-project/39',                      type: '表單/作業', note: 'Portal同步' },
  { itemNo: 230, module: '核准請購單',       name: '停管部請購單（清單）',                url: 'https://ap12.ragic.com/soutlet001/lequn-traffic-management/6',                   type: '報表/清單', note: 'Portal同步 / Ragic部門值=客服' },
  { itemNo: 231, module: '核准請購單',       name: '停管部請購單（內頁）',                url: 'https://ap12.ragic.com/soutlet001/lequn-traffic-management/6',                   type: '表單/作業', note: 'Portal同步 / 內頁與清單同sheet' },
  { itemNo: 232, module: '核准請購單',       name: '財務部請購單（清單）',                url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/9',                   type: '報表/清單', note: 'Portal同步' },
  { itemNo: 233, module: '核准請購單',       name: '財務部請購單（內頁）',                url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/2',                   type: '表單/作業', note: 'Portal同步' },
  { itemNo: 234, module: '核准請購單',       name: '資訊部請購單（清單）',                url: 'https://ap12.ragic.com/soutlet001/joy-group-it-department/11',                   type: '報表/清單', note: 'Portal同步' },
  { itemNo: 235, module: '核准請購單',       name: '資訊部請購單（內頁）',                url: 'https://ap12.ragic.com/soutlet001/lequn-finance-department/5',                   type: '表單/作業', note: 'Portal同步 / Ragic重導向至lequn-finance-department/5' },
]

// ── 本地 DB 表對應（Ragic sheet 路徑 → 本地 SQLite table name(s)）────────────
// 格式：多張表用 \n 分隔；未同步本地（直連 Ragic）的 sheet 不列入
const LOCAL_TABLE_MAP: Record<number, string> = {
  // 例行抄表/設備檢查 — 4 張 synced sheets → hotel_mr_batch / hotel_mr_reading（sheet_key 區分）
  1:  'hotel_mr_batch\nhotel_mr_reading',   // hotel-routine-inspection/11  (全棟電錶 ACB123)
  2:  'hotel_mr_batch\nhotel_mr_reading',   // hotel-routine-inspection/12  (商場空調箱電錶)
  3:  'hotel_mr_batch\nhotel_mr_reading',   // hotel-routine-inspection/15  (專櫃水錶)
  4:  'hotel_mr_batch\nhotel_mr_reading',   // hotel-routine-inspection/14  (專櫃電錶)

  // 保全巡檢 — 7 張 synced sheets → security_patrol_batch / _item（sheet_key 區分）
  5:  'security_patrol_batch\nsecurity_patrol_item',   // security-patrol/2  (1F~3F 夜間)
  6:  'security_patrol_batch\nsecurity_patrol_item',   // security-patrol/6  (1F 閉店)
  7:  'security_patrol_batch\nsecurity_patrol_item',   // security-patrol/9  (1F 開店)
  8:  'security_patrol_batch\nsecurity_patrol_item',   // security-patrol/5  (1F 夜間飯店大廳)
  9:  'security_patrol_batch\nsecurity_patrol_item',   // security-patrol/4  (4F)
  10: 'security_patrol_batch\nsecurity_patrol_item',   // security-patrol/3  (5F~10F)
  13: 'security_patrol_batch\nsecurity_patrol_item',   // security-patrol/1  (B1F~B4F)

  // 工務/保養報表
  68: 'room_maintenance_detail_records',               // report2/2 (客房保養表明細)

  // 整棟工務每日巡檢
  71: 'b1f_inspection_batch\nb1f_inspection_item',     // full-building-inspection/4 (B1F)
  72: 'b2f_inspection_batch\nb2f_inspection_item',     // full-building-inspection/3 (B2F)
  73: 'b4f_inspection_batch\nb4f_inspection_item',     // full-building-inspection/2 (B4F)
  74: 'rf_inspection_batch\nrf_inspection_item',       // full-building-inspection/1 (RF)

  // 春大直報修系統
  77: 'luqun_repair_case',                             // luqun-public-works-repair-reporting-system/6

  // 大直工務部（lequn-public-works/8 為實際同步來源；/4 為主表單無 PAGEID 查閱）
  87: 'dazhi_repair_case',                             // lequn-public-works/4  (工程維修單，主表單)
  88: 'dazhi_repair_case',                             // lequn-public-works/8  (工程維修單 房務部查閱用，Portal 同步來源)

  // 商場工務每日巡檢 — 5 張 synced sheets → mall_fi_inspection_batch / _item（sheet_key 區分）
  51: 'mall_fi_inspection_batch\nmall_fi_inspection_item',  // mall-facility-inspection/5 (1F)
  52: 'mall_fi_inspection_batch\nmall_fi_inspection_item',  // mall-facility-inspection/4 (1F~3F)
  53: 'mall_fi_inspection_batch\nmall_fi_inspection_item',  // mall-facility-inspection/3 (3F)
  54: 'mall_fi_inspection_batch\nmall_fi_inspection_item',  // mall-facility-inspection/2 (4F)
  55: 'mall_fi_inspection_batch\nmall_fi_inspection_item',  // mall-facility-inspection/7 (B1F~B4F)

  // 核准請購單（樂群）— 原始清單 sheet（同步資料來源）
  84:  'approved_purchase_requests\napproved_purchase_request_items',  // lequn-executive-office/10    (商場主管室/執董室 請購單)
  99:  'approved_purchase_requests\napproved_purchase_request_items',  // lequn-public-works-department/1 (商場工務部 請購單)
  107: 'approved_purchase_requests\napproved_purchase_request_items',  // new-tab/10                   (商場營業 請購單)
  114: 'approved_purchase_requests\napproved_purchase_request_items',  // lequn-marketing-department/12 (商場行銷部 請購單)
  122: 'approved_purchase_requests\napproved_purchase_request_items',  // lequn-finance-department/9   (商場財務部 請購單)
  127: 'approved_purchase_requests\napproved_purchase_request_items',  // lequn-traffic-management/6   (商場車務管理/停管部 請購單)
  132: 'approved_purchase_requests\napproved_purchase_request_items',  // community-management-department/22 (社區管理部 請購單)
  199: 'approved_purchase_requests\napproved_purchase_request_items',  // joy-group-it-department/11   (資訊部 請購單)
  212: 'approved_purchase_requests\napproved_purchase_request_items',  // happy-group-project/2        (集團專案 請購單)

  // 核准請款單（樂群）— 各部門請款清單 sheet
  98:  'approved_claim_requests\napproved_claim_request_items',  // lequn-public-works-department/2   (商場工務部 請款單)
  106: 'approved_claim_requests\napproved_claim_request_items',  // new-tab/8                         (商場營業 請款單)
  113: 'approved_claim_requests\napproved_claim_request_items',  // lequn-marketing-department/13     (商場行銷部 請款單)
  121: 'approved_claim_requests\napproved_claim_request_items',  // lequn-finance-department/6        (商場財務部 請款單)
  126: 'approved_claim_requests\napproved_claim_request_items',  // lequn-traffic-management/5        (商場車務管理 請款單)
  131: 'approved_claim_requests\napproved_claim_request_items',  // community-management-department/24 (社區管理部 請款單)
  198: 'approved_claim_requests\napproved_claim_request_items',  // joy-group-it-department/14        (資訊部 請款單)
  211: 'approved_claim_requests\napproved_claim_request_items',  // happy-group-project/1             (集團專案 請款單)

  // 日曜核准請購單（自由系列 請購單）→ nichiyo_purchase_requests / _items
  139: 'nichiyo_purchase_requests\nnichiyo_purchase_request_items',  // free-executive-office/9       (自由主管室 請購單)
  149: 'nichiyo_purchase_requests\nnichiyo_purchase_request_items',  // free-business-division/21     (自由營業部 請購單)
  154: 'nichiyo_purchase_requests\nnichiyo_purchase_request_items',  // freed-management-division/19  (自由管理處 請購單)
  162: 'nichiyo_purchase_requests\nnichiyo_purchase_request_items',  // free-management-department/10 (自由管理部 請購單)
  170: 'nichiyo_purchase_requests\nnichiyo_purchase_request_items',  // marketing/40                  (自由行銷部 請購單)
  177: 'nichiyo_purchase_requests\nnichiyo_purchase_request_items',  // free-design-department/2      (自由設計部 請購單)
  195: 'nichiyo_purchase_requests\nnichiyo_purchase_request_items',  // department-of-free-information/23 (自由資訊部 請購單)

  // 日曜核准請款單（自由系列 請款單）→ nichiyo_claim_requests / _items
  137: 'nichiyo_claim_requests\nnichiyo_claim_request_items',  // free-executive-office/8              (自由主管室 請款單)
  148: 'nichiyo_claim_requests\nnichiyo_claim_request_items',  // free-business-division/12            (自由營業部 請款單)
  153: 'nichiyo_claim_requests\nnichiyo_claim_request_items',  // freed-management-division/8          (自由管理處 請款單)
  161: 'nichiyo_claim_requests\nnichiyo_claim_request_items',  // free-management-department/8         (自由管理部 請款單)
  169: 'nichiyo_claim_requests\nnichiyo_claim_request_items',  // marketing/32                         (自由行銷部 請款單)
  176: 'nichiyo_claim_requests\nnichiyo_claim_request_items',  // free-design-department/1             (自由設計部 請款單)
  183: 'nichiyo_claim_requests\nnichiyo_claim_request_items',  // free-finance-department/15           (自由財務部 請款單)
  192: 'nichiyo_claim_requests\nnichiyo_claim_request_items',  // department-of-free-information/22    (自由資訊部 請款單)

  // 週期保養 — 商場
  203: 'mall_pm_batch\nmall_pm_batch_item',            // periodic-maintenance/18 (同仁執行)

  // 週期保養 — IHG 客房保養
  204: 'ihg_rm_master\nihg_rm_detail',                 // periodic-maintenance/4  (IHG客房保養)

  // 週期保養 — 飯店
  206: 'pm_batch',                                     // periodic-maintenance/6  (主表單)
  207: 'pm_batch_item',                                // periodic-maintenance/8  (同仁執行明細)
  208: 'pm_batch_item',                                // periodic-maintenance/11 (子表：項目)

  // 飯店工務每日巡檢 — 5 張 synced sheets → hotel_di_inspection_batch / _item（sheet_key 區分）
  215: 'hotel_di_inspection_batch\nhotel_di_inspection_item',  // main-project-inspection/21 (1F)
  216: 'hotel_di_inspection_batch\nhotel_di_inspection_item',  // main-project-inspection/20 (2F)
  217: 'hotel_di_inspection_batch\nhotel_di_inspection_item',  // main-project-inspection/19 (4F)
  218: 'hotel_di_inspection_batch\nhotel_di_inspection_item',  // main-project-inspection/18 (4F~10F)
  219: 'hotel_di_inspection_batch\nhotel_di_inspection_item',  // main-project-inspection/17 (RF)

  // 核准請購單（樂群）— 重複列出的 Portal 同步標記版（220-235）
  220: 'approved_purchase_requests\napproved_purchase_request_items',  // 執董室（清單）
  221: 'approved_purchase_requests\napproved_purchase_request_items',  // 執董室（內頁）
  222: 'approved_purchase_requests\napproved_purchase_request_items',  // 行銷部（清單）
  223: 'approved_purchase_requests\napproved_purchase_request_items',  // 行銷部（內頁）
  224: 'approved_purchase_requests\napproved_purchase_request_items',  // 管理部（清單）
  225: 'approved_purchase_requests\napproved_purchase_request_items',  // 管理部（內頁）
  226: 'approved_purchase_requests\napproved_purchase_request_items',  // 工務部（清單）
  227: 'approved_purchase_requests\napproved_purchase_request_items',  // 工務部（內頁）
  228: 'approved_purchase_requests\napproved_purchase_request_items',  // 專案（清單）
  229: 'approved_purchase_requests\napproved_purchase_request_items',  // 專案（內頁）
  230: 'approved_purchase_requests\napproved_purchase_request_items',  // 停管部（清單，Ragic部門值=客服）
  231: 'approved_purchase_requests\napproved_purchase_request_items',  // 停管部（內頁）
  232: 'approved_purchase_requests\napproved_purchase_request_items',  // 財務部（清單）
  233: 'approved_purchase_requests\napproved_purchase_request_items',  // 財務部（內頁）
  234: 'approved_purchase_requests\napproved_purchase_request_items',  // 資訊部（清單）
  235: 'approved_purchase_requests\napproved_purchase_request_items',  // 資訊部（內頁，Ragic重導向至lequn-finance-department/5）
}

// 類型 → Tag 顏色對應
const TYPE_COLOR: Record<string, string> = {
  '表單/作業': 'blue',
  '報表/清單': 'green',
  '設定主檔':  'orange',
  '入口頁':    'cyan',
  '封存資料':  'default',
  '查閱頁':    'geekblue',
  '子表':      'purple',
  '其他':      'default',
}

// ── Portal 選單層級 + 名稱查找表 ─────────────────────────────────────────────
// 從 menuItems 掃描三層結構，建立 portalUrl → { level, label } 的對照
// 每次前端重新載入自動同步，不需要手動維護
interface PortalMenuInfo { level: 1 | 2 | 3; label: string }

function buildPortalInfoMap(): Map<string, PortalMenuInfo> {
  const map = new Map<string, PortalMenuInfo>()
  for (const l1 of menuItems) {
    map.set(l1.key as string, { level: 1, label: l1.label as string })
    for (const l2 of ((l1 as any).children ?? []) as any[]) {
      map.set(l2.key as string, { level: 2, label: l2.label as string })
      for (const l3 of ((l2 as any).children ?? []) as any[]) {
        map.set(l3.key as string, { level: 3, label: l3.label as string })
      }
    }
  }
  return map
}
const PORTAL_INFO_MAP = buildPortalInfoMap()

function getPortalInfo(portalUrl: string): PortalMenuInfo | null {
  if (!portalUrl || !portalUrl.startsWith('/')) return null
  return PORTAL_INFO_MAP.get(portalUrl) ?? null
}

const LEVEL_CONFIG: Record<1 | 2 | 3, { label: string; color: string; bg: string; border: string }> = {
  1: { label: '一階', color: '#1677ff', bg: '#e6f4ff', border: '#91caff'  },
  2: { label: '二階', color: '#389e0d', bg: '#f6ffed', border: '#b7eb8f'  },
  3: { label: '三階', color: '#d46b08', bg: '#fff7e6', border: '#ffd591'  },
}

// ── 已知 Portal 對應預設值 ────────────────────────────────────────────────────
// 優先度：DB 使用者標註 > 此處預設 > 空白
// 規則：以 Ragic 模組/URL 推斷對應的 Portal 頁面
interface PortalDefault { portalName: string; portalUrl: string }

const PORTAL_DEFAULTS: Record<number, PortalDefault> = {
  // ── 例行抄表/設備檢查 (1~4) → 每日數值登錄表 ─────────────────────────────────
  ...(Object.fromEntries(
    [1,2,3,4].map((n) => [
      n, { portalName: '每日數值登錄表', portalUrl: '/hotel/daily-meter-readings' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 保全巡檢 (5~18) → 保全巡檢（整合後統一入口）──────────────────────────────
  ...(Object.fromEntries(
    [5,6,7,8,9,10,11,12,13,14,15,16,17,18].map((n) => [
      n, { portalName: '保全巡檢', portalUrl: '/security/dashboard' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 商場工務每日巡檢 (51~55) → 商場工務巡檢 ─────────────────────────────────
  ...(Object.fromEntries(
    [51,52,53,54,55].map((n) => [
      n, { portalName: '商場工務巡檢', portalUrl: '/mall-facility-inspection/dashboard' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 工務/保養報表 (67~70) → 客房保養明細 ────────────────────────────────────
  ...(Object.fromEntries(
    [67,68,69,70].map((n) => [
      n, { portalName: '客房保養明細', portalUrl: '/hotel/room-maintenance-detail' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 整棟工務每日巡檢 (71~74) → 整棟工務巡檢 ─────────────────────────────────
  ...(Object.fromEntries(
    [71,72,73,74].map((n) => [
      n, { portalName: '整棟工務巡檢', portalUrl: '/full-building-inspection/dashboard' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 春大直報修系統 (75~80) → 大直工務報修 ────────────────────────────────────
  ...(Object.fromEntries(
    [75,76,77,78,79,80].map((n) => [
      n, { portalName: '大直工務報修', portalUrl: '/dazhi-repair/dashboard' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 商場工務報修 (85~89) ─────────────────────────────────────────────────────
  // ⚠️  85、86、89 → 商場工務報修（查閱/驗收頁）
  // ⚠️  87、88   → 大直工務部（工程維修單；88 為 Portal 實際同步來源 lequn-public-works/8）
  ...(Object.fromEntries(
    [85,86,89].map((n) => [
      n, { portalName: '商場工務報修', portalUrl: '/luqun-repair/dashboard' },
    ])
  ) as Record<number, PortalDefault>),
  87: { portalName: '大直工務部', portalUrl: '/dazhi-repair/dashboard' },
  88: { portalName: '大直工務部（同步來源）', portalUrl: '/dazhi-repair/dashboard' },

  // ── 商場工務報表中心 (90~95) → 商場工務報修 ─────────────────────────────────
  ...(Object.fromEntries(
    [90,91,92,93,94,95].map((n) => [
      n, { portalName: '商場工務報修', portalUrl: '/luqun-repair/dashboard' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 核准請購單（樂群）— 原始 sheet (84,99,107,114,122,127,132,199,212) ───────
  ...(Object.fromEntries(
    [84,99,107,114,122,127,132,199,212].map((n) => [
      n, { portalName: '核准請購單月報表', portalUrl: '/purchase-report/monthly' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 核准請款單（樂群）— 各部門請款 sheet ─────────────────────────────────────
  ...(Object.fromEntries(
    [98,106,113,121,126,131,198,211].map((n) => [
      n, { portalName: '核准請款單月報表', portalUrl: '/claim-report/monthly' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 日曜核准請購單（自由系列 請購單）────────────────────────────────────────
  ...(Object.fromEntries(
    [139,149,154,162,170,177,195].map((n) => [
      n, { portalName: '日曜請購月報表', portalUrl: '/nichiyo-purchase-report/monthly' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 日曜核准請款單（自由系列 請款單）────────────────────────────────────────
  ...(Object.fromEntries(
    [137,148,153,161,169,176,183,192].map((n) => [
      n, { portalName: '日曜請款月報表', portalUrl: '/nichiyo-claim-report/monthly' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 週期保養 — 商場 (201~203) → 商場週期保養 ─────────────────────────────────
  ...(Object.fromEntries(
    [201,202,203].map((n) => [
      n, { portalName: '商場週期保養', portalUrl: '/mall/periodic-maintenance' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 週期保養 — IHG 客房保養 (204) → IHG客房保養矩陣 ─────────────────────────
  204: { portalName: 'IHG客房保養', portalUrl: '/hotel/ihg-room-maintenance' },

  // ── 週期保養 — 飯店 (205~208) → 飯店週期保養 ─────────────────────────────────
  ...(Object.fromEntries(
    [205,206,207,208].map((n) => [
      n, { portalName: '飯店週期保養', portalUrl: '/hotel/periodic-maintenance' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 飯店工務每日巡檢 (215~219) → 飯店每日巡檢 ───────────────────────────────
  ...(Object.fromEntries(
    [215,216,217,218,219].map((n) => [
      n, { portalName: '飯店每日巡檢', portalUrl: '/hotel/daily-inspection' },
    ])
  ) as Record<number, PortalDefault>),

  // ── 核准請購單（樂群）— Portal 同步標記版 (220~235) ──────────────────────────
  ...(Object.fromEntries(
    [220,221,222,223,224,225,226,227,228,229,230,231,232,233,234,235].map((n) => [
      n, { portalName: '核准請購單月報表', portalUrl: '/purchase-report/monthly' },
    ])
  ) as Record<number, PortalDefault>),
}

// ── API helper ───────────────────────────────────────────────────────────────
type Annotations = Record<number, { portal_name: string; portal_url: string }>

async function fetchAnnotations(): Promise<Annotations> {
  const res = await apiClient.get<Annotations>('/ragic/app-directory/annotations')
  return res.data
}

async function saveAnnotation(
  itemNo: number,
  portalName: string,
  portalUrl: string,
): Promise<void> {
  await apiClient.put(`/ragic/app-directory/annotations/${itemNo}`, {
    portal_name: portalName,
    portal_url:  portalUrl,
  })
}

// ── Component ────────────────────────────────────────────────────────────────
const RagicAppDirectory: React.FC = () => {
  const [data, setData] = useState<RagicApp[]>([])
  const [loading, setLoading] = useState(true)
  const [searchText, setSearchText] = useState('')
  const [filterModule, setFilterModule] = useState<string>('')

  // 編輯 Modal
  const [editTarget, setEditTarget] = useState<RagicApp | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  // ── 初始載入：合併靜態資料 + 後端標註 ──────────────────────────────────────
  // 優先度：DB 使用者標註 > PORTAL_DEFAULTS 預設 > 空白
  const load = useCallback(async () => {
    setLoading(true)
    try {
      const annotations = await fetchAnnotations()
      const merged: RagicApp[] = RAGIC_APPS_STATIC.map((app) => {
        const dbRow  = annotations[app.itemNo]
        const defRow = PORTAL_DEFAULTS[app.itemNo]
        // DB 有記錄（即使為空字串）時，以 DB 為準；否則用預設值
        if (dbRow !== undefined) {
          return {
            ...app,
            portalName: dbRow.portal_name,
            portalUrl:  dbRow.portal_url,
            localTable: LOCAL_TABLE_MAP[app.itemNo] ?? '',
          }
        }
        return {
          ...app,
          portalName: defRow?.portalName ?? '',
          portalUrl:  defRow?.portalUrl  ?? '',
          localTable: LOCAL_TABLE_MAP[app.itemNo] ?? '',
        }
      })
      setData(merged)
    } catch {
      // 若 API 失敗，仍以預設值顯示
      setData(
        RAGIC_APPS_STATIC.map((a) => ({
          ...a,
          portalName: PORTAL_DEFAULTS[a.itemNo]?.portalName ?? '',
          portalUrl:  PORTAL_DEFAULTS[a.itemNo]?.portalUrl  ?? '',
          localTable: LOCAL_TABLE_MAP[a.itemNo] ?? '',
        })),
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // ── 開啟編輯 Modal ──────────────────────────────────────────────────────────
  const openEdit = (row: RagicApp) => {
    setEditTarget(row)
    form.setFieldsValue({ portalName: row.portalName, portalUrl: row.portalUrl })
  }

  const handleSave = async () => {
    if (!editTarget) return
    try {
      const values = await form.validateFields()
      setSaving(true)
      await saveAnnotation(editTarget.itemNo, values.portalName ?? '', values.portalUrl ?? '')
      // 更新本地 state
      setData((prev) =>
        prev.map((r) =>
          r.itemNo === editTarget.itemNo
            ? { ...r, portalName: values.portalName ?? '', portalUrl: values.portalUrl ?? '' }
            : r,
        ),
      )
      message.success('Portal 標註已更新')
      setEditTarget(null)
    } catch (err: any) {
      if (err?.errorFields) return // Form validation error, don't close
      message.error('儲存失敗，請稍後再試')
    } finally {
      setSaving(false)
    }
  }

  // ── 篩選邏輯 ────────────────────────────────────────────────────────────────
  const filtered = data.filter((row) => {
    const q = searchText.toLowerCase()
    const matchSearch =
      !q ||
      row.name.toLowerCase().includes(q) ||
      row.module.toLowerCase().includes(q) ||
      row.portalName.toLowerCase().includes(q) ||
      row.note.toLowerCase().includes(q) ||
      row.url.toLowerCase().includes(q)
    const matchModule = !filterModule || row.module === filterModule
    return matchSearch && matchModule
  })

  const modules = Array.from(new Set(RAGIC_APPS_STATIC.map((a) => a.module))).sort()

  // ── 統計：有標註的筆數 ──────────────────────────────────────────────────────
  const annotatedCount = data.filter((r) => r.portalName).length

  // ── Table 欄位定義 ──────────────────────────────────────────────────────────
  const columns: ColumnsType<RagicApp> = [
    // ── Portal 欄位（前兩欄，重點標示）
    {
      title: (
        <span style={{ color: '#1B3A5C', fontWeight: 700 }}>
          Portal 名稱
        </span>
      ),
      dataIndex: 'portalName',
      key: 'portalName',
      width: 160,
      fixed: 'left',
      sorter: (a: RagicApp, b: RagicApp) => a.portalName.localeCompare(b.portalName, 'zh-TW'),
      render: (v: string, row: RagicApp) => (
        <div
          style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}
          onClick={() => openEdit(row)}
        >
          {v ? (
            <Tag color="blue" style={{ fontSize: 12, margin: 0 }}>{v}</Tag>
          ) : (
            <Text type="secondary" style={{ fontSize: 11 }}>— 未設定</Text>
          )}
          <EditOutlined style={{ color: '#4BA8E8', fontSize: 11, opacity: 0.7 }} />
        </div>
      ),
    },
    {
      title: (
        <span style={{ color: '#1B3A5C', fontWeight: 700 }}>
          Portal 超連結
        </span>
      ),
      dataIndex: 'portalUrl',
      key: 'portalUrl',
      width: 180,
      fixed: 'left',
      render: (v: string, row: RagicApp) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {v ? (
            // Portal 路由路徑（如 /security/dashboard）直接顯示；完整 URL 則截斷
            v.startsWith('/') ? (
              <Tooltip title={`Portal: ${v}`}>
                <span
                  style={{ fontSize: 12, color: '#4BA8E8', cursor: 'pointer' }}
                  onClick={() => openEdit(row)}
                >
                  <LinkOutlined style={{ marginRight: 3 }} />
                  {v}
                </span>
              </Tooltip>
            ) : (
              <Link href={v} target="_blank" style={{ fontSize: 12 }}>
                <LinkOutlined style={{ marginRight: 3 }} />
                {v.replace(/^https?:\/\//, '').substring(0, 30)}…
              </Link>
            )
          ) : (
            <Text
              type="secondary"
              style={{ fontSize: 11, cursor: 'pointer' }}
              onClick={() => openEdit(row)}
            >
              — 未設定
            </Text>
          )}
        </div>
      ),
    },
    // ── 選單位置（由 portalUrl 推導）
    {
      title: (
        <Tooltip title="此 Ragic 應用程式對應的 Portal 選單層級與名稱（由 Portal 超連結自動推導）">
          <span style={{ color: '#1B3A5C', fontWeight: 700 }}>選單位置</span>
        </Tooltip>
      ),
      key: 'menuLevel',
      width: 150,
      sorter: (a: RagicApp, b: RagicApp) => {
        const la = getPortalInfo(a.portalUrl)?.level ?? 9
        const lb = getPortalInfo(b.portalUrl)?.level ?? 9
        return la - lb
      },
      filters: [
        { text: '一階', value: 1 },
        { text: '二階', value: 2 },
        { text: '三階', value: 3 },
        { text: '— 未對應', value: 0 },
      ],
      onFilter: (v: unknown, r: RagicApp) => {
        const level = getPortalInfo(r.portalUrl)?.level ?? 0
        return level === (v as number)
      },
      render: (_: unknown, row: RagicApp) => {
        const info = getPortalInfo(row.portalUrl)
        if (!info) return <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
        const cfg = LEVEL_CONFIG[info.level]
        return (
          <Space direction="vertical" size={2} style={{ lineHeight: 1.3 }}>
            <Tag
              style={{
                fontSize: 11,
                lineHeight: '18px',
                color: cfg.color,
                background: cfg.bg,
                borderColor: cfg.border,
                margin: 0,
              }}
            >
              {cfg.label}
            </Tag>
            <Text style={{ fontSize: 11, color: '#374151' }}>{info.label}</Text>
          </Space>
        )
      },
    },
    // ── 靜態欄位
    {
      title: '序號',
      dataIndex: 'itemNo',
      key: 'itemNo',
      width: 60,
      align: 'center',
      sorter: (a, b) => a.itemNo - b.itemNo,
      defaultSortOrder: 'ascend',
    },
    {
      title: '模組',
      dataIndex: 'module',
      key: 'module',
      width: 160,
      ellipsis: true,
      filters: modules.map((m) => ({ text: m, value: m })),
      onFilter: (v, r) => r.module === v,
    },
    {
      title: '應用程式名稱',
      dataIndex: 'name',
      key: 'name',
      width: 240,
      ellipsis: true,
    },
    {
      title: 'Ragic URL',
      dataIndex: 'url',
      key: 'url',
      width: 220,
      ellipsis: true,
      render: (url: string) => {
        // 擷取 domain 後的路徑，例：/soutlet001/luqun-.../6
        const path = url.replace(/^https?:\/\/[^/]+/, '')
        return (
          <Tooltip title={url}>
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              style={{ fontSize: 11, color: '#4BA8E8', display: 'flex', alignItems: 'center', gap: 4 }}
            >
              <ExportOutlined style={{ flexShrink: 0 }} />
              <span
                style={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: 175,
                  display: 'inline-block',
                }}
              >
                {path}
              </span>
            </a>
          </Tooltip>
        )
      },
    },
    {
      title: '類型',
      dataIndex: 'type',
      key: 'type',
      width: 90,
      filters: Object.keys(TYPE_COLOR).map((t) => ({ text: t, value: t })),
      onFilter: (v, r) => r.type === v,
      render: (v: string) => <Tag color={TYPE_COLOR[v] ?? 'default'}>{v}</Tag>,
    },
    {
      title: (
        <Tooltip title="Portal 同步時寫入的本地 SQLite 資料表">
          <span>本地 DB 表</span>
        </Tooltip>
      ),
      dataIndex: 'localTable',
      key: 'localTable',
      width: 200,
      filters: [
        { text: '有本地 DB', value: '__has__' },
        { text: '直連 Ragic', value: '' },
      ],
      onFilter: (v, r) =>
        v === '__has__' ? !!r.localTable : r.localTable === '',
      render: (v: string) => {
        if (!v) return <Text type="secondary" style={{ fontSize: 11 }}>— 直連 Ragic</Text>
        const tables = v.split('\n')
        return (
          <Space direction="vertical" size={2}>
            {tables.map((t) => (
              <code
                key={t}
                style={{
                  fontSize: 11,
                  background: '#f0f4f8',
                  padding: '1px 5px',
                  borderRadius: 3,
                  color: '#1B3A5C',
                  display: 'block',
                }}
              >
                {t}
              </code>
            ))}
          </Space>
        )
      },
    },
    {
      title: '備註',
      dataIndex: 'note',
      key: 'note',
      width: 100,
      ellipsis: true,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 70,
      align: 'center',
      render: (_: unknown, row: RagicApp) => (
        <Button
          size="small"
          type="text"
          icon={<EditOutlined />}
          style={{ color: '#4BA8E8' }}
          onClick={() => openEdit(row)}
        />
      ),
    },
  ]

  return (
    <div>
      {/* 頁面標題 */}
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
          Ragic 應用程式對應表
        </Title>
        <Text style={{ color: '#64748b' }}>
          共 {data.length} 筆 Ragic 應用程式，已標註 Portal 對應：{annotatedCount} 筆
        </Text>
      </div>

      {/* 搜尋列 */}
      <Card
        bordered={false}
        style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)', marginBottom: 16 }}
        bodyStyle={{ padding: '12px 16px' }}
      >
        <Space wrap>
          <Input.Search
            placeholder="搜尋名稱、模組、Portal 名稱、Ragic URL…"
            allowClear
            style={{ width: 280 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onSearch={setSearchText}
          />
          <Input.Search
            placeholder="篩選模組（空白=全部）"
            allowClear
            style={{ width: 220 }}
            value={filterModule}
            onChange={(e) => setFilterModule(e.target.value)}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            顯示 {filtered.length} / {data.length} 筆
          </Text>
        </Space>
      </Card>

      {/* 主表格 */}
      <Card
        bordered={false}
        style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
        bodyStyle={{ padding: 0 }}
      >
        <Table<RagicApp>
          dataSource={filtered}
          columns={columns}
          rowKey="itemNo"
          loading={loading}
          size="small"
          scroll={{ x: 1610 }}
          pagination={{
            pageSize: 50,
            showSizeChanger: true,
            pageSizeOptions: ['25', '50', '100', '219'],
            showTotal: (t) => `共 ${t} 筆`,
          }}
          rowClassName={(r) =>
            r.portalName ? 'ragic-dir-row-linked' : ''
          }
        />
      </Card>

      {/* 說明文字 */}
      <div
        style={{
          marginTop: 12,
          padding: '8px 14px',
          background: '#f0f4f8',
          borderRadius: 8,
          fontSize: 12,
          color: '#64748b',
        }}
      >
        點擊「Portal 名稱」欄或右側編輯按鈕，可設定該 Ragic 應用程式對應的 Portal 頁面名稱與路徑。
        標註資料由後端持久化，服務重啟後不會遺失。
      </div>

      {/* 編輯 Modal */}
      <Modal
        open={!!editTarget}
        title={
          <Space>
            <EditOutlined style={{ color: '#4BA8E8' }} />
            <span>設定 Portal 對應 — {editTarget?.name}</span>
          </Space>
        }
        onCancel={() => setEditTarget(null)}
        onOk={handleSave}
        okText={<><SaveOutlined /> 儲存</>}
        confirmLoading={saving}
        width={520}
        destroyOnClose
      >
        {editTarget && (
          <>
            <div
              style={{
                marginBottom: 16,
                padding: '8px 12px',
                background: '#f8fafc',
                borderRadius: 6,
                fontSize: 12,
                color: '#475569',
              }}
            >
              <div><strong>模組：</strong>{editTarget.module}</div>
              <div><strong>應用程式：</strong>{editTarget.name}</div>
              <div>
                <strong>Ragic URL：</strong>
                <a href={editTarget.url} target="_blank" rel="noreferrer">
                  {editTarget.url}
                </a>
              </div>
            </div>

            <Form form={form} layout="vertical">
              <Form.Item
                name="portalName"
                label="Portal 名稱"
                extra="例：飯店週期保養、大直工務報修（留空表示未使用）"
              >
                <Input placeholder="Portal 頁面中文名稱" maxLength={100} />
              </Form.Item>
              <Form.Item
                name="portalUrl"
                label="Portal 超連結"
                extra="例：/hotel/periodic-maintenance 或完整網址"
              >
                <Input placeholder="Portal 路由路徑或完整網址" maxLength={300} />
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>

      {/* row 樣式：已標註的行加底色 */}
      <style>{`
        .ragic-dir-row-linked td {
          background: #f0f7ff !important;
        }
        .ragic-dir-row-linked:hover td {
          background: #e0f0ff !important;
        }
      `}</style>
    </div>
  )
}

export default RagicAppDirectory
