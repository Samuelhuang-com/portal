/**
 * 班表總覽頁
 * 路由：/schedule
 * 預設呈現兩個 Tab：
 *   A. 表格式班表（橫向日期 × 縱向人員，類 Excel）
 *   B. 明細列表（可篩選、可編輯）
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Button, Card, Col, Descriptions, Drawer, Form, Modal, Popconfirm,
  Row, Select, Space, Table, Tag, Tabs, Tooltip, Typography, message,
} from 'antd'
import {
  CalendarOutlined, DeleteOutlined, EditOutlined,
  PlusOutlined, ReloadOutlined, TableOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  fetchSchedules, fetchScheduleTable, fetchDetailList,
  fetchStaff, fetchShifts, fetchDepartments, fetchStats,
  editDetail, deleteDetail, addDetail, deleteSchedule,
} from '@/api/schedule'
import type {
  Schedule, ScheduleTableData, ScheduleDetailRow,
  StaffMember, ShiftType, Department,
} from '@/types/schedule'

const { Title, Text } = Typography

// ── 目前年月（預設） ─────────────────────────────────────────
const NOW = new Date()
const DEFAULT_YEAR  = NOW.getFullYear()
const DEFAULT_MONTH = NOW.getMonth() + 1

// ── 月份選項 ──────────────────────────────────────────────────
const MONTHS = Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1} 月`, value: i + 1 }))
const YEARS  = Array.from({ length: 5  }, (_, i) => {
  const y = DEFAULT_YEAR - 2 + i
  return { label: `${y} 年`, value: y }
})

export default function ScheduleOverviewPage() {
  const [year, setYear]   = useState(DEFAULT_YEAR)
  const [month, setMonth] = useState(DEFAULT_MONTH)

  // 資源清單（共用）
  const [schedules, setSchedules]   = useState<Schedule[]>([])
  const [staffList, setStaffList]   = useState<StaffMember[]>([])
  const [shiftList, setShiftList]   = useState<ShiftType[]>([])
  const [deptList, setDeptList]     = useState<Department[]>([])

  // 表格式班表
  const [tableData, setTableData]   = useState<ScheduleTableData | null>(null)
  const [tableLoading, setTableLoading] = useState(false)

  // 明細列表
  const [details, setDetails]       = useState<ScheduleDetailRow[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [filterStaff, setFilterStaff]   = useState<string | undefined>()
  const [filterShift, setFilterShift]   = useState<string | undefined>()
  const [filterDept, setFilterDept]     = useState<string | undefined>()

  // 編輯明細 Drawer
  const [editDrawerOpen, setEditDrawerOpen]   = useState(false)
  const [editingDetail, setEditingDetail]     = useState<ScheduleDetailRow | null>(null)
  const [editShiftCode, setEditShiftCode]     = useState<string>('')
  const [editRemark, setEditRemark]           = useState<string>('')

  // 新增明細 Modal
  const [addModalOpen, setAddModalOpen]       = useState(false)
  const [addForm] = Form.useForm()

  // 目前選中的 schedule
  const currentSchedule = schedules.find(
    s => s.schedule_year === year && s.schedule_month === month
  )

  // ── 載入資源 ──────────────────────────────────────────────
  const loadResources = useCallback(async () => {
    const [sl, sh, dp] = await Promise.all([
      fetchStaff({ is_active: true }),
      fetchShifts(),
      fetchDepartments(),
    ])
    setStaffList(sl)
    setShiftList(sh)
    setDeptList(dp)
  }, [])

  const loadSchedules = useCallback(async () => {
    const list = await fetchSchedules({ year })
    setSchedules(list)
  }, [year])

  // ── 表格式班表 ─────────────────────────────────────────────
  const loadTable = useCallback(async () => {
    if (!currentSchedule) { setTableData(null); return }
    setTableLoading(true)
    try {
      const data = await fetchScheduleTable(currentSchedule.id)
      setTableData(data)
    } finally {
      setTableLoading(false)
    }
  }, [currentSchedule])

  // ── 明細列表 ───────────────────────────────────────────────
  const loadDetails = useCallback(async () => {
    setDetailLoading(true)
    try {
      const list = await fetchDetailList({
        year, month,
        staff_id: filterStaff,
        shift_code: filterShift,
        department_id: filterDept,
      })
      setDetails(list)
    } finally {
      setDetailLoading(false)
    }
  }, [year, month, filterStaff, filterShift, filterDept])

  useEffect(() => {
    loadResources()
  }, [loadResources])

  useEffect(() => {
    loadSchedules()
  }, [loadSchedules])

  useEffect(() => {
    loadTable()
    loadDetails()
  }, [loadTable, loadDetails])

  // ── 編輯明細 ───────────────────────────────────────────────
  const openEditDrawer = (row: ScheduleDetailRow) => {
    setEditingDetail(row)
    setEditShiftCode(row.shift_code)
    setEditRemark(row.remark)
    setEditDrawerOpen(true)
  }

  const handleEditSave = async () => {
    if (!editingDetail || !currentSchedule) return
    try {
      await editDetail(currentSchedule.id, editingDetail.id, {
        shift_code: editShiftCode,
        remark: editRemark,
      })
      message.success('班表已更新')
      setEditDrawerOpen(false)
      loadTable()
      loadDetails()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '更新失敗')
    }
  }

  const handleDeleteDetail = async (row: ScheduleDetailRow) => {
    if (!currentSchedule) return
    try {
      await deleteDetail(currentSchedule.id, row.id)
      message.success('已刪除')
      loadTable()
      loadDetails()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '刪除失敗')
    }
  }

  // ── 新增明細 ───────────────────────────────────────────────
  const handleAddDetail = async () => {
    if (!currentSchedule) return
    try {
      const values = await addForm.validateFields()
      await addDetail(currentSchedule.id, {
        work_date: values.work_date,
        staff_id: values.staff_id,
        shift_code: values.shift_code,
        remark: values.remark || '',
      })
      message.success('已新增班表記錄')
      setAddModalOpen(false)
      addForm.resetFields()
      loadTable()
      loadDetails()
    } catch { /* form validation */ }
  }

  // ── 刪除整份班表 ──────────────────────────────────────────
  const handleDeleteSchedule = async () => {
    if (!currentSchedule) return
    try {
      await deleteSchedule(currentSchedule.id)
      message.success('班表已刪除')
      loadSchedules()
      setTableData(null)
      setDetails([])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '刪除失敗')
    }
  }

  // ── 表格式班表渲染 ─────────────────────────────────────────
  const renderTableView = () => {
    if (!tableData?.schedule) {
      return (
        <div style={{ textAlign: 'center', padding: 60, color: '#aaa' }}>
          {year} 年 {month} 月尚無班表資料，請至「匯入班表」頁面匯入 Excel。
        </div>
      )
    }

    const { headers, rows, days_in_month } = tableData

    // 動態建立欄位：姓名 + 每日 + 統計
    const cols: any[] = [
      {
        title: '姓名', dataIndex: 'staff_name', fixed: 'left', width: 110,
        render: (v: string, r: any) => (
          <div>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{v}</div>
            {r.employment_type && r.employment_type !== '正職' && (
              <Tag color="orange" style={{ fontSize: 10, marginTop: 2 }}>{r.employment_type}</Tag>
            )}
          </div>
        ),
      },
    ]

    headers.forEach(h => {
      const isWeekend = h.weekday === '六' || h.weekday === '日'
      cols.push({
        title: (
          <div style={{ textAlign: 'center', lineHeight: 1.3 }}>
            <div style={{ fontWeight: 600, color: isWeekend ? '#ef4444' : undefined }}>{h.day}</div>
            <div style={{ fontSize: 10, color: isWeekend ? '#ef4444' : '#999' }}>{h.weekday}</div>
          </div>
        ),
        key: `day_${h.day}`,
        width: 46,
        align: 'center' as const,
        render: (_: any, row: any) => {
          const cell = row.cells?.[h.day]
          if (!cell) return <span style={{ color: '#e5e7eb' }}>—</span>
          return (
            <Tooltip title={`點擊編輯（${cell.shift_code}）`}>
              <Tag
                color={cell.color}
                style={{ cursor: 'pointer', minWidth: 32, textAlign: 'center', fontSize: 11 }}
                onClick={() => {
                  // 找到對應的 detail row 開 drawer
                  const dr = details.find(d => d.id === cell.detail_id)
                  if (dr) openEditDrawer(dr)
                }}
              >
                {cell.shift_code}
              </Tag>
            </Tooltip>
          )
        },
      })
    })

    cols.push(
      {
        title: '出勤天數', dataIndex: 'work_days', fixed: 'right', width: 80,
        align: 'center' as const,
        render: (v: number) => <Tag color="blue">{v} 天</Tag>,
      },
      {
        title: '工時(hr)', dataIndex: 'work_minutes', fixed: 'right', width: 80,
        align: 'center' as const,
        render: (v: number) => (v / 60).toFixed(1),
      },
    )

    return (
      <Table
        rowKey="staff_id"
        columns={cols}
        dataSource={rows}
        loading={tableLoading}
        pagination={false}
        size="small"
        scroll={{ x: Math.max(800, 140 + days_in_month * 46 + 160) }}
        bordered
      />
    )
  }

  // ── 明細列表欄位 ──────────────────────────────────────────
  const detailColumns: ColumnsType<ScheduleDetailRow> = [
    {
      title: '日期', dataIndex: 'work_date', width: 100,
      sorter: (a, b) => a.work_date.localeCompare(b.work_date),
    },
    { title: '星期', dataIndex: 'weekday', width: 60 },
    { title: '姓名', dataIndex: 'staff_name', width: 110 },
    { title: '部門', dataIndex: 'department_name', width: 90, render: v => v || '—' },
    {
      title: '雇用', dataIndex: 'employment_type', width: 80,
      render: (v: string) => v !== '正職' ? <Tag color="orange">{v}</Tag> : '—',
    },
    {
      title: '班別', width: 80,
      render: (_: any, r: ScheduleDetailRow) => (
        <Tag color={r.shift_color} style={{ fontWeight: 600 }}>{r.shift_code}</Tag>
      ),
    },
    {
      title: '上班時間', width: 100,
      render: (_: any, r: ScheduleDetailRow) =>
        r.start_time ? `${r.start_time} – ${r.end_time}` : '—',
    },
    {
      title: '工時(hr)', dataIndex: 'work_minutes', width: 80,
      render: (v: number) => v ? (v / 60).toFixed(1) : '—',
    },
    { title: '備註', dataIndex: 'remark', render: v => v || '—' },
    {
      title: '操作', width: 100, fixed: 'right',
      render: (_: any, row: ScheduleDetailRow) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditDrawer(row)} />
          <Popconfirm title="確認刪除此筆班表記錄？" onConfirm={() => handleDeleteDetail(row)} okText="確認" cancelText="取消">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // ── 篩選 Bar ──────────────────────────────────────────────
  const FilterBar = () => (
    <Space wrap style={{ marginBottom: 12 }}>
      <Select
        allowClear placeholder="篩選人員" style={{ width: 140 }}
        value={filterStaff} onChange={setFilterStaff}
        options={staffList.map(s => ({ label: s.name, value: s.id }))}
        showSearch filterOption={(input, opt) => (opt?.label as string)?.includes(input)}
      />
      <Select
        allowClear placeholder="篩選班別" style={{ width: 120 }}
        value={filterShift} onChange={setFilterShift}
        options={shiftList.map(s => ({ label: `${s.code} ${s.name}`, value: s.code }))}
      />
      <Select
        allowClear placeholder="篩選部門" style={{ width: 120 }}
        value={filterDept} onChange={setFilterDept}
        options={deptList.map(d => ({ label: d.name, value: d.id }))}
      />
      <Button icon={<ReloadOutlined />} onClick={() => { loadTable(); loadDetails() }}>重新整理</Button>
      {currentSchedule && (
        <Button
          type="dashed" icon={<PlusOutlined />}
          onClick={() => { addForm.resetFields(); setAddModalOpen(true) }}
        >
          新增單筆
        </Button>
      )}
    </Space>
  )

  return (
    <div style={{ padding: '24px' }}>
      {/* ── 頁頭：年月選擇 + 刪除班表 ── */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            班表總覽
            {currentSchedule && (
              <Tag color="blue" style={{ marginLeft: 12, fontWeight: 400, fontSize: 13 }}>
                {currentSchedule.title}
              </Tag>
            )}
          </Title>
        </Col>
        <Col>
          <Space>
            <Select
              value={year} onChange={setYear} style={{ width: 100 }}
              options={YEARS}
            />
            <Select
              value={month} onChange={setMonth} style={{ width: 90 }}
              options={MONTHS}
            />
            {currentSchedule && (
              <Popconfirm
                title={`確認刪除 ${year}年${month}月 整份班表？此操作無法復原。`}
                onConfirm={handleDeleteSchedule}
                okText="確認刪除" okButtonProps={{ danger: true }}
                cancelText="取消"
              >
                <Button danger>刪除此份班表</Button>
              </Popconfirm>
            )}
          </Space>
        </Col>
      </Row>

      {/* ── 主內容 Tabs ── */}
      <Card>
        <Tabs
          defaultActiveKey="table"
          items={[
            {
              key: 'table',
              label: <Space><TableOutlined />表格式班表</Space>,
              children: (
                <>
                  <FilterBar />
                  {renderTableView()}
                </>
              ),
            },
            {
              key: 'list',
              label: <Space><CalendarOutlined />明細列表</Space>,
              children: (
                <>
                  <FilterBar />
                  <Table
                    rowKey="id"
                    columns={detailColumns}
                    dataSource={details}
                    loading={detailLoading}
                    size="small"
                    scroll={{ x: 900 }}
                    pagination={{ pageSize: 50, showSizeChanger: true, showTotal: t => `共 ${t} 筆` }}
                  />
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* ── 編輯明細 Drawer ── */}
      <Drawer
        title={
          editingDetail
            ? `編輯班表：${editingDetail.staff_name} ${editingDetail.work_date}`
            : '編輯班表'
        }
        open={editDrawerOpen}
        onClose={() => setEditDrawerOpen(false)}
        width={400}
        footer={
          <Space>
            <Button type="primary" onClick={handleEditSave}>儲存</Button>
            <Button onClick={() => setEditDrawerOpen(false)}>取消</Button>
          </Space>
        }
      >
        {editingDetail && (
          <Descriptions bordered column={1} size="small" style={{ marginBottom: 20 }}>
            <Descriptions.Item label="日期">{editingDetail.work_date}（{editingDetail.weekday}）</Descriptions.Item>
            <Descriptions.Item label="人員">{editingDetail.staff_name}</Descriptions.Item>
          </Descriptions>
        )}
        <Form layout="vertical">
          <Form.Item label="班別代碼" required>
            <Select
              value={editShiftCode}
              onChange={setEditShiftCode}
              options={shiftList.map(s => ({
                label: (
                  <Space>
                    <Tag color={s.color}>{s.code}</Tag>
                    {s.name}
                  </Space>
                ),
                value: s.code,
              }))}
              showSearch
              filterOption={(input, opt) => String(opt?.value).includes(input)}
            />
          </Form.Item>
          <Form.Item label="備註">
            <input
              value={editRemark}
              onChange={e => setEditRemark(e.target.value)}
              placeholder="選填備註"
              style={{ width: '100%', padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6 }}
            />
          </Form.Item>
        </Form>
      </Drawer>

      {/* ── 新增明細 Modal ── */}
      <Modal
        title="新增班表記錄"
        open={addModalOpen}
        onOk={handleAddDetail}
        onCancel={() => setAddModalOpen(false)}
        okText="新增" cancelText="取消"
        destroyOnClose
      >
        <Form form={addForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="work_date" label="日期" rules={[{ required: true, message: '請輸入日期' }]}>
            <input
              type="date"
              style={{ width: '100%', padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6 }}
            />
          </Form.Item>
          <Form.Item name="staff_id" label="人員" rules={[{ required: true, message: '請選擇人員' }]}>
            <Select
              placeholder="選擇人員"
              showSearch
              options={staffList.map(s => ({ label: `${s.name}（${s.employment_type}）`, value: s.id }))}
              filterOption={(input, opt) => (opt?.label as string)?.includes(input)}
            />
          </Form.Item>
          <Form.Item name="shift_code" label="班別" rules={[{ required: true, message: '請選擇班別' }]}>
            <Select
              placeholder="選擇班別"
              options={shiftList.map(s => ({ label: `${s.code} - ${s.name}`, value: s.code }))}
            />
          </Form.Item>
          <Form.Item name="remark" label="備註">
            <input
              placeholder="選填"
              style={{ width: '100%', padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6 }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
