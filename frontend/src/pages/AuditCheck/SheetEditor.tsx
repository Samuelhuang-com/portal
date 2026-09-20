/**
 * 稽核檢查 — 稽核單矩陣編輯（模組主畫面）
 * route: /audit-check/sheets/:id     permissionKey: audit_check_view（編輯需 audit_check_edit）
 *
 * 版面刻意比照 Excel（財#3系統建置稽核）：同一張表格由上而下依序是
 *   稽核子項數 / 達標項數 / 各部門本期稽核分數 / 缺失 / 抽檢項（1 階 + 2 階）
 *   / 上期待補正項目 / 結果 / 稽核完成率
 * 讓長期使用 Excel 的稽核人員不需要重新學版面。
 *
 * ⚠️ 三列統計數字一律由後端即時計算，前端不重算也不可編輯（使用者裁示）。
 * ⚠️ 格子編輯一律走 CellDrawer（CLAUDE.md §7）。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Button, Card, Checkbox, DatePicker, Empty, Input, InputNumber, Modal, Progress, Radio,
  Select, Space, Spin, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ArrowLeftOutlined, DownloadOutlined, EditOutlined, LayoutOutlined, PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import { itemsApi, sheetsApi } from '@/api/auditCheck'
import type {
  AuditItem, Cell, ResultType, SheetDepartment, SheetDetail, SheetItem, SheetItemSpec,
} from '@/api/auditCheck'
import { departmentsApi } from '@/api/referenceData'
import type { DepartmentRecord } from '@/api/referenceData'
import { downloadFile } from '@/api/downloadFile'
import { useAuthStore } from '@/stores/authStore'
import CellDrawer from './CellDrawer'

const { Title, Text, Paragraph } = Typography

const COL_ITEM_WIDTH = 280
const COL_DEPT_WIDTH = 210

type RowKind = 'stat' | 'deficiency' | 'major' | 'minor' | 'pending' | 'result'

interface MatrixRow {
  key: string
  kind: RowKind
  label: string
  item?: SheetItem
  statKey?: 'sub_count' | 'pass_count' | 'score'
}

function rateColor(rate: number | null): string {
  if (rate == null) return '#94a3b8'
  if (rate >= 1) return '#52c41a'
  if (rate >= 0.8) return '#4BA8E8'
  return '#cf1322'
}

export default function AuditSheetEditorPage() {
  const { id } = useParams<{ id: string }>()
  const sheetId = Number(id)
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canEdit = hasPermission('audit_check_edit')

  const [detail, setDetail] = useState<SheetDetail | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!sheetId) return
    setLoading(true)
    try {
      const res = await sheetsApi.get(sheetId)
      setDetail(res.data)
    } catch {
      message.error('載入稽核單失敗')
    } finally {
      setLoading(false)
    }
  }, [sheetId])

  useEffect(() => { load() }, [load])

  // ── 索引 ────────────────────────────────────────────────────────────────
  const cellMap = useMemo(() => {
    const m = new Map<string, Cell>()
    detail?.cells.forEach((c) => m.set(`${c.sheet_item_id}-${c.sheet_department_id}`, c))
    return m
  }, [detail])

  const typeByCode = useMemo(() => {
    const m = new Map<string, ResultType>()
    detail?.result_types.forEach((t) => m.set(t.code, t))
    return m
  }, [detail])

  const scoreByDept = useMemo(() => {
    const m = new Map<number, { sub_count: number; pass_count: number; score: number | null; score_label: string }>()
    detail?.scores.forEach((s) => m.set(s.sheet_department_id, s))
    return m
  }, [detail])

  const reviewByDept = useMemo(() => {
    const m = new Map<number, { pending_text: string | null; pending_result: string; result_text: string | null; result_status: string; source_period: string | null }>()
    detail?.reviews.forEach((r) => m.set(r.sheet_department_id, r))
    return m
  }, [detail])

  const majorNameOf = useCallback((item: SheetItem): string => {
    if (!detail) return ''
    if (item.parent_sheet_item_id == null) return item.name
    const parent = detail.items.find((i) => i.id === item.parent_sheet_item_id)
    return parent?.name ?? ''
  }, [detail])

  // ── 表格列 ──────────────────────────────────────────────────────────────
  const rows: MatrixRow[] = useMemo(() => {
    if (!detail) return []
    const out: MatrixRow[] = [
      { key: 'stat-sub', kind: 'stat', label: '稽核子項數', statKey: 'sub_count' },
      { key: 'stat-pass', kind: 'stat', label: '達標項數', statKey: 'pass_count' },
      { key: 'stat-score', kind: 'stat', label: '各部門本期稽核分數', statKey: 'score' },
      { key: 'deficiency', kind: 'deficiency', label: '缺失' },
    ]
    detail.items.forEach((it) => {
      out.push({
        key: `item-${it.id}`,
        kind: it.level === 1 ? 'major' : 'minor',
        label: `${it.display_no ?? ''} ${it.name}${it.scope_note ?? ''}`.trim(),
        item: it,
      })
    })
    out.push({ key: 'pending', kind: 'pending', label: `${detail.reviews[0]?.source_period ?? '上期'}待補正項目` })
    out.push({ key: 'result', kind: 'result', label: '結果' })
    return out
  }, [detail])

  // ── 格子 Drawer ─────────────────────────────────────────────────────────
  const [drawerItemId, setDrawerItemId] = useState<number | null>(null)
  const [drawerDeptIdx, setDrawerDeptIdx] = useState(0)

  const drawerItem = detail?.items.find((i) => i.id === drawerItemId) ?? null
  const drawerDept: SheetDepartment | null = detail?.departments[drawerDeptIdx] ?? null

  const openCell = (item: SheetItem, deptIdx: number) => {
    setDrawerItemId(item.id)
    setDrawerDeptIdx(deptIdx)
  }

  const navigateCell = (delta: number) => {
    if (!detail) return
    const next = drawerDeptIdx + delta
    if (next < 0 || next >= detail.departments.length) {
      message.info(delta > 0 ? '已是最後一欄' : '已是第一欄')
      return
    }
    setDrawerDeptIdx(next)
  }

  // ── 文字編輯 Modal（缺失 / 覆核）─────────────────────────────────────────
  const [textModal, setTextModal] = useState<{
    open: boolean
    kind: RowKind
    deptId: number
    title: string
    value: string
    code: string
  } | null>(null)

  const openTextModal = (kind: RowKind, dept: SheetDepartment) => {
    if (!canEdit || !detail) return
    if (kind === 'deficiency') {
      setTextModal({
        open: true, kind, deptId: dept.id,
        title: `缺失 — ${dept.name}`,
        value: dept.deficiency_override ?? dept.deficiency,
        code: '',
      })
      return
    }
    const rv = reviewByDept.get(dept.id)
    setTextModal({
      open: true, kind, deptId: dept.id,
      title: `${kind === 'pending' ? '待補正項目' : '覆核結果'} — ${dept.name}`,
      value: (kind === 'pending' ? rv?.pending_text : rv?.result_text) ?? '',
      code: (kind === 'pending' ? rv?.pending_result : rv?.result_status) ?? 'ok',
    })
  }

  const saveTextModal = async () => {
    if (!textModal || !detail) return
    try {
      let res
      if (textModal.kind === 'deficiency') {
        res = await sheetsApi.upsertDeficiency(detail.id, textModal.deptId, textModal.value.trim() || null)
      } else if (textModal.kind === 'pending') {
        res = await sheetsApi.upsertReview(detail.id, textModal.deptId, {
          pending_text: textModal.value, pending_result: textModal.code,
        })
      } else {
        res = await sheetsApi.upsertReview(detail.id, textModal.deptId, {
          result_text: textModal.value, result_status: textModal.code,
        })
      }
      setDetail(res.data)
      setTextModal(null)
      message.success('已儲存')
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    }
  }

  // ── 新增部門欄（2026-09-21 使用者要求：能直接在稽核單上加部門）──────────
  // 部門仍然只能從 settings/company-departments 主檔挑（CLAUDE.md §9 單一真實
  // 來源），這裡只是省掉「開版面調整 Modal → 在一大包設定裡找部門」那一步。
  const [deptModalOpen, setDeptModalOpen] = useState(false)
  const [deptOptions, setDeptOptions] = useState<DepartmentRecord[]>([])
  const [deptPicked, setDeptPicked] = useState<number[]>([])
  const [deptSaving, setDeptSaving] = useState(false)

  const openDeptModal = async () => {
    if (!detail) return
    try {
      const res = await departmentsApi.list(detail.company_id)
      setDeptOptions(res.data.filter((d) => d.is_active))
      setDeptPicked([])
      setDeptModalOpen(true)
    } catch {
      message.error('載入部門主檔失敗')
    }
  }

  /**
   * 以「現有部門 ＋ 新勾選的」呼叫 layout API。
   * ⚠️ 檢查項一定要原封不動帶回去（含 scope_note 與本期應查部門），
   *    後端的 apply_layout 是「完全取代」語意，沒帶到的列會被刪掉，
   *    連同該列已填的評語一起消失。
   */
  const addDepartments = async () => {
    if (!detail || deptPicked.length === 0) return
    const specs: SheetItemSpec[] = detail.items
      .filter((i) => i.level === 2)
      .map((i) => ({
        item_id: i.item_id,
        scope_note: i.scope_note,
        target_department_ids: i.target_department_ids,
      }))
    setDeptSaving(true)
    try {
      const res = await sheetsApi.updateLayout(detail.id, {
        department_ids: [...detail.departments.map((d) => d.department_id), ...deptPicked],
        items: specs,
      })
      setDetail(res.data)
      setDeptModalOpen(false)
      message.success(`已新增 ${deptPicked.length} 個部門欄`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '新增失敗')
    } finally {
      setDeptSaving(false)
    }
  }

  // ── 版面調整 ────────────────────────────────────────────────────────────
  const [layoutOpen, setLayoutOpen] = useState(false)
  const [allItems, setAllItems] = useState<AuditItem[]>([])
  const [depts, setDepts] = useState<DepartmentRecord[]>([])
  const [pickedItems, setPickedItems] = useState<number[]>([])
  const [pickedDepts, setPickedDepts] = useState<number[]>([])
  const [layoutSaving, setLayoutSaving] = useState(false)

  const openLayout = async () => {
    if (!detail) return
    try {
      const [i, d] = await Promise.all([itemsApi.list(), departmentsApi.list(detail.company_id)])
      setAllItems(i.data)
      setDepts(d.data.filter((x) => x.is_active))
      setPickedItems(detail.items.filter((x) => x.level === 2).map((x) => x.item_id))
      setPickedDepts(detail.departments.map((x) => x.department_id))
      setLayoutOpen(true)
    } catch {
      message.error('載入主檔失敗')
    }
  }

  const saveLayout = async () => {
    if (!detail) return
    if (pickedItems.length === 0 || pickedDepts.length === 0) {
      message.warning('檢查項與部門至少各選一項')
      return
    }
    const specs: SheetItemSpec[] = pickedItems.map((itemId) => {
      const existing = detail.items.find((x) => x.item_id === itemId)
      return {
        item_id: itemId,
        scope_note: existing?.scope_note ?? null,
        target_department_ids: existing?.target_department_ids ?? [],
      }
    })
    setLayoutSaving(true)
    try {
      const res = await sheetsApi.updateLayout(detail.id, {
        department_ids: pickedDepts,
        items: specs,
      })
      setDetail(res.data)
      setLayoutOpen(false)
      message.success('版面已更新')
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '更新失敗')
    } finally {
      setLayoutSaving(false)
    }
  }

  // ── 抬頭欄位 ────────────────────────────────────────────────────────────
  const patchSheet = async (body: Record<string, unknown>) => {
    if (!detail) return
    try {
      const res = await sheetsApi.update(detail.id, body)
      setDetail(res.data)
      message.success('已儲存')
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    }
  }

  const doExport = async () => {
    if (!detail) return
    await downloadFile(
      sheetsApi.exportUrl(detail.id),
      `${detail.title}-${detail.period}-${detail.company_name}.xlsx`,
    )
  }

  // ── 欄位定義 ────────────────────────────────────────────────────────────
  const columns: ColumnsType<MatrixRow> = useMemo(() => {
    if (!detail) return []
    const first: ColumnsType<MatrixRow>[number] = {
      title: '檢查項 / 統計',
      dataIndex: 'label',
      key: 'label',
      fixed: 'left',
      width: COL_ITEM_WIDTH,
      render: (_: unknown, row: MatrixRow) => {
        if (row.kind === 'major') {
          return <Text strong style={{ color: '#1B3A5C' }}>{row.label}</Text>
        }
        if (row.kind === 'minor') {
          return <span style={{ paddingLeft: 16 }}>{row.label}</span>
        }
        return <Text strong style={{ color: row.kind === 'deficiency' ? '#cf1322' : undefined }}>{row.label}</Text>
      },
    }

    const deptCols = detail.departments.map((d, idx) => ({
      title: d.name,
      key: `dept-${d.id}`,
      width: COL_DEPT_WIDTH,
      render: (_: unknown, row: MatrixRow) => {
        if (row.kind === 'stat') {
          const sc = scoreByDept.get(d.id)
          if (!sc) return <Text type="secondary">—</Text>
          if (row.statKey === 'score') {
            if (sc.score == null) return <Text type="secondary">本月無</Text>
            const pct = Math.round(sc.score * 100)
            return (
              <Text strong style={{ color: sc.score >= 1 ? '#52c41a' : '#cf1322' }}>
                {sc.score.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')}（{pct}%）
              </Text>
            )
          }
          return <Text strong>{row.statKey === 'sub_count' ? sc.sub_count : sc.pass_count}</Text>
        }

        if (row.kind === 'deficiency') {
          const isOverride = !!d.deficiency_override
          return (
            <div
              onClick={() => openTextModal('deficiency', d)}
              style={{
                whiteSpace: 'pre-wrap', color: '#cf1322', fontSize: 12,
                cursor: canEdit ? 'pointer' : 'default', minHeight: 20,
              }}
            >
              {d.deficiency || <Text type="secondary">—</Text>}
              {isOverride && <Tag color="default" style={{ marginLeft: 4 }}>人工</Tag>}
            </div>
          )
        }

        if (row.kind === 'pending' || row.kind === 'result') {
          const rv = reviewByDept.get(d.id)
          const text = (row.kind === 'pending' ? rv?.pending_text : rv?.result_text) ?? ''
          const code = (row.kind === 'pending' ? rv?.pending_result : rv?.result_status) ?? 'ok'
          const t = typeByCode.get(code)
          return (
            <div
              onClick={() => openTextModal(row.kind, d)}
              style={{
                whiteSpace: 'pre-wrap', fontSize: 12, color: t?.color,
                cursor: canEdit ? 'pointer' : 'default', minHeight: 20,
              }}
            >
              {text || <Text type="secondary">—</Text>}
            </div>
          )
        }

        // major / minor：查核評語
        const item = row.item!
        const c = cellMap.get(`${item.id}-${d.id}`)
        const t = c ? typeByCode.get(c.result_code) : undefined
        const isTarget = item.target_department_ids.includes(d.department_id)
        return (
          <div
            onClick={() => openCell(item, idx)}
            style={{
              whiteSpace: 'pre-wrap',
              fontSize: 12,
              color: t?.color,
              cursor: 'pointer',
              minHeight: 22,
              padding: '2px 4px',
              borderRadius: 4,
              background: t && !t.counts_as_pass ? '#fff5f5' : undefined,
              border: t && !t.counts_as_pass ? '1px solid #ffccc7'
                : (isTarget && !c ? '1px dashed #d9d9d9' : '1px solid transparent'),
            }}
          >
            {c?.comment || <Text type="secondary">{isTarget ? '（本期應查）' : '—'}</Text>}
          </div>
        )
      },
    }))

    return [first, ...deptCols]
  }, [detail, cellMap, typeByCode, scoreByDept, reviewByDept, canEdit])

  if (!detail) {
    return <Spin spinning={loading}><Empty description="載入中" /></Spin>
  }

  const activeTypes = detail.result_types.filter((t) => t.is_active)

  return (
    <div>
      {/* ── 抬頭 ──────────────────────────────────────────────────────── */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center' }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/audit-check')}>返回</Button>
          <div>
            <Title level={5} style={{ margin: 0, color: '#1B3A5C' }}>
              <Tag color="#1B3A5C">{detail.period}</Tag>
              {detail.title}
              <Tag color="blue" style={{ marginLeft: 8 }}>{detail.company_name}</Tag>
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {detail.audited_label || '尚未設定查核日期'}
              {detail.executor_label ? ` ・ ${detail.executor_label}` : ''}
            </Text>
          </div>

          <div style={{ minWidth: 220 }}>
            <Progress
              percent={Math.round((detail.completion_rate ?? 0) * 100)}
              strokeColor={rateColor(detail.completion_rate)}
              size="small"
            />
            <Text type="secondary" style={{ fontSize: 12 }}>稽核完成率 {detail.completion_label}</Text>
          </div>

          <div style={{ marginLeft: 'auto' }}>
            <Space wrap>
              {canEdit && (
                <DatePicker
                  value={detail.audited_on ? dayjs(detail.audited_on) : null}
                  onChange={(v) => patchSheet({ audited_on: v ? v.format('YYYY-MM-DD') : null })}
                  placeholder="查核日期"
                />
              )}
              {canEdit && (
                <Select
                  value={detail.audited_session ?? undefined}
                  onChange={(v) => patchSheet({ audited_session: v ?? null })}
                  placeholder="時段"
                  allowClear
                  style={{ width: 96 }}
                  options={[{ value: '上午', label: '上午' }, { value: '下午', label: '下午' }]}
                />
              )}
              {canEdit && (
                <Select
                  value={detail.status}
                  onChange={(v) => patchSheet({ status: v })}
                  style={{ width: 120 }}
                  options={[
                    { value: 'draft', label: '草稿' },
                    { value: 'submitted', label: '已送出' },
                    { value: 'reviewed', label: '已覆核' },
                  ]}
                />
              )}
              {canEdit && (
                <Tooltip title="完成率「已完成數」的人工調整。本期有項目其實沒做到就填 -1，畫面會顯示成「3*3-1=8　8/9 = 88.9%」（比照 Excel 寫法）">
                  <InputNumber
                    value={detail.completion_adjust}
                    onChange={(v) => patchSheet({ completion_adjust: v ?? 0 })}
                    style={{ width: 120 }}
                    addonBefore="完成數±"
                    step={1}
                  />
                </Tooltip>
              )}
              {canEdit && (
                <Button type="primary" ghost icon={<PlusOutlined />} onClick={openDeptModal}>
                  新增部門欄
                </Button>
              )}
              {canEdit && <Button icon={<LayoutOutlined />} onClick={openLayout}>版面調整</Button>}
              <Button icon={<DownloadOutlined />} onClick={doExport}>匯出 Excel</Button>
              <Button icon={<ReloadOutlined />} onClick={load} loading={loading} />
            </Space>
          </div>
        </div>

        <div style={{ marginTop: 8 }}>
          <Space size={4} wrap>
            <Text type="secondary" style={{ fontSize: 12 }}>判定：</Text>
            {activeTypes.map((t) => (
              <Tag key={t.code} color={t.counts_as_pass ? 'default' : 'error'} style={{ color: t.color }}>
                {t.label}{t.counts_as_pass ? '' : '（不達標）'}
              </Tag>
            ))}
            <Tooltip title="可在「稽核期別」編輯中切換；關閉後覆核不計入各部門分數">
              <Tag color={detail.review_counts_in_score ? 'processing' : 'default'}>
                覆核{detail.review_counts_in_score ? '計入' : '不計入'}分數
              </Tag>
            </Tooltip>
          </Space>
        </div>
      </Card>

      {/* ── 矩陣 ──────────────────────────────────────────────────────── */}
      <Spin spinning={loading}>
        <Table<MatrixRow>
          size="small"
          bordered
          sticky
          rowKey="key"
          columns={columns}
          dataSource={rows}
          pagination={false}
          scroll={{ x: COL_ITEM_WIDTH + detail.departments.length * COL_DEPT_WIDTH }}
          rowClassName={(row) =>
            row.kind === 'major' ? 'audit-row-major'
              : row.kind === 'stat' ? 'audit-row-stat'
                : row.kind === 'deficiency' ? 'audit-row-deficiency' : ''
          }
        />
      </Spin>

      <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8 }}>
        點任一格即可填寫評語與判定。評語留空 ＝ 該部門本期不查此項，不計入分數分母。
        三列統計數字由系統依評語與判定自動計算，不可手改。
      </Paragraph>

      {/* ── 備註 ──────────────────────────────────────────────────────── */}
      <Card size="small" title="備註" style={{ marginTop: 12 }}>
        <Input.TextArea
          defaultValue={detail.remark ?? ''}
          rows={3}
          disabled={!canEdit}
          placeholder="表尾自由備註（如合約用印進度）"
          onBlur={(e) => {
            if (e.target.value !== (detail.remark ?? '')) patchSheet({ remark: e.target.value })
          }}
        />
      </Card>

      {/* ── Drawer / Modal ───────────────────────────────────────────── */}
      <CellDrawer
        open={drawerItem != null && drawerDept != null}
        sheetId={detail.id}
        period={detail.period}
        companyName={detail.company_name}
        item={drawerItem}
        majorName={drawerItem ? majorNameOf(drawerItem) : ''}
        department={drawerDept}
        cell={drawerItem && drawerDept ? cellMap.get(`${drawerItem.id}-${drawerDept.id}`) : undefined}
        resultTypes={detail.result_types}
        readOnly={!canEdit}
        onClose={() => setDrawerItemId(null)}
        onSaved={(d) => setDetail(d)}
        onNavigate={navigateCell}
      />

      <Modal
        open={!!textModal?.open}
        title={textModal?.title}
        onOk={saveTextModal}
        onCancel={() => setTextModal(null)}
        okText="儲存"
        cancelText="取消"
        destroyOnClose
      >
        <Input.TextArea
          value={textModal?.value ?? ''}
          rows={6}
          onChange={(e) => setTextModal((s) => (s ? { ...s, value: e.target.value } : s))}
        />
        {textModal?.kind === 'deficiency' ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            留空 ＝ 還原成系統自動彙整（依判定類型的「列入缺失彙整」設定）
          </Text>
        ) : (
          <div style={{ marginTop: 12 }}>
            <Radio.Group
              value={textModal?.code}
              onChange={(e) => setTextModal((s) => (s ? { ...s, code: e.target.value } : s))}
              optionType="button"
              buttonStyle="solid"
            >
              {activeTypes.map((t) => (
                <Radio.Button key={t.code} value={t.code}>{t.label}</Radio.Button>
              ))}
            </Radio.Group>
          </div>
        )}
      </Modal>

      <Modal
        open={deptModalOpen}
        title="新增部門欄"
        onOk={addDepartments}
        confirmLoading={deptSaving}
        onCancel={() => setDeptModalOpen(false)}
        okText="新增"
        cancelText="取消"
        okButtonProps={{ disabled: deptPicked.length === 0 }}
        destroyOnClose
      >
        {(() => {
          const used = new Set(detail.departments.map((d) => d.department_id))
          const candidates = deptOptions.filter((d) => !used.has(d.id))
          if (candidates.length === 0) {
            return (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <div>
                    <div>「{detail.company_name}」底下的部門都已經在這張稽核單上了</div>
                    <Button type="link" onClick={() => navigate('/settings/company-departments')}>
                      前往「系統設定 → 公司/部門管理」新增部門
                    </Button>
                  </div>
                }
              />
            )
          }
          return (
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                只列出「{detail.company_name}」底下、還沒加進這張稽核單的部門
              </Text>
              <Select
                mode="multiple"
                value={deptPicked}
                onChange={setDeptPicked}
                style={{ width: '100%', marginTop: 8 }}
                placeholder="可一次選多個"
                options={candidates.map((d) => ({ value: d.id, label: d.name }))}
              />
              <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 10, marginBottom: 0 }}>
                新增的欄位會排在最後面，已填的評語不受影響。要調整順序或移除欄位請用「版面調整」。
                <br />
                找不到要的部門？部門主檔在「系統設定 → 公司/部門管理」，
                本模組不另建部門主檔。
              </Paragraph>
            </div>
          )
        })()}
      </Modal>

      <Modal
        open={layoutOpen}
        title="版面調整 — 本期抽檢項目與部門欄"
        onOk={saveLayout}
        confirmLoading={layoutSaving}
        onCancel={() => setLayoutOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={760}
        destroyOnClose
      >
        <div style={{ marginBottom: 12 }}>
          <Text strong>部門欄</Text>
          <Select
            mode="multiple"
            value={pickedDepts}
            onChange={setPickedDepts}
            style={{ width: '100%', marginTop: 6 }}
            options={depts.map((d) => ({ value: d.id, label: d.name }))}
          />
        </div>
        <Text strong>抽檢項目（已選 {pickedItems.length} 項）</Text>
        <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 6, padding: 12, marginTop: 6 }}>
          {allItems.filter((m) => m.is_active).map((major) => (
            <div key={major.id} style={{ marginBottom: 12 }}>
              <Text strong style={{ color: '#1B3A5C' }}>{major.name}</Text>
              <div style={{ paddingLeft: 16, marginTop: 4 }}>
                <Checkbox.Group
                  value={pickedItems}
                  onChange={(vals) => {
                    const others = pickedItems.filter(
                      (pid) => !(major.children ?? []).some((c) => c.id === pid),
                    )
                    setPickedItems([...others, ...(vals as number[])])
                  }}
                  options={(major.children ?? []).filter((c) => c.is_active).map((c) => ({ value: c.id, label: c.name }))}
                />
              </div>
            </div>
          ))}
        </div>
        <Tooltip title="移除的列或欄，其已填寫的評語會一併刪除">
          <Text type="warning" style={{ fontSize: 12 }}>⚠️ 取消勾選會連同該列／該欄已填的評語一起刪除</Text>
        </Tooltip>
      </Modal>

      <style>{`
        .audit-row-major > td { background: #f6f9fc !important; }
        .audit-row-stat > td { background: #fafafa !important; }
        .audit-row-deficiency > td { background: #fff5f5 !important; }
      `}</style>
    </div>
  )
}
