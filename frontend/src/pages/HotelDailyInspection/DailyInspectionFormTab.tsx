/**
 * 每日巡檢表 TAB
 *
 * 篩選模式：
 *   月份模式（預設）：YYYY + MM → 整月彙整，多筆 batch 合併
 *   單日模式（選填）：YYYY + MM + 日期 → 只取該日；無資料時顯示提示橫幅
 *
 * 欄位：樓層 | 項目 | 檢查內容 | 實際巡檢人員 | 運轉狀況(結果) | 異常說明 | 時間(分)
 */
import { useState, useCallback, useEffect } from 'react'
import {
  Alert, Button, Col, DatePicker, Divider, InputNumber,
  Row, Select, Space, Table, Tag, Typography,
} from 'antd'
import { CalendarOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { type Dayjs } from 'dayjs'
import {
  fetchHotelDailyForm,
  type DailyFormRow,
} from '@/api/hotelDailyInspection'

const { Text } = Typography

// ── 狀態標籤 ──────────────────────────────────────────────────────────────────

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  normal:    { color: '#52C41A', label: '正常'  },
  abnormal:  { color: '#FF4D4F', label: '異常'  },
  pending:   { color: '#FAAD14', label: '待處理' },
  unchecked: { color: '#d9d9d9', label: '未巡檢' },
}

type RowWithKey = DailyFormRow & { _key: string }

// ── 主元件 ────────────────────────────────────────────────────────────────────

export default function DailyInspectionFormTab() {
  const now = dayjs()

  // ── 篩選狀態
  const [year,           setYear]           = useState<number>(now.year())
  const [month,          setMonth]          = useState<number>(now.month() + 1)
  const [selectedDate,   setSelectedDate]   = useState<Dayjs | null>(null)   // 單日日曆篩選

  // ── 資料狀態
  const [rows,         setRows]         = useState<RowWithKey[]>([])
  const [loading,      setLoading]      = useState(false)
  const [queried,      setQueried]      = useState(false)
  const [hasDataToday, setHasDataToday] = useState<boolean | null>(null)
  const [queriedDate,  setQueriedDate]  = useState<string>('')   // 已查詢的日期字串

  // ── 查詢 ─────────────────────────────────────────────────────────────────────

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const inspDate = selectedDate ? selectedDate.format('YYYY/MM/DD') : undefined
      const data = await fetchHotelDailyForm(year, month, inspDate)
      const withKey: RowWithKey[] = data.rows.map((r, i) => ({
        ...r,
        _key: `${r.floor}__${r.item}__${r.check_content}__${i}`,
      }))
      setRows(withKey)
      setHasDataToday(data.has_data_today)
      setQueriedDate(inspDate ?? '')
    } catch {
      setRows([])
      setHasDataToday(null)
    } finally {
      setQueried(true)
      setLoading(false)
    }
  }, [year, month, selectedDate])

  // 元件載入時自動查詢當月資料
  useEffect(() => { load() }, [load])

  // 切換年份或月份時清除日期選擇（避免日期跨月）
  const handleYearChange = (v: number | null) => {
    if (v) { setYear(v); setSelectedDate(null) }
  }
  const handleMonthChange = (v: number) => {
    setMonth(v); setSelectedDate(null)
  }

  // 日曆日期需落在選取的 year/month 內
  const disabledDate = (current: Dayjs) =>
    current.year() !== year || current.month() + 1 !== month

  // ── 結果呈現 ─────────────────────────────────────────────────────────────────

  const renderResult = (row: RowWithKey) => {
    if (!row.matched) {
      return (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {row.result_options}
        </Text>
      )
    }
    const { color, label } = STATUS_TAG[row.result_status] ?? STATUS_TAG.unchecked
    return (
      <Space direction="vertical" size={2} style={{ width: '100%' }}>
        <Tag color={color} style={{ marginBottom: 0 }}>{label}</Tag>
        {row.result_text && (
          <Text style={{ fontSize: 11, color: '#555', whiteSpace: 'pre-wrap' }}>
            {row.result_text}
          </Text>
        )}
      </Space>
    )
  }

  // ── 列底色 ───────────────────────────────────────────────────────────────────

  const rowClassName = (row: RowWithKey): string => {
    if (row.abnormal) return 'daily-form-row--abnormal'
    if (!row.matched) return 'daily-form-row--unchecked'
    return ''
  }

  // ── 欄位定義 ─────────────────────────────────────────────────────────────────

  const columns: ColumnsType<RowWithKey> = [
    {
      title:   '樓層',
      dataIndex: 'floor',
      width:   60,
      align:   'center',
      onCell:  (row) => ({ rowSpan: row.floor_first_row ? row.floor_row_count : 0 }),
      render:  (v: string) => (
        <Text strong style={{ fontSize: 13, color: '#1B3A5C' }}>{v}</Text>
      ),
    },
    {
      title:   '項目',
      dataIndex: 'item',
      width:   110,
      align:   'center',
      onCell:  (row) => ({ rowSpan: row.item_first_row ? row.item_row_count : 0 }),
      render:  (v: string) => <Text strong style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title:   '檢查內容',
      dataIndex: 'check_content',
      width:   200,
      render:  (v: string) => (
        <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>{v}</Text>
      ),
    },
    {
      title:     '實際巡檢人員',
      dataIndex: 'inspector',
      width:     110,
      align:     'center',
      render: (v: string) =>
        v ? (
          <Text style={{ fontSize: 12 }}>{v}</Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
        ),
    },
    {
      title:  '運轉狀況(結果)',
      width:  200,
      render: (_: unknown, row: RowWithKey) => renderResult(row),
    },
    {
      title:     '異常說明',
      dataIndex: 'abnormal_note',
      width:     180,
      render: (v: string) =>
        v ? (
          <Text style={{ fontSize: 11, color: '#c0392b', whiteSpace: 'pre-wrap' }}>{v}</Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
        ),
    },
    {
      title:  '時間(分)',
      width:  75,
      align:  'center',
      onCell: (row) => ({ rowSpan: row.item_first_row ? row.item_row_count : 0 }),
      render: (_: unknown, row: RowWithKey) => {
        if (!row.item_first_row) return null
        // 有實際巡檢資料時顯示計算值，否則顯示標準模板值
        const mins = row.actual_minutes > 0 ? row.actual_minutes : row.minutes
        if (mins <= 0) return null
        return (
          <Text
            strong
            style={{ color: '#1B3A5C' }}
            title={row.actual_minutes > 0 ? `實際：${row.actual_minutes} 分` : `標準：${row.minutes} 分`}
          >
            {mins}
          </Text>
        )
      },
    },
  ]

  // ── 總巡檢時間（優先取實際值，否則用模板標準值） ──────────────────────────

  const totalMinutes = (() => {
    const firstRows = rows.filter((r) => r.item_first_row)
    // 若有任何實際時間，各 tab 實際時間已重複於每列，需依 source_tab 去重後加總
    const hasActual = firstRows.some((r) => r.actual_minutes > 0)
    if (hasActual) {
      const seen = new Set<string>()
      return firstRows.reduce((s, r) => {
        if (r.actual_minutes > 0 && !seen.has(r.source_tab)) {
          seen.add(r.source_tab)
          return s + r.actual_minutes
        }
        return s
      }, 0)
    }
    // 無實際資料時加總標準模板時間（各 item 不重複）
    return firstRows.reduce((s, r) => s + (r.minutes > 0 ? r.minutes : 0), 0)
  })()

  // ── 是否為單日模式且已查詢 ───────────────────────────────────────────────────

  const isDailyMode   = !!queriedDate
  const noDataToday   = isDailyMode && hasDataToday === false
  const hasDataBanner = isDailyMode && hasDataToday === true

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div>
      {/* CSS */}
      <style>{`
        .daily-form-row--abnormal td  { background-color: #fff1f0 !important; }
        .daily-form-row--unchecked td { background-color: #fffbe6 !important; }
        .daily-form-table .ant-table-thead > tr > th {
          background-color: #f0f4f8;
          color: #1B3A5C;
          font-weight: 600;
          text-align: center;
          white-space: nowrap;
        }
        .daily-form-table .ant-table-cell {
          vertical-align: middle;
          padding: 6px 8px !important;
        }
      `}</style>

      {/* ── 篩選列 ── */}
      <Row gutter={[8, 8]} align="middle" style={{ marginBottom: 8 }}>
        <Col>
          <Space wrap>
            <Text strong>年度：</Text>
            <InputNumber
              min={2020} max={2035}
              value={year}
              onChange={handleYearChange}
              style={{ width: 80 }}
              controls={false}
            />
            <Text strong>月份：</Text>
            <Select
              value={month}
              onChange={handleMonthChange}
              style={{ width: 75 }}
              options={Array.from({ length: 12 }, (_, i) => ({
                value: i + 1, label: `${i + 1} 月`,
              }))}
            />
          </Space>
        </Col>

        <Col>
          <Divider type="vertical" style={{ height: 24 }} />
        </Col>

        <Col>
          <Space wrap>
            <CalendarOutlined style={{ color: '#4BA8E8' }} />
            <Text strong style={{ color: '#4BA8E8' }}>單日篩選：</Text>
            <DatePicker
              value={selectedDate}
              disabledDate={disabledDate}
              onChange={(d) => setSelectedDate(d)}
              placeholder="選擇日期（選填）"
              allowClear
              format="YYYY/MM/DD"
              style={{ width: 150 }}
            />
            {selectedDate && (
              <Button size="small" onClick={() => setSelectedDate(null)}>
                清除日期
              </Button>
            )}
          </Space>
        </Col>

        <Col>
          <Space>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={load}
              loading={loading}
              style={{ background: '#1B3A5C', borderColor: '#1B3A5C' }}
            >
              查詢
            </Button>
            {queried && (
              <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
                重新整理
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      {/* ── 無資料提示（單日模式） ── */}
      {noDataToday && (
        <Alert
          type="warning"
          showIcon
          message={`無 ${queriedDate} 巡檢資料`}
          description="該日期尚無任何巡檢紀錄，以下表格顯示標準模板（未填結果）。"
          style={{ marginBottom: 12 }}
        />
      )}
      {hasDataBanner && (
        <Alert
          type="success"
          showIcon
          message={`${queriedDate} 巡檢資料`}
          style={{ marginBottom: 12 }}
        />
      )}

      {/* ── 表格 ── */}
      <Table<RowWithKey>
        className="daily-form-table"
        dataSource={rows}
        rowKey="_key"
        columns={columns}
        loading={loading}
        size="small"
        pagination={false}
        scroll={{ x: 940, y: 520 }}
        rowClassName={rowClassName}
        bordered
        locale={{
          emptyText: `${year} 年 ${month} 月尚無巡檢資料，請確認資料是否已同步。`,
        }}
        summary={() =>
          queried && rows.length > 0 ? (
            <Table.Summary fixed>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={7}>
                  <Space split={<span style={{ color: '#ccc' }}>|</span>}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      早班巡檢時間：08:30 ~ 10:00
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      晚班巡檢時間：18:30 ~ 20:00
                    </Text>
                    <Text strong style={{ fontSize: 12, color: '#1B3A5C' }}>
                      {rows.some((r) => r.actual_minutes > 0) ? '實際' : '標準'}總巡檢時間：{totalMinutes} 分
                    </Text>
                  </Space>
                </Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          ) : null
        }
      />
    </div>
  )
}
