/**
 * 全棟例行維護 — 每日巡檢表 TAB
 *
 * 嵌入整棟巡檢（FullBuildingInspection）的每日巡檢表，
 * 顯示模板結構，待本地同步接通後自動呈現真實資料。
 */
import { useState, useCallback, useEffect } from 'react'
import {
  Alert, Button, Col, DatePicker, Row, Space, Table, Tag, Typography,
} from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  fetchFullBuildingDailyForm,
  type FullBuildingDailyFormRow,
} from '@/api/fullBuildingInspection'

const { Text } = Typography

export default function FullBldgDailyFormTab() {
  const today = dayjs()
  const [inspectionDate, setInspectionDate] = useState<string>(today.format('YYYY/MM/DD'))
  const [loading,  setLoading]  = useState(false)
  const [rows,     setRows]     = useState<FullBuildingDailyFormRow[]>([])

  const load = useCallback(async (date: string) => {
    setLoading(true)
    try {
      const [yr, mo] = date.split('/').map(Number)
      const data = await fetchFullBuildingDailyForm(yr, mo, date)
      setRows(data.rows)
    } catch {
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(inspectionDate) }, [load, inspectionDate])

  const columns = [
    {
      title:     '樓層',
      dataIndex: 'floor',
      width: 60,
      onCell: (record: FullBuildingDailyFormRow) => ({
        rowSpan: record.floor_first_row ? record.floor_row_count : 0,
        style:   { fontWeight: 600, verticalAlign: 'middle', background: '#f0f4f8', textAlign: 'center' as const },
      }),
    },
    {
      title:     '項目',
      dataIndex: 'item',
      width: 160,
      onCell: (record: FullBuildingDailyFormRow) => ({
        rowSpan: record.item_first_row ? record.item_row_count : 0,
        style:   { verticalAlign: 'middle', fontWeight: 500 },
      }),
    },
    {
      title:     '檢查內容',
      dataIndex: 'check_content',
      width: 240,
    },
    {
      title:     '運轉狀況（結果）',
      dataIndex: 'result_options',
      width: 200,
      render: (_: string, row: FullBuildingDailyFormRow) => {
        if (!row.matched) return <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
        return (
          <Space size={4} wrap>
            {row.result_text
              ? <Tag color={row.result_status === 'normal' ? '#52C41A' : row.result_status === 'abnormal' ? '#FF4D4F' : '#FAAD14'}>{row.result_text}</Tag>
              : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
            }
          </Space>
        )
      },
    },
    {
      title:     '實際巡檢人員',
      dataIndex: 'inspector',
      width: 110,
      render: (v: string) => v || <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
    {
      title:     '異常說明',
      dataIndex: 'abnormal_note',
      render: (v: string) => v
        ? <Text type="danger" style={{ fontSize: 11, whiteSpace: 'pre-wrap' }}>{v}</Text>
        : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
    {
      title:     '時間(分)',
      dataIndex: 'minutes',
      width: 75,
      align: 'center' as const,
      render: (v: number) => v > 0 ? <Text style={{ fontSize: 11 }}>{v}</Text> : null,
      onCell: (record: FullBuildingDailyFormRow) => ({
        rowSpan: record.item_first_row ? record.item_row_count : 0,
        style:   { verticalAlign: 'middle', textAlign: 'center' as const },
      }),
    },
  ]

  return (
    <div>
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <DatePicker
            value={dayjs(inspectionDate, 'YYYY/MM/DD')}
            format="YYYY/MM/DD"
            allowClear={false}
            onChange={(d) => { if (d) setInspectionDate(d.format('YYYY/MM/DD')) }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={() => load(inspectionDate)} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="整棟巡檢本地同步功能開發中"
        description="目前每日巡檢表尚未接通本地 DB，模板欄位已備妥。請至 Ragic 系統填寫各樓層巡檢表單，接通後資料將自動顯示於此。"
      />

      <Table<FullBuildingDailyFormRow>
        dataSource={rows}
        rowKey={(r) => `${r.floor}-${r.item}-${r.check_content}`}
        columns={columns}
        loading={loading}
        size="small"
        pagination={false}
        bordered
        rowClassName={(r) => r.abnormal ? 'row-abnormal' : ''}
        style={{ fontSize: 12 }}
        locale={{ emptyText: '尚無巡檢資料' }}
      />
    </div>
  )
}
