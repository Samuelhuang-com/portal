/**
 * 科目與門檻設定（/jinxu/settings）— 規格書 §13.1、§12.6
 *
 * 科目分類存 DB 不寫死在程式碼（E7）——金旭可能新增科目。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Card, Input, InputNumber, Select, Space, Switch, Table, Tabs, Tag, Typography, message,
} from 'antd'

import { fetchSubjects, fetchThresholds, updateSubject, updateThreshold } from '@/api/jinxu'
import type { SubjectMapRow, ThresholdRow } from '@/types/jinxu'
import { GROUP_COLORS, dash } from '../components/constants'

const { Text, Title } = Typography

export default function JinxuSettings() {
  const [subjects, setSubjects] = useState<SubjectMapRow[]>([])
  const [groupOpts, setGroupOpts] = useState<{ value: string; label: string }[]>([])
  const [note, setNote] = useState('')
  const [thresholds, setThresholds] = useState<ThresholdRow[]>([])
  const [includeInactive, setIncludeInactive] = useState(false)

  const load = useCallback(async () => {
    const s = await fetchSubjects(includeInactive)
    setSubjects(s.items); setGroupOpts(s.group_options); setNote(s.note)
    setThresholds((await fetchThresholds()).items)
  }, [includeInactive])

  useEffect(() => { void load() }, [load])

  const saveSubject = async (code: string, patch: Partial<SubjectMapRow>) => {
    try {
      await updateSubject(code, patch)
      message.success(`科目 ${code} 已更新`)
      void load()
    } catch { message.error('更新失敗（需 jinxu_admin 權限）') }
  }

  const saveThreshold = async (key: string, value: string) => {
    try {
      await updateThreshold(key, value)
      message.success('門檻已更新')
      void load()
    } catch { message.error('更新失敗（需 jinxu_admin 權限）') }
  }

  return (
    <div>
      <Title level={4}>科目與門檻設定</Title>
      <Tabs items={[
        {
          key: 'subjects', label: '科目分類',
          children: (
            <Card size="small">
              {note && <Alert type="info" showIcon message={note} style={{ marginBottom: 12 }} />}
              <Space style={{ marginBottom: 12 }}>
                <Text>顯示已停用科目</Text>
                <Switch checked={includeInactive} onChange={setIncludeInactive} />
              </Space>
              <Table<SubjectMapRow> rowKey="subject_code" size="small" dataSource={subjects}
                pagination={false} scroll={{ x: 1000, y: 620 }}
                columns={[
                  { title: '科目代碼', dataIndex: 'subject_code', width: 100,
                    render: (v: string) => <Text strong>{v}</Text> },
                  { title: '科目名稱', dataIndex: 'subject_name', width: 190, render: dash },
                  { title: '收/抵', dataIndex: 'side_label', width: 80,
                    render: (v: string, r: SubjectMapRow) => (
                      <Tag color={r.side === 'REVENUE' ? 'green' : 'blue'}>{v}</Tag>) },
                  { title: '分析大類', dataIndex: 'group_code', width: 190,
                    render: (v: string, r: SubjectMapRow) => (
                      <Select size="small" style={{ width: 165 }} value={v} options={groupOpts}
                        onChange={(nv) => saveSubject(r.subject_code, { group_code: nv })} />) },
                  { title: '純記錄', dataIndex: 'is_memo_only', width: 110,
                    render: (v: number, r: SubjectMapRow) => (
                      <Switch size="small" checked={!!v}
                        onChange={(c) => saveSubject(r.subject_code, { is_memo_only: c ? 1 : 0 })} />) },
                  { title: '排序', dataIndex: 'sort_order', width: 90,
                    render: (v: number, r: SubjectMapRow) => (
                      <InputNumber size="small" style={{ width: 70 }} value={v}
                        onBlur={(e) => {
                          const nv = Number((e.target as HTMLInputElement).value)
                          if (nv !== v) saveSubject(r.subject_code, { sort_order: nv })
                        }} />) },
                  { title: '啟用', dataIndex: 'is_active', width: 80,
                    render: (v: number, r: SubjectMapRow) => (
                      <Switch size="small" checked={!!v}
                        onChange={(c) => saveSubject(r.subject_code, { is_active: c ? 1 : 0 })} />) },
                  { title: '最後更新', dataIndex: 'updated_at', width: 165, render: dash },
                ]} />
              <Space wrap style={{ marginTop: 12 }}>
                <Text type="secondary">大類配色：</Text>
                {groupOpts.map((g) => (
                  <Tag key={g.value} color={GROUP_COLORS[g.value] || '#bdc3c7'}>{g.label}</Tag>))}
              </Space>
            </Card>
          ),
        },
        {
          key: 'thresholds', label: '分析門檻',
          children: (
            <Card size="small">
              <Table<ThresholdRow> rowKey="setting_key" size="small" dataSource={thresholds}
                pagination={false}
                columns={[
                  { title: '設定鍵', dataIndex: 'setting_key', width: 240,
                    render: (v: string) => <Text code>{v}</Text> },
                  { title: '值', dataIndex: 'setting_value', width: 180,
                    render: (v: string, r: ThresholdRow) => (
                      <Input size="small" defaultValue={v}
                        onBlur={(e) => { if (e.target.value !== v) saveThreshold(r.setting_key, e.target.value) }} />) },
                  { title: '型別', dataIndex: 'value_type', width: 90 },
                  { title: '說明', dataIndex: 'description', render: dash },
                  { title: '最後更新', dataIndex: 'updated_at', width: 165, render: dash },
                ]} />
            </Card>
          ),
        },
      ]} />
    </div>
  )
}
