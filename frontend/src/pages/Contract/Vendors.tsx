/**
 * 廠商管理 — 列表頁面
 *
 * 包含：
 *   - 廠商清單表格（分頁、搜尋）
 *   - Drawer 明細檢視
 *   - 新增、刪除操作
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Table, Tag, Button, Space,
  Typography, Breadcrumb, Drawer, Descriptions, message,
  Input, Modal, Tooltip, Badge, Form, Select, Switch,
  Tabs, Progress, Statistic, Spin, Empty, Upload, Alert, List,
} from 'antd'
import type { UploadProps } from 'antd'
import {
  HomeOutlined, PlusOutlined, DeleteOutlined,
  ReloadOutlined, SearchOutlined, LinkOutlined,
  TrophyOutlined, FileTextOutlined, UploadOutlined,
  CheckCircleOutlined, WarningOutlined,
} from '@ant-design/icons'
import type { ColumnsType, TableProps } from 'antd/es/table'

import {
  fetchVendors, deleteVendor, createVendor, fetchVendorPerformance, importVendors,
} from '@/api/contract'
import type { VendorImportResult } from '@/api/contract'
import type { VendorRecord, VendorPerformance } from '@/types/contract'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import { companiesApi } from '@/api/referenceData'
import type { CompanyOption } from '@/api/referenceData'

const { Title } = Typography

// ── 常數 ──────────────────────────────────────────────────────────────────────
const RISK_LEVEL_COLOR: Record<string, string> = {
  '低': '#52C41A',
  '中': '#FAAD14',
  '高': '#FF7A45',
}

// ═════════════════════════════════════════════════════════════════════════════
// 主元件
// ═════════════════════════════════════════════════════════════════════════════

export default function VendorListPage() {
  const [vendors, setVendors] = useState<VendorRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({ page: 1, size: 20, total: 0 })

  // 詳情 Drawer 狀態
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedVendor, setSelectedVendor] = useState<VendorRecord | null>(null)

  // 新增 Modal 狀態
  const [addOpen, setAddOpen] = useState(false)
  const [addLoading, setAddLoading] = useState(false)
  const [addForm] = Form.useForm()
  // F7 管理公司下拉
  const [vendorCompanyOpts, setVendorCompanyOpts] = useState<CompanyOption[]>([])

  // 搜尋
  const [searchText, setSearchText] = useState('')

  // 匯入 Excel 狀態
  const [importOpen, setImportOpen] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<VendorImportResult | null>(null)

  // ── 載入廠商清單 ──────────────────────────────────────────────────────────
  const loadVendors = useCallback(async (page: number, size: number, search?: string) => {
    setLoading(true)
    try {
      const result = await fetchVendors({ page, size, search: search || undefined })
      setVendors(result.items)
      setPagination({ page, size, total: result.total })
    } catch (err: any) {
      message.error(err?.message || '載入廠商失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  // ── 初始化 ────────────────────────────────────────────────────────────────
  useEffect(() => {
    loadVendors(1, pagination.size)
    companiesApi.options().then(res => setVendorCompanyOpts(Array.isArray(res.data) ? res.data : [])).catch(() => {})
  }, [])

  // ── 搜尋變更 ──────────────────────────────────────────────────────────────
  useEffect(() => {
    loadVendors(1, pagination.size, searchText)
  }, [searchText])

  // ── 提交新增廠商 ──────────────────────────────────────────────────────────
  const handleAddOk = async () => {
    try {
      const values = await addForm.validateFields()
      setAddLoading(true)
      await createVendor({ ...values, is_critical: values.is_critical ?? false })
      message.success('廠商已新增')
      setAddOpen(false)
      loadVendors(1, pagination.size, searchText)
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.response?.data?.detail ?? err?.message ?? '新增失敗')
    } finally {
      setAddLoading(false)
    }
  }

  // ── 刪除操作 ────────────────────────────────────────────────────────────
  const handleDelete = (vendorId: string) => {
    Modal.confirm({
      title: '確定刪除此廠商？',
      content: '此操作無法復原，請謹慎執行。',
      okText: '確定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteVendor(vendorId)
          message.success('廠商已刪除')
          loadVendors(pagination.page, pagination.size, searchText)
        } catch (err: any) {
          message.error(err?.message || '刪除失敗')
        }
      },
    })
  }

  // ── 匯入 Excel ──────────────────────────────────────────────────────────
  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.xlsx',
    maxCount: 1,
    beforeUpload: async (file) => {
      setImporting(true)
      setImportResult(null)
      try {
        const result = await importVendors(file)
        setImportResult(result)
        if (result.errors.length === 0) {
          message.success(`匯入完成：新增 ${result.created} 筆，更新 ${result.updated} 筆`)
        } else {
          message.warning(`匯入完成，但有 ${result.errors.length} 列錯誤，請查看明細`)
        }
        loadVendors(1, pagination.size, searchText)
      } catch (err: any) {
        message.error(err?.response?.data?.detail ?? '匯入失敗')
      } finally {
        setImporting(false)
      }
      return false  // 阻止 antd 預設上傳行為
    },
    showUploadList: false,
  }

  // ── 分頁變更 ────────────────────────────────────────────────────────────
  const handleTableChange: TableProps<VendorRecord>['onChange'] = (pg) => {
    if (pg.current && pg.pageSize) {
      loadVendors(pg.current, pg.pageSize, searchText)
    }
  }

  // ── 表格欄位定義 ──────────────────────────────────────────────────────────
  const columns: ColumnsType<VendorRecord> = [
    {
      title: '廠商編號',
      dataIndex: 'vendor_id',
      width: 120,
      fixed: 'left',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: '廠商名稱',
      dataIndex: 'vendor_name',
      width: 200,
      ellipsis: { showTitle: false },
      render: (text) => (
        <Tooltip title={text}>
          <span style={{ cursor: 'pointer', color: '#4BA8E8' }}>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '統一編號',
      dataIndex: 'tax_id',
      width: 130,
    },
    {
      title: '聯絡人',
      dataIndex: 'contact_person',
      width: 120,
      render: (text) => text || '-',
    },
    {
      title: '電話',
      dataIndex: 'phone',
      width: 130,
      render: (text) => text || '-',
    },
    {
      title: '信用等級',
      dataIndex: 'risk_level',
      width: 100,
      render: (level) =>
        level ? <Tag color={RISK_LEVEL_COLOR[level] ?? 'default'}>{level}</Tag> : <span>—</span>,
    },
    {
      title: '關鍵廠商',
      dataIndex: 'is_critical',
      width: 100,
      render: (isCritical) => isCritical ? <Tag color="red">是</Tag> : <span>—</span>,
    },
    {
      title: '管理公司',
      dataIndex: 'managing_company',
      width: 100,
      render: (v?: string) => v ? <Tag color="blue">{v}</Tag> : '—',
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
              setSelectedVendor(record)
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
              handleDelete(record.vendor_id)
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
        <Breadcrumb.Item>{NAV_PAGE.contractVendors}</Breadcrumb.Item>
      </Breadcrumb>

      {/* 搜尋列 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={16}>
          <Col xs={24} sm={12} lg={8}>
            <Input
              placeholder="搜尋廠商名稱或編號..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
          </Col>
          <Col xs={24} sm={12} lg={16}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button icon={<ReloadOutlined />} onClick={() => loadVendors(1, pagination.size, searchText)}>
                重新整理
              </Button>
              <Button
                icon={<UploadOutlined />}
                onClick={() => { setImportOpen(true); setImportResult(null) }}
              >
                匯入 Excel
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => { setAddOpen(true); addForm.resetFields() }}
              >
                新增廠商
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 表格 */}
      <Card>
        <Table<VendorRecord>
          columns={columns}
          dataSource={vendors}
          loading={loading}
          pagination={{
            current: pagination.page,
            pageSize: pagination.size,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 筆`,
          }}
          onChange={handleTableChange}
          rowKey="vendor_id"
          onRow={(record) => ({
            onClick: () => {
              setSelectedVendor(record)
              setDrawerOpen(true)
            },
            style: { cursor: 'pointer' },
          })}
        />
      </Card>

      {/* 詳情 Drawer */}
      {selectedVendor && (
        <VendorDetailDrawer
          vendor={selectedVendor}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        />
      )}

      {/* 新增廠商 Modal */}
      <Modal
        title="新增廠商"
        open={addOpen}
        onOk={handleAddOk}
        onCancel={() => setAddOpen(false)}
        confirmLoading={addLoading}
        okText="確認新增"
        cancelText="取消"
        width={640}
        destroyOnClose
      >
        <Form form={addForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="vendor_id"
                label="廠商編號"
                rules={[
                  { required: true, message: '請輸入廠商編號' },
                  { pattern: /^VND-\d{4}$/, message: '格式：VND-NNNN，例如 VND-0001' },
                ]}
              >
                <Input placeholder="VND-0001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="vendor_name"
                label="廠商名稱"
                rules={[{ required: true, message: '請輸入廠商名稱' }]}
              >
                <Input placeholder="請輸入廠商名稱" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="tax_id"
                label="統一編號"
                rules={[{ required: true, message: '請輸入統一編號' }]}
              >
                <Input placeholder="8 位數統編" maxLength={8} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="vendor_type" label="廠商類型">
                <Select placeholder="請選擇" allowClear>
                  {['維護廠商', '採購廠商', '服務廠商', '工程廠商', '顧問廠商', '其他'].map(t => (
                    <Select.Option key={t} value={t}>{t}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="contact_person" label="聯絡人">
                <Input placeholder="選填" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone" label="電話">
                <Input placeholder="選填" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="address" label="地址">
            <Input placeholder="選填" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="payment_terms" label="付款條款">
                <Input placeholder="例：月結30天" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="is_critical" label="關鍵廠商" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="managing_company" label="管理公司">
                <Select showSearch allowClear placeholder="選填" optionFilterProp="label"
                  options={vendorCompanyOpts} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* 匯入 Excel Modal */}
      <Modal
        title="廠商 Excel 批次匯入"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        footer={null}
        width={560}
        destroyOnClose
      >
        <div style={{ marginBottom: 16 }}>
          <Alert
            type="info"
            showIcon
            message="Excel 欄位順序"
            description="A 廠商編號（VND-NNNN）　B 廠商名稱　C 統一編號　D 聯絡人　E 聯絡電話　F Email　G 地址　H 付款條件　I 銀行名稱　J 銀行帳號　K 廠商類別　L 風險等級（低/中/高）　M 關鍵供應商（是/否）"
            style={{ marginBottom: 12 }}
          />
          <Upload.Dragger {...uploadProps} disabled={importing} style={{ padding: '12px 0' }}>
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: 32, color: '#4BA8E8' }} />
            </p>
            <p className="ant-upload-text">
              {importing ? '匯入中…' : '點擊或拖曳 .xlsx 檔案至此區域'}
            </p>
            <p className="ant-upload-hint">僅支援 .xlsx 格式，第一列為標題列</p>
          </Upload.Dragger>
        </div>

        {importResult && (
          <div>
            <Alert
              type={importResult.errors.length === 0 ? 'success' : 'warning'}
              showIcon
              icon={importResult.errors.length === 0 ? <CheckCircleOutlined /> : <WarningOutlined />}
              message={`匯入完成 — 共 ${importResult.total_rows} 列：新增 ${importResult.created}　更新 ${importResult.updated}　略過 ${importResult.skipped}`}
              style={{ marginBottom: importResult.errors.length > 0 ? 8 : 0 }}
            />
            {importResult.errors.length > 0 && (
              <List
                size="small"
                header={<span style={{ color: '#cf1322' }}>錯誤明細（{importResult.errors.length} 列）</span>}
                dataSource={importResult.errors}
                renderItem={(e) => (
                  <List.Item style={{ padding: '4px 0' }}>
                    <span style={{ color: '#888', marginRight: 8 }}>第 {e.row} 列</span>
                    {e.vendor_id && <Tag>{e.vendor_id}</Tag>}
                    <span style={{ color: '#cf1322' }}>{e.message}</span>
                  </List.Item>
                )}
                style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #ffa39e', borderRadius: 6, padding: '4px 12px' }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// 詳情 Drawer 元件
// ═════════════════════════════════════════════════════════════════════════════

interface VendorDetailDrawerProps {
  vendor: VendorRecord
  open: boolean
  onClose: () => void
}

const GRADE_COLOR: Record<string, string> = {
  A: '#52c41a', B: '#1677ff', C: '#fa8c16', D: '#f5222d',
}
const GRADE_LABEL: Record<string, string> = {
  A: '優良', B: '良好', C: '待改善', D: '高風險',
}

function VendorDetailDrawer({ vendor, open, onClose }: VendorDetailDrawerProps) {
  const [perf, setPerf] = useState<VendorPerformance | null>(null)
  const [perfLoading, setPerfLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setPerfLoading(true)
    fetchVendorPerformance(vendor.vendor_id)
      .then(setPerf)
      .catch(() => setPerf(null))
      .finally(() => setPerfLoading(false))
  }, [open, vendor.vendor_id])

  const basicTab = (
    <>
      <Title level={5} style={{ marginTop: 0 }}>基本資訊</Title>
      <Descriptions column={1} bordered size="small" style={{ marginBottom: 20 }}>
        <Descriptions.Item label="廠商編號"><strong>{vendor.vendor_id}</strong></Descriptions.Item>
        <Descriptions.Item label="廠商名稱">{vendor.vendor_name}</Descriptions.Item>
        <Descriptions.Item label="統一編號">{vendor.tax_id || '-'}</Descriptions.Item>
      </Descriptions>

      <Title level={5}>聯絡資訊</Title>
      <Descriptions column={1} bordered size="small" style={{ marginBottom: 20 }}>
        <Descriptions.Item label="聯絡人">{vendor.contact_person || '-'}</Descriptions.Item>
        <Descriptions.Item label="電話">{vendor.phone || '-'}</Descriptions.Item>
        <Descriptions.Item label="電子郵件">{vendor.email || '-'}</Descriptions.Item>
        <Descriptions.Item label="地址">{vendor.address || '-'}</Descriptions.Item>
      </Descriptions>

      <Title level={5}>付款資訊</Title>
      <Descriptions column={1} bordered size="small" style={{ marginBottom: 20 }}>
        <Descriptions.Item label="付款條款">{vendor.payment_terms || '-'}</Descriptions.Item>
        <Descriptions.Item label="銀行名稱">{vendor.bank_name || '-'}</Descriptions.Item>
        <Descriptions.Item label="銀行帳戶">{vendor.bank_account || '-'}</Descriptions.Item>
      </Descriptions>

      <Title level={5}>分類與風險</Title>
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="廠商類型">{vendor.vendor_type || '-'}</Descriptions.Item>
        <Descriptions.Item label="信用等級">
          {vendor.risk_level ? (
            <Tag color={RISK_LEVEL_COLOR[vendor.risk_level] ?? 'default'}>{vendor.risk_level}</Tag>
          ) : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="關鍵廠商">
          {vendor.is_critical ? <Tag color="red">是</Tag> : <span>否</span>}
        </Descriptions.Item>
        <Descriptions.Item label="管理公司">
          {vendor.managing_company ? <Tag color="blue">{vendor.managing_company}</Tag> : '—'}
        </Descriptions.Item>
      </Descriptions>
    </>
  )

  const perfTab = (
    <Spin spinning={perfLoading}>
      {!perf || perf.total_claims === 0 ? (
        <Empty description="尚無請款記錄，無法計算績效" style={{ marginTop: 40 }} />
      ) : (
        <>
          {/* 評分等級 */}
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <div style={{
              display: 'inline-flex', flexDirection: 'column', alignItems: 'center',
              background: '#f6ffed', border: `2px solid ${GRADE_COLOR[perf.grade ?? 'D']}`,
              borderRadius: 12, padding: '16px 32px',
            }}>
              <TrophyOutlined style={{ fontSize: 28, color: GRADE_COLOR[perf.grade ?? 'D'], marginBottom: 4 }} />
              <span style={{ fontSize: 36, fontWeight: 800, color: GRADE_COLOR[perf.grade ?? 'D'], lineHeight: 1 }}>
                {perf.grade}
              </span>
              <span style={{ fontSize: 13, color: '#595959', marginTop: 4 }}>
                {GRADE_LABEL[perf.grade ?? 'D']}
              </span>
            </div>
          </div>

          {/* 準時率 */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontWeight: 600 }}>準時率</span>
              <span style={{ color: '#1B3A5C', fontWeight: 700 }}>
                {perf.ontime_rate != null ? `${(perf.ontime_rate * 100).toFixed(1)}%` : '—'}
              </span>
            </div>
            <Progress
              percent={perf.ontime_rate != null ? Math.round(perf.ontime_rate * 100) : 0}
              strokeColor={perf.ontime_rate != null && perf.ontime_rate >= 0.85 ? '#52c41a' : perf.ontime_rate != null && perf.ontime_rate >= 0.70 ? '#1677ff' : '#fa8c16'}
              showInfo={false}
            />
            <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 2 }}>
              已核出/已付款 {perf.approved_count} 筆 / 總計 {perf.total_claims} 筆
            </div>
          </div>

          {/* 爭議率 */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontWeight: 600 }}>爭議率（拒絕率）</span>
              <span style={{ color: perf.dispute_rate != null && perf.dispute_rate > 0.15 ? '#f5222d' : '#1B3A5C', fontWeight: 700 }}>
                {perf.dispute_rate != null ? `${(perf.dispute_rate * 100).toFixed(1)}%` : '—'}
              </span>
            </div>
            <Progress
              percent={perf.dispute_rate != null ? Math.round(perf.dispute_rate * 100) : 0}
              strokeColor={perf.dispute_rate != null && perf.dispute_rate > 0.15 ? '#f5222d' : '#fa8c16'}
              showInfo={false}
            />
            <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 2 }}>
              已拒絕 {perf.rejected_count} 筆 / 總計 {perf.total_claims} 筆
            </div>
          </div>

          {/* 數字卡 */}
          <Row gutter={16} style={{ marginBottom: 20 }}>
            <Col span={8}><Statistic title="總合約數" value={perf.contract_count} /></Col>
            <Col span={8}><Statistic title="總請款筆" value={perf.total_claims} /></Col>
            <Col span={8}>
              <Statistic
                title="平均處理天"
                value={perf.avg_process_days ?? '—'}
                suffix={perf.avg_process_days != null ? '天' : ''}
              />
            </Col>
          </Row>

          {/* 金額 */}
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="請款總額">
              ${perf.total_amount.toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="已核出金額">
              <span style={{ color: '#1677ff', fontWeight: 600 }}>
                ${perf.approved_amount.toLocaleString()}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="已付款金額">
              <span style={{ color: '#52c41a', fontWeight: 600 }}>
                ${perf.paid_amount.toLocaleString()}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="待審核筆數">
              {perf.pending_count > 0
                ? <Tag color="orange">{perf.pending_count} 筆</Tag>
                : <span style={{ color: '#52c41a' }}>無</span>}
            </Descriptions.Item>
          </Descriptions>
        </>
      )}
    </Spin>
  )

  return (
    <Drawer
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Tag color={vendor.is_critical ? 'red' : 'blue'}>
            {vendor.is_critical ? '關鍵廠商' : '廠商'}
          </Tag>
          <span style={{ fontWeight: 600 }}>廠商：{vendor.vendor_id}</span>
          {vendor.vendor_name && (
            <span style={{ color: '#595959', fontWeight: 400 }}>（{vendor.vendor_name}）</span>
          )}
        </div>
      }
      placement="right"
      width={480}
      onClose={onClose}
      open={open}
      bodyStyle={{ paddingBottom: 80 }}
    >
      <Tabs
        items={[
          {
            key: 'basic',
            label: <span><FileTextOutlined /> 基本資訊</span>,
            children: basicTab,
          },
          {
            key: 'performance',
            label: <span><TrophyOutlined /> 縣效評分</span>,
            children: perfTab,
          },
        ]}
      />
    </Drawer>
  )
}
