/**
 * 退件統計（規格 docs/SPEC_return_reject_stats.md §7）
 * 篩選：公司、部門、表單類型、表單名稱、狀態、期間（StandardRangePicker，anchor=資料最後一天）、簽核人、申請人、關鍵字
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Checkbox, Col, Descriptions, Drawer, Input, Modal, Radio, Row, Select, Space, Statistic, Switch, Table, Tag, Tooltip, message } from 'antd'
import { FullscreenExitOutlined, FullscreenOutlined, LinkOutlined, ReloadOutlined, SettingOutlined, SyncOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import StandardRangePicker, { type StandardRange } from '@/components/StandardRangePicker'
import {
  exportReturnStatsExcel,
  getReturnStatsDetail,
  getReturnStatsFilters,
  getReturnStatsRecords,
  getReturnStatsSummary,
  getReturnStatsSources,
  refreshReturnApproval,
  runReturnStatsSync,
  setReturnStatsSourceActive,
  type RRSourceRow,
  type Outcome,
  type RRDetail,
  type RRSyncResult,
  type RRFilters,
  type RRListItem,
  type RRQuery,
  type RRSummary,
} from '@/api/returnRejectStats'

const OUTCOME_COLOR: Record<Outcome, string> = {
  rejected: 'red', withdrawn: 'orange', approved: 'green', agreed: 'cyan', pending: 'gold', unknown: 'default',
}
const FORM_TYPE_LABEL: Record<string, string> = { purchase: '請購', claim: '請款', seal: '用印', payable: '應付憑單', memo: '簽呈' }
const CARD_OUTCOMES: { key: Outcome; label: string }[] = [
  { key: 'rejected', label: '退件' },
  { key: 'withdrawn', label: '退簽' },
  { key: 'agreed', label: '同意' },
  { key: 'pending', label: '待審' },
]

const emptyCounts = (): Record<Outcome, number> => ({
  rejected: 0, withdrawn: 0, approved: 0, agreed: 0, pending: 0, unknown: 0,
})

export default function ReturnRejectStatsPage() {
  const [filters, setFilters] = useState<RRFilters | null>(null)
  const [company, setCompany] = useState<string[]>([])
  const [dept, setDept] = useState<string[]>([])
  const [formType, setFormType] = useState<string[]>([])
  const [formName, setFormName] = useState<string[]>([])
  const [outcome, setOutcome] = useState<string[]>([])
  const [range, setRange] = useState<StandardRange>(null)
  const [dateField, setDateField] = useState<'apply' | 'last_sign'>('apply')
  const [approver, setApprover] = useState('')
  const [ragicRej, setRagicRej] = useState(false)
  // 預設篩選退件簽核人＝楊國鼎（2026-11-03）；清空即為全部簽核人
  const [rejectionApprover, setRejectionApprover] = useState<string | undefined>('楊國鼎')
  const [applicant, setApplicant] = useState('')
  const [keyword, setKeyword] = useState('')

  const [summary, setSummary] = useState<RRSummary | null>(null)
  const [rows, setRows] = useState<RRListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [loading, setLoading] = useState(false)

  const [drawerId, setDrawerId] = useState<number | null>(null)
  const [drawerFull, setDrawerFull] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<RRSyncResult | null>(null)
  const [syncOpen, setSyncOpen] = useState(false)
  const [refreshingApproval, setRefreshingApproval] = useState(false)
  const [sourceOpen, setSourceOpen] = useState(false)
  const [sources, setSources] = useState<RRSourceRow[]>([])
  const [sourceLoading, setSourceLoading] = useState(false)
  const [detail, setDetail] = useState<RRDetail | null>(null)

  useEffect(() => {
    getReturnStatsFilters().then((r) => setFilters(r.data)).catch(() => message.error('讀取篩選選項失敗'))
  }, [])

  const query: RRQuery = useMemo(() => ({
    company, dept, form_type: formType, form_name: formName, outcome,
    start: range ? range[0].format('YYYY-MM-DD') : undefined,
    end: range ? range[1].format('YYYY-MM-DD') : undefined,
    date_field: dateField,
    approver: approver || undefined,
    rejection_approver: rejectionApprover || undefined,
    applicant: applicant || undefined,
    keyword: keyword || undefined,
    ragic_rej: ragicRej || undefined,
  }), [company, dept, formType, formName, outcome, range, dateField, approver, rejectionApprover, applicant, keyword, ragicRej])

  const load = useCallback(async (p = page, ps = pageSize) => {
    setLoading(true)
    try {
      const [s, l] = await Promise.all([
        getReturnStatsSummary(query),
        getReturnStatsRecords({ ...query, page: p, page_size: ps }),
      ])
      setSummary(s.data)
      setRows(l.data.items)
      setTotal(l.data.total)
    } catch {
      message.error('查詢失敗，請確認權限或稍後再試')
    } finally {
      setLoading(false)
    }
  }, [query, page, pageSize])

  useEffect(() => { setPage(1); load(1, pageSize) /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [query])

  const deptOptions = useMemo(() => (filters?.departments ?? [])
    .filter((d) => company.length === 0 || company.includes(d.company))
    .map((d) => ({ label: `${d.company}｜${d.dept}`, value: d.dept })), [filters, company])

  const openDetail = async (id: number) => {
    setDrawerId(id)
    setDetail(null)
    try {
      const r = await getReturnStatsDetail(id)
      setDetail(r.data)
    } catch {
      message.error('讀取明細失敗')
    }
  }

  const onExport = async () => {
    try {
      const res = await exportReturnStatsExcel(query)
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `退件統計_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      message.error('匯出失敗（筆數可能超過上限，或沒有權限）')
    }
  }

  const openSourceSettings = async () => {
    setSourceOpen(true)
    setSourceLoading(true)
    try {
      const r = await getReturnStatsSources()
      setSources(r.data)
    } catch (e) {
      const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(`讀取表單清單失敗：${d ?? '請確認「退件統計：管理」權限'}`)
    } finally {
      setSourceLoading(false)
    }
  }

  const onToggleSource = async (row: RRSourceRow, checked: boolean) => {
    try {
      await setReturnStatsSourceActive(row.id, checked)
      setSources((prev) => prev.map((s) => (s.id === row.id ? { ...s, is_active: checked } : s)))
      // 停用後統計與篩選下拉都要重算
      const [f] = await Promise.all([getReturnStatsFilters(), load(1, pageSize)])
      setFilters(f.data)
      message.success(`${checked ? '已啟用' : '已停用'}：${row.company}／${row.dept_display}／${row.form_name}`)
    } catch (e) {
      const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(`切換失敗：${d ?? '請查看後端紀錄'}`)
    }
  }

  const sourceColumns: ColumnsType<RRSourceRow> = [
    { title: '公司', dataIndex: 'company', width: 80 },
    { title: '類型', dataIndex: 'form_type', width: 80, render: (v: string) => FORM_TYPE_LABEL[v] ?? v },
    { title: '部門', dataIndex: 'dept_display', width: 110 },
    { title: '表單名稱', dataIndex: 'form_name', ellipsis: true },
    { title: '筆數', dataIndex: 'record_count', width: 80, align: 'right' },
    {
      title: '統計', dataIndex: 'is_active', width: 90, align: 'center',
      render: (_: boolean, row) => (
        <Switch checked={row.is_active} checkedChildren="啟用" unCheckedChildren="停用"
          onChange={(checked) => onToggleSource(row, checked)} />
      ),
    },
  ]

  const onManualSync = async () => {
    setSyncing(true)
    try {
      const r = await runReturnStatsSync()
      setSyncResult(r.data)
      const hasError = r.data.errors.length > 0 || r.data.sources.some((s) => (s.backfill_failed ?? 0) > 0)
      if (hasError) {
        setSyncOpen(true)
        message.warning('同步完成，但有錯誤，請看結果')
      } else {
        message.success('已完成同步')
      }
      await load(1, pageSize)
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(`同步失敗${detail ? `：${detail}` : '（請確認「退件統計：管理」權限與後端紀錄）'}`)
    } finally {
      setSyncing(false)
    }
  }

  const onRefreshApproval = async () => {
    if (drawerId === null) return
    setRefreshingApproval(true)
    try {
      const r = await refreshReturnApproval(drawerId)
      message.success(`已更新 ${r.data.steps} 筆簽核步驟，判定：${r.data.outcome_reason}`)
      await Promise.all([openDetail(drawerId), load(page, pageSize)])
    } catch (e) {
      const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(`重新抓取失敗：${d ?? '請查看後端紀錄'}`)
    } finally {
      setRefreshingApproval(false)
    }
  }

  const onRefresh = async () => {
    try {
      const [f] = await Promise.all([getReturnStatsFilters(), load(page, pageSize)])
      setFilters(f.data)
      message.success('已重新整理')
    } catch {
      message.error('重新整理失敗')
    }
  }

  const syncColumns: ColumnsType<RRSyncResult['sources'][number]> = [
    { title: '來源', dataIndex: 'source_key', ellipsis: true },
    { title: '讀取', dataIndex: 'fetched', width: 70, align: 'right', render: (v?: number) => v ?? '—' },
    { title: '新增', dataIndex: 'inserted', width: 70, align: 'right', render: (v?: number) => v ?? '—' },
    { title: '更新', dataIndex: 'updated', width: 70, align: 'right', render: (v?: number) => v ?? '—' },
    { title: '標記刪除', dataIndex: 'deleted_marked', width: 90, align: 'right', render: (v?: number) => v ?? '—' },
    {
      title: '簽核補抓（REJ）', key: 'backfill', width: 170,
      render: (_: unknown, r) => (r.backfill_tried
        ? <span>{r.backfill_tried} 筆：有步驟 {r.backfill_ok ?? 0}／無 {r.backfill_empty ?? 0}／<span style={{ color: r.backfill_failed ? '#cf1322' : undefined }}>失敗 {r.backfill_failed ?? 0}</span></span>
        : '—'),
    },
    {
      title: '錯誤', key: 'error',
      render: (_: unknown, r) => {
        const msg = r.error || (r.backfill_failed ? `補抓失敗：${r.backfill_error ?? ''}` : '')
        return msg ? <span style={{ color: '#cf1322' }}>{msg}</span> : '—'
      },
    },
  ]

  const counts = summary?.counts ?? emptyCounts()
  const toggleOutcome = (key: Outcome) => setOutcome(outcome.length === 1 && outcome[0] === key ? [] : [key])

  const columns: ColumnsType<RRListItem> = [
    { title: '公司', dataIndex: 'company', width: 70 },
    { title: '部門', dataIndex: 'dept', width: 90 },
    { title: '表單', dataIndex: 'form_name', width: 110,
      render: (v: string, r) => `${FORM_TYPE_LABEL[r.form_type] ?? r.form_type}｜${v}` },
    { title: '記錄編號', dataIndex: 'doc_no', width: 150,
      render: (v: string, r) => <a onClick={() => openDetail(r.id)}>{v}</a> },
    { title: '申請人', dataIndex: 'applicant', width: 90 },
    { title: '申請日期', dataIndex: 'apply_date', width: 110, sorter: (a, b) => (a.apply_date ?? '').localeCompare(b.apply_date ?? '') },
    { title: '金額', dataIndex: 'amount', width: 100, align: 'right',
      render: (v: number | null) => (v == null ? '—' : `$${v.toLocaleString()}`) },
    { title: '事由', dataIndex: 'purpose', ellipsis: true, width: 220 },
    { title: '狀態', dataIndex: 'outcome', width: 110,
      render: (v: Outcome, r) => <Tooltip title={r.outcome_reason}><Tag color={OUTCOME_COLOR[v]}>{r.outcome_label}</Tag></Tooltip> },
    { title: '退件／退簽原因', dataIndex: 'rejection_note', ellipsis: true, width: 220,
      render: (v: string) => (v ? <Tooltip title={v}>{v.length > 40 ? `${v.slice(0, 40)}…` : v}</Tooltip> : '—') },
    { title: '退件簽核人', dataIndex: 'rejection_approver', width: 110, render: (v: string) => v || '—' },
    { title: '下一位簽核人', dataIndex: 'next_approver', width: 120, render: (v: string | null) => v || '—' },
    { title: 'Ragic', key: 'ragic', width: 60, align: 'center',
      render: (_: unknown, r) => r.ragic_url
        ? <Tooltip title="在 Ragic 開啟"><a href={r.ragic_url} target="_blank" rel="noreferrer"><LinkOutlined /></a></Tooltip>
        : '—' },
  ]

  const identifier = detail
    ? (detail.detail['行請編號'] || detail.detail['付款編號'] || detail.ragic_record_id)
    : ''

  return (
    <div>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap size={8} style={{ width: '100%' }}>
          <Select mode="multiple" allowClear placeholder="公司" style={{ minWidth: 120 }}
            value={company} onChange={(v) => { setCompany(v); setDept([]) }}
            options={(filters?.companies ?? []).map((c) => ({ label: c, value: c }))} />
          <Select mode="multiple" allowClear placeholder="部門" style={{ minWidth: 160 }}
            value={dept} onChange={setDept} options={deptOptions} />
          <Select mode="multiple" allowClear placeholder="表單類型" style={{ minWidth: 120 }}
            value={formType} onChange={setFormType}
            options={(filters?.form_types ?? []).map((t) => ({ label: FORM_TYPE_LABEL[t] ?? t, value: t }))} />
          <Select mode="multiple" allowClear placeholder="表單名稱" style={{ minWidth: 150 }}
            value={formName} onChange={setFormName}
            options={(filters?.form_names ?? []).map((n) => ({ label: n, value: n }))} />
          <Select mode="multiple" allowClear placeholder="狀態" style={{ minWidth: 160 }}
            value={outcome} onChange={setOutcome}
            options={(filters?.outcomes ?? []).map((o) => ({ label: o.label, value: o.value }))} />
          <StandardRangePicker value={range} onChange={setRange} anchor={filters?.data_end ?? null} />
          <Radio.Group value={dateField} onChange={(e) => setDateField(e.target.value)} optionType="button" size="small">
            <Radio.Button value="apply">依申請日期</Radio.Button>
            <Radio.Button value="last_sign">依最後簽署日期</Radio.Button>
          </Radio.Group>
          <Input allowClear placeholder="流程含簽核人" style={{ width: 130 }} value={approver} onChange={(e) => setApprover(e.target.value)} />
          <Checkbox checked={ragicRej} onChange={(e) => setRagicRej(e.target.checked)}>簽核狀態 REJ（退件）</Checkbox>
          <Select allowClear showSearch placeholder="退件簽核人" style={{ minWidth: 130 }}
            value={rejectionApprover} onChange={(v) => setRejectionApprover(v)}
            options={(filters?.rejection_approvers ?? []).map((n) => ({ label: n, value: n }))} />
          <Input allowClear placeholder="申請人" style={{ width: 120 }} value={applicant} onChange={(e) => setApplicant(e.target.value)} />
          <Input allowClear placeholder="關鍵字（事由／回應）" style={{ width: 180 }} value={keyword} onChange={(e) => setKeyword(e.target.value)} />
          <Button onClick={() => {
            setCompany([]); setDept([]); setFormType([]); setFormName([]); setOutcome([])
            setRange(null); setDateField('apply'); setApprover(''); setRagicRej(false); setRejectionApprover(undefined); setApplicant(''); setKeyword('')
          }}>清除篩選</Button>
          <Button onClick={onExport}>匯出 Excel</Button>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={onRefresh}>重新整理</Button>
          <Button icon={<SettingOutlined />} onClick={openSourceSettings}>表單啟用設定</Button>
          <Button icon={<SyncOutlined />} loading={syncing} onClick={onManualSync}>重新同步</Button>
          <span style={{ color: '#595959', fontSize: 13 }}>
            上次同步：{summary?.last_synced_at ?? '尚未同步過'}
          </span>
          <Modal
            title="表單啟用設定（停用後不同步、不計入統計）"
            open={sourceOpen}
            width={820}
            footer={null}
            onCancel={() => setSourceOpen(false)}
          >
            <Table size="small" rowKey="id" loading={sourceLoading} pagination={false}
              dataSource={sources} columns={sourceColumns} />
          </Modal>
          <Modal
            open={syncOpen}
            title={syncResult && syncResult.errors.length > 0 ? '同步完成（有來源失敗）' : '同步完成'}
            onOk={() => setSyncOpen(false)}
            onCancel={() => setSyncOpen(false)}
            okText="關閉"
            cancelButtonProps={{ style: { display: 'none' } }}
            width={760}
          >
            {syncResult && (
              <>
                <p>共讀取 {syncResult.fetched} 筆，寫入 {syncResult.upserted} 筆（新增與更新合計）。完成時間 {syncResult.finished_at.replace('T', ' ').slice(0, 19)}</p>
                {syncResult.errors.length > 0 && (
                  <Alert type="error" showIcon style={{ marginBottom: 12 }}
                    message={`${syncResult.errors.length} 個來源失敗`} description={syncResult.errors.join('；')} />
                )}
                <Table size="small" pagination={false} rowKey="source_key"
                  dataSource={syncResult.sources} columns={syncColumns} />
              </>
            )}
          </Modal>
        </Space>
      </Card>

      <Row gutter={12} style={{ marginBottom: 12 }}>
        {CARD_OUTCOMES.map((c) => (
          <Col span={6} key={c.key}>
            <Card size="small" hoverable onClick={() => toggleOutcome(c.key)}
              style={{ cursor: 'pointer', borderColor: outcome.includes(c.key) ? '#1B3A5C' : undefined }}>
              <Statistic title={c.label} value={counts[c.key]} />
            </Card>
          </Col>
        ))}
      </Row>

      <Table<RRListItem>
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={rows}
        scroll={{ x: 1400 }}
        pagination={{
          current: page, pageSize, total, showSizeChanger: true, pageSizeOptions: [20, 50, 100, 200],
          showTotal: (t) => `共 ${t} 筆`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); load(p, ps) },
        }}
        onRow={(r) => ({ onClick: () => openDetail(r.id), style: { cursor: 'pointer' } })}
      />

      <Drawer
        open={drawerId !== null}
        width={drawerFull ? '100%' : 480}
        onClose={() => { setDrawerId(null); setDetail(null); setDrawerFull(false) }}
        title={detail ? (
          <Space>
            <Tag color={OUTCOME_COLOR[detail.outcome]}>{detail.outcome_label}</Tag>
            <span>{`${detail.form_name}：${identifier}`}</span>
            {detail.ragic_url && (
              <a href={detail.ragic_url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}>
                <LinkOutlined /> 在 Ragic 查看
              </a>
            )}
            <Tooltip title={drawerFull ? '還原寬度' : '全畫面檢視'}>
              <Button size="small" type="text"
                icon={drawerFull ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                onClick={() => setDrawerFull((v) => !v)} />
            </Tooltip>
          </Space>
        ) : '載入中…'}
      >
        {detail && (
          <>
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="公司">{detail.company}</Descriptions.Item>
              <Descriptions.Item label="部門">{detail.dept}</Descriptions.Item>
              <Descriptions.Item label="表單類型">{FORM_TYPE_LABEL[detail.form_type] ?? detail.form_type}</Descriptions.Item>
              <Descriptions.Item label="申請人">{detail.applicant || '—'}</Descriptions.Item>
              <Descriptions.Item label="申請日期">{detail.apply_date || '—'}</Descriptions.Item>
              <Descriptions.Item label="金額">{detail.amount == null ? '—' : `$${detail.amount.toLocaleString()}`}</Descriptions.Item>
              <Descriptions.Item label="事由"><span style={{ whiteSpace: 'pre-wrap' }}>{detail.purpose || '—'}</span></Descriptions.Item>
              <Descriptions.Item label="送簽人">{detail.submitter || '—'}</Descriptions.Item>
              <Descriptions.Item label="下一位簽核人">{detail.next_approver || '—'}</Descriptions.Item>
              <Descriptions.Item label="Ragic 狀態">{detail.ragic_status || '—'}</Descriptions.Item>
              <Descriptions.Item label="判定依據">{detail.outcome_reason}</Descriptions.Item>
            </Descriptions>

            <Space style={{ marginBottom: 6 }}>
              <span style={{ fontWeight: 600 }}>簽核流程</span>
              <Button size="small" icon={<SyncOutlined />} loading={refreshingApproval} onClick={onRefreshApproval}>
                重新抓取 Ragic 簽核資料
              </Button>
            </Space>
            <Table
              size="small"
              rowKey={(s) => `${s.step_no}-${s.role_field}`}
              pagination={false}
              dataSource={detail.steps}
              columns={[
                { title: '步驟', dataIndex: 'step_no', width: 50 },
                { title: '角色', dataIndex: 'role_field', width: 100 },
                { title: '簽核人', dataIndex: 'approver', width: 100,
                  render: (v: string, s) => (s.inferred_last ? <span>{v}（推斷）</span> : v || '—') },
                { title: '簽署日期', dataIndex: 'sign_date', width: 100, render: (v: string | null) => v || '—' },
                { title: '回應／備註', dataIndex: 'remark', render: (v: string) => (v ? <span style={{ whiteSpace: 'pre-wrap' }}>{v}</span> : '—') },
              ]}
            />

            <div style={{ fontWeight: 600, margin: '16px 0 6px' }}>原始欄位</div>
            <Descriptions size="small" column={1} bordered>
              {Object.entries(detail.detail).map(([k, v]) => (
                <Descriptions.Item key={k} label={k}>
                  <span style={{ whiteSpace: 'pre-wrap' }}>{v}</span>
                </Descriptions.Item>
              ))}
            </Descriptions>
          </>
        )}
      </Drawer>
    </div>
  )
}

