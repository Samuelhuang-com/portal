/**
 * 週期採購 — 請購單清單
 *
 * 2026-07-11（與 Samuel 討論後拿掉「批次」）：
 * 請購單不再依批次自動產生，改成在這頁按「產生本期請購單」，依週期設定
 * 的 applicable_scope 一次幫所有適用公司的啟用中部門建立空白單。這個動作
 * 隨時可觸發、同一週期＋期別（如「2026-07」）冪等，不會重複建立，也沒有
 * 固定時間窗限制 —— 週採的範圍界線是「料號主檔」，不是時間窗。
 *
 * 「新增請購單」是備用手動路徑：正常情況請購單由「產生本期請購單」一次
 * 建好，這個按鈕給某個部門臨時需要補建一張的情境用，走後端原本就有的
 * POST /requests 備用路徑，同一週期＋期別＋部門只能有一張。
 *
 * 2026-07-17（第三次調整，請購單流程大改版，與 Samuel 確認）：
 * 拿掉送出／核准／退回。期別（period_label）不再由使用者輸入，一律由後端
 * 在建立當下蓋章為現在的月份，因此「產生本期請購單」與「新增請購單」都不
 * 再有期別輸入欄位。新增「關閉」功能（全部關閉／勾選關閉），關閉當月的
 * 請購單，關閉後不能再新增/編輯明細；也支援「重新開啟」已關閉的請購單。
 */
import { useEffect, useState } from 'react'
import { Button, Card, Modal, Select, Space, Table, Tag, Typography, message } from 'antd'
import { EditOutlined, EyeOutlined, LockOutlined, PlusOutlined, ThunderboltOutlined, UnlockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import {
  closeAllRequests, closeRequests, createRequest, generateRequestsForPeriod, getCpDepartments,
  getCycles, getOpenRequestsForClose, getRequests, reopenRequests,
} from '@/api/cyclePurchase'
import type { CpCycle, CpDepartment, CpRequest } from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title } = Typography

// 2026-07-17：拿掉送出/核准狀態機，狀態欄位只剩改版前的歷史殘留值（新資料
// 一律是 draft），畫面改用 is_closed 判斷開放中／已關閉，不再需要狀態對照表。

function currentYearMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function recentMonthOptions(count = 6) {
  const opts: string[] = []
  const now = new Date()
  for (let i = 0; i < count; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    opts.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }
  return opts
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpRequestsPage() {
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canEdit = hasPermission('cycle_purchase_request')
  const canCreate = hasPermission('cycle_purchase_buyer')
  const canClose = hasPermission('cycle_purchase_close')

  const [rows, setRows] = useState<CpRequest[]>([])
  const [cycles, setCycles] = useState<CpCycle[]>([])
  const [departments, setDepartments] = useState<CpDepartment[]>([])
  const [cycleId, setCycleId] = useState<number | undefined>(undefined)
  const [periodLabel, setPeriodLabel] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)

  const [createModal, setCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createCycleId, setCreateCycleId] = useState<number | undefined>(undefined)
  const [createDeptId, setCreateDeptId] = useState<number | undefined>(undefined)

  const [generateModal, setGenerateModal] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generateCycleId, setGenerateCycleId] = useState<number | undefined>(undefined)

  // 關閉功能
  const [closeModal, setCloseModal] = useState(false)
  const [closing, setClosing] = useState(false)
  const [closeCycleId, setCloseCycleId] = useState<number | undefined>(undefined)
  const [closeCompany, setCloseCompany] = useState<string | undefined>(undefined)
  const [closeMonth, setCloseMonth] = useState<string>(currentYearMonth())
  const [openRequests, setOpenRequests] = useState<CpRequest[]>([])
  const [loadingOpen, setLoadingOpen] = useState(false)
  const [selectedCloseIds, setSelectedCloseIds] = useState<number[]>([])

  const load = () => {
    setLoading(true)
    Promise.all([
      getRequests({ cycle_id: cycleId, period_label: periodLabel }),
      getCycles(),
      getCpDepartments({ is_active: true }),
    ])
      .then(([rRes, cRes, dRes]) => {
        setRows(rRes.data)
        setCycles(cRes.data)
        setDepartments(dRes.data)
      })
      .catch(() => message.error('載入失敗'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [cycleId, periodLabel])

  const openCreate = () => {
    setCreateCycleId(undefined)
    setCreateDeptId(undefined)
    setCreateModal(true)
  }

  const handleCreate = async () => {
    if (!createCycleId || !createDeptId) { message.warning('請選擇週期與部門'); return }
    try {
      setCreating(true)
      const created = await createRequest({ cycle_id: createCycleId, department_id: createDeptId })
      message.success('已建立請購單')
      setCreateModal(false)
      load()
      navigate(`/cycle-purchase/requests/${created.data.id}`)
    } catch (err: any) {
      message.error(errMsg(err, '建立失敗'))
    } finally {
      setCreating(false)
    }
  }

  const openGenerate = () => {
    setGenerateCycleId(undefined)
    setGenerateModal(true)
  }

  const handleGenerate = async () => {
    if (!generateCycleId) { message.warning('請選擇週期'); return }
    try {
      setGenerating(true)
      const res = await generateRequestsForPeriod({ cycle_id: generateCycleId })
      message.success(`已產生（或確認既有）${res.data.length} 張本期請購單`)
      setGenerateModal(false)
      setCycleId(generateCycleId)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '產生失敗'))
    } finally {
      setGenerating(false)
    }
  }

  const openCloseModal = () => {
    setCloseCycleId(cycleId)
    setCloseCompany(undefined)
    setCloseMonth(currentYearMonth())
    setOpenRequests([])
    setSelectedCloseIds([])
    setCloseModal(true)
  }

  useEffect(() => {
    if (!closeModal || !closeCycleId || !closeMonth) { setOpenRequests([]); return }
    setLoadingOpen(true)
    getOpenRequestsForClose({ cycle_id: closeCycleId, company: closeCompany, year_month: closeMonth })
      .then((res) => {
        setOpenRequests(res.data)
        setSelectedCloseIds(res.data.map((r) => r.id))
      })
      .catch((err) => message.error(errMsg(err, '載入開放中請購單失敗')))
      .finally(() => setLoadingOpen(false))
  }, [closeModal, closeCycleId, closeCompany, closeMonth])

  const handleCloseSelected = async () => {
    if (selectedCloseIds.length === 0) { message.warning('請至少勾選一張請購單'); return }
    setClosing(true)
    try {
      const res = await closeRequests(selectedCloseIds)
      message.success(`已關閉 ${res.data.length} 張請購單`)
      setCloseModal(false)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '關閉失敗'))
    } finally {
      setClosing(false)
    }
  }

  const handleCloseAll = async () => {
    if (!closeCycleId) { message.warning('請選擇週期'); return }
    setClosing(true)
    try {
      const res = await closeAllRequests({ cycle_id: closeCycleId, company: closeCompany, year_month: closeMonth })
      message.success(`已全部關閉，共 ${res.data.length} 張請購單`)
      setCloseModal(false)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '全部關閉失敗'))
    } finally {
      setClosing(false)
    }
  }

  const handleReopen = async (row: CpRequest) => {
    try {
      await reopenRequests([row.id])
      message.success(`已重新開啟 ${row.request_no}`)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '重新開啟失敗'))
    }
  }

  const companyOptions = Array.from(new Set(departments.map((d) => d.company))).map((c) => ({ label: c, value: c }))

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 請購單</Title>
        <Space>
          {canClose && (
            <Button icon={<LockOutlined />} onClick={openCloseModal}>關閉請購單</Button>
          )}
          {canCreate && (
            <Button icon={<ThunderboltOutlined />} onClick={openGenerate}>產生本期請購單</Button>
          )}
          {canCreate && (
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增請購單</Button>
          )}
        </Space>
      </div>

      <Card>
        <Space style={{ marginBottom: 12 }}>
          <Select
            allowClear
            placeholder="依週期篩選"
            style={{ width: 200 }}
            value={cycleId}
            onChange={setCycleId}
            showSearch
            optionFilterProp="label"
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
          <Select
            allowClear
            placeholder="依期別篩選"
            style={{ width: 140 }}
            value={periodLabel}
            onChange={setPeriodLabel}
            showSearch
            options={Array.from(new Set(rows.map((r) => r.period_label))).map((p) => ({ label: p, value: p }))}
          />
        </Space>

        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          columns={[
            { title: '請購單號', dataIndex: 'request_no', width: 160 },
            { title: '週期', dataIndex: 'cycle_name', width: 140 },
            { title: '期別', dataIndex: 'period_label', width: 100 },
            { title: '公司', dataIndex: 'company', width: 110 },
            { title: '部門', dataIndex: 'department_name', width: 140 },
            {
              title: '請購總金額',
              dataIndex: 'total_amount',
              width: 120,
              align: 'right',
              render: (v: number) => v?.toLocaleString(undefined, { minimumFractionDigits: 0 }),
            },
            {
              title: '狀態',
              key: 'is_closed',
              width: 90,
              render: (_: unknown, r: CpRequest) =>
                r.is_closed
                  ? <Tag color="default" icon={<LockOutlined />}>已關閉</Tag>
                  : <Tag color="green">開放中</Tag>,
            },
            { title: '填寫人', dataIndex: 'submitted_by_name', width: 100, render: (v?: string | null) => v || '—' },
            { title: '關閉人', dataIndex: 'closed_by_name', width: 100, render: (v?: string | null) => v || '—' },
            {
              title: '操作',
              key: 'actions',
              width: 160,
              render: (_: unknown, r: CpRequest) => (
                <Space size="small">
                  <Button
                    size="small"
                    icon={canEdit && !r.is_closed ? <EditOutlined /> : <EyeOutlined />}
                    onClick={() => navigate(`/cycle-purchase/requests/${r.id}`)}
                  >
                    {canEdit && !r.is_closed ? '填寫' : '檢視'}
                  </Button>
                  {canClose && r.is_closed && (
                    <Button size="small" icon={<UnlockOutlined />} onClick={() => handleReopen(r)}>重新開啟</Button>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="產生本期請購單"
        open={generateModal}
        onOk={handleGenerate}
        onCancel={() => setGenerateModal(false)}
        okText="產生"
        cancelText="取消"
        confirmLoading={generating}
      >
        <div style={{ marginTop: 16, marginBottom: 8 }}>
          <div style={{ marginBottom: 4 }}>週期</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇週期"
            value={generateCycleId}
            onChange={setGenerateCycleId}
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
        </div>
        <div style={{ color: '#888', fontSize: 12 }}>
          會依週期設定的「適用公司」，為每個啟用中部門建立一張本月（{currentYearMonth()}）的空白請購單
          （已存在的不會重複建立）。
        </div>
      </Modal>

      <Modal
        title="新增請購單（手動備用路徑）"
        open={createModal}
        onOk={handleCreate}
        onCancel={() => setCreateModal(false)}
        okText="建立"
        cancelText="取消"
        confirmLoading={creating}
      >
        <div style={{ marginTop: 16, marginBottom: 8 }}>
          <div style={{ marginBottom: 4 }}>週期</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇週期"
            value={createCycleId}
            onChange={setCreateCycleId}
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
        </div>
        <div style={{ marginBottom: 8 }}>
          <div style={{ marginBottom: 4 }}>部門</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇部門"
            value={createDeptId}
            onChange={setCreateDeptId}
            options={departments.map((d) => ({ label: `${d.company} - ${d.dept_name}`, value: d.id }))}
          />
        </div>
        <div style={{ color: '#888', fontSize: 12 }}>
          會建立本月（{currentYearMonth()}）的請購單；同一週期＋期別＋部門只能有一張，
          若「產生本期請購單」已經建過，這裡會顯示錯誤訊息。
        </div>
      </Modal>

      <Modal
        title="關閉請購單"
        open={closeModal}
        onCancel={() => setCloseModal(false)}
        width={720}
        footer={[
          <Button key="cancel" onClick={() => setCloseModal(false)}>取消</Button>,
          <Button key="all" danger loading={closing} onClick={handleCloseAll}>全部關閉</Button>,
          <Button key="selected" type="primary" loading={closing} onClick={handleCloseSelected}>
            關閉勾選（{selectedCloseIds.length}）
          </Button>,
        ]}
      >
        <Space style={{ marginBottom: 12 }} wrap>
          <Select
            style={{ width: 200 }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇週期"
            value={closeCycleId}
            onChange={setCloseCycleId}
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
          <Select
            allowClear
            style={{ width: 160 }}
            placeholder="依公司篩選（不選＝全部）"
            value={closeCompany}
            onChange={setCloseCompany}
            options={companyOptions}
          />
          <Select
            style={{ width: 140 }}
            value={closeMonth}
            onChange={setCloseMonth}
            options={recentMonthOptions().map((m) => ({ label: m, value: m }))}
          />
        </Space>
        <Table
          dataSource={openRequests}
          rowKey="id"
          size="small"
          loading={loadingOpen}
          pagination={false}
          rowSelection={{
            selectedRowKeys: selectedCloseIds,
            onChange: (keys) => setSelectedCloseIds(keys as number[]),
          }}
          columns={[
            { title: '請購單號', dataIndex: 'request_no', width: 150 },
            { title: '公司', dataIndex: 'company', width: 100 },
            { title: '部門', dataIndex: 'department_name', width: 140 },
            { title: '填寫人', dataIndex: 'submitted_by_name', width: 100, render: (v?: string | null) => v || '—' },
            {
              title: '請購總金額',
              dataIndex: 'total_amount',
              width: 120,
              align: 'right',
              render: (v: number) => v?.toLocaleString(undefined, { minimumFractionDigits: 0 }),
            },
          ]}
        />
        <div style={{ color: '#888', fontSize: 12, marginTop: 8 }}>
          只列出目前「開放中」（尚未關閉）的請購單。「全部關閉」會關閉這個篩選條件下全部開放中的請購單
          （不受勾選影響）；「關閉勾選」只關閉目前打勾的列。
        </div>
      </Modal>
    </div>
  )
}
