/**
 * 資料匯入（/jinxu/import）— 規格書 §13.1、§9.1
 * TAB：上傳（?tab=upload，預設）／匯入紀錄（?tab=batches）
 *
 * ⚠️ 品質 FAIL 一律不得匯入，且**不提供強制覆寫按鈕**（§9.1）。
 * ⚠️ 回捲會警告「事實表的 UPDATE 無法自動回捲」（§8.4）。
 */
import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Alert, Button, Card, Col, Descriptions, Divider, Modal, Row, Select, Space,
  Statistic, Table, Tabs, Tag, Typography, Upload, message,
} from 'antd'
import { DownloadOutlined, InboxOutlined, RollbackOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'

import {
  batchErrorsCsvUrl, commitFile, fetchBatchErrors, fetchBatches, rollbackBatch, validateFile,
} from '@/api/jinxu'
import type {
  CommitResult, JinxuBatch, JinxuIssue, JinxuSourceType, ValidateResult,
} from '@/types/jinxu'
import { dash, fmtInt } from '../components/constants'

const { Text, Title } = Typography
const { Dragger } = Upload

const SOURCE_OPTIONS = [
  { value: 'FCR02_LEDGER', label: '客帳帳目明細表（FCR02）' },
  { value: 'RESV_DETAIL', label: '訂房狀況表' },
]

const SEV_COLOR: Record<string, string> = { ERROR: 'error', WARNING: 'warning', INFO: 'default' }
const QUALITY_COLOR: Record<string, string> = {
  PASS: 'success', PASS_WITH_WARNINGS: 'warning', FAIL: 'error',
}

export default function JinxuImport() {
  const [sp, setSp] = useSearchParams()
  const tab = sp.get('tab') || 'upload'

  const [file, setFile] = useState<UploadFile | null>(null)
  const [sourceType, setSourceType] = useState<JinxuSourceType | undefined>()
  const [busy, setBusy] = useState(false)
  const [vr, setVr] = useState<ValidateResult | null>(null)
  const [cr, setCr] = useState<CommitResult | null>(null)

  const [batches, setBatches] = useState<JinxuBatch[]>([])
  const [bTotal, setBTotal] = useState(0)
  const [bPage, setBPage] = useState(1)
  const [errBatch, setErrBatch] = useState<number | null>(null)
  const [errs, setErrs] = useState<JinxuIssue[]>([])

  const loadBatches = useCallback(async () => {
    const r = await fetchBatches({ page: bPage, page_size: 20 })
    setBatches(r.items); setBTotal(r.total)
  }, [bPage])

  useEffect(() => { if (tab === 'batches') void loadBatches() }, [tab, loadBatches])

  const doValidate = async () => {
    if (!file?.originFileObj) return message.warning('請先選擇 xlsx 檔案')
    setBusy(true); setVr(null); setCr(null)
    try {
      setVr(await validateFile(file.originFileObj as File, sourceType))
    } catch (e: unknown) {
      message.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '驗證失敗')
    } finally { setBusy(false) }
  }

  const doCommit = async () => {
    if (!file?.originFileObj) return
    setBusy(true)
    try {
      const r = await commitFile(file.originFileObj as File, sourceType)
      setCr(r)
      if (r.ok) { message.success(`匯入完成（批次 #${r.batch_id}）`); setVr(null); setFile(null) }
      else message.error(r.message ?? '匯入未通過品質檢查')
    } catch (e: unknown) {
      message.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '匯入失敗')
    } finally { setBusy(false) }
  }

  const doRollback = (b: JinxuBatch) => {
    Modal.confirm({
      title: `回捲批次 #${b.id}？`,
      content: (
        <Space direction="vertical">
          <Text>將刪除此批次寫入的原始資料列。</Text>
          <Alert type="warning" showIcon message={
            '事實表的 UPDATE 無法自動回捲——本批次若曾覆蓋既有資料，舊值已消失無法還原。' +
            '回捲後系統會列出受影響的業務鍵清單，需人工確認。'} />
        </Space>
      ),
      okText: '確認回捲', okButtonProps: { danger: true }, cancelText: '取消',
      onOk: async () => {
        const r = await rollbackBatch(b.id)
        Modal.info({
          title: '回捲完成',
          content: (
            <Space direction="vertical">
              <Text>已刪除原始列 {fmtInt(r.deleted_raw_rows)} 筆。</Text>
              {r.updated_keys_count > 0 && (
                <Alert type="warning" showIcon message={r.warning} />)}
              {r.updated_keys_count > 0 && (
                <Text type="secondary">受影響業務鍵：{r.updated_keys.slice(0, 20).join('、')}
                  {r.updated_keys.length > 20 && ' …'}</Text>)}
            </Space>
          ),
        })
        void loadBatches()
      },
    })
  }

  const openErrors = async (id: number) => {
    setErrBatch(id)
    setErrs((await fetchBatchErrors(id, { page: 1, page_size: 200 })).items)
  }

  const uploadTab = (
    <Card size="small">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Space wrap>
          <Text>來源類型</Text>
          <Select style={{ width: 260 }} allowClear placeholder="自動判定（依報表標題）"
                  options={SOURCE_OPTIONS} value={sourceType}
                  onChange={(v) => setSourceType(v as JinxuSourceType)} />
        </Space>

        <Dragger maxCount={1} accept=".xlsx" beforeUpload={() => false}
                 fileList={file ? [file] : []}
                 onChange={({ fileList }) => { setFile(fileList[0] ?? null); setVr(null); setCr(null) }}>
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">點擊或拖曳金旭匯出的 xlsx 到此處</p>
          <p className="ant-upload-hint">僅接受 .xlsx，單檔上限 20 MB</p>
        </Dragger>

        <Space>
          <Button type="primary" onClick={doValidate} loading={busy} disabled={!file}>驗證</Button>
          <Button danger type="primary" onClick={doCommit} loading={busy}
                  disabled={!vr?.can_commit}>確認匯入</Button>
        </Space>

        {vr && !vr.ok && <Alert type="error" showIcon message={vr.error} />}

        {vr?.ok && (
          <Card size="small" title={
            <Space><Text strong>驗證報告</Text>
              <Tag color={QUALITY_COLOR[vr.quality_result]}>{vr.quality_result}</Tag>
              <Tag color="blue">{vr.source_label}</Tag></Space>}>
            {vr.duplicate_batch && (
              <Alert type="error" showIcon style={{ marginBottom: 12 }}
                message={`此檔案已於批次 #${vr.duplicate_batch.id} 匯入過（SHA-256 相同），無法重複匯入。`}
                description={`原匯入：${vr.duplicate_batch.completed_at}　上傳者：${vr.duplicate_batch.uploaded_by}`} />
            )}
            {vr.quality_result === 'FAIL' && (
              <Alert type="error" showIcon style={{ marginBottom: 12 }}
                message="資料品質檢查未通過，無法匯入"
                description="對帳不符或存在致命錯誤。這是刻意的嚴格設定——財務與營運數字對不上一定有問題，系統不提供強制覆寫。" />
            )}
            <Row gutter={16} style={{ marginBottom: 12 }}>
              <Col span={6}><Statistic title="有效資料列" value={vr.data_rows} /></Col>
              <Col span={6}><Statistic title="住宿明細段" value={vr.child_rows} /></Col>
              <Col span={6}><Statistic title="檔案總列數" value={vr.total_source_rows} /></Col>
              <Col span={6}><Statistic title="拒絕列數" value={vr.issue_samples.filter((i) => i.severity === 'ERROR').length} /></Col>
            </Row>
            <Descriptions size="small" column={2} bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label="報表區間">
                {vr.report_start_date} ~ {vr.report_end_date}</Descriptions.Item>
              <Descriptions.Item label="飯店">{dash(vr.property_name)}</Descriptions.Item>
              <Descriptions.Item label="工作表">{vr.sheet_name}</Descriptions.Item>
              <Descriptions.Item label="印表時間">{dash(vr.printed_at)}</Descriptions.Item>
            </Descriptions>

            <Text strong>預估寫入</Text>
            <Row gutter={16} style={{ margin: '8px 0 16px' }}>
              <Col span={8}><Statistic title="新增" value={vr.delta.insert} /></Col>
              <Col span={8}><Statistic title="更新（覆蓋既有）" value={vr.delta.update}
                                       valueStyle={{ color: vr.delta.update ? '#d46b08' : undefined }} /></Col>
              <Col span={8}><Statistic title="略過（內容未變）" value={vr.delta.skip} /></Col>
            </Row>

            <Text strong>對帳結果</Text>
            <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, fontSize: 12, overflow: 'auto' }}>
              {JSON.stringify(vr.reconcile, null, 2)}
            </pre>

            {vr.unknown_subjects.length > 0 && (
              <Alert type="warning" showIcon style={{ marginBottom: 12 }}
                message={`發現 ${vr.unknown_subjects.length} 個未登錄科目，將歸為「未分類」`}
                description={vr.unknown_subjects.join('、')} />
            )}

            {vr.issue_summary.length > 0 && (
              <>
                <Text strong>問題摘要</Text>
                <Table size="small" rowKey="error_code" pagination={false} dataSource={vr.issue_summary}
                  style={{ marginTop: 8 }}
                  columns={[
                    { title: '錯誤碼', dataIndex: 'error_code' },
                    { title: '層級', dataIndex: 'severity', width: 100,
                      render: (v: string) => <Tag color={SEV_COLOR[v]}>{v}</Tag> },
                    { title: '筆數', dataIndex: 'count', align: 'right', width: 100, render: fmtInt },
                  ]} />
              </>
            )}
          </Card>
        )}

        {cr && (
          <Alert type={cr.ok ? 'success' : 'error'} showIcon
            message={cr.ok ? `匯入完成（批次 #${cr.batch_id}）` : (cr.message ?? '匯入失敗')}
            description={cr.ok
              ? `新增 ${fmtInt(cr.row_count_inserted)}／更新 ${fmtInt(cr.row_count_updated)}／略過 ${fmtInt(cr.row_count_skipped)}`
              + (cr.row_count_child ? `／住宿明細段 ${fmtInt(cr.row_count_child)}` : '')
              : '資料庫未寫入任何資料。'} />
        )}
      </Space>
    </Card>
  )

  const batchTab = (
    <Card size="small">
      <Table<JinxuBatch> rowKey="id" size="small" dataSource={batches} scroll={{ x: 1400 }}
        columns={[
          { title: '#', dataIndex: 'id', width: 60 },
          { title: '來源', dataIndex: 'source_label', width: 160 },
          { title: '檔名', dataIndex: 'source_file_name', ellipsis: true },
          { title: '區間', dataIndex: 'report_start_date', width: 190,
            render: (_: string, r: JinxuBatch) => `${r.report_start_date} ~ ${r.report_end_date}` },
          { title: '狀態', dataIndex: 'status', width: 110,
            render: (v: string) => <Tag color={v === 'COMMITTED' ? 'success' : v === 'FAILED' ? 'error' : 'default'}>{v}</Tag> },
          { title: '品質', dataIndex: 'quality_result', width: 160,
            render: (v: string) => (v ? <Tag color={QUALITY_COLOR[v]}>{v}</Tag> : '—') },
          { title: '新增', dataIndex: 'row_count_inserted', align: 'right', width: 85, render: fmtInt },
          { title: '更新', dataIndex: 'row_count_updated', align: 'right', width: 85,
            render: (v: number) => (v ? <Text type="warning">{fmtInt(v)}</Text> : '—') },
          { title: '略過', dataIndex: 'row_count_skipped', align: 'right', width: 85, render: fmtInt },
          { title: '完成時間', dataIndex: 'completed_at', width: 165, render: dash },
          { title: '上傳者', dataIndex: 'uploaded_by_name', width: 110, render: dash },
          { title: '操作', width: 200, fixed: 'right' as const,
            render: (_: unknown, r: JinxuBatch) => (
              <Space size="small">
                <a onClick={() => openErrors(r.id)}>問題明細</a>
                <a href={batchErrorsCsvUrl(r.id)} target="_blank" rel="noreferrer">
                  <DownloadOutlined /> CSV</a>
                {r.status === 'COMMITTED' && (
                  <a onClick={() => doRollback(r)} style={{ color: '#cf1322' }}>
                    <RollbackOutlined /> 回捲</a>)}
              </Space>
            ) },
        ]}
        pagination={{ current: bPage, pageSize: 20, total: bTotal, showSizeChanger: false,
                      onChange: setBPage, showTotal: (t) => `共 ${fmtInt(t)} 批次` }} />

      <Modal open={errBatch !== null} onCancel={() => setErrBatch(null)} footer={null} width={900}
             title={`批次 #${errBatch} 問題明細（前 200 筆）`}>
        <Table<JinxuIssue> rowKey="id" size="small" dataSource={errs} pagination={{ pageSize: 20 }}
          columns={[
            { title: '列號', dataIndex: 'source_row_no', width: 80 },
            { title: '欄位', dataIndex: 'field_name', width: 110 },
            { title: '原始值', dataIndex: 'raw_value', width: 190, ellipsis: true, render: dash },
            { title: '錯誤碼', dataIndex: 'error_code', width: 175 },
            { title: '說明', dataIndex: 'error_message', ellipsis: true },
            { title: '層級', dataIndex: 'severity', width: 90,
              render: (v: string) => <Tag color={SEV_COLOR[v]}>{v}</Tag> },
          ]} />
      </Modal>
    </Card>
  )

  return (
    <div>
      <Title level={4}>資料匯入</Title>
      <Tabs activeKey={tab} onChange={(k) => setSp({ tab: k })} items={[
        { key: 'upload', label: '上傳', children: uploadTab },
        { key: 'batches', label: '匯入紀錄', children: batchTab },
      ]} />
    </div>
  )
}
