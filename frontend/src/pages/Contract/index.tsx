/**
 * 合約管理 — 列表頁面
 *
 * 包含：
 *   - 合約清單表格（分頁、篩選）
 *   - Drawer 明細檢視
 *   - 新增、刪除操作
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Table, Tag, Button, Space,
  Typography, Breadcrumb, Drawer, Descriptions, message,
  Input, Select, Tooltip, Switch, Divider, Tabs,
  Empty, Modal, Form, InputNumber, Spin, Popconfirm, Progress,
  Upload, Image,
} from 'antd'
import { DatePicker } from 'antd'
import {
  HomeOutlined, PlusOutlined, DeleteOutlined,
  LinkOutlined, ReloadOutlined, SearchOutlined,
  EditOutlined, SaveOutlined, CloseOutlined,
  UnorderedListOutlined, DollarOutlined, DownloadOutlined, SyncOutlined,
  PaperClipOutlined, FilePdfOutlined, InboxOutlined,
  ClockCircleOutlined, AuditOutlined,
  ExpandOutlined, CompressOutlined,
  SafetyOutlined, CheckSquareOutlined, SolutionOutlined, DashboardOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType, TableProps } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchContracts, deleteContract, fetchContractStats,
  createContract, fetchVendorOptions, updateContract,
  fetchContractItems, createContractItem, updateContractItem, deleteContractItem,
  fetchClaims, fetchBudgetCategoryOptions, exportContractsExcel,
  fetchRenewalsByContract, applyRenewal,
  fetchClaimAttachments, uploadClaimAttachment, deleteClaimAttachment, getAttachmentUrl,
  submitContractForReview, approveContract, rejectContract,
  fetchContractAttachments, uploadContractAttachment, deleteContractAttachment,
  fetchCostAllocations, saveCostAllocations,
  batchUpdateManager, batchSubmit,
} from '@/api/contract'
import type { CostAllocationItem, CostAllocationRecord } from '@/api/contract'
import { companiesApi, departmentsApi, pricingSpecsApi } from '@/api/referenceData'
import type { CompanyOption, DepartmentOption, PricingSpecOption } from '@/api/referenceData'
import { usersApi } from '@/api/users'
import type { UserOptionItem } from '@/api/users'
import type {
  ContractRecord, ContractFilters, VendorListResponse, ContractUpdate,
  BudgetCategoryListResponse, RenewalRecord, ClaimAttachment, ContractAttachment,
} from '@/types/contract'
import type { ContractItemRecord, ContractItemCreate, ClaimRecord } from '@/api/contract'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import {
  ContractChangeLogTab,
  ContractPaymentScheduleTab,
  ContractAuditLogTab,
} from './HistoryTabs'
import {
  ContractApprovalStagesTab,
  ContractAcceptancesTab,
  ContractDepositsTab,
  CostSummaryCard,
} from './PhasITabs'
import ContractSlaTab from './SlaTab'

const { Title } = Typography
const { Option } = Select

// ── 常數 ──────────────────────────────────────────────────────────────────────
const STATUS_TAG_COLOR: Record<string, string> = {
  '草稿': 'default',
  '審核中': 'processing',
  '生效中': 'success',
  '即將到期': 'warning',
  '已終止': 'error',
}

const RISK_LEVEL_COLOR: Record<string, string> = {
  '低': '#52C41A',
  '中': '#FAAD14',
  '高': '#FF7A45',
  '關鍵': '#FF4D4F',
}

// ── 工具函式 ──────────────────────────────────────────────────────────────────
const fmtMoney = (n: number | null | undefined) =>
  n == null ? '-' : `$${n.toLocaleString('zh-TW')}`

const fmtDate = (d: string | null | undefined) =>
  d ? dayjs(d).format('YYYY-MM-DD') : '-'

const statusTag = (status: string) => {
  const color = STATUS_TAG_COLOR[status] ?? 'default'
  return <Tag color={color}>{status || '-'}</Tag>
}

// ═════════════════════════════════════════════════════════════════════════════
// 主元件
// ═════════════════════════════════════════════════════════════════════════════

export default function ContractListPage() {
  const [contracts, setContracts] = useState<ContractRecord[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({ page: 1, size: 20, total: 0 })
  const [filters, setFilters] = useState<ContractFilters>({})

  // 詳情 Drawer 狀態
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedContract, setSelectedContract] = useState<ContractRecord | null>(null)

  // 新增 Modal 狀態
  const [addOpen, setAddOpen] = useState(false)
  const [addLoading, setAddLoading] = useState(false)
  const [vendorOptions, setVendorOptions] = useState<VendorListResponse[]>([])
  const [userOptions, setUserOptions] = useState<UserOptionItem[]>([])
  const [addForm] = Form.useForm()

  // F4 — 基礎參考資料下拉（新增 Modal 用）
  const [companyOptions, setCompanyOptions] = useState<CompanyOption[]>([])
  const [addSigningDeptOpts, setAddSigningDeptOpts] = useState<DepartmentOption[]>([])
  const [addBudgetDeptOpts, setAddBudgetDeptOpts] = useState<DepartmentOption[]>([])
  const [pricingSpecOptions, setPricingSpecOptions] = useState<PricingSpecOption[]>([])

  // 預算科目聯動下拉
  // 預算科目聯動下拉（options 端點已過濾 is_enabled=true）
  const [budgetCatOptions, setBudgetCatOptions] = useState<BudgetCategoryListResponse[]>([])
  const [selectedBudgetYear, setSelectedBudgetYear] = useState<number>(new Date().getFullYear())
  const [selectedL1, setSelectedL1] = useState<string | undefined>()

  // 搜尋欄位
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [riskLevelFilter, setRiskLevelFilter] = useState<string | undefined>()

  // J4 — 批次操作
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])
  const [batchManagerModal, setBatchManagerModal] = useState(false)
  const [batchNewManager, setBatchNewManager] = useState('')
  const [batchLoading, setBatchLoading] = useState(false)

  // J5 — 個人化篩選（記憶 localStorage）
  const [myContractsOnly, setMyContractsOnly] = useState<boolean>(() => {
    try { return localStorage.getItem('contract_my_only') === 'true' } catch { return false }
  })

  // ── 載入合約清單 ──────────────────────────────────────────────────────────
  const loadContracts = useCallback(async (page: number, size: number, f: ContractFilters) => {
    setLoading(true)
    try {
      const result = await fetchContracts({ ...f, page, size })
      setContracts(result.items)
      setPagination({ page: result.page, size: result.size, total: result.total })
    } catch (err: any) {
      message.error(err?.message || '載入合約失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  // ── 載入統計資訊 ──────────────────────────────────────────────────────────
  const loadStats = useCallback(async () => {
    try {
      const result = await fetchContractStats()
      setStats(result)
    } catch (err) {
      console.error('載入統計失敗', err)
    }
  }, [])

  // ── 初始化 ────────────────────────────────────────────────────────────────
  useEffect(() => {
    loadStats()
    // 預先載入使用者清單供 J4 批次改管理人用
    usersApi.options().then(res => setUserOptions(Array.isArray(res.data) ? res.data : [])).catch(() => {})
  }, [loadStats])

  // ── 搜尋和篩選（含 J5 個人化）──────────────────────────────────────────────
  useEffect(() => {
    const newFilters: ContractFilters = {}
    if (searchText) newFilters.search = searchText
    if (statusFilter) newFilters.status = statusFilter
    if (riskLevelFilter) newFilters.risk_level = riskLevelFilter
    // J5：若開啟「只看我的合約」，從 localStorage 取當前使用者 username
    if (myContractsOnly) {
      try {
        const authRaw = localStorage.getItem('auth-storage')
        if (authRaw) {
          const auth = JSON.parse(authRaw)
          const username = auth?.state?.user?.username || auth?.state?.username
          if (username) newFilters.manager = username
        }
      } catch { /* 靜默處理 */ }
    }
    setFilters(newFilters)
    loadContracts(1, pagination.size, newFilters)
  }, [searchText, statusFilter, riskLevelFilter, myContractsOnly, pagination.size, loadContracts])

  // ── 開啟新增 Modal ────────────────────────────────────────────────────────
  const openAddModal = async () => {
    addForm.resetFields()
    const curYear = dayjs().year()
    addForm.setFieldsValue({
      budget_year: curYear,
      currency: 'TWD',
      risk_level: '中',
      contract_status: '草稿',
    })
    setSelectedBudgetYear(curYear)
    setSelectedL1(undefined)
    setAddOpen(true)
    try {
      const [vendors, cats, usersRes, companies, specs] = await Promise.all([
        fetchVendorOptions(),
        fetchBudgetCategoryOptions(),
        usersApi.options(),
        companiesApi.options(),
        pricingSpecsApi.options(),
      ])
      setVendorOptions(Array.isArray(vendors) ? vendors : [])
      setBudgetCatOptions(Array.isArray(cats) ? cats : [])
      setUserOptions(Array.isArray(usersRes.data) ? usersRes.data : [])
      setCompanyOptions(Array.isArray(companies.data) ? companies.data : [])
      setPricingSpecOptions(Array.isArray(specs.data) ? specs.data : [])
      // 部門清單等選公司後才載入
      setAddSigningDeptOpts([])
      setAddBudgetDeptOpts([])
    } catch {
      setVendorOptions([])
      setBudgetCatOptions([])
    }
  }

  // ── 提交新增合約 ──────────────────────────────────────────────────────────
  const handleAddOk = async () => {
    try {
      const values = await addForm.validateFields()
      setAddLoading(true)
      const payload = {
        ...values,
        start_date: values.start_date?.format('YYYY-MM-DD'),
        end_date: values.end_date?.format('YYYY-MM-DD'),
        vendor_name: vendorOptions.find(v => v.vendor_id === values.vendor_id)?.vendor_name ?? '',
        using_depts: '',
        notification_days: 0,
        auto_renewal: false,
        needs_purchase_order: false,
        can_claim_without_po: false,
        needs_allocation: false,
        budget_source: '年度預算',
        budget_control_method: '提醒',
        require_acceptance: false,
        manager: '',
        reviewer: '',
        remarks: values.remarks ?? '',
      }
      await createContract(payload)
      message.success('合約已新增')
      setAddOpen(false)
      loadContracts(1, pagination.size, filters)
      loadStats()
    } catch (err: any) {
      if (err?.errorFields) return   // form validation — stay open, antd shows inline errors
      const detail = err?.response?.data?.detail
      const errMsg = typeof detail === 'string'
        ? detail
        : (detail?.message ?? err?.message ?? '新增失敗')
      message.error(errMsg)
    } finally {
      setAddLoading(false)
    }
  }

  // ── 刪除操作 ────────────────────────────────────────────────────────────
  const handleDelete = (contractId: string) => {
    Modal.confirm({
      title: '確定刪除此合約？',
      content: '此操作無法復原，請謹慎執行。',
      okText: '確定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteContract(contractId)
          message.success('合約已刪除')
          loadContracts(pagination.page, pagination.size, filters)
        } catch (err: any) {
          message.error(err?.message || '刪除失敗')
        }
      },
    })
  }

  // ── 分頁變更 ────────────────────────────────────────────────────────────
  const handleTableChange: TableProps<ContractRecord>['onChange'] = (pg) => {
    if (pg.current && pg.pageSize) {
      loadContracts(pg.current, pg.pageSize, filters)
    }
  }

  // ── 表格欄位定義 ──────────────────────────────────────────────────────────
  const columns: ColumnsType<ContractRecord> = [
    {
      title: '合約編號',
      dataIndex: 'contract_id',
      width: 140,
      fixed: 'left',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: '合約名稱',
      dataIndex: 'contract_name',
      width: 200,
      ellipsis: { showTitle: false },
      render: (text) => (
        <Tooltip title={text}>
          <span style={{ cursor: 'pointer', color: '#4BA8E8' }}>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '廠商',
      dataIndex: 'vendor_name',
      width: 150,
      ellipsis: { showTitle: false },
    },
    {
      title: '狀態',
      dataIndex: 'contract_status',
      width: 100,
      render: (status) => statusTag(status),
    },
    {
      title: '風險等級',
      dataIndex: 'risk_level',
      width: 90,
      render: (level) => (
        <Tag color={RISK_LEVEL_COLOR[level] ?? 'default'}>{level || '-'}</Tag>
      ),
    },
    {
      title: '開始日期',
      dataIndex: 'start_date',
      width: 120,
      render: (date) => fmtDate(date),
    },
    {
      title: '截止日期',
      dataIndex: 'end_date',
      width: 120,
      render: (date) => fmtDate(date),
    },
    {
      title: '合約金額',
      dataIndex: 'total_amount_tax_included',
      width: 140,
      align: 'right' as const,
      render: (amount) => <span style={{ fontWeight: 600 }}>{fmtMoney(amount)}</span>,
    },
    {
      title: '操作',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={(e) => {
              e.stopPropagation()
              setSelectedContract(record)
              setDrawerOpen(true)
            }}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={(e) => {
              e.stopPropagation()
              handleDelete(record.contract_id)
            }}
          >
            刪除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 麵包屑 */}
      <Breadcrumb style={{ marginBottom: '24px' }}>
        <Breadcrumb.Item><HomeOutlined /></Breadcrumb.Item>
        <Breadcrumb.Item>{NAV_GROUP.contract}</Breadcrumb.Item>
        <Breadcrumb.Item>{NAV_PAGE.contractList}</Breadcrumb.Item>
      </Breadcrumb>

      {/* 統計卡片 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col xs={12} sm={8} lg={4}>
            <Card>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1B3A5C' }}>{stats.total || 0}</div>
                <div style={{ fontSize: 14, color: '#666' }}>合約總數</div>
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52C41A' }}>{stats.by_status?.['生效中'] || 0}</div>
                <div style={{ fontSize: 14, color: '#666' }}>生效中</div>
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={8} lg={4}>
            <Card>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#FAAD14' }}>{stats.by_status?.['即將到期'] || 0}</div>
                <div style={{ fontSize: 14, color: '#666' }}>即將到期</div>
              </div>
            </Card>
          </Col>
        </Row>
      )}

      {/* 搜尋和篩選 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={16}>
          <Col xs={24} sm={12} lg={8}>
            <Input
              placeholder="搜尋合約名稱、編號、廠商、管理人、部門、備註…"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
          </Col>
          <Col xs={12} sm={12} lg={4}>
            <Select
              placeholder="狀態"
              allowClear
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: '100%' }}
            >
              <Option value="草稿">草稿</Option>
              <Option value="審核中">審核中</Option>
              <Option value="生效中">生效中</Option>
              <Option value="即將到期">即將到期</Option>
              <Option value="已終止">已終止</Option>
            </Select>
          </Col>
          <Col xs={12} sm={12} lg={4}>
            <Select
              placeholder="風險等級"
              allowClear
              value={riskLevelFilter}
              onChange={setRiskLevelFilter}
              style={{ width: '100%' }}
            >
              <Option value="低">低</Option>
              <Option value="中">中</Option>
              <Option value="高">高</Option>
              <Option value="關鍵">關鍵</Option>
            </Select>
          </Col>
          <Col xs={24} sm={12} lg={8}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }} wrap>
              {/* J5 — 只看我的合約 Toggle */}
              <Button
                type={myContractsOnly ? 'primary' : 'default'}
                onClick={() => {
                  const next = !myContractsOnly
                  setMyContractsOnly(next)
                  try { localStorage.setItem('contract_my_only', String(next)) } catch {}
                }}
                style={myContractsOnly ? { background: '#1B3A5C', borderColor: '#1B3A5C' } : {}}
              >
                {myContractsOnly ? '✓ 只看我的合約' : '只看我的合約'}
              </Button>
              <Button icon={<ReloadOutlined />} onClick={() => loadContracts(1, pagination.size, filters)}>
                重新整理
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => exportContractsExcel({
                  search: filters.search,
                  status: filters.status,
                  risk_level: filters.risk_level,
                })}
              >
                匯出 Excel
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openAddModal}>
                新增合約
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* J4 — 批次操作浮動工具列 */}
      {selectedRowKeys.length > 0 && (
        <div style={{
          position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)',
          background: '#1B3A5C', color: '#fff', borderRadius: 8,
          padding: '10px 20px', zIndex: 1000, boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <span style={{ fontWeight: 600 }}>已選 {selectedRowKeys.length} 份合約</span>
          <Button size="small" ghost onClick={() => setBatchManagerModal(true)}>批次改管理人</Button>
          <Button size="small" ghost loading={batchLoading} onClick={async () => {
            setBatchLoading(true)
            try {
              const res = await batchSubmit(selectedRowKeys)
              message.success(`批次送審：${res.submitted} 份成功`)
              if (res.failed.length) message.warning(`${res.failed.length} 份失敗：${res.failed.map(f => f.reason).join('；')}`)
              setSelectedRowKeys([])
              loadContracts(pagination.page, pagination.size, filters)
            } catch { message.error('批次送審失敗') }
            finally { setBatchLoading(false) }
          }}>批次送審</Button>
          <Button size="small" ghost onClick={() => setSelectedRowKeys([])}>取消選取</Button>
        </div>
      )}

      {/* 批次改管理人 Modal */}
      <Modal
        title={`批次更新管理人（${selectedRowKeys.length} 份合約）`}
        open={batchManagerModal}
        onOk={async () => {
          if (!batchNewManager.trim()) { message.warning('請輸入管理人帳號'); return }
          setBatchLoading(true)
          try {
            const res = await batchUpdateManager(selectedRowKeys, batchNewManager.trim())
            message.success(`已更新 ${res.updated} 份合約的管理人`)
            setBatchManagerModal(false)
            setBatchNewManager('')
            setSelectedRowKeys([])
            loadContracts(pagination.page, pagination.size, filters)
          } catch { message.error('批次更新失敗') }
          finally { setBatchLoading(false) }
        }}
        onCancel={() => { setBatchManagerModal(false); setBatchNewManager('') }}
        confirmLoading={batchLoading}
        okText="確認更新"
        cancelText="取消"
        destroyOnClose
      >
        <Form layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item label="新管理人帳號" required>
            <Select
              showSearch
              placeholder="搜尋使用者帳號"
              value={batchNewManager || undefined}
              onChange={setBatchNewManager}
              filterOption={(input, opt) =>
                String(opt?.label ?? '').toLowerCase().includes(input.toLowerCase())}
              options={userOptions.map(u => ({ value: u.value, label: u.label }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 表格 */}
      <Card>
        <Table<ContractRecord>
          columns={columns}
          dataSource={contracts}
          loading={loading}
          rowSelection={{
            type: 'checkbox',
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as string[]),
            getCheckboxProps: () => ({}),
          }}
          pagination={{
            current: pagination.page,
            pageSize: pagination.size,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 筆`,
          }}
          onChange={handleTableChange}
          rowKey="contract_id"
          onRow={(record) => ({
            onClick: () => {
              setSelectedContract(record)
              setDrawerOpen(true)
            },
            style: { cursor: 'pointer' },
          })}
        />
      </Card>

      {/* 詳情 Drawer */}
      {selectedContract && (
        <ContractDetailDrawer
          contract={selectedContract}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          onUpdate={(updated) => {
            setContracts(prev =>
              prev.map(c => c.contract_id === updated.contract_id ? updated : c)
            )
            setSelectedContract(updated)
          }}
        />
      )}

      {/* 新增合約 Modal */}
      <Modal
        title="新增合約"
        open={addOpen}
        onOk={handleAddOk}
        onCancel={() => setAddOpen(false)}
        confirmLoading={addLoading}
        okText="確認新增"
        cancelText="取消"
        width={720}
        destroyOnClose
      >
        <Form form={addForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="contract_id"
                label="合約編號"
                rules={[
                  { required: true, message: '請輸入合約編號' },
                  { pattern: /^CON-\d{4}-\d{4}$/, message: '格式：CON-YYYY-NNNN，例如 CON-2026-0001' },
                ]}
              >
                <Input placeholder="CON-2026-0001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="contract_name"
                label="合約名稱"
                rules={[{ required: true, message: '請輸入合約名稱' }]}
              >
                <Input placeholder="請輸入合約名稱" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="contract_type"
                label="合約類型"
                rules={[{ required: true, message: '請選擇合約類型' }]}
              >
                <Select placeholder="請選擇">
                  {['服務合約', '採購合約', '維護合約', '租賃合約', '工程合約', '顧問合約', '其他'].map(t => (
                    <Option key={t} value={t}>{t}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="responsible_dept"
                label="權責部門"
                rules={[{ required: true, message: '請輸入權責部門' }]}
              >
                <Input placeholder="請輸入部門名稱" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="vendor_id"
                label="廠商"
                rules={[{ required: true, message: '請選擇廠商' }]}
              >
                <Select
                  placeholder="請選擇廠商"
                  showSearch
                  optionFilterProp="label"
                  options={vendorOptions.map(v => ({
                    value: v.vendor_id,
                    label: `${v.vendor_name}（${v.vendor_id}）`,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="risk_level" label="風險等級" rules={[{ required: true }]}>
                <Select>
                  {['低', '中', '高', '關鍵'].map(l => (
                    <Option key={l} value={l}>{l}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="start_date"
                label="合約起日"
                rules={[{ required: true, message: '請選擇起日' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="end_date"
                label="合約迄日"
                rules={[{ required: true, message: '請選擇迄日' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="total_amount_tax_included"
                label="合約總額（含稅）"
                rules={[{ required: true, message: '請輸入金額' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  step={1000}
                  formatter={(v) => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(v) => v?.replace(/\$\s?|(,*)/g, '') as any}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="pricing_method"
                label="計價方式"
                rules={[{ required: true, message: '請選擇計價方式' }]}
              >
                <Select placeholder="請選擇">
                  {['固定費用', '月費', '按次收費', '依量計費', '里程碑付款', '其他'].map(m => (
                    <Option key={m} value={m}>{m}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="budget_year" label="預算年度" rules={[{ required: true }]}>
                <InputNumber
                  style={{ width: '100%' }} min={2000} max={2100}
                  onChange={(v) => {
                    setSelectedBudgetYear(v as number)
                    setSelectedL1(undefined)
                    addForm.setFieldsValue({ budget_category_l1: undefined, budget_category_l2: undefined })
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="budget_category_l1"
                label="預算大項"
                rules={[{ required: true, message: '請選擇預算大項' }]}
              >
                <Select
                  placeholder="請選擇"
                  showSearch
                  onChange={(v: string) => {
                    setSelectedL1(v)
                    addForm.setFieldsValue({ budget_category_l2: undefined })
                  }}
                  options={[
                    ...new Set(
                      budgetCatOptions
                        .filter(c => c.budget_year === selectedBudgetYear)
                        .map(c => c.category_l1)
                    )
                  ].map(l1 => ({ value: l1, label: l1 }))}
                  notFoundContent="此年度無可用科目"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="budget_category_l2"
                label="預算細項"
                rules={[{ required: true, message: '請選擇預算細項' }]}
              >
                <Select
                  placeholder="請選擇"
                  showSearch
                  disabled={!selectedL1}
                  options={budgetCatOptions
                    .filter(c =>
                      c.budget_year === selectedBudgetYear &&
                      c.category_l1 === selectedL1
                    )
                    .map(c => ({ value: c.category_l2, label: c.category_l2 }))}
                  notFoundContent="無可用細項"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="accounting_code"
                label="會計科目"
                rules={[{ required: true, message: '請輸入會計科目' }]}
              >
                <Input placeholder="例：6215" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="currency" label="幣別">
                <Select>
                  {['TWD', 'USD', 'EUR', 'JPY', 'CNY'].map(c => (
                    <Option key={c} value={c}>{c}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" orientationMargin={0} style={{ fontSize: 13 }}>公司與部門</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="signing_company" label="簽約公司">
                <Select
                  showSearch allowClear placeholder="請選擇" optionFilterProp="label"
                  options={companyOptions}
                  onChange={(val: string | undefined) => {
                    addForm.setFieldsValue({ signing_dept: undefined })
                    setAddSigningDeptOpts([])
                    if (!val) return
                    const co = companyOptions.find(c => c.value === val)
                    if (co) {
                      departmentsApi.options(co.id)
                        .then(res => setAddSigningDeptOpts(Array.isArray(res.data) ? res.data : []))
                        .catch(() => {})
                    }
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="signing_dept" label="簽約權責部門">
                <Select showSearch allowClear placeholder="先選簽約公司" optionFilterProp="label"
                  options={addSigningDeptOpts}
                  disabled={addSigningDeptOpts.length === 0 && !addForm.getFieldValue('signing_company')} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="budget_company" label="預算使用公司">
                <Select
                  showSearch allowClear placeholder="請選擇" optionFilterProp="label"
                  options={companyOptions}
                  onChange={(val: string | undefined) => {
                    addForm.setFieldsValue({ budget_dept: undefined })
                    setAddBudgetDeptOpts([])
                    if (!val) return
                    const co = companyOptions.find(c => c.value === val)
                    if (co) {
                      departmentsApi.options(co.id)
                        .then(res => setAddBudgetDeptOpts(Array.isArray(res.data) ? res.data : []))
                        .catch(() => {})
                    }
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="budget_dept" label="預算使用部門">
                <Select showSearch allowClear placeholder="先選預算使用公司" optionFilterProp="label"
                  options={addBudgetDeptOpts}
                  disabled={addBudgetDeptOpts.length === 0 && !addForm.getFieldValue('budget_company')} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="pricing_spec" label="計價規格">
                <Select showSearch allowClear placeholder="請選擇" optionFilterProp="label"
                  options={pricingSpecOptions} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="remarks" label="備註">
            <Input.TextArea rows={2} placeholder="選填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// ═════════════════════════════════════════════════════════════════════════════
// 詳情 Drawer 元件（含 Drawer 內直接編輯）
// ═════════════════════════════════════════════════════════════════════════════

interface ContractDetailDrawerProps {
  contract: ContractRecord
  open: boolean
  onClose: () => void
  onUpdate?: (updated: ContractRecord) => void
}

function ContractDetailDrawer({ contract, open, onClose, onUpdate }: ContractDetailDrawerProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [editForm] = Form.useForm()

  // 人員下拉選單（Drawer 內自行管理）
  const [userOptions, setUserOptions] = useState<UserOptionItem[]>([])
  // F4 — 費用分攤
  const [costAllocations, setCostAllocations] = useState<CostAllocationRecord[]>([])
  const [editAllocations, setEditAllocations] = useState<CostAllocationItem[]>([])
  // F4 — 基礎下拉
  const [drawerCompanyOpts, setDrawerCompanyOpts] = useState<CompanyOption[]>([])
  const [drawerSigningDeptOpts, setDrawerSigningDeptOpts] = useState<DepartmentOption[]>([])
  const [drawerBudgetDeptOpts, setDrawerBudgetDeptOpts] = useState<DepartmentOption[]>([])
  const [drawerSpecOpts, setDrawerSpecOpts] = useState<PricingSpecOption[]>([])

  // 審核操作狀態
  const [approvalLoading, setApprovalLoading] = useState(false)
  const [approvalModalOpen, setApprovalModalOpen] = useState(false)
  const [approvalAction, setApprovalAction] = useState<'approve' | 'reject' | null>(null)
  const [approvalComment, setApprovalComment] = useState('')

  const ragicUrl = contract.ragic_url
  const identifier = contract.contract_id

  // F4 — Drawer 開啟時載入費用分攤 + 公司下拉 + 現有部門清單
  useEffect(() => {
    if (!open) return
    fetchCostAllocations(contract.contract_id)
      .then(rows => setCostAllocations(rows))
      .catch(() => {})

    // 載入公司 + 計價規格下拉
    Promise.all([
      companiesApi.options(),
      pricingSpecsApi.options(),
    ]).then(([c, s]) => {
      const cos = Array.isArray(c.data) ? c.data : []
      setDrawerCompanyOpts(cos)
      setDrawerSpecOpts(Array.isArray(s.data) ? s.data : [])

      // 依現有合約的公司值初始化部門清單
      const loadDepts = async (companyName: string | undefined, setter: (v: DepartmentOption[]) => void) => {
        if (!companyName) return
        const co = cos.find(x => x.value === companyName)
        if (!co) return
        try {
          const res = await departmentsApi.options(co.id)
          setter(Array.isArray(res.data) ? res.data : [])
        } catch {}
      }
      loadDepts(contract.signing_company, setDrawerSigningDeptOpts)
      loadDepts(contract.budget_company,  setDrawerBudgetDeptOpts)
    }).catch(() => {})
  }, [open, contract.contract_id])

  // 進入編輯模式時初始化 form 值（同時確保 userOptions 已載入）
  const enterEdit = () => {
    if (userOptions.length === 0) {
      usersApi.options().then(res => setUserOptions(Array.isArray(res.data) ? res.data : [])).catch(() => {})
    }
    setEditAllocations(costAllocations.map(r => ({
      company_name:    r.company_name,
      allocation_type: r.allocation_type,
      value:           r.value,
    })))
    editForm.setFieldsValue({
      contract_name:             contract.contract_name,
      contract_type:             contract.contract_type,
      contract_status:           contract.contract_status,
      risk_level:                contract.risk_level,
      start_date:                contract.start_date ? dayjs(contract.start_date) : null,
      end_date:                  contract.end_date   ? dayjs(contract.end_date)   : null,
      notification_days:         contract.notification_days,
      auto_renewal:              contract.auto_renewal,
      total_amount_tax_included: contract.total_amount_tax_included,
      monthly_fixed_amount:      contract.monthly_fixed_amount ?? undefined,
      manager:                   contract.manager,
      reviewer:                  contract.reviewer,
      signing_company:           contract.signing_company ?? undefined,
      signing_dept:              contract.signing_dept ?? undefined,
      budget_company:            contract.budget_company ?? undefined,
      budget_dept:               contract.budget_dept ?? undefined,
      pricing_spec:              contract.pricing_spec ?? undefined,
      remarks:                   contract.remarks,
    })
    setIsEditing(true)
  }

  const cancelEdit = () => {
    setIsEditing(false)
    editForm.resetFields()
  }

  const handleSave = async () => {
    try {
      const values = await editForm.validateFields()

      // ── 費用分攤驗證（存檔前） ─────────────────────────────────────────
      if (editAllocations.length > 0) {
        const contractAmt = values.total_amount_tax_included ?? contract.total_amount_tax_included
        const pricingMeth = values.pricing_method ?? contract.pricing_method
        const allocResult = validateAllocations(editAllocations, contractAmt, pricingMeth)
        // 混用類型：詢問使用者確認
        if (allocResult.warnings.length > 0) {
          const confirmed = await new Promise<boolean>(resolve =>
            Modal.confirm({
              title: '費用分攤：類型混用提醒',
              content: allocResult.warnings[0],
              okText: '我了解，繼續存檔',
              cancelText: '返回修改',
              onOk:    () => resolve(true),
              onCancel: () => resolve(false),
            })
          )
          if (!confirmed) return
        }
        // 加總不符：阻擋存檔
        if (allocResult.errors.length > 0) {
          allocResult.errors.forEach(e => message.error(e, 6))
          return
        }
      }

      setSaveLoading(true)
      const payload: ContractUpdate = {
        ...values,
        start_date: values.start_date ? values.start_date.format('YYYY-MM-DD') : undefined,
        end_date:   values.end_date   ? values.end_date.format('YYYY-MM-DD')   : undefined,
      }
      const result = await updateContract(contract.contract_id, payload)
      // 費用分攤整批儲存
      const saved = await saveCostAllocations(contract.contract_id, editAllocations)
      setCostAllocations(saved)
      message.success('合約已更新')
      setIsEditing(false)
      onUpdate?.(result)
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.response?.data?.detail ?? err?.message ?? '更新失敗')
    } finally {
      setSaveLoading(false)
    }
  }

  // ── 送審 ──────────────────────────────────────────────────────────────
  const handleSubmitForReview = async () => {
    setApprovalLoading(true)
    try {
      const result = await submitContractForReview(contract.contract_id)
      message.success('已送審，目前狀態：審核中')
      onUpdate?.(result)
    } catch (err: any) {
      message.error(err?.response?.data?.detail?.message ?? err?.response?.data?.detail ?? '送審失敗')
    } finally {
      setApprovalLoading(false)
    }
  }

  // ── 核准 / 拒絕確認 ────────────────────────────────────────────────────
  const handleApprovalConfirm = async () => {
    if (!approvalAction) return
    setApprovalLoading(true)
    try {
      const result = approvalAction === 'approve'
        ? await approveContract(contract.contract_id, approvalComment || undefined)
        : await rejectContract(contract.contract_id, approvalComment || undefined)
      message.success(approvalAction === 'approve' ? '合約已核准，狀態：生效中' : '合約已拒絕，狀態退回草稿')
      setApprovalModalOpen(false)
      setApprovalComment('')
      onUpdate?.(result)
    } catch (err: any) {
      message.error(err?.response?.data?.detail?.message ?? err?.response?.data?.detail ?? '操作失敗')
    } finally {
      setApprovalLoading(false)
    }
  }

  return (
    <>
    <Drawer
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Tag color="blue">合約</Tag>
          <span style={{ fontWeight: 600 }}>合約編號：{identifier}</span>
          {ragicUrl && !isEditing && (
            <a href={ragicUrl} target="_blank" rel="noopener noreferrer"
               onClick={(e) => e.stopPropagation()}
               style={{ marginLeft: 4, color: '#4BA8E8', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <LinkOutlined style={{ fontSize: 13 }} /> 在 Ragic 查看
            </a>
          )}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
            {isEditing ? (
              <>
                <Button size="small" icon={<CloseOutlined />} onClick={cancelEdit}>取消</Button>
                <Button size="small" type="primary" icon={<SaveOutlined />}
                  loading={saveLoading} onClick={handleSave}>儲存</Button>
              </>
            ) : (
              <>
                {/* 草稿狀態：顯示送審按鈕 */}
                {contract.contract_status === '草稿' && (
                  <Button
                    size="small"
                    type="default"
                    loading={approvalLoading}
                    onClick={handleSubmitForReview}
                    style={{ color: '#1677ff', borderColor: '#1677ff' }}
                  >
                    送審
                  </Button>
                )}
                {/* 審核中：顯示核准 / 拒絕 */}
                {contract.contract_status === '審核中' && (
                  <>
                    <Button
                      size="small"
                      type="primary"
                      style={{ background: '#52c41a', borderColor: '#52c41a' }}
                      loading={approvalLoading}
                      onClick={() => { setApprovalAction('approve'); setApprovalComment(''); setApprovalModalOpen(true) }}
                    >
                      核准
                    </Button>
                    <Button
                      size="small"
                      danger
                      loading={approvalLoading}
                      onClick={() => { setApprovalAction('reject'); setApprovalComment(''); setApprovalModalOpen(true) }}
                    >
                      拒絕
                    </Button>
                  </>
                )}
                <Button size="small" icon={<EditOutlined />} onClick={enterEdit}>編輯</Button>
              </>
            )}
            {/* 放大 / 縮小切換 */}
            <Tooltip title={isFullscreen ? '縮小' : '全螢幕'}>
              <Button
                size="small"
                icon={isFullscreen ? <CompressOutlined /> : <ExpandOutlined />}
                onClick={() => setIsFullscreen(f => !f)}
                style={{ color: '#4BA8E8', borderColor: '#4BA8E8' }}
              />
            </Tooltip>
          </div>
        </div>
      }
      placement="right"
      width={isFullscreen ? '100vw' : 640}
      onClose={() => { cancelEdit(); setIsFullscreen(false); onClose() }}
      open={open}
      bodyStyle={{ paddingBottom: 80 }}
      styles={{ header: { paddingRight: 16 } }}
    >
      {isEditing ? (
        /* ── 編輯模式 ─────────────────────────────────────────────────────── */
        <Spin spinning={saveLoading}>
          <Form form={editForm} layout="vertical">
            <Divider orientation="left" orientationMargin={0}>基本資訊</Divider>
            <Form.Item name="contract_name" label="合約名稱" rules={[{ required: true, message: '必填' }]}>
              <Input />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="contract_type" label="合約類型">
                  <Select allowClear>
                    {['服務合約','採購合約','工程合約','租賃合約','顧問合約','其他'].map(t => (
                      <Option key={t} value={t}>{t}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="contract_status" label="狀態">
                  <Select>
                    {['草稿','審核中','生效中','即將到期','已終止'].map(s => (
                      <Option key={s} value={s}>{s}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="risk_level" label="風險等級">
                  <Select>
                    {['低','中','高','關鍵'].map(r => (
                      <Option key={r} value={r}>{r}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="auto_renewal" label="自動續約" valuePropName="checked">
                  <Switch checkedChildren="是" unCheckedChildren="否" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="manager" label="管理人">
                  <Select
                    showSearch
                    allowClear
                    placeholder="請選擇管理人"
                    optionFilterProp="label"
                    options={userOptions}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="reviewer" label="審核人">
                  <Select
                    showSearch
                    allowClear
                    placeholder="請選擇審核人"
                    optionFilterProp="label"
                    options={userOptions}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Divider orientation="left" orientationMargin={0}>期限</Divider>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="start_date" label="開始日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="end_date" label="截止日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="notification_days" label="提前通知天數">
              <InputNumber style={{ width: '100%' }} min={0} addonAfter="天" />
            </Form.Item>

            <Divider orientation="left" orientationMargin={0}>金額</Divider>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="total_amount_tax_included" label="合約總額（含稅）"
                  rules={[{ required: true, message: '必填' }]}>
                  <InputNumber style={{ width: '100%' }} min={0} step={10000}
                    formatter={v => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={v => (v?.replace(/\$\s?|(,*)/g, '') ?? '') as any}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="monthly_fixed_amount" label="月固定金額">
                  <InputNumber style={{ width: '100%' }} min={0} step={1000}
                    formatter={v => v ? `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',') : ''}
                    parser={v => (v?.replace(/\$\s?|(,*)/g, '') ?? '') as any}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Divider orientation="left" orientationMargin={0}>公司與部門</Divider>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="signing_company" label="簽約公司">
                  <Select
                    showSearch allowClear placeholder="請選擇" optionFilterProp="label"
                    options={drawerCompanyOpts}
                    onChange={(val: string | undefined) => {
                      editForm.setFieldsValue({ signing_dept: undefined })
                      setDrawerSigningDeptOpts([])
                      if (!val) return
                      const co = drawerCompanyOpts.find(c => c.value === val)
                      if (co) {
                        departmentsApi.options(co.id)
                          .then(res => setDrawerSigningDeptOpts(Array.isArray(res.data) ? res.data : []))
                          .catch(() => {})
                      }
                    }}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="signing_dept" label="簽約權責部門">
                  <Select showSearch allowClear placeholder="先選簽約公司" optionFilterProp="label"
                    options={drawerSigningDeptOpts} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="budget_company" label="預算使用公司">
                  <Select
                    showSearch allowClear placeholder="請選擇" optionFilterProp="label"
                    options={drawerCompanyOpts}
                    onChange={(val: string | undefined) => {
                      editForm.setFieldsValue({ budget_dept: undefined })
                      setDrawerBudgetDeptOpts([])
                      if (!val) return
                      const co = drawerCompanyOpts.find(c => c.value === val)
                      if (co) {
                        departmentsApi.options(co.id)
                          .then(res => setDrawerBudgetDeptOpts(Array.isArray(res.data) ? res.data : []))
                          .catch(() => {})
                      }
                    }}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="budget_dept" label="預算使用部門">
                  <Select showSearch allowClear placeholder="先選預算使用公司" optionFilterProp="label"
                    options={drawerBudgetDeptOpts} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="pricing_spec" label="計價規格">
                  <Select showSearch allowClear placeholder="請選擇" optionFilterProp="label"
                    options={drawerSpecOpts} />
                </Form.Item>
              </Col>
            </Row>

            <Divider orientation="left" orientationMargin={0}>費用分攤</Divider>
            <CostAllocationEditor
              value={editAllocations}
              onChange={setEditAllocations}
              companyOptions={drawerCompanyOpts}
              contractAmount={contract.total_amount_tax_included}
              pricingMethod={contract.pricing_method}
            />

            <Divider orientation="left" orientationMargin={0}>備註</Divider>
            <Form.Item name="remarks" label="備註">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        </Spin>
      ) : (
        /* ── 查看模式 ─────────────────────────────────────────────────────── */
        <Tabs
          defaultActiveKey="info"
          items={[
            {
              key: 'info',
              label: <span>基本資訊</span>,
              children: (
                <>
          {/* I4 財務摘要卡 */}
          <CostSummaryCard contractId={contract.contract_id} open={open} />
          <Title level={5}>基本資訊</Title>
          <Descriptions column={2} bordered size="small" style={{ marginBottom: '24px' }}>
            <Descriptions.Item label="合約編號"><strong>{contract.contract_id}</strong></Descriptions.Item>
            <Descriptions.Item label="合約名稱">{contract.contract_name}</Descriptions.Item>
            <Descriptions.Item label="狀態">{statusTag(contract.contract_status)}</Descriptions.Item>
            <Descriptions.Item label="風險等級">
              <Tag color={RISK_LEVEL_COLOR[contract.risk_level] ?? 'default'}>{contract.risk_level || '-'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="廠商">{contract.vendor_name}</Descriptions.Item>
            <Descriptions.Item label="合約類型">{contract.contract_type || '-'}</Descriptions.Item>
            <Descriptions.Item label="管理人">{contract.manager || '-'}</Descriptions.Item>
            <Descriptions.Item label="審核人">{contract.reviewer || '-'}</Descriptions.Item>
            <Descriptions.Item label="簽約公司">{contract.signing_company || '-'}</Descriptions.Item>
            <Descriptions.Item label="簽約權責部門">{contract.signing_dept || '-'}</Descriptions.Item>
            <Descriptions.Item label="預算使用公司">{contract.budget_company || '-'}</Descriptions.Item>
            <Descriptions.Item label="預算使用部門">{contract.budget_dept || '-'}</Descriptions.Item>
            <Descriptions.Item label="計價規格">{contract.pricing_spec || '-'}</Descriptions.Item>
          </Descriptions>

          {costAllocations.length > 0 && (
            <>
              <Title level={5}>費用分攤</Title>
              <Descriptions column={1} bordered size="small" style={{ marginBottom: '24px' }}>
                {costAllocations.map((r, i) => (
                  <Descriptions.Item key={r.id} label={`分攤 ${i + 1}`}>
                    {r.company_name}
                    {r.allocation_type === 'percentage'
                      ? <Tag color="blue">{r.value}%</Tag>
                      : <Tag color="purple">${Number(r.value).toLocaleString('zh-TW')}</Tag>
                    }
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </>
          )}

          <Title level={5}>期限</Title>
          <Descriptions column={2} bordered size="small" style={{ marginBottom: '24px' }}>
            <Descriptions.Item label="開始日期">{fmtDate(contract.start_date)}</Descriptions.Item>
            <Descriptions.Item label="截止日期">{fmtDate(contract.end_date)}</Descriptions.Item>
            <Descriptions.Item label="提前通知天數">{contract.notification_days || '-'} 天</Descriptions.Item>
            <Descriptions.Item label="自動續約">{contract.auto_renewal ? '是' : '否'}</Descriptions.Item>
          </Descriptions>

          <Title level={5}>金額與定價</Title>
          <Descriptions column={2} bordered size="small" style={{ marginBottom: '24px' }}>
            <Descriptions.Item label="合約總額（含稅）">
              <strong style={{ color: '#722ED1', fontSize: 14 }}>
                {contract.currency} {fmtMoney(contract.total_amount_tax_included)}
              </strong>
            </Descriptions.Item>
            <Descriptions.Item label="月固定金額">
              {contract.monthly_fixed_amount ? fmtMoney(contract.monthly_fixed_amount) : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="定價方式">{contract.pricing_method || '-'}</Descriptions.Item>
            <Descriptions.Item label="幣別">{contract.currency || '-'}</Descriptions.Item>
          </Descriptions>

          <Title level={5}>預算與會計</Title>
          <Descriptions column={2} bordered size="small" style={{ marginBottom: '24px' }}>
            <Descriptions.Item label="預算年度">{contract.budget_year}</Descriptions.Item>
            <Descriptions.Item label="預算科目 L1">{contract.budget_category_l1 || '-'}</Descriptions.Item>
            <Descriptions.Item label="預算科目 L2">{contract.budget_category_l2 || '-'}</Descriptions.Item>
            <Descriptions.Item label="會計科目">{contract.accounting_code || '-'}</Descriptions.Item>
            <Descriptions.Item label="預算來源">{contract.budget_source || '-'}</Descriptions.Item>
            <Descriptions.Item label="預算控制方式">{contract.budget_control_method || '-'}</Descriptions.Item>
          </Descriptions>

          {contract.remarks && (
            <>
              <Title level={5}>備註</Title>
              <div style={{ padding: '12px', backgroundColor: '#fafafa', borderRadius: '4px', marginBottom: '24px' }}>
                {contract.remarks}
              </div>
            </>
          )}

          {contract.detail && Object.keys(contract.detail).length > 0 && (
            <>
              <Title level={5}>詳細資訊</Title>
              <Descriptions column={1} bordered size="small">
                {Object.entries(contract.detail).map(([key, value]) => (
                  <Descriptions.Item key={key} label={key}>{String(value) || '—'}</Descriptions.Item>
                ))}
              </Descriptions>
            </>
          )}
                </>
              ),
            },
            {
              key: 'items',
              label: <span><UnorderedListOutlined /> 合約項目</span>,
              children: <ContractItemsTab contractId={contract.contract_id} open={open} />,
            },
            {
              key: 'claims',
              label: <span><DollarOutlined /> 請款紀錄</span>,
              children: <ContractClaimsTab contractId={contract.contract_id} open={open} totalAmount={contract.total_amount_tax_included} />,
            },
            {
              key: 'renewals',
              label: <span><SyncOutlined /> 續約申請</span>,
              children: <ContractRenewalsTab contractId={contract.contract_id} open={open} />,
            },
            {
              key: 'attachments',
              label: <span><PaperClipOutlined /> 合約附件</span>,
              children: <ContractAttachmentsTab contractId={contract.contract_id} open={open} />,
            },
            {
              key: 'payment-schedules',
              label: <span><DollarOutlined /> 付款計劃</span>,
              children: <ContractPaymentScheduleTab contractId={contract.contract_id} open={open} />,
            },
            {
              key: 'change-logs',
              label: <span><ClockCircleOutlined /> 變更歷程</span>,
              children: <ContractChangeLogTab contractId={contract.contract_id} open={open} />,
            },
            {
              key: 'audit-logs',
              label: <span><AuditOutlined /> 稽核日誌</span>,
              children: <ContractAuditLogTab contractId={contract.contract_id} open={open} />,
            },
            {
              key: 'approval-stages',
              label: <span><SolutionOutlined /> 審核關卡</span>,
              children: <ContractApprovalStagesTab contractId={contract.contract_id} open={open} contractStatus={contract.contract_status} />,
            },
            {
              key: 'acceptances',
              label: <span><CheckSquareOutlined /> 驗收記錄</span>,
              children: <ContractAcceptancesTab contractId={contract.contract_id} open={open} />,
            },
            {
              key: 'deposits',
              label: <span><SafetyOutlined /> 保證金</span>,
              children: <ContractDepositsTab contractId={contract.contract_id} open={open} />,
            },
            {
              key: 'sla',
              label: <span><DashboardOutlined /> SLA 追蹤</span>,
              children: <ContractSlaTab contractId={contract.contract_id} open={open} />,
            },
          ]}
        />
      )}
    </Drawer>

    {/* 核准 / 拒絕確認 Modal */}
    <Modal
      title={approvalAction === 'approve' ? '核准合約' : '拒絕合約（退回草稿）'}
      open={approvalModalOpen}
      onOk={handleApprovalConfirm}
      onCancel={() => { setApprovalModalOpen(false); setApprovalComment('') }}
      confirmLoading={approvalLoading}
      okText={approvalAction === 'approve' ? '確認核准' : '確認拒絕'}
      okButtonProps={{ danger: approvalAction === 'reject' }}
      cancelText="取消"
      destroyOnClose
    >
      <Form layout="vertical">
        <Form.Item
          label={approvalAction === 'approve' ? '核准意見（選填）' : '拒絕原因（選填）'}
        >
          <Input.TextArea
            rows={3}
            value={approvalComment}
            onChange={(e) => setApprovalComment(e.target.value)}
            placeholder={approvalAction === 'approve' ? '如：符合採購規範，同意生效' : '如：合約條款需修正，請重新提交'}
          />
        </Form.Item>
      </Form>
    </Modal>
    </>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// 合約項目 Tab 元件
// ═════════════════════════════════════════════════════════════════════════════

const ITEM_CATEGORY_OPTIONS = ['月費', '年費', '一次性', '用量', '加購', '其他']

interface ContractItemsTabProps {
  contractId: string
  open: boolean
}

function ContractItemsTab({ contractId, open }: ContractItemsTabProps) {
  const [items, setItems] = useState<ContractItemRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [addLoading, setAddLoading] = useState(false)
  const [editRecord, setEditRecord] = useState<ContractItemRecord | null>(null)
  const [form] = Form.useForm()

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetchContractItems(contractId)
      setItems(res.items || [])
    } catch {
      message.error('載入合約項目失敗')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open && contractId) load()
  }, [open, contractId])

  const openAdd = () => {
    setEditRecord(null)
    form.resetFields()
    setAddOpen(true)
  }
  const openEdit = (record: ContractItemRecord) => {
    setEditRecord(record)
    form.setFieldsValue({
      item_name: record.item_name,
      item_category: record.item_category,
      unit_price_tax_excluded: record.unit_price_tax_excluded,
      quantity: record.quantity,
      unit: record.unit,
      tax_rate: record.tax_rate,
      amount_tax_excluded: record.amount_tax_excluded,
      amount_tax_included: record.amount_tax_included,
    })
    setAddOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setAddLoading(true)
      const payload: ContractItemCreate = {
        item_name: values.item_name,
        item_category: values.item_category ?? '',
        unit_price_tax_excluded: values.unit_price_tax_excluded,
        quantity: values.quantity,
        unit: values.unit,
        tax_rate: values.tax_rate ?? 5,
        amount_tax_excluded: values.amount_tax_excluded ?? 0,
        amount_tax_included: values.amount_tax_included ?? 0,
      }
      if (editRecord) {
        await updateContractItem(contractId, editRecord.id, payload)
        message.success('項目已更新')
      } else {
        await createContractItem(contractId, payload)
        message.success('項目已新增')
      }
      setAddOpen(false)
      load()
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.response?.data?.detail ?? '操作失敗')
    } finally {
      setAddLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteContractItem(contractId, id)
      message.success('已刪除')
      load()
    } catch {
      message.error('刪除失敗')
    }
  }

  const fmtAmt = (v?: number) => (v == null ? '-' : `$${Number(v).toLocaleString('zh-TW')}`)

  const columns = [
    { title: '項次', dataIndex: 'item_seq', key: 'seq', width: 55, align: 'center' as const },
    { title: '項目名稱', dataIndex: 'item_name', key: 'name', ellipsis: true },
    { title: '類別', dataIndex: 'item_category', key: 'cat', width: 80 },
    {
      title: '數量', dataIndex: 'quantity', key: 'qty', width: 70, align: 'right' as const,
      render: (v?: number, r?: any) => v != null ? `${v} ${r?.unit ?? ''}` : '-',
    },
    {
      title: '含稅金額', dataIndex: 'amount_tax_included', key: 'amt', width: 110, align: 'right' as const,
      render: fmtAmt,
    },
    {
      title: '操作', key: 'action', width: 90, align: 'center' as const,
      render: (_: any, record: ContractItemRecord) => (
        <Space size={4}>
          <Tooltip title="編輯">
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          </Tooltip>
          <Popconfirm title="確認刪除此項目？" onConfirm={() => handleDelete(record.id)}>
            <Tooltip title="刪除">
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const totalIncluded = items.reduce((s, i) => s + (i.amount_tax_included ?? 0), 0)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ color: '#595959', fontSize: 13 }}>
          共 {items.length} 項，合計含稅：
          <strong style={{ color: '#722ED1', marginLeft: 4 }}>
            ${totalIncluded.toLocaleString('zh-TW')}
          </strong>
        </span>
        <Button size="small" type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增項目</Button>
      </div>
      <Table
        dataSource={items}
        columns={columns}
        rowKey="id"
        size="small"
        loading={loading}
        pagination={false}
        locale={{ emptyText: <Empty description="尚無合約項目" /> }}
      />

      <Modal
        title={editRecord ? '編輯合約項目' : '新增合約項目'}
        open={addOpen}
        onOk={handleSubmit}
        onCancel={() => setAddOpen(false)}
        confirmLoading={addLoading}
        width={520}
        okText="儲存"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="item_name" label="項目名稱" rules={[{ required: true, message: '必填' }]}>
            <Input placeholder="例：月租費、一次性授權費" />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="item_category" label="項目類別">
                <Select allowClear placeholder="請選擇">
                  {ITEM_CATEGORY_OPTIONS.map(c => <Option key={c} value={c}>{c}</Option>)}
                </Select>
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="quantity" label="數量">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="unit" label="單位">
                <Input placeholder="月/次/人" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="unit_price_tax_excluded" label="單價（未稅）">
                <InputNumber style={{ width: '100%' }} min={0} prefix="$"
                  formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={v => (v?.replace(/\$\s?|(,*)/g, '') ?? '') as any} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="tax_rate" label="稅率（%）" initialValue={5}>
                <InputNumber style={{ width: '100%' }} min={0} max={100} suffix="%" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="amount_tax_excluded" label="金額（未稅）">
                <InputNumber style={{ width: '100%' }} min={0} prefix="$"
                  formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={v => (v?.replace(/\$\s?|(,*)/g, '') ?? '') as any} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="amount_tax_included" label="金額（含稅）">
                <InputNumber style={{ width: '100%' }} min={0} prefix="$"
                  formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={v => (v?.replace(/\$\s?|(,*)/g, '') ?? '') as any} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// 請款紀錄 Tab 元件（B1）
// ═════════════════════════════════════════════════════════════════════════════

const CLAIM_STATUS_COLOR: Record<string, string> = {
  '待審核': 'default',
  '已核准': 'success',
  '已拒絕': 'error',
  '已付款': 'blue',
}

const fmtClaimMoney = (v?: number) =>
  v == null ? '—' : `$ ${v.toLocaleString()}`

interface ContractClaimsTabProps {
  contractId: string
  open: boolean
  totalAmount?: number
}

function ContractClaimsTab({ contractId, open, totalAmount }: ContractClaimsTabProps) {
  const [claims, setClaims] = useState<ClaimRecord[]>([])
  const [claimsLoading, setClaimsLoading] = useState(false)
  const [claimStatusFilter, setClaimStatusFilter] = useState<string | undefined>(undefined)
  const [selectedClaimIds, setSelectedClaimIds] = useState<number[]>([])
  const [batchLoading, setBatchLoading] = useState(false)
  const [addClaimOpen, setAddClaimOpen] = useState(false)
  const [addClaimLoading, setAddClaimLoading] = useState(false)
  const [addClaimForm] = Form.useForm()
  // F6 費用歸屬公司下拉
  const [claimCompanyOpts, setClaimCompanyOpts] = useState<CompanyOption[]>([])
  // 附件 Modal
  const [claimDetailOpen, setClaimDetailOpen] = useState(false)
  const [selectedClaim, setSelectedClaim] = useState<ClaimRecord | null>(null)
  const [attachments, setAttachments] = useState<ClaimAttachment[]>([])
  const [attachLoading, setAttachLoading] = useState(false)
  const [uploadingAttach, setUploadingAttach] = useState(false)

  const openClaimDetail = useCallback(async (claim: ClaimRecord) => {
    setSelectedClaim(claim)
    setClaimDetailOpen(true)
    setAttachments([])
    setAttachLoading(true)
    try {
      const list = await fetchClaimAttachments(claim.id)
      setAttachments(list)
    } catch { setAttachments([]) }
    finally { setAttachLoading(false) }
  }, [])

  const handleDeleteAttachment = async (id: number) => {
    try {
      await deleteClaimAttachment(id)
      setAttachments(prev => prev.filter(a => a.id !== id))
      message.success('附件已刪除')
    } catch { message.error('刪除失敗') }
  }

  const loadClaims = useCallback(async () => {
    if (!open || !contractId) return
    setClaimsLoading(true)
    try {
      const r = await fetchClaims({ contract_id: contractId, size: 200 })
      setClaims(r.items)
    } catch { /* ignore */ }
    finally { setClaimsLoading(false) }
  }, [open, contractId])

  useEffect(() => { loadClaims() }, [loadClaims])

  // 載入費用歸屬公司下拉（lazy，只在第一次開啟時載入）
  useEffect(() => {
    if (open && claimCompanyOpts.length === 0) {
      companiesApi.options().then(res => setClaimCompanyOpts(Array.isArray(res.data) ? res.data : [])).catch(() => {})
    }
  }, [open])

  const handleAddClaimOk = async () => {
    const values = await addClaimForm.validateFields()
    setAddClaimLoading(true)
    try {
      const { createClaim } = await import('@/api/contract')
      await createClaim({
        contract_id: contractId,
        claim_date: values.claim_date,
        amount: values.amount,
        invoice_no: values.invoice_no,
        claim_type: values.claim_type ?? '請款',
        remarks: values.remarks,
        cost_company: values.cost_company,
      })
      message.success('請款已新增')
      setAddClaimOpen(false)
      addClaimForm.resetFields()
      loadClaims()
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? '新增失敗')
    } finally { setAddClaimLoading(false) }
  }

  const handleBatchApprove = async () => {
    if (!selectedClaimIds.length) return
    setBatchLoading(true)
    try {
      const { batchReviewClaims } = await import('@/api/contract')
      await batchReviewClaims(selectedClaimIds, 'approve', undefined, '管理員')
      message.success(`已批次核准 ${selectedClaimIds.length} 筆請款`)
      setSelectedClaimIds([])
      loadClaims()
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? '批次審核失敗')
    } finally { setBatchLoading(false) }
  }

  const filteredClaims = claimStatusFilter
    ? claims.filter(c => c.status === claimStatusFilter)
    : claims
  const totalClaimed = claims.reduce((sum, c) => sum + (c.amount ?? 0), 0)
  const paidAmount   = claims.filter(c => c.status === '已付款').reduce((sum, c) => sum + (c.amount ?? 0), 0)
  const pendingOverdue = claims.filter(c => {
    if (c.status !== '待審核') return false
    const daysOld = (Date.now() - new Date(c.created_at ?? '').getTime()) / 86400000
    return daysOld > 7
  }).length
  const pct = totalAmount && totalAmount > 0
    ? Math.min(Math.round((totalClaimed / totalAmount) * 100), 100)
    : 0

  const columns: ColumnsType<ClaimRecord> = [
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => <Tag color={CLAIM_STATUS_COLOR[s] ?? 'default'}>{s}</Tag>,
    },
    {
      title: '類型',
      dataIndex: 'claim_type',
      key: 'claim_type',
      width: 70,
    },
    {
      title: '請款日期',
      dataIndex: 'claim_date',
      key: 'claim_date',
      width: 110,
      render: (v: string) => v ? v.slice(0, 10) : '—',
    },
    {
      title: '發票號碼',
      dataIndex: 'invoice_no',
      key: 'invoice_no',
      width: 110,
      render: (v?: string) => v || '—',
    },
    {
      title: '費用歸屬',
      dataIndex: 'cost_company',
      key: 'cost_company',
      width: 90,
      render: (v?: string) => v ? <Tag color="blue">{v}</Tag> : '—',
    },
    {
      title: '金額',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      align: 'right' as const,
      render: (v: number) => (
        <span style={{ fontWeight: 600, color: '#722ED1' }}>{fmtClaimMoney(v)}</span>
      ),
    },
  ]

  if (claimsLoading && claims.length === 0) return <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>

  return (
    <div>
      {/* 金額使用率進度條 (A1) */}
      {totalAmount != null && totalAmount > 0 && (
        <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }} bordered={false}>
          <Row gutter={16} align="middle">
            <Col span={24}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 13, color: '#595959' }}>合約總額使用率</span>
                <span style={{ fontSize: 13 }}>
                  <strong style={{ color: '#722ED1' }}>{fmtClaimMoney(totalClaimed)}</strong>
                  <span style={{ color: '#8c8c8c' }}> / {fmtClaimMoney(totalAmount)}</span>
                </span>
              </div>
              <Progress
                percent={pct}
                strokeColor={pct >= 90 ? '#ff4d4f' : pct >= 70 ? '#faad14' : '#52c41a'}
                size="small"
              />
              <Row gutter={8} style={{ marginTop: 8 }}>
                <Col span={8}>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>請款筆數</div>
                  <div style={{ fontWeight: 600 }}>{claims.length} 筆</div>
                </Col>
                <Col span={8}>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>已付款金額</div>
                  <div style={{ fontWeight: 600, color: '#1890ff' }}>{fmtClaimMoney(paidAmount)}</div>
                </Col>
                <Col span={8}>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>待審核筆數</div>
                  <div style={{ fontWeight: 600, color: '#faad14' }}>
                    {claims.filter(c => c.status === '待審核').length} 筆
                  </div>
                </Col>
              </Row>
            </Col>
          </Row>
        </Card>
      )}


      {claims.length === 0 && claimStatusFilter == null ? (
        <Empty description="尚無請款紀錄" style={{ padding: '40px 0' }} />
      ) : (
        <>
          <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Select
                allowClear placeholder="篩選狀態" size="small" style={{ width: 110 }}
                value={claimStatusFilter}
                onChange={(v) => setClaimStatusFilter(v)}
                options={[
                  { value: '待審核', label: '待審核' },
                  { value: '已核准', label: '已核准' },
                  { value: '已拒絕', label: '已拒絕' },
                  { value: '已付款', label: '已付款' },
                ]}
              />
              <Button size="small" icon={<ReloadOutlined />} onClick={loadClaims} loading={claimsLoading}>
                重整
              </Button>
              <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => { setAddClaimOpen(true); addClaimForm.resetFields() }}>
                新增請款
              </Button>
            </Space>
            {selectedClaimIds.length > 0 && (
              <Button size="small" type="primary" loading={batchLoading} onClick={handleBatchApprove}>
                批次核准（{selectedClaimIds.length}）
              </Button>
            )}
          </div>

          <Table
            size="small"
            rowSelection={{
              type: 'checkbox',
              selectedRowKeys: selectedClaimIds,
              onChange: (keys) => setSelectedClaimIds(keys as number[]),
              getCheckboxProps: (r) => ({ disabled: r.status !== '待審核' }),
            }}
            columns={columns}
            dataSource={filteredClaims}
            pagination={false}
            scroll={{ x: 520 }}
            onRow={(record) => ({
              onClick: (e) => {
                const target = e.target as HTMLElement
                if (target.closest('.ant-checkbox-wrapper') || target.closest('button')) return
                openClaimDetail(record)
              },
              style: { cursor: 'pointer' },
            })}
            footer={() => (
              <div style={{ textAlign: 'right', fontWeight: 600 }}>
                合計：{`$${filteredClaims.reduce((s, c) => s + Number(c.amount), 0).toLocaleString('zh-TW', { minimumFractionDigits: 0 })}`}
                {` / 合約總額 $${(totalAmount ?? 0).toLocaleString('zh-TW', { minimumFractionDigits: 0 })}`}
              </div>
            )}
          />
        </>
      )}

      {/* 請款明細 + 附件 Modal */}
      {selectedClaim && (
        <Modal
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Tag color={
                selectedClaim.status === '待審核' ? 'gold' :
                selectedClaim.status === '已核准' ? 'blue' :
                selectedClaim.status === '已付款' ? 'green' : 'red'
              }>{selectedClaim.status}</Tag>
              <span style={{ fontWeight: 600 }}>請款 #{selectedClaim.id}</span>
            </div>
          }
          open={claimDetailOpen}
          onCancel={() => setClaimDetailOpen(false)}
          footer={null}
          width={520}
          destroyOnClose
        >
          <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
            <Descriptions.Item label="類型">{selectedClaim.claim_type}</Descriptions.Item>
            <Descriptions.Item label="請款日期">{selectedClaim.claim_date}</Descriptions.Item>
            <Descriptions.Item label="金額">
              <strong style={{ color: '#722ED1' }}>${Number(selectedClaim.amount).toLocaleString()}</strong>
            </Descriptions.Item>
            <Descriptions.Item label="費用歸屬公司">
              {selectedClaim.cost_company ? <Tag color="blue">{selectedClaim.cost_company}</Tag> : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="發票號碼">{selectedClaim.invoice_no || '—'}</Descriptions.Item>
            <Descriptions.Item label="核准人">{selectedClaim.approver || '—'}</Descriptions.Item>
            <Descriptions.Item label="備註">{selectedClaim.remarks || '—'}</Descriptions.Item>
          </Descriptions>

          <Divider style={{ margin: '12px 0' }} />
          <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontWeight: 600 }}><PaperClipOutlined style={{ marginRight: 4 }} />附件</span>
            <span style={{ fontSize: 12, color: '#8c8c8c' }}>PDF / JPG / PNG / WEBP，最大 20MB</span>
          </div>

          <Upload.Dragger
            multiple={false}
            showUploadList={false}
            accept=".pdf,.jpg,.jpeg,.png,.webp"
            beforeUpload={async (file) => {
              if (!selectedClaim) return false
              setUploadingAttach(true)
              try {
                const att = await uploadClaimAttachment(selectedClaim.id, file)
                setAttachments(prev => [...prev, att])
                message.success(`${file.name} 上傳成功`)
              } catch {
                message.error('上傳失敗，請確認格式與大小')
              } finally { setUploadingAttach(false) }
              return false
            }}
            disabled={uploadingAttach}
            style={{ marginBottom: 12 }}
          >
            <p className="ant-upload-drag-icon">{uploadingAttach ? <Spin /> : <InboxOutlined />}</p>
            <p className="ant-upload-text" style={{ fontSize: 13 }}>
              {uploadingAttach ? '上傳中…' : '點擊或拖曳檔案上傳'}
            </p>
          </Upload.Dragger>

          <Spin spinning={attachLoading}>
            {attachments.length === 0 && !attachLoading && (
              <span style={{ fontSize: 13, color: '#8c8c8c' }}>尚未上傳任何附件</span>
            )}
            <Image.PreviewGroup>
              {attachments.map(att => {
                const isImage = att.content_type.startsWith('image/')
                const url = getAttachmentUrl(att.download_url)
                return (
                  <div key={att.id} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '6px 8px', borderRadius: 6,
                    background: '#fafafa', border: '1px solid #f0f0f0',
                    marginBottom: 6,
                  }}>
                    {isImage ? (
                      <Image width={36} height={36} src={url}
                        style={{ objectFit: 'cover', borderRadius: 4 }} preview={{ src: url }} />
                    ) : (
                      <FilePdfOutlined style={{ fontSize: 28, color: '#f5222d' }} />
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <a href={url} target="_blank" rel="noopener noreferrer"
                        style={{ color: '#1B3A5C', fontSize: 13, fontWeight: 500 }}
                        title={att.original_filename}>
                        {att.original_filename}
                      </a>
                      <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                        {(att.file_size / 1024).toFixed(0)} KB　{att.uploader}　{att.created_at.slice(0, 16)}
                      </div>
                    </div>
                    <Popconfirm title="確認刪除此附件？" onConfirm={() => handleDeleteAttachment(att.id)}
                      okText="刪除" cancelText="取消" okType="danger">
                      <Button type="text" danger size="small" icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </div>
                )
              })}
            </Image.PreviewGroup>
          </Spin>
        </Modal>
      )}

      {/* 新增請款 Modal */}
      <Modal
        title="新增請款"
        open={addClaimOpen}
        onOk={handleAddClaimOk}
        onCancel={() => setAddClaimOpen(false)}
        confirmLoading={addClaimLoading}
        okText="確認新增"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={addClaimForm} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="claim_date" label="請款日期" rules={[{ required: true, message: '請選擇日期' }]}>
            <Input type="date" />
          </Form.Item>
          <Form.Item name="amount" label="請款金額" rules={[{ required: true, message: '請輸入金額' }]}>
            <InputNumber style={{ width: '100%' }} min={0} precision={2} prefix="$" />
          </Form.Item>
          <Form.Item name="invoice_no" label="發票號碼">
            <Input placeholder="選填" />
          </Form.Item>
          <Form.Item name="claim_type" label="類型" initialValue="請款">
            <Select options={[
              { value: '請款', label: '請款' },
              { value: '核銷', label: '核銷' },
              { value: '其他', label: '其他' },
            ]} />
          </Form.Item>
          <Form.Item name="cost_company" label="費用歸屬公司">
            <Select showSearch allowClear placeholder="選填" optionFilterProp="label" options={claimCompanyOpts} />
          </Form.Item>
          <Form.Item name="remarks" label="備註">
            <Input.TextArea rows={2} placeholder="選填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// 合約續約 Tab 元件
// ═════════════════════════════════════════════════════════════════════════════

interface ContractRenewalsTabProps {
  contractId: string
  open: boolean
}

function ContractRenewalsTab({ contractId, open }: ContractRenewalsTabProps) {
  const [renewals, setRenewals] = useState<RenewalRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [applyOpen, setApplyOpen] = useState(false)
  const [applyLoading, setApplyLoading] = useState(false)
  const [applyForm] = Form.useForm()

  const loadRenewals = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const rows = await fetchRenewalsByContract(contractId)
      setRenewals(rows)
    } catch {
      message.error('無法載入續約申請')
    } finally {
      setLoading(false)
    }
  }, [contractId, open])

  useEffect(() => { loadRenewals() }, [loadRenewals])

  const handleApplyOk = async () => {
    const values = await applyForm.validateFields()
    setApplyLoading(true)
    try {
      await applyRenewal(contractId, {
        renewal_start_date: values.renewal_start_date,
        renewal_end_date:   values.renewal_end_date,
        new_amount:         values.new_amount ?? null,
        renewal_reason:     values.renewal_reason,
        remarks:            values.remarks,
        applicant_dept:     values.applicant_dept,
      })
      message.success('續約申請已提交，等待審核')
      setApplyOpen(false)
      applyForm.resetFields()
      loadRenewals()
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? '申請失敗')
    } finally {
      setApplyLoading(false)
    }
  }

  const RENEWAL_STATUS_COLOR: Record<string, string> = {
    '待審核': 'gold', '已核准': 'green', '已拒絕': 'red', '已撤回': 'default',
  }

  const columns: ColumnsType<RenewalRecord> = [
    { title: '#', dataIndex: 'id', key: 'id', width: 50, render: (v) => `#${v}` },
    { title: '續約期間', key: 'period', width: 180,
      render: (_, r) => `${r.renewal_start_date} ～ ${r.renewal_end_date}` },
    { title: '金額', dataIndex: 'new_amount', key: 'new_amount', width: 110,
      render: (v) => v == null ? '同原合約' : `$${Number(v).toLocaleString('zh-TW')}` },
    { title: '狀態', dataIndex: 'status', key: 'status', width: 80,
      render: (s) => <Tag color={RENEWAL_STATUS_COLOR[s] ?? 'default'}>{s}</Tag> },
    { title: '申請人', dataIndex: 'applicant', key: 'applicant', width: 80 },
    { title: '申請時間', dataIndex: 'created_at', key: 'created_at', width: 100,
      render: (v) => v ? v.slice(0, 10) : '—' },
  ]

  return (
    <div style={{ padding: '8px 0' }}>
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'flex-end' }}>
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={loadRenewals} loading={loading}>重整</Button>
          <Button
            size="small" type="primary" icon={<SyncOutlined />}
            onClick={() => { setApplyOpen(true); applyForm.resetFields() }}
          >
            申請續約
          </Button>
        </Space>
      </div>

      <Table
        size="small"
        columns={columns}
        dataSource={renewals}
        loading={loading}
        rowKey="id"
        pagination={false}
        scroll={{ x: 600 }}
        locale={{ emptyText: <Empty description="尚無續約申請" /> }}
      />

      {/* 申請續約 Modal */}
      <Modal
        title="申請合約續約"
        open={applyOpen}
        onOk={handleApplyOk}
        onCancel={() => setApplyOpen(false)}
        confirmLoading={applyLoading}
        okText="確認提交"
        cancelText="取消"
        width={520}
        destroyOnClose
      >
        <Form form={applyForm} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="renewal_start_date" label="續約起日" rules={[{ required: true, message: '請填寫' }]}>
            <Input type="date" />
          </Form.Item>
          <Form.Item name="renewal_end_date" label="續約迄日" rules={[{ required: true, message: '請填寫' }]}>
            <Input type="date" />
          </Form.Item>
          <Form.Item name="new_amount" label="續約金額（含稅）" tooltip="不填表示同原合約金額">
            <InputNumber style={{ width: '100%' }} min={0} precision={0} prefix="$" placeholder="選填，不填表示同原合約" />
          </Form.Item>
          <Form.Item name="renewal_reason" label="續約原因" rules={[{ required: true, message: '請說明續約原因' }]}>
            <Input.TextArea rows={3} placeholder="請說明續約原因或背景" />
          </Form.Item>
          <Form.Item name="applicant_dept" label="申請部門">
            <Input placeholder="選填" />
          </Form.Item>
          <Form.Item name="remarks" label="備註">
            <Input.TextArea rows={2} placeholder="選填" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// E1 合約本體附件 Tab 元件
// ═════════════════════════════════════════════════════════════════════════════

interface ContractAttachmentsTabProps {
  contractId: string
  open: boolean
}

function ContractAttachmentsTab({ contractId, open }: ContractAttachmentsTabProps) {
  const [attachments, setAttachments] = useState<ContractAttachment[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  const loadAttachments = useCallback(async () => {
    if (!open || !contractId) return
    setLoading(true)
    try {
      const list = await fetchContractAttachments(contractId)
      setAttachments(list)
    } catch {
      message.error('載入附件失敗')
    } finally {
      setLoading(false)
    }
  }, [contractId, open])

  useEffect(() => { loadAttachments() }, [loadAttachments])

  const handleUpload = async (file: File) => {
    setUploading(true)
    try {
      const att = await uploadContractAttachment(contractId, file)
      setAttachments(prev => [...prev, att])
      message.success(`${file.name} 上傳成功`)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      message.error(typeof detail === 'string' ? detail : '上傳失敗，請確認格式（PDF/Word/Excel/圖片）與大小（≤20 MB）')
    } finally {
      setUploading(false)
    }
    return false
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteContractAttachment(id)
      setAttachments(prev => prev.filter(a => a.id !== id))
      message.success('附件已刪除')
    } catch {
      message.error('刪除失敗')
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <span style={{ fontSize: 13, color: '#8c8c8c' }}>
          支援格式：PDF / Word / Excel / 圖片，單檔最大 20 MB
        </span>
      </div>

      <Upload.Dragger
        multiple
        showUploadList={false}
        accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.webp"
        beforeUpload={handleUpload}
        disabled={uploading}
        style={{ marginBottom: 16 }}
      >
        <p className="ant-upload-drag-icon">
          {uploading ? <Spin /> : <InboxOutlined />}
        </p>
        <p className="ant-upload-text" style={{ fontSize: 13 }}>
          {uploading ? '上傳中…' : '點擊或拖曳檔案至此上傳'}
        </p>
      </Upload.Dragger>

      <Spin spinning={loading}>
        {attachments.length === 0 && !loading && (
          <Empty description="尚未上傳任何合約附件" style={{ padding: '24px 0' }} />
        )}
        <Image.PreviewGroup>
          {attachments.map(att => {
            const isImage = att.content_type.startsWith('image/')
            const url = getAttachmentUrl(att.download_url)
            return (
              <div
                key={att.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '8px 10px', borderRadius: 6,
                  background: '#fafafa', border: '1px solid #f0f0f0',
                  marginBottom: 8,
                }}
              >
                {isImage ? (
                  <Image
                    width={40} height={40} src={url}
                    style={{ objectFit: 'cover', borderRadius: 4, flexShrink: 0 }}
                    preview={{ src: url }}
                  />
                ) : (
                  <FilePdfOutlined style={{ fontSize: 30, color: '#f5222d', flexShrink: 0 }} />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <a
                    href={url} target="_blank" rel="noopener noreferrer"
                    style={{ color: '#1B3A5C', fontSize: 13, fontWeight: 500 }}
                    title={att.original_filename}
                  >
                    {att.original_filename}
                  </a>
                  <div style={{ fontSize: 11, color: '#8c8c8c', marginTop: 2 }}>
                    {(att.file_size / 1024).toFixed(0)} KB　{att.uploader}　{att.created_at.slice(0, 16)}
                  </div>
                </div>
                <Popconfirm
                  title="確認刪除此附件？"
                  onConfirm={() => handleDelete(att.id)}
                  okText="刪除" cancelText="取消" okType="danger"
                >
                  <Button type="text" danger size="small" icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            )
          })}
        </Image.PreviewGroup>
      </Spin>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// F4 — 費用分攤驗證邏輯
// ═════════════════════════════════════════════════════════════════════════════

/** 固定總額計價方式 → 需驗證固定金額加總等於合約金額 */
const STRICT_PRICING = ['固定費用', '月費', '里程碑付款']

interface AllocValidationResult {
  errors:   string[]  // 阻擋存檔，需修正
  warnings: string[]  // 詢問使用者確認後可繼續
}

function validateAllocations(
  items: CostAllocationItem[],
  contractAmount: number | undefined,
  pricingMethod: string | undefined,
): AllocValidationResult {
  const errors: string[] = []
  const warnings: string[] = []
  if (items.length === 0) return { errors, warnings }

  const hasPct   = items.some(i => i.allocation_type === 'percentage')
  const hasFixed = items.some(i => i.allocation_type === 'fixed')
  const isMixed  = hasPct && hasFixed

  if (isMixed) {
    warnings.push(
      '費用分攤同時包含「比例 %」與「固定金額」兩種類型。\n' +
      '混用時系統無法自動確認加總是否等於合約金額，請手動確認後再存檔。'
    )
  }

  const isStrictPricing = pricingMethod ? STRICT_PRICING.includes(pricingMethod) : false

  if (hasPct) {
    const pctSum = items.filter(i => i.allocation_type === 'percentage').reduce((s, i) => s + (i.value || 0), 0)
    if (Math.abs(pctSum - 100) > 0.01) {
      errors.push(`比例行加總為 ${pctSum.toFixed(2)}%，必須等於 100%（尚差 ${(100 - pctSum).toFixed(2)}%）`)
    }
  }

  if (hasFixed && isStrictPricing && contractAmount && !isMixed) {
    const fixedSum = items.filter(i => i.allocation_type === 'fixed').reduce((s, i) => s + (i.value || 0), 0)
    const diff = fixedSum - contractAmount
    if (Math.abs(diff) > 1) {
      errors.push(
        `固定金額加總 $${fixedSum.toLocaleString('zh-TW')}，` +
        `必須等於合約總額 $${contractAmount.toLocaleString('zh-TW')}` +
        `（差額 ${diff > 0 ? '+' : ''}$${diff.toLocaleString('zh-TW')}）`
      )
    }
  }

  return { errors, warnings }
}

// ═════════════════════════════════════════════════════════════════════════════
// F4 — 費用分攤編輯器元件
// ═════════════════════════════════════════════════════════════════════════════

interface CostAllocationEditorProps {
  value: CostAllocationItem[]
  onChange: (v: CostAllocationItem[]) => void
  companyOptions: CompanyOption[]
  contractAmount?: number   // 合約總額，供即時驗證
  pricingMethod?: string    // 計價方式，決定是否驗證固定金額加總
}

function CostAllocationEditor({
  value, onChange, companyOptions, contractAmount, pricingMethod,
}: CostAllocationEditorProps) {
  const addRow = () => onChange([...value, { company_name: '', allocation_type: 'percentage', value: 0 }])
  const updateRow = (index: number, patch: Partial<CostAllocationItem>) =>
    onChange(value.map((r, i) => (i === index ? { ...r, ...patch } : r)))
  const removeRow = (index: number) => onChange(value.filter((_, i) => i !== index))

  const hasPct   = value.some(r => r.allocation_type === 'percentage')
  const hasFixed = value.some(r => r.allocation_type === 'fixed')
  const pctSum   = value.filter(r => r.allocation_type === 'percentage').reduce((s, r) => s + (r.value || 0), 0)
  const fixedSum = value.filter(r => r.allocation_type === 'fixed').reduce((s, r) => s + (r.value || 0), 0)
  const isStrictPricing = pricingMethod ? STRICT_PRICING.includes(pricingMethod) : false
  const { errors, warnings } = validateAllocations(value, contractAmount, pricingMethod)
  const hasIssue = errors.length > 0
  const hasWarn  = warnings.length > 0

  return (
    <div>
      {value.map((row, idx) => (
        <div key={idx} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
          <Select
            style={{ flex: 2 }} showSearch allowClear placeholder="選擇公司"
            value={row.company_name || undefined} options={companyOptions}
            onChange={(v) => updateRow(idx, { company_name: v ?? '' })}
          />
          <Select
            style={{ width: 120 }} value={row.allocation_type}
            onChange={(v) => updateRow(idx, { allocation_type: v as 'percentage' | 'fixed' })}
            options={[{ value: 'percentage', label: '比例 %' }, { value: 'fixed', label: '固定金額' }]}
          />
          <InputNumber
            style={{ flex: 1 }} min={0}
            max={row.allocation_type === 'percentage' ? 100 : undefined}
            value={row.value}
            onChange={(v) => updateRow(idx, { value: v ?? 0 })}
            suffix={row.allocation_type === 'percentage' ? '%' : '元'}
          />
          <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => removeRow(idx)} />
        </div>
      ))}

      <Button size="small" icon={<PlusOutlined />} onClick={addRow} style={{ marginBottom: 10 }}>
        新增分攤行
      </Button>

      {/* ── 即時狀態面板 ── */}
      {value.length > 0 && (
        <div style={{
          padding: '8px 12px', borderRadius: 6, fontSize: 12,
          background: hasIssue ? '#fff2f0' : hasWarn ? '#fffbe6' : '#f6ffed',
          border: `1px solid ${hasIssue ? '#ffccc7' : hasWarn ? '#ffe58f' : '#b7eb8f'}`,
        }}>
          {/* 比例加總 */}
          {hasPct && (
            <div>
              比例加總：
              <span style={{ fontWeight: 600, color: Math.abs(pctSum - 100) <= 0.01 ? '#52c41a' : '#ff4d4f' }}>
                {pctSum.toFixed(2)}%
              </span>
              {Math.abs(pctSum - 100) > 0.01 && (
                <span style={{ color: '#ff4d4f', marginLeft: 4 }}>
                  （尚差 {(100 - pctSum).toFixed(2)}%）
                </span>
              )}
            </div>
          )}
          {/* 固定金額加總（僅固定計價方式顯示） */}
          {hasFixed && isStrictPricing && contractAmount && (
            <div style={{ marginTop: hasPct ? 4 : 0 }}>
              固定金額加總：
              <span style={{ fontWeight: 600, color: Math.abs(fixedSum - contractAmount) <= 1 ? '#52c41a' : '#ff4d4f' }}>
                ${fixedSum.toLocaleString('zh-TW')}
              </span>
              <span style={{ color: '#8c8c8c', marginLeft: 4 }}>
                / 合約總額 ${contractAmount.toLocaleString('zh-TW')}
              </span>
              {Math.abs(fixedSum - contractAmount) > 1 && (
                <span style={{ color: '#ff4d4f', marginLeft: 4 }}>
                  （差額 {fixedSum > contractAmount ? '+' : ''}${(fixedSum - contractAmount).toLocaleString('zh-TW')}）
                </span>
              )}
            </div>
          )}
          {/* 非固定計價說明 */}
          {hasFixed && !isStrictPricing && pricingMethod && (
            <div style={{ color: '#8c8c8c' }}>
              計價方式「{pricingMethod}」為變動計費，固定金額不強制驗證加總
            </div>
          )}
          {/* 混用警告 */}
          {hasWarn && (
            <div style={{ color: '#d48806', marginTop: 4 }}>
              ⚠ 比例與固定金額混用 — 存檔前將請求確認
            </div>
          )}
        </div>
      )}
    </div>
  )
}
