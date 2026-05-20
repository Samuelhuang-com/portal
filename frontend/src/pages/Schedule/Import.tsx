/**
 * Excel 班表匯入頁
 * 路由：/schedule/import
 * 權限：schedule_manage
 * 功能：上傳 .xlsx，顯示匯入結果；年月辨識失敗時提供 fallback 手動設定
 */
import { useState, useCallback } from 'react'
import {
  Alert, Button, Card, Col, Descriptions, Divider, Form, InputNumber,
  Row, Space, Steps, Table, Tag, Typography, Upload, message,
} from 'antd'
import {
  CheckCircleOutlined, CloudUploadOutlined, ExclamationCircleOutlined,
  InboxOutlined, ReloadOutlined,
} from '@ant-design/icons'
import type { RcFile } from 'antd/es/upload'
import { importExcel, fetchImportLogs } from '@/api/schedule'
import type { ImportLog, ImportResult } from '@/types/schedule'
import { useEffect } from 'react'

const { Title, Text } = Typography
const { Dragger } = Upload

export default function ImportPage() {
  const [step, setStep]             = useState(0)   // 0=選檔 1=處理中 2=結果
  const [result, setResult]         = useState<ImportResult | null>(null)
  const [logs, setLogs]             = useState<ImportLog[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  // fallback：年月手動輸入
  const [needFallback, setNeedFallback] = useState(false)
  const [fallbackYear, setFallbackYear]   = useState<number | null>(null)
  const [fallbackMonth, setFallbackMonth] = useState<number | null>(null)
  const [pendingFile, setPendingFile]     = useState<File | null>(null)

  const loadLogs = useCallback(async () => {
    setLogsLoading(true)
    try { setLogs(await fetchImportLogs(10)) }
    finally { setLogsLoading(false) }
  }, [])

  useEffect(() => { loadLogs() }, [loadLogs])

  const doImport = async (file: File, yr?: number, mo?: number) => {
    setStep(1)
    try {
      const res = await importExcel(file, yr, mo)
      setResult(res)

      // 年月辨識失敗，需使用者手動輸入
      if (!res.year_month_detected && !yr) {
        setNeedFallback(true)
        setPendingFile(file)
        setStep(0)
        return
      }

      setStep(2)
      if (res.schedule_id) loadLogs()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '匯入失敗，請確認檔案格式')
      setStep(0)
    }
  }

  const handleFallbackSubmit = async () => {
    if (!pendingFile || !fallbackYear || !fallbackMonth) {
      message.warning('請填入年份與月份')
      return
    }
    setNeedFallback(false)
    await doImport(pendingFile, fallbackYear, fallbackMonth)
  }

  const reset = () => {
    setStep(0)
    setResult(null)
    setNeedFallback(false)
    setPendingFile(null)
    setFallbackYear(null)
    setFallbackMonth(null)
  }

  const logColumns = [
    {
      title: '年月',
      width: 80,
      render: (_: any, r: ImportLog) => `${r.schedule_year}/${String(r.schedule_month).padStart(2,'0')}`,
    },
    { title: '檔名', dataIndex: 'file_name', ellipsis: true },
    {
      title: '明細筆數',
      render: (_: any, r: ImportLog) => (
        <Space>
          <Tag color="green">成功 {r.success_count}</Tag>
          {r.warning_count > 0 && <Tag color="orange">警告 {r.warning_count}</Tag>}
          {r.error_count > 0 && <Tag color="red">錯誤 {r.error_count}</Tag>}
        </Space>
      ),
    },
    {
      title: '未知班別',
      dataIndex: 'unknown_shift_codes',
      render: (v: string[] | null) =>
        v?.length ? v.map(c => <Tag key={c} color="red">{c}</Tag>) : '—',
    },
    {
      title: '匯入時間',
      dataIndex: 'created_at',
      width: 160,
      render: (v: string) => v ? v.slice(0, 16).replace('T', ' ') : '—',
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Title level={4}>Excel 班表匯入</Title>

      <Row gutter={24}>
        <Col span={14}>
          {/* ── 步驟流程 ── */}
          <Card style={{ marginBottom: 16 }}>
            <Steps
              current={step}
              size="small"
              items={[
                { title: '選擇檔案' },
                { title: '解析處理' },
                { title: '匯入結果' },
              ]}
            />
          </Card>

          {/* ── 說明 ── */}
          {step === 0 && !needFallback && (
            <Card title="匯入說明" style={{ marginBottom: 16 }}>
              <ul style={{ paddingLeft: 20, color: '#555' }}>
                <li>支援 <b>.xlsx</b> / <b>.xls</b> 格式</li>
                <li>Sheet 名稱建議格式：<b>115年5月</b>（民國年自動轉換西元年）</li>
                <li>第 1 欄為姓名，可含括號如 <b>李宗銘(PT)</b>、<b>吳友仁(福群)</b></li>
                <li>日期列含 1～31 之日期數字，系統自動辨識</li>
                <li>空白欄位 = 未排班，不建立記錄</li>
                <li>未知班別代碼列入警告，不中斷匯入</li>
                <li><b>同年月班表已存在時，需先刪除舊班表再重新匯入</b></li>
              </ul>
            </Card>
          )}

          {/* ── Fallback：手動設定年月 ── */}
          {needFallback && (
            <Card
              style={{ marginBottom: 16, border: '2px solid #faad14' }}
              title={<Text type="warning"><ExclamationCircleOutlined /> 無法自動辨識年月</Text>}
            >
              <Alert
                type="warning"
                message={`系統無法從 Sheet 名稱辨識年月，請手動填入此班表的年月後重新匯入。`}
                style={{ marginBottom: 16 }}
              />
              <Space>
                <InputNumber
                  placeholder="西元年（如 2026）"
                  min={2020} max={2099}
                  value={fallbackYear}
                  onChange={v => setFallbackYear(v)}
                  style={{ width: 160 }}
                />
                <InputNumber
                  placeholder="月份（1-12）"
                  min={1} max={12}
                  value={fallbackMonth}
                  onChange={v => setFallbackMonth(v)}
                  style={{ width: 120 }}
                />
                <Button type="primary" onClick={handleFallbackSubmit}>確認並匯入</Button>
                <Button onClick={reset}>取消</Button>
              </Space>
            </Card>
          )}

          {/* ── 上傳區 ── */}
          {step === 0 && !needFallback && (
            <Card>
              <Dragger
                accept=".xlsx,.xls"
                showUploadList={false}
                beforeUpload={(file: RcFile) => {
                  doImport(file as File)
                  return false   // 阻止預設上傳行為
                }}
                style={{ padding: 20 }}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined style={{ fontSize: 48, color: '#4BA8E8' }} />
                </p>
                <p className="ant-upload-text">點擊或拖拽 Excel 班表檔案至此區域</p>
                <p className="ant-upload-hint" style={{ color: '#999' }}>
                  支援 .xlsx / .xls，每次匯入單一檔案
                </p>
              </Dragger>
            </Card>
          )}

          {/* ── 處理中 ── */}
          {step === 1 && (
            <Card>
              <div style={{ textAlign: 'center', padding: 40 }}>
                <CloudUploadOutlined style={{ fontSize: 48, color: '#4BA8E8' }} spin />
                <p style={{ marginTop: 16 }}>正在解析班表，請稍候…</p>
              </div>
            </Card>
          )}

          {/* ── 匯入結果 ── */}
          {step === 2 && result && (
            <Card
              title={
                result.schedule_id
                  ? <Text type="success"><CheckCircleOutlined /> 匯入完成</Text>
                  : <Text type="danger"><ExclamationCircleOutlined /> 匯入失敗</Text>
              }
              extra={<Button icon={<ReloadOutlined />} onClick={reset}>重新匯入</Button>}
            >
              {result.already_exists && (
                <Alert type="error" message={result.message} style={{ marginBottom: 16 }} />
              )}

              {result.schedule_id && (
                <>
                  <Descriptions bordered size="small" column={2}>
                    <Descriptions.Item label="班表年月">
                      {result.schedule_year} 年 {result.schedule_month} 月
                    </Descriptions.Item>
                    <Descriptions.Item label="明細總筆數">
                      <Tag color="green">{result.total_details} 筆</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="掃描人員列">
                      {result.total_rows} 列
                    </Descriptions.Item>
                    <Descriptions.Item label="警告數">
                      {result.warning_count
                        ? <Tag color="orange">{result.warning_count} 筆</Tag>
                        : <Tag color="green">0 筆</Tag>}
                    </Descriptions.Item>
                  </Descriptions>

                  {(result.unknown_shift_codes?.length ?? 0) > 0 && (
                    <>
                      <Divider orientation="left">⚠️ 未辨識班別代碼</Divider>
                      <Space wrap>
                        {result.unknown_shift_codes?.map(c => (
                          <Tag key={c} color="red">{c}</Tag>
                        ))}
                      </Space>
                      <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                        這些班別代碼尚未建立，請至「班別管理」新增後重新匯入，或忽略（明細已保留原始代碼）。
                      </Text>
                    </>
                  )}

                  {(result.new_staff_names?.length ?? 0) > 0 && (
                    <>
                      <Divider orientation="left">✅ 自動新增人員</Divider>
                      <Space wrap>
                        {result.new_staff_names?.map(n => (
                          <Tag key={n} color="blue">{n}</Tag>
                        ))}
                      </Space>
                    </>
                  )}
                </>
              )}
            </Card>
          )}
        </Col>

        {/* ── 最近匯入紀錄 ── */}
        <Col span={10}>
          <Card
            title="最近匯入紀錄"
            extra={<Button size="small" icon={<ReloadOutlined />} onClick={loadLogs}>重新整理</Button>}
          >
            <Table
              rowKey="id"
              columns={logColumns}
              dataSource={logs}
              loading={logsLoading}
              size="small"
              pagination={false}
              scroll={{ x: 500 }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
