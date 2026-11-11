/**
 * 戰情 KPI 頁簽定義（2026-11-11）— key 與後端 routers/war_room.py 的 TAB_KEYS 一致。
 * defaultLabel 為預設名稱；頁簽名稱與顯示／隱藏由「編輯頁簽」（系統管理員）存在後端。
 */
export const WR_TAB_DEFS = [
  { key: 'overview', defaultLabel: '值班總覽' },
  { key: 'control', defaultLabel: '工務營運中控台' },
  { key: 'dashboard', defaultLabel: 'Dashboard' },
  { key: 'iso', defaultLabel: '3D 樓層' },
  { key: 'alerts', defaultLabel: '告警' },
  { key: 'staff', defaultLabel: '人員動態' },
  { key: 'person-journal', defaultLabel: '人員工作日誌' },
  { key: 'history', defaultLabel: '房間／設備履歷' },
] as const

/** 後端沒有設定紀錄時採用的隱藏清單（工務營運中控台：開發中，先隱藏） */
export const WR_DEFAULT_HIDDEN: string[] = ['control']
