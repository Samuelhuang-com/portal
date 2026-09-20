/**
 * 稽核檢查 — 手機版填寫頁（2026-09-20 新增）
 *
 * 路由：/m/audit-check/:id    權限：audit_check_view（編輯需 audit_check_edit）
 *
 * 流程刻意與桌面版不同：桌面是「一次看整張九欄矩陣」，手機是
 *   ① 先選一個部門 → ② 逐項卡片檢視 → ③ 點卡片開底部 Drawer 填寫
 * 這樣在 390px 寬也不會有橫向捲動，現場拿手機邊查邊登錄最順。
 *
 * 與桌面版 /audit-check/sheets/:id 打同一支 API、同一組口徑 →
 * **分數與完成率兩邊必須完全一致**，這是驗收基準。
 *
 * ⚠️ 明細 Drawer 依 CLAUDE.md §7 採 placement="bottom"（手機殼層慣例），
 *    標題列格式仍照規範；本模組無 Ragic 來源故不顯示 Ragic 連結。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Button, Card, Drawer, Empty, Input, List, Progress, Radio, Segmented, Space,
  Spin, Statistic, Tag, Typography, message,
} from 'antd'
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons'

import { sheetsApi } from '@/api/auditCheck'
import type { Cell, SheetDetail, SheetItem } from '@/api/auditCheck'
import { useAuthStore } from '@/stores/authStore'

const { Text, Title } = Typography

export default function MobileAuditCheckSheet() {
  const { id } = useParams<{ id: string }>()
  const sheetId = Number(id)
  const navigate = useNavigate()
  const canEdit = useAuthStore((s) => s.hasPermission)('audit_check_edit')

  const [detail, setDetail] = useState<SheetDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [deptId, setDeptId] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (!sheetId) return
    setLoading(true)
    try {
      const res = await sheetsApi.get(sheetId)
      setDetail(res.data)
      setDeptId((prev) => prev ?? res.data.departments[0]?.id ?? null)
    } catch {
      message.error('載入稽核單失敗')
    } finally {
      setLoading(false)
    }
  }, [sheetId])

  useEffect(() => { load() }, [load])

  const cellMap = useMemo(() => {
    const m = new Map<string, Cell>()
    detail?.cells.forEach((c) => m.set(`${c.sheet_item_id}-${c.sheet_department_id}`, c))
    return m
  }, [detail])

  const typeByCode = useMemo(() => {
    const m = new Map<string, { label: string; color: string; counts_as_pass: boolean }>()
    detail?.result_types.forEach((t) => m.set(t.code, t))
    return m
  }, [detail])

  const score = detail?.scores.find((s) => s.sheet_department_id === deptId)

  // ── 編輯 Drawer ─────────────────────────────────────────────────────────
  const [picked, setPicked] = useState<SheetItem | null>(null)
  const [comment, setComment] = useState('')
  const [code, setCode] = useState('ok')
  const [saving, setSaving] = useState(false)

  const openItem = (item: SheetItem) => {
    if (!detail || deptId == null) return
    const c = cellMap.get(`${item.id}-${deptId}`)
    const def = detail.result_types.find((t) => t.is_default && t.is_active)?.code
      ?? detail.result_types[0]?.code ?? 'ok'
    setPicked(item)
    setComment(c?.comment ?? '')
    setCode(c?.result_code ?? def)
  }

  const save = async () => {
    if (!detail || !picked || deptId == null) return
    setSaving(true)
    try {
      const res = await sheetsApi.upsertCell(detail.id, {
        sheet_item_id: picked.id,
        sheet_department_id: deptId,
        comment,
        result_code: code,
      })
      setDetail(res.data)
      setPicked(null)
      message.success(comment.trim() ? '已儲存' : '已清空')
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  if (!detail) {
    return <Spin spinning={loading}><Empty description="載入中" /></Spin>
  }

  const majorNameOf = (item: SheetItem): string => {
    if (item.parent_sheet_item_id == null) return item.name
    return detail.items.find((i) => i.id === item.parent_sheet_item_id)?.name ?? ''
  }

  const activeTypes = detail.result_types.filter((t) => t.is_active)

  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => navigate('/m/audit-check')}>返回</Button>
        <Tag color="#1B3A5C" style={{ margin: 0 }}>{detail.period}</Tag>
        <Tag color="blue" style={{ margin: 0 }}>{detail.company_name}</Tag>
      </Space>

      <Card size="small" style={{ marginBottom: 10 }}>
        <Title level={5} style={{ margin: 0, color: '#1B3A5C' }}>{detail.title}</Title>
        <Text type="secondary" style={{ fontSize: 11 }}>{detail.audited_label || '尚未設定查核日期'}</Text>
        <Progress
          percent={Math.round((detail.completion_rate ?? 0) * 100)}
          size="small"
          style={{ marginTop: 6 }}
        />
        <Text type="secondary" style={{ fontSize: 11 }}>稽核完成率 {detail.completion_label}</Text>
      </Card>

      {detail.departments.length === 0 ? (
        <Empty description="這張稽核單還沒有部門欄" />
      ) : (
        <>
          <div style={{ overflowX: 'auto', marginBottom: 10 }}>
            <Segmented
              value={deptId ?? undefined}
              onChange={(v) => setDeptId(Number(v))}
              options={detail.departments.map((d) => ({ label: d.name, value: d.id }))}
            />
          </div>

          <Card size="small" style={{ marginBottom: 10 }}>
            <Space size="large">
              <Statistic title="稽核子項數" value={score?.sub_count ?? 0} valueStyle={{ fontSize: 18 }} />
              <Statistic title="達標項數" value={score?.pass_count ?? 0} valueStyle={{ fontSize: 18 }} />
              <Statistic
                title="本期分數"
                value={score?.score == null ? '本月無' : `${Math.round(score.score * 100)}%`}
                valueStyle={{ fontSize: 18, color: score?.score === 1 ? '#52c41a' : '#cf1322' }}
              />
            </Space>
          </Card>

          <List
            dataSource={detail.items}
            renderItem={(item) => {
              const c = deptId == null ? undefined : cellMap.get(`${item.id}-${deptId}`)
              const t = c ? typeByCode.get(c.result_code) : undefined
              const isTarget = deptId != null
                && item.target_department_ids.includes(
                  detail.departments.find((d) => d.id === deptId)?.department_id ?? -1,
                )
              if (item.level === 1) {
                return (
                  <div style={{ padding: '10px 4px 4px', fontWeight: 600, color: '#1B3A5C' }}>
                    {item.display_no}. {item.name}
                  </div>
                )
              }
              return (
                <Card
                  size="small"
                  style={{
                    marginBottom: 8,
                    borderColor: t && !t.counts_as_pass ? '#ffccc7' : undefined,
                    background: t && !t.counts_as_pass ? '#fff5f5' : undefined,
                  }}
                  onClick={() => openItem(item)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <Text style={{ fontSize: 13 }}>
                      {item.display_no} {item.name}
                      {item.scope_note ? <Text type="secondary">{item.scope_note}</Text> : null}
                    </Text>
                    {t && <Tag style={{ color: t.color, margin: 0 }}>{t.label}</Tag>}
                  </div>
                  <div style={{ marginTop: 6, fontSize: 12, whiteSpace: 'pre-wrap', color: t?.color }}>
                    {c?.comment || (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {isTarget ? '（本期應查，尚未填寫）' : '尚未填寫'}
                      </Text>
                    )}
                  </div>
                </Card>
              )
            }}
          />
        </>
      )}

      <Drawer
        open={!!picked}
        onClose={() => setPicked(null)}
        placement="bottom"
        height="82%"
        destroyOnClose
        title={
          <Space size={4} wrap>
            <Tag color="#1B3A5C" style={{ margin: 0 }}>{picked ? majorNameOf(picked) : ''}</Tag>
            <span style={{ fontWeight: 600, fontSize: 14 }}>
              {picked ? `${picked.display_no ?? ''} ${picked.name}` : ''}
              ：{detail.departments.find((d) => d.id === deptId)?.name ?? ''}
            </span>
          </Space>
        }
      >
        <Text type="secondary" style={{ fontSize: 12 }}>
          評語留空 ＝ 該部門本期不查此項，不計入分數分母
        </Text>
        <Input.TextArea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={6}
          disabled={!canEdit}
          style={{ marginTop: 8 }}
          placeholder="填寫查核情形"
        />
        <div style={{ marginTop: 12, marginBottom: 6 }}><Text strong>判定</Text></div>
        <Radio.Group
          value={code}
          onChange={(e) => setCode(e.target.value)}
          disabled={!canEdit}
          optionType="button"
          buttonStyle="solid"
        >
          {activeTypes.map((t) => (
            <Radio.Button key={t.code} value={t.code}>{t.label}</Radio.Button>
          ))}
        </Radio.Group>

        {canEdit && (
          <Button
            type="primary"
            block
            size="large"
            icon={<SaveOutlined />}
            loading={saving}
            style={{ marginTop: 20 }}
            onClick={save}
          >
            儲存
          </Button>
        )}
      </Drawer>
    </div>
  )
}
