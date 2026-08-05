/**
 * 事件月曆
 * 評估文件：docs/EVAL_opera_rate_forecasting.md §3.4（需求 3）
 *
 * ⚠️ 2026-08-05：本元件已改為嵌在「房價預測」頁（/opera/forecast）的「事件月曆」TAB 內，
 *    不再是獨立頁面。`/opera/events` 路由仍保留（CLAUDE.md §5 禁止移除既有路由），
 *    但改為導向 `/opera/forecast?tab=events`。
 *    `embedded` 為 true 時不畫外層 padding、標題與回頂端按鈕，交由承載頁負責。
 *
 * 權限：清單為唯讀（承載頁的 opera_forecast_view 即可看），
 *      新增／修改／刪除／學習係數需要 opera_event_admin，無權限時按鈕停用而非隱藏，
 *      讓使用者知道有這個功能、只是需要授權。
 *
 * 為什麼需要這一頁：模型不知道 2024 年 6 月哪幾天有電腦展，自然學不出
 * 「電腦展會讓 ADR 上升幾成」。事件月曆就是把這件事告訴模型的地方。
 *
 * 關鍵規則（不可為了方便而放寬）：
 *   同名事件累積 3 次以上才能改用「資料學習」的係數。
 *   只辦過一次的展覽，係數等於拿單一樣本當結論 —— 後端會擋，前端也要講清楚。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Drawer, Form, Input, InputNumber,
  Modal, Popconfirm, Row, Select, Space, Switch, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  BulbOutlined, DeleteOutlined, EditOutlined, InfoCircleOutlined,
  PlusOutlined, ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  createEvent, deleteEvent, fetchEvents, learnEventCoefficients, updateEvent,
} from '@/api/opera'
import type { EventListResult, OperaEventItem } from '@/types/opera'
import { useAuthStore } from '@/stores/authStore'
import BackToTop from '../components/BackToTop'
import { ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED, fmtInt } from '../components/formatters'

const { Title, Text, Paragraph } = Typography
const { RangePicker } = DatePicker

const CATEGORY_COLOR: Record<string, string> = {
  展覽:     'purple',
  連假:     'orange',
  國定假日: 'gold',
  春節:     'red',
  大型團體: 'blue',
  在地活動: 'cyan',
  其他:     'default',
}

/** 倍數的顯示色：偏離 1.0 越多越明顯 */
function indexColor(v: number): string {
  if (v >= 1.15) return GREEN
  if (v <= 0.85) return RED
  return 'inherit'
}

interface Props {
  /** true = 嵌在其他頁面的 TAB 內，不畫外層 padding、標題與回頂端按鈕 */
  embedded?: boolean
}

const OperaEventsPage: React.FC<Props> = ({ embedded = false }) => {
  const canEdit = useAuthStore((s) => s.hasPermission)('opera_event_admin')
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [data, setData] = useState<EventListResult | null>(null)
  const [editing, setEditing] = useState<OperaEventItem | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [detailRow, setDetailRow] = useState<OperaEventItem | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await fetchEvents())
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入事件月曆失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const openModal = (row: OperaEventItem | null) => {
    setEditing(row)
    form.setFieldsValue(row
      ? {
        name: row.name,
        category: row.category,
        dates: [dayjs(row.start_date), dayjs(row.end_date)],
        expected_adr_index: row.expected_adr_index,
        expected_occ_index: row.expected_occ_index,
        source: row.source,
        is_active: row.is_active,
        note: row.note,
      }
      : {
        category: '展覽',
        expected_adr_index: 1.2,
        expected_occ_index: 1.1,
        source: 'manual',
        is_active: true,
      })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const v = await form.validateFields()
    const payload = {
      name: v.name,
      category: v.category,
      start_date: v.dates[0].format('YYYY-MM-DD'),
      end_date: v.dates[1].format('YYYY-MM-DD'),
      expected_adr_index: v.expected_adr_index,
      expected_occ_index: v.expected_occ_index,
      source: v.source,
      is_active: v.is_active,
      note: v.note || '',
    }
    setBusy(true)
    try {
      if (editing) {
        await updateEvent(editing.id, payload)
        message.success('已更新事件')
      } else {
        await createEvent(payload)
        message.success('已新增事件')
      }
      setModalOpen(false)
      await load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '儲存失敗')
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async (row: OperaEventItem) => {
    setBusy(true)
    try {
      await deleteEvent(row.id)
      message.success('已刪除')
      await load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '刪除失敗')
    } finally {
      setBusy(false)
    }
  }

  const handleLearn = async () => {
    setBusy(true)
    try {
      const res = await learnEventCoefficients()
      Modal.info({
        title: '事件係數學習完成',
        width: 720,
        content: (
          <Space direction="vertical" size={8} style={{ width: '100%', marginTop: 12 }}>
            <Text>
              {`共 ${res.total} 組事件，其中 ${res.reliable_count} 組達到 ${res.min_samples} 次以上，可採用學習係數。`}
            </Text>
            <Table
              rowKey="name"
              size="small"
              pagination={false}
              scroll={{ y: 320 }}
              dataSource={res.items}
              columns={[
                { title: '事件', dataIndex: 'name', width: 180 },
                { title: '次數', dataIndex: 'occurrences', width: 70, align: 'right' },
                { title: '涵蓋天數', dataIndex: 'covered_days', width: 90, align: 'right' },
                {
                  title: '學習 ADR 倍數',
                  dataIndex: 'learned_adr_index',
                  width: 120,
                  align: 'right',
                  render: (v: number | null) => (v !== null
                    ? <Text style={{ color: indexColor(v) }}>{`×${v.toFixed(3)}`}</Text>
                    : EMPTY),
                },
                {
                  title: '可靠',
                  width: 80,
                  align: 'center',
                  render: (_, r) => (r.is_reliable
                    ? <Tag color="green">是</Tag>
                    : <Tag color={ORANGE}>否</Tag>),
                },
                { title: '說明', dataIndex: 'note', ellipsis: true },
              ]}
            />
            <Alert
              type="info"
              showIcon
              message="學習完成不代表模型已改用學習值"
              description={
                '每個事件的「採用來源」預設仍是人工設定。確認學習值合理後，'
                + '再逐一改成「資料學習」才會生效。'
              }
            />
          </Space>
        ),
      })
      await load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '學習失敗')
    } finally {
      setBusy(false)
    }
  }

  const columns: ColumnsType<OperaEventItem> = [
    {
      title: '事件名稱',
      dataIndex: 'name',
      width: 200,
      render: (v: string, r) => (
        <Space direction="vertical" size={0}>
          <Text strong={r.is_active}>{v}</Text>
          {!r.is_active && <Tag>已停用</Tag>}
        </Space>
      ),
    },
    {
      title: '類別',
      dataIndex: 'category',
      width: 100,
      render: (v: string) => <Tag color={CATEGORY_COLOR[v] || 'default'}>{v}</Tag>,
    },
    {
      title: '期間',
      width: 220,
      render: (_, r) => `${r.start_date} ~ ${r.end_date}（${r.days} 天）`,
    },
    {
      title: '採用倍數',
      width: 170,
      render: (_, r) => (
        <Space size={4}>
          <Text style={{ color: indexColor(r.effective_adr_index) }}>
            {`ADR ×${r.effective_adr_index.toFixed(2)}`}
          </Text>
          <Text type="secondary">/</Text>
          <Text style={{ color: indexColor(r.effective_occ_index) }}>
            {`住 ×${r.effective_occ_index.toFixed(2)}`}
          </Text>
        </Space>
      ),
    },
    {
      title: '來源',
      width: 130,
      render: (_, r) => (
        <Tooltip
          title={r.source === 'learned'
            ? `由 ${r.sample_count} 次歷史紀錄學習而得`
            : '人工填入的預期倍數'}
        >
          <Tag color={r.source === 'learned' ? 'blue' : 'default'}>{r.source_label}</Tag>
        </Tooltip>
      ),
    },
    {
      title: '學習值',
      width: 160,
      render: (_, r) => {
        if (r.learned_adr_index === null) {
          return <Text type="secondary">{EMPTY}（尚未學習）</Text>
        }
        return (
          <Space direction="vertical" size={0}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {`ADR ×${r.learned_adr_index.toFixed(3)}`}
            </Text>
            {r.is_learnable
              ? <Tag color="green">{`${r.sample_count} 次，可採用`}</Tag>
              : <Tag color={ORANGE}>{`只有 ${r.sample_count} 次`}</Tag>}
          </Space>
        )
      },
    },
    {
      title: '操作',
      width: 130,
      render: (_, r) => (
        <Space size={2}>
          <Button type="text" size="small" icon={<EditOutlined />} disabled={!canEdit}
            onClick={(e) => { e.stopPropagation(); openModal(r) }} />
          <Popconfirm
            title="確定刪除這個事件？"
            description="刪除內容會寫入稽核日誌。若只是暫時不套用，建議改用「停用」。"
            disabled={!canEdit}
            onConfirm={() => handleDelete(r)}
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} disabled={!canEdit}
              onClick={(e) => e.stopPropagation()} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: embedded ? 0 : 24 }}>
      {!embedded && (
        <>
          <Title level={4} style={{ color: BRAND }}>事件月曆</Title>
          <Paragraph type="secondary" style={{ marginTop: -8 }}>
            告訴模型哪幾天有展覽、連假或大型團體。沒有這份資料，預測就只看得到星期與月份。
          </Paragraph>
        </>
      )}

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="先用人工倍數，累積夠了再改用學習值"
        description={
          data?.hint
          || '同名事件累積 3 次以上才能改用「資料學習」的係數；少於這個次數等於拿單一樣本當結論。'
        }
      />

      <Card
        size="small"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load}>重新載入</Button>
            <Tooltip
              title={canEdit
                ? '用事件期間的實際值 ÷ 不含事件的模型預測值，算出每組事件的倍數'
                : '需要「事件月曆」權限'}
            >
              <Button icon={<BulbOutlined />} loading={busy} disabled={!canEdit} onClick={handleLearn}>
                學習事件係數
              </Button>
            </Tooltip>
            <Tooltip title={canEdit ? '' : '需要「事件月曆」權限'}>
              <Button type="primary" icon={<PlusOutlined />} disabled={!canEdit}
                onClick={() => openModal(null)}>
                新增事件
              </Button>
            </Tooltip>
          </Space>
        }
      >
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={data?.items || []}
          columns={columns}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          onRow={(row) => ({ onClick: () => setDetailRow(row), style: { cursor: 'pointer' } })}
        />
      </Card>

      {/* 新增／修改 */}
      <Modal
        open={modalOpen}
        title={editing ? `修改事件：${editing.name}` : '新增事件'}
        width={640}
        confirmLoading={busy}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={14}>
              <Form.Item name="name" label="事件名稱" rules={[{ required: true, message: '請填事件名稱' }]}>
                <Input placeholder="例：國際電腦展" />
              </Form.Item>
            </Col>
            <Col span={10}>
              <Form.Item name="category" label="類別" rules={[{ required: true }]}>
                <Select options={(data?.categories || []).map((c) => ({ label: c, value: c }))} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="dates" label="期間" rules={[{ required: true, message: '請選期間' }]}>
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="expected_adr_index"
                label="人工 ADR 倍數"
                extra="1.35 = ADR 提高 35%（不是 135）"
                rules={[{ required: true }, { type: 'number', min: 0.1, max: 5, message: '合理範圍 0.1 ~ 5' }]}
              >
                <InputNumber style={{ width: '100%' }} step={0.05} precision={2} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="expected_occ_index"
                label="人工住房率倍數"
                extra="滿房有上限，實際會壓在 100% 以內"
                rules={[{ required: true }, { type: 'number', min: 0.1, max: 5, message: '合理範圍 0.1 ~ 5' }]}
              >
                <InputNumber style={{ width: '100%' }} step={0.05} precision={2} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="source"
                label={<Space size={4}>
                  <span>採用來源</span>
                  <Tooltip title={`同名事件累積 ${data?.min_samples ?? 3} 次以上才能選「資料學習」`}>
                    <InfoCircleOutlined style={{ color: GREY }} />
                  </Tooltip>
                </Space>}
              >
                <Select
                  options={[
                    { label: '人工設定', value: 'manual' },
                    {
                      label: '資料學習',
                      value: 'learned',
                      disabled: !editing?.is_learnable,
                    },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="is_active" label="啟用" valuePropName="checked">
                <Switch checkedChildren="套用" unCheckedChildren="停用" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="note" label="備註">
            <Input.TextArea rows={2} maxLength={500} showCount />
          </Form.Item>
        </Form>
      </Modal>

      {/* 明細 Drawer（CLAUDE.md §7）*/}
      <Drawer
        open={!!detailRow}
        width={480}
        onClose={() => setDetailRow(null)}
        title={detailRow && (
          <Space size={8} wrap>
            <Tag color={CATEGORY_COLOR[detailRow.category] || 'default'}>{detailRow.category}</Tag>
            <Text strong style={{ color: BRAND }}>{`事件：${detailRow.name}`}</Text>
          </Space>
        )}
      >
        {detailRow && (
          <>
            <Descriptions size="small" column={1} bordered title="基本欄位">
              <Descriptions.Item label="期間">
                {`${detailRow.start_date} ~ ${detailRow.end_date}`}
              </Descriptions.Item>
              <Descriptions.Item label="天數">{`${detailRow.days} 天`}</Descriptions.Item>
              <Descriptions.Item label="實際採用 ADR 倍數">
                <Text strong style={{ color: indexColor(detailRow.effective_adr_index) }}>
                  {`×${detailRow.effective_adr_index.toFixed(3)}`}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="實際採用住房率倍數">
                <Text strong style={{ color: indexColor(detailRow.effective_occ_index) }}>
                  {`×${detailRow.effective_occ_index.toFixed(3)}`}
                </Text>
              </Descriptions.Item>
            </Descriptions>

            <Descriptions size="small" column={1} bordered title="明細欄位" style={{ marginTop: 16 }}>
              {Object.entries(detailRow.detail || {}).map(([k, v]) => (
                <Descriptions.Item key={k} label={k}>
                  {v === '—' || !v ? <Text type="secondary">{EMPTY}</Text> : <Text>{v}</Text>}
                </Descriptions.Item>
              ))}
            </Descriptions>

            {!detailRow.is_learnable && detailRow.learned_adr_index !== null && (
              <Alert
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
                message="學習樣本不足"
                description={
                  `這組事件只有 ${detailRow.sample_count} 次歷史紀錄，`
                  + `不足 ${data?.min_samples ?? 3} 次。學習值僅供參考，模型仍會採用人工設定的倍數。`
                }
              />
            )}
          </>
        )}
      </Drawer>

      {!embedded && <BackToTop />}
    </div>
  )
}

export default OperaEventsPage
