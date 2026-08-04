/**
 * 資料匯入（/opera/import）
 * 規格書：docs/SPEC_opera_analytics.md §11.6、§7.1
 *
 * 流程：選檔 → 驗證 → （必要時勾選警示確認）→ 匯入 → 對帳摘要
 * 比照既有 /contract/import、/schedule/import 的 UI 模式。
 */
import React, { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Button, Card, Checkbox, Col, Descriptions, Divider, Empty, Progress,
  Result, Row, Space, Spin, Table, Tag, Typography, Upload, message,
} from 'antd'
import {
  CheckCircleOutlined, CloseCircleOutlined, DownloadOutlined,
  InboxOutlined, WarningOutlined,
} from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'

import {
  batchErrorsCsvUrl, commitOperaFile, fetchImportStatus, validateOperaFile,
} from '@/api/opera'
import type {
  CommitResult, ImportStatus, OperaSourceType, ValidateResult,
} from '@/types/opera'
import {
  ACCENT, BRAND, EMPTY, GREEN, ORANGE, QUALITY_TAG, RED,
  fmtBytes, fmtInt, fmtMoney,
} from '../components/formatters'

const { Title, Text, Paragraph } = Typography
const { Dragger } = Upload

interface SlotState {
  file: File | null
  fileList: UploadFile[]
  validating: boolean
  committing: boolean
  result: ValidateResult | null
  commit: CommitResult | null
  ackWarnings: boolean
  error: string
}

const emptySlot = (): SlotState => ({
  file: null, fileList: [], validating: false, committing: false,
  result: null, commit: null, ackWarnings: false, error: '',
})

const SLOTS: Array<{ key: OperaSourceType; title: string; hint: string }> = [
  {
    key: 'DEPARTURE',
    title: 'Departure All',
    hint: '提供訂房、住客、通路、房型、Rate Code、住宿晚數',
  },
  {
    key: 'HISTORY_FORECAST',
    title: 'History and Forecast',
    hint: '提供每日房間營收、ADR、住房率、可售房、OOO、散客／團體',
  },
]

const OperaImportPage: React.FC = () => {
  const navigate = useNavigate()
  const [slots, setSlots] = useState<Record<string, SlotState>>({
    DEPARTURE: emptySlot(),
    HISTORY_FORECAST: emptySlot(),
  })
  const [status, setStatus] = useState<ImportStatus | null>(null)
  const [sessionId] = useState(() => `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`)

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await fetchImportStatus())
    } catch {
      /* 靜默 */
    }
  }, [])

  useEffect(() => { loadStatus() }, [loadStatus])

  const patch = (key: string, next: Partial<SlotState>) =>
    setSlots((prev) => ({ ...prev, [key]: { ...prev[key], ...next } }))

  // ── 驗證 ────────────────────────────────────────────────────────────────
  const handleValidate = async (key: OperaSourceType) => {
    const slot = slots[key]
    if (!slot.file) {
      message.warning('請先選擇檔案')
      return
    }
    patch(key, { validating: true, error: '', result: null, commit: null, ackWarnings: false })
    try {
      const res = await validateOperaFile(slot.file, key)
      patch(key, { result: res })
      if (res.source_type !== key) {
        message.warning(`偵測到的報表類型是「${res.source_label}」，與此上傳區不符，請確認檔案`)
      }
    } catch (e: any) {
      patch(key, { error: e?.response?.data?.detail || '驗證失敗' })
    } finally {
      patch(key, { validating: false })
    }
  }

  // ── 匯入 ────────────────────────────────────────────────────────────────
  const handleCommit = async (key: OperaSourceType) => {
    const slot = slots[key]
    if (!slot.file || !slot.result) return
    patch(key, { committing: true, error: '' })
    try {
      const res = await commitOperaFile(slot.file, {
        sourceType: slot.result.source_type,
        sessionId,
        allowWarnings: slot.result.needs_warning_ack ? slot.ackWarnings : true,
      })
      patch(key, { commit: res })
      message.success(`${slot.result.source_label} 匯入完成（批次 #${res.batch_id}）`)
      loadStatus()
    } catch (e: any) {
      patch(key, { error: e?.response?.data?.detail || '匯入失敗' })
    } finally {
      patch(key, { committing: false })
    }
  }

  const resetSlot = (key: OperaSourceType) => setSlots((p) => ({ ...p, [key]: emptySlot() }))

  // ── 驗證摘要 ────────────────────────────────────────────────────────────
  const renderValidation = (key: OperaSourceType, slot: SlotState) => {
    const v = slot.result
    if (!v) return null
    const quality = QUALITY_TAG[v.quality_result] || { color: 'default', text: v.quality_result }

    return (
      <>
        <Divider style={{ margin: '12px 0' }} />

        {v.file_state === 'DUPLICATE' && v.duplicate && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
            message="這個檔案已經匯入過了"
            description={`原批次 #${v.duplicate.batch_id}（${v.duplicate.file_name}），匯入時間 ${v.duplicate.imported_at}。相同內容不會重複匯入，若來源檔有更新請重新匯出後再上傳。`}
          />
        )}
        {v.file_state === 'UPDATED' && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message="這個檔案包含更新後的資料"
            description={`匯入後會有 ${fmtInt(v.delta.will_update)} 筆更新為新版本（舊版本保留但標記為非目前有效），另新增 ${fmtInt(v.delta.will_insert)} 筆。`}
          />
        )}

        <Descriptions size="small" column={{ xs: 1, sm: 2 }} bordered>
          <Descriptions.Item label="報表類型">
            <Tag color="blue">{v.source_label}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="飯店代碼">{v.property_code || EMPTY}</Descriptions.Item>
          <Descriptions.Item label="檔案大小">{fmtBytes(v.file_size)}</Descriptions.Item>
          <Descriptions.Item label="編碼">{v.encoding}</Descriptions.Item>
          <Descriptions.Item label="資料期間" span={2}>
            <Text strong>{`${v.report_start_date || EMPTY} ～ ${v.report_end_date || EMPTY}`}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="有效列數">{fmtInt(v.row_count_valid)}</Descriptions.Item>
          <Descriptions.Item label="拒絕列數">
            {v.row_count_rejected > 0
              ? <Text style={{ color: RED }}>{fmtInt(v.row_count_rejected)}</Text>
              : fmtInt(0)}
          </Descriptions.Item>
          {v.source_type === 'DEPARTURE' && (
            <Descriptions.Item label="續行合併對數" span={2}>
              {fmtInt(v.merged_pairs)}
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                （PROF_ATTACHED 換行造成的拆列，已自動合併）
              </Text>
            </Descriptions.Item>
          )}
          <Descriptions.Item label="預估變動" span={2}>
            <Space size={12} wrap>
              <span>新增 <Text strong style={{ color: GREEN }}>{fmtInt(v.delta.will_insert)}</Text></span>
              <span>更新 <Text strong style={{ color: ORANGE }}>{fmtInt(v.delta.will_update)}</Text></span>
              <span>略過 <Text strong>{fmtInt(v.delta.will_skip)}</Text></span>
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="品質結果" span={2}>
            <Tag color={quality.color}>{quality.text}</Tag>
          </Descriptions.Item>
        </Descriptions>

        {/* 對帳表 */}
        <Card
          size="small"
          title="Footer 對帳（OPERA 報表尾列 vs 程式彙總）"
          style={{ marginTop: 12 }}
          extra={
            v.reconcile.ok
              ? <Tag icon={<CheckCircleOutlined />} color="success">全部相符</Tag>
              : <Tag icon={<CloseCircleOutlined />} color="error">有差異</Tag>
          }
        >
          <Table
            size="small"
            rowKey="footer_key"
            pagination={false}
            dataSource={v.reconcile.items}
            columns={[
              { title: '項目', dataIndex: 'label', width: 110 },
              { title: 'OPERA footer', dataIndex: 'footer_value', align: 'right', render: (x: number) => fmtMoney(x) },
              { title: '程式彙總', dataIndex: 'computed_value', align: 'right', render: (x: number) => fmtMoney(x) },
              {
                title: '差異',
                dataIndex: 'diff',
                align: 'right',
                render: (x: number, r) => (
                  <Text style={{ color: r.ok ? GREEN : RED }}>{r.ok ? '0' : fmtMoney(x)}</Text>
                ),
              },
            ]}
          />
          {v.source_type === 'HISTORY_FORECAST' && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              OPERA footer 的合計是整份報表（History + Forecast 都算）；分析實績時只取 History。
            </Text>
          )}
        </Card>

        {/* 品質檢查 */}
        <Card size="small" title="資料品質檢查" style={{ marginTop: 12 }}>
          <Table
            size="small"
            rowKey="name"
            pagination={false}
            dataSource={v.quality_checks}
            columns={[
              {
                title: '',
                dataIndex: 'ok',
                width: 40,
                render: (ok: boolean, r) => (ok
                  ? <CheckCircleOutlined style={{ color: GREEN }} />
                  : <WarningOutlined style={{ color: r.fatal ? RED : ORANGE }} />),
              },
              { title: '檢查項目', dataIndex: 'name', width: 180 },
              { title: '結果', dataIndex: 'detail' },
              {
                title: '阻擋匯入',
                dataIndex: 'fatal',
                width: 90,
                align: 'center',
                render: (fatal: boolean, r) => (!r.ok && fatal ? <Tag color="red">是</Tag> : <Tag>否</Tag>),
              },
            ]}
          />
        </Card>

        {/* 錯誤明細 */}
        {v.issues.length > 0 && (
          <Card
            size="small"
            title={`錯誤與警示明細（顯示前 ${v.issues.length} 筆，共 ${fmtInt(v.issue_total)} 筆）`}
            style={{ marginTop: 12 }}
          >
            <Table
              size="small"
              rowKey={(r, i) => `${r.source_row_no}-${r.error_code}-${i}`}
              dataSource={v.issues}
              pagination={{ pageSize: 10 }}
              columns={[
                {
                  title: '嚴重度',
                  dataIndex: 'severity',
                  width: 90,
                  render: (s: string) => <Tag color={s === 'ERROR' ? 'red' : 'orange'}>{s}</Tag>,
                },
                { title: '列號', dataIndex: 'source_row_no', width: 80, render: (n: number) => (n > 0 ? n : '—') },
                { title: '欄位', dataIndex: 'field_name', width: 140 },
                { title: '說明', dataIndex: 'error_message' },
              ]}
            />
          </Card>
        )}

        {/* 匯入按鈕 */}
        <div style={{ marginTop: 16 }}>
          {v.needs_warning_ack && (
            <Checkbox
              checked={slot.ackWarnings}
              onChange={(e) => patch(key, { ackWarnings: e.target.checked })}
              style={{ marginBottom: 12, display: 'block' }}
            >
              我已了解上方警示，確認繼續匯入
            </Checkbox>
          )}
          <Space>
            <Button
              type="primary"
              size="large"
              loading={slot.committing}
              disabled={!v.can_commit || (v.needs_warning_ack && !slot.ackWarnings)}
              onClick={() => handleCommit(key)}
            >
              匯入資料庫
            </Button>
            <Button onClick={() => resetSlot(key)}>重新選擇檔案</Button>
          </Space>
          {!v.can_commit && (
            <Paragraph type="secondary" style={{ marginTop: 8, fontSize: 12 }}>
              {v.quality_result === 'FAIL'
                ? '品質檢查為 FAIL，必須先修正來源檔案才能匯入。'
                : '此檔案已匯入過，不重複匯入。'}
            </Paragraph>
          )}
          {slot.committing && (
            <Progress
              percent={99}
              status="active"
              showInfo={false}
              style={{ marginTop: 12 }}
            />
          )}
          {slot.committing && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              匯入中，3.5 萬列約需 10～60 秒，請勿關閉頁面……
            </Text>
          )}
        </div>
      </>
    )
  }

  // ── 匯入結果 ────────────────────────────────────────────────────────────
  const renderCommitResult = (key: OperaSourceType, slot: SlotState) => {
    const c = slot.commit!
    return (
      <Result
        status="success"
        title={`${c.source_label} 匯入完成`}
        subTitle={`批次 #${c.batch_id}　資料期間 ${c.report_start_date} ～ ${c.report_end_date}`}
        extra={[
          <Button type="primary" key="dash" onClick={() => navigate('/opera/dashboard')}>前往 Dashboard</Button>,
          <Button key="batch" onClick={() => navigate('/opera/batches')}>查看匯入紀錄</Button>,
          c.issue_total > 0 ? (
            <Button
              key="csv"
              icon={<DownloadOutlined />}
              href={batchErrorsCsvUrl(c.batch_id)}
              target="_blank"
            >
              下載錯誤明細 CSV
            </Button>
          ) : null,
          <Button key="again" onClick={() => resetSlot(key)}>再匯入一份</Button>,
        ].filter(Boolean)}
      >
        <Descriptions size="small" column={{ xs: 2, sm: 4 }} bordered>
          <Descriptions.Item label="新增"><Text strong style={{ color: GREEN }}>{fmtInt(c.inserted)}</Text></Descriptions.Item>
          <Descriptions.Item label="更新"><Text strong style={{ color: ORANGE }}>{fmtInt(c.updated)}</Text></Descriptions.Item>
          <Descriptions.Item label="略過">{fmtInt(c.skipped)}</Descriptions.Item>
          <Descriptions.Item label="拒絕">
            {c.rejected > 0 ? <Text style={{ color: RED }}>{fmtInt(c.rejected)}</Text> : fmtInt(0)}
          </Descriptions.Item>
        </Descriptions>
      </Result>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ color: BRAND }}>資料匯入</Title>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="上傳 OPERA 匯出的 TXT 報表（Tab 分隔）"
        description={
          <>
            兩份檔案可分開上傳，也可先後各匯入一次。相同內容的檔案不會重複匯入。
            <br />
            <Text type="secondary">
              個資保護：住客姓名在解析階段就會轉成遮罩版本，會員卡號完全不寫入資料庫。
            </Text>
          </>
        }
      />

      {/* 目前資料涵蓋 */}
      {status && (
        <Card size="small" title="目前資料庫涵蓋範圍" style={{ marginBottom: 16 }}>
          {!status.has_data ? <Empty description="尚未匯入任何資料" /> : (
            <>
              <Descriptions size="small" column={{ xs: 1, md: 3 }} bordered>
                <Descriptions.Item label="Departure">
                  {status.departure.start
                    ? `${status.departure.start} ～ ${status.departure.end}（${fmtInt(status.departure.rows)} 筆）`
                    : EMPTY}
                </Descriptions.Item>
                <Descriptions.Item label="History">
                  {status.history.start
                    ? `${status.history.start} ～ ${status.history.end}（${fmtInt(status.history.rows)} 天）`
                    : EMPTY}
                </Descriptions.Item>
                <Descriptions.Item label="Forecast">
                  {status.forecast.start
                    ? `${status.forecast.start} ～ ${status.forecast.end}（${fmtInt(status.forecast.rows)} 天）`
                    : EMPTY}
                </Descriptions.Item>
              </Descriptions>

              {/* C14：各年度 × 來源涵蓋 */}
              <Table
                size="small"
                style={{ marginTop: 12 }}
                pagination={false}
                rowKey="year"
                dataSource={Object.entries(status.coverage_by_year)
                  .sort((a, b) => a[0].localeCompare(b[0]))
                  .map(([year, m]) => ({ year, ...m }))}
                columns={[
                  { title: '年度', dataIndex: 'year', width: 90 },
                  {
                    title: 'Departure（筆）',
                    dataIndex: 'Departure',
                    align: 'right',
                    render: (v?: number) => (v ? fmtInt(v) : <Tag>無</Tag>),
                  },
                  {
                    title: 'History（天）',
                    dataIndex: 'History',
                    align: 'right',
                    render: (v?: number) => (v ? fmtInt(v) : <Tag color="orange">缺</Tag>),
                  },
                  {
                    title: 'Forecast（天）',
                    dataIndex: 'Forecast',
                    align: 'right',
                    render: (v?: number) => (v ? fmtInt(v) : <Tag>無</Tag>),
                  },
                ]}
              />
              {status.missing_history_years.length > 0 && (
                <Alert
                  type="warning"
                  showIcon
                  style={{ marginTop: 12 }}
                  message={`${status.missing_history_years.join('、')} 年度缺少 History and Forecast`}
                  description="這些年度只有 Departure 資料，無法計算營收、ADR、住房率，也做不出 YoY 比較。請補匯出對應年度的 History and Forecast TXT。"
                />
              )}
            </>
          )}
        </Card>
      )}

      <Row gutter={[16, 16]}>
        {SLOTS.map(({ key, title, hint }) => {
          const slot = slots[key]
          return (
            <Col xs={24} xl={12} key={key}>
              <Card
                title={<Space><Text strong style={{ color: BRAND }}>{title}</Text></Space>}
                extra={<Text type="secondary" style={{ fontSize: 12 }}>{hint}</Text>}
              >
                <Spin spinning={slot.validating}>
                  {slot.commit ? renderCommitResult(key, slot) : (
                    <>
                      <Dragger
                        accept=".txt"
                        maxCount={1}
                        fileList={slot.fileList}
                        beforeUpload={(file) => {
                          patch(key, {
                            file,
                            fileList: [{ uid: file.name, name: file.name, status: 'done' } as UploadFile],
                            result: null,
                            commit: null,
                            error: '',
                            ackWarnings: false,
                          })
                          return false      // 阻止自動上傳，改由「驗證」按鈕觸發
                        }}
                        onRemove={() => { resetSlot(key); return true }}
                      >
                        <p className="ant-upload-drag-icon"><InboxOutlined style={{ color: ACCENT }} /></p>
                        <p className="ant-upload-text">點擊或拖曳 TXT 到這裡</p>
                        <p className="ant-upload-hint">僅接受 OPERA 匯出的 .txt（Tab 分隔），單檔上限 50 MB</p>
                      </Dragger>

                      <Space style={{ marginTop: 12 }}>
                        <Button
                          type="primary"
                          disabled={!slot.file}
                          loading={slot.validating}
                          onClick={() => handleValidate(key)}
                        >
                          驗證
                        </Button>
                        {slot.file && <Text type="secondary">{`${slot.file.name}（${fmtBytes(slot.file.size)}）`}</Text>}
                      </Space>

                      {slot.error && (
                        <Alert type="error" showIcon style={{ marginTop: 12 }} message={slot.error} />
                      )}

                      {renderValidation(key, slot)}
                    </>
                  )}
                </Spin>
              </Card>
            </Col>
          )
        })}
      </Row>
    </div>
  )
}

export default OperaImportPage
