/**
 * 合約資料導入 — CSV / Excel 上傳頁面
 *
 * 功能：
 *   - CSV (.csv) 或 Excel (.xlsx / .xls) 檔案上傳
 *   - 欄位預覽與對應
 *   - 驗證與批次導入（呼叫 createContract API）
 *   - 結果報告（成功 / 失敗明細）
 */
import React, { useState } from 'react'
import {
  Card, Button, Upload, message, Table, Tag, Progress,
  Steps, Row, Col, Alert, Divider, Space, Select, Spin,
  Typography, Breadcrumb,
} from 'antd'
import {
  HomeOutlined, UploadOutlined, CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { RcFile, UploadFile } from 'antd/es/upload'
// @ts-ignore
import Papa from 'papaparse'

import { createContract } from '@/api/contract'
import { NAV_GROUP } from '@/constants/navLabels'

const { Text } = Typography

// ── 欄位對應表（中文標題 → API 欄位名稱）────────────────────────────────────
const FIELD_MAPPING: Record<string, string> = {
  '合約編號': 'contract_id',
  '合約名稱': 'contract_name',
  '合約類型': 'contract_type',
  '廠商名稱': 'vendor_name',
  '狀態': 'contract_status',
  '開始日期': 'start_date',
  '截止日期': 'end_date',
  '含稅總金額': 'total_amount_tax_included',
  '預算年度': 'budget_year',
  '定價方式': 'pricing_method',
  '負責部門': 'responsible_dept',
  '預算科目L1': 'budget_category_l1',
  '預算科目L2': 'budget_category_l2',
  '會計科目': 'accounting_code',
  '備註': 'remarks',
}

// 必填欄位（中文名稱）
const REQUIRED_FIELDS = ['合約名稱', '廠商名稱', '開始日期', '截止日期', '含稅總金額']

// 導入結果型別
interface ImportResultRow {
  rowIndex: number
  contract_name: string
  status: 'success' | 'error'
  message: string
}

// ── 解析各 row 為物件陣列（header + rows） ─────────────────────────────────
function buildRows(headers: string[], rawRows: any[][]): Record<string, string>[] {
  return rawRows.map((row) =>
    Object.fromEntries(headers.map((h, i) => [h, String(row[i] ?? '').trim()])),
  )
}

// ════════════════════════════════════════════════════════════════════════════

export default function ContractImportPage() {
  const [step, setStep] = useState(0)
  const [csvData, setCsvData] = useState<Record<string, any>[]>([])
  const [headers, setHeaders] = useState<string[]>([])
  const [file, setFile] = useState<UploadFile | null>(null)
  const [loading, setLoading] = useState(false)
  const [columnMap, setColumnMap] = useState<Record<string, string>>({})  // requiredField → fileHeader
  const [validationErrors, setValidationErrors] = useState<Record<number, string[]>>({})
  const [importResults, setImportResults] = useState<ImportResultRow[]>([])
  const [importSummary, setImportSummary] = useState<{ success: number; failed: number; total: number } | null>(null)

  // ── 解析 CSV ─────────────────────────────────────────────────────────────
  const parseCSV = (fileObj: RcFile) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string
      Papa.parse(text, {
        header: false,
        skipEmptyLines: true,
        complete: (results: any) => {
          const rows = results.data as string[][]
          if (!rows || rows.length < 2) {
            message.error('CSV 檔案資料不足（至少需要標題列 + 一筆資料）')
            return
          }
          const hdrs = rows[0].map((h) => h.trim())
          const dataRows = buildRows(hdrs, rows.slice(1))
          setHeaders(hdrs)
          setCsvData(dataRows)
          setStep(1)
          message.success(`成功讀取 ${dataRows.length} 筆資料`)
        },
        error: (err: any) => {
          message.error(`解析 CSV 失敗：${err.message}`)
        },
      })
    }
    reader.readAsText(fileObj, 'UTF-8')
  }

  // ── 解析 Excel ──────────────────────────────────────────────────────────
  const parseExcel = async (fileObj: RcFile) => {
    try {
      const XLSX = await import('xlsx')
      const arrayBuffer = await fileObj.arrayBuffer()
      const workbook = XLSX.read(arrayBuffer, { type: 'array' })
      const sheetName = workbook.SheetNames[0]
      const sheet = workbook.Sheets[sheetName]
      const rows: any[][] = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })

      if (!rows || rows.length < 2) {
        message.error('Excel 檔案資料不足（至少需要標題列 + 一筆資料）')
        return
      }
      const hdrs = rows[0].map((h: any) => String(h).trim())
      const dataRows = buildRows(hdrs, rows.slice(1))
      setHeaders(hdrs)
      setCsvData(dataRows)
      setStep(1)
      message.success(`成功讀取 ${dataRows.length} 筆資料`)
    } catch (err: any) {
      message.error(`解析 Excel 失敗：${err.message}`)
    }
  }

  // ── 上傳處理 ────────────────────────────────────────────────────────────
  const handleFileUpload = (fileObj: RcFile) => {
    setFile({
      uid: fileObj.uid,
      name: fileObj.name,
      status: 'done',
      size: fileObj.size,
      type: fileObj.type,
    })

    const ext = fileObj.name.split('.').pop()?.toLowerCase()
    if (ext === 'csv') {
      parseCSV(fileObj)
    } else if (ext === 'xlsx' || ext === 'xls') {
      parseExcel(fileObj)
    } else {
      message.error('不支援的檔案格式，請上傳 .csv 或 .xlsx 檔案')
    }
    return false
  }

  // ── 驗證資料 ────────────────────────────────────────────────────────────
  const validateData = () => {
    // 確認必填欄位都已對應
    const unmapped = REQUIRED_FIELDS.filter((f) => !columnMap[f])
    if (unmapped.length > 0) {
      message.error(`請先對應必填欄位：${unmapped.join('、')}`)
      return false
    }

    const errors: Record<number, string[]> = {}

    csvData.forEach((row, idx) => {
      const rowErrors: string[] = []

      REQUIRED_FIELDS.forEach((field) => {
        const fileCol = columnMap[field]
        if (!fileCol || !row[fileCol]?.toString().trim()) {
          rowErrors.push(`【${field}】為必填`)
        }
      })

      // 金額格式驗證
      const amountCol = columnMap['含稅總金額']
      if (amountCol && row[amountCol]) {
        const amt = parseFloat(row[amountCol])
        if (isNaN(amt) || amt <= 0) {
          rowErrors.push('【含稅總金額】必須為正數')
        }
      }

      // 日期格式驗證（簡單判斷）
      for (const dateField of ['開始日期', '截止日期']) {
        const col = columnMap[dateField]
        if (col && row[col]) {
          const val = row[col]
          if (!/^\d{4}[-/]\d{1,2}[-/]\d{1,2}$/.test(val)) {
            rowErrors.push(`【${dateField}】格式應為 YYYY-MM-DD`)
          }
        }
      }

      if (rowErrors.length > 0) {
        errors[idx] = rowErrors
      }
    })

    setValidationErrors(errors)

    const totalErrors = Object.values(errors).reduce((s, a) => s + a.length, 0)
    if (totalErrors > 0) {
      message.error(`驗證失敗：共 ${totalErrors} 個錯誤`)
      return false
    }

    message.success('驗證通過！')
    setStep(2)
    return true
  }

  // ── 真實導入（呼叫 createContract API）──────────────────────────────────
  const handleImport = async () => {
    setLoading(true)
    const results: ImportResultRow[] = []
    let successCount = 0

    // 只導入無錯誤的列
    const validRows = csvData.filter((_, idx) => !validationErrors[idx])

    for (let i = 0; i < validRows.length; i++) {
      const row = validRows[i]
      const contractName = row[columnMap['合約名稱']] || `第 ${i + 1} 筆`

      try {
        // 建立 payload（對應 ContractCreate 必填欄位）
        const payload: Record<string, any> = {
          contract_name: row[columnMap['合約名稱']],
          vendor_name: row[columnMap['廠商名稱']],
          start_date: row[columnMap['開始日期']]?.replace(/\//g, '-'),
          end_date: row[columnMap['截止日期']]?.replace(/\//g, '-'),
          total_amount_tax_included: parseFloat(row[columnMap['含稅總金額']]),
          // 選填欄位（若有對應才加入）
          ...(columnMap['合約編號'] && row[columnMap['合約編號']]
            ? { contract_id: row[columnMap['合約編號']] }
            : {}),
          ...(columnMap['合約類型'] && row[columnMap['合約類型']]
            ? { contract_type: row[columnMap['合約類型']] }
            : { contract_type: '服務合約' }),
          ...(columnMap['狀態'] && row[columnMap['狀態']]
            ? { contract_status: row[columnMap['狀態']] }
            : { contract_status: '草稿' }),
          ...(columnMap['負責部門'] && row[columnMap['負責部門']]
            ? { responsible_dept: row[columnMap['負責部門']] }
            : { responsible_dept: '' }),
          ...(columnMap['定價方式'] && row[columnMap['定價方式']]
            ? { pricing_method: row[columnMap['定價方式']] }
            : { pricing_method: '固定價格' }),
          ...(columnMap['預算年度'] && row[columnMap['預算年度']]
            ? { budget_year: parseInt(row[columnMap['預算年度']]) }
            : { budget_year: new Date().getFullYear() }),
          ...(columnMap['預算科目L1'] && row[columnMap['預算科目L1']]
            ? { budget_category_l1: row[columnMap['預算科目L1']] }
            : { budget_category_l1: '' }),
          ...(columnMap['預算科目L2'] && row[columnMap['預算科目L2']]
            ? { budget_category_l2: row[columnMap['預算科目L2']] }
            : { budget_category_l2: '' }),
          ...(columnMap['會計科目'] && row[columnMap['會計科目']]
            ? { accounting_code: row[columnMap['會計科目']] }
            : { accounting_code: '' }),
          ...(columnMap['備註'] && row[columnMap['備註']]
            ? { remarks: row[columnMap['備註']] }
            : {}),
        }

        await createContract(payload as any)
        successCount++
        results.push({
          rowIndex: i + 1,
          contract_name: contractName,
          status: 'success',
          message: '導入成功',
        })
      } catch (err: any) {
        const errMsg =
          err?.response?.data?.detail ||
          err?.message ||
          '未知錯誤'
        results.push({
          rowIndex: i + 1,
          contract_name: contractName,
          status: 'error',
          message: errMsg,
        })
      }
    }

    setImportResults(results)
    setImportSummary({
      success: successCount,
      failed: validRows.length - successCount,
      total: csvData.length,
    })
    setStep(3)
    setLoading(false)

    if (successCount > 0) {
      message.success(`成功導入 ${successCount} 筆合約`)
    }
    if (validRows.length - successCount > 0) {
      message.warning(`${validRows.length - successCount} 筆導入失敗，請查看結果報告`)
    }
  }

  // ── 重置 ─────────────────────────────────────────────────────────────────
  const handleReset = () => {
    setStep(0)
    setCsvData([])
    setHeaders([])
    setFile(null)
    setColumnMap({})
    setValidationErrors({})
    setImportResults([])
    setImportSummary(null)
  }

  // ── 結果表格欄位 ──────────────────────────────────────────────────────────
  const resultColumns: ColumnsType<ImportResultRow> = [
    { title: '列號', dataIndex: 'rowIndex', width: 70 },
    { title: '合約名稱', dataIndex: 'contract_name', ellipsis: true },
    {
      title: '結果',
      dataIndex: 'status',
      width: 90,
      render: (s) =>
        s === 'success' ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>成功</Tag>
        ) : (
          <Tag color="error" icon={<ExclamationCircleOutlined />}>失敗</Tag>
        ),
    },
    {
      title: '說明',
      dataIndex: 'message',
      ellipsis: true,
      render: (msg, rec) => (
        <span style={{ color: rec.status === 'error' ? '#FF4D4F' : '#52C41A' }}>{msg}</span>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 麵包屑 */}
      <Breadcrumb style={{ marginBottom: '24px' }}>
        <Breadcrumb.Item>
          <HomeOutlined />
        </Breadcrumb.Item>
        <Breadcrumb.Item>{NAV_GROUP.contract}</Breadcrumb.Item>
        <Breadcrumb.Item>資料導入</Breadcrumb.Item>
      </Breadcrumb>

      {/* 步驟指示 */}
      <Card style={{ marginBottom: '24px' }}>
        <Steps
          current={step}
          items={[
            { title: '上傳檔案', status: step > 0 ? 'finish' : 'process' },
            { title: '欄位對應', status: step > 1 ? 'finish' : step === 1 ? 'process' : 'wait' },
            { title: '驗證導入', status: step > 2 ? 'finish' : step === 2 ? 'process' : 'wait' },
            { title: '完成', status: step === 3 ? 'finish' : 'wait' },
          ]}
        />
      </Card>

      {/* Step 0: 上傳 */}
      {step === 0 && (
        <Card title="步驟 1：上傳檔案">
          <Alert
            message="支援格式：CSV（.csv）或 Excel（.xlsx / .xls）"
            description={
              <>
                <div>• 第一行為欄位名稱，之後為資料列</div>
                <div>• 必填欄位：合約名稱、廠商名稱、開始日期、截止日期、含稅總金額</div>
                <div>• 日期格式：YYYY-MM-DD 或 YYYY/MM/DD</div>
              </>
            }
            type="info"
            showIcon
            style={{ marginBottom: '16px' }}
          />
          <Upload.Dragger
            accept=".csv,.xlsx,.xls"
            beforeUpload={handleFileUpload}
            maxCount={1}
            fileList={file ? [file] : []}
            onRemove={handleReset}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined />
            </p>
            <p className="ant-upload-text">點擊或拖拽檔案到此區域上傳</p>
            <p className="ant-upload-hint">支援 CSV、Excel (.xlsx / .xls) 格式</p>
          </Upload.Dragger>
        </Card>
      )}

      {/* Step 1: 欄位對應 */}
      {step === 1 && headers.length > 0 && (
        <Card title="步驟 2：欄位對應">
          <Alert
            message="請將必填欄位對應到檔案中的標題"
            description="選擇各必填欄位對應的檔案欄位標題，若欄位名稱完全符合會自動對應"
            type="warning"
            showIcon
            style={{ marginBottom: '16px' }}
          />

          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            {REQUIRED_FIELDS.map((field) => {
              const autoMatch = headers.find((h) => h === field)
              if (autoMatch && !columnMap[field]) {
                setColumnMap((prev) => ({ ...prev, [field]: autoMatch }))
              }
              return (
                <Col xs={24} sm={12} lg={8} key={field}>
                  <div>
                    <Text strong>
                      {field} <span style={{ color: '#FF4D4F' }}>*</span>
                    </Text>
                    <Select
                      style={{ width: '100%', marginTop: '8px' }}
                      placeholder={`選擇對應 ${field}`}
                      value={columnMap[field] || undefined}
                      onChange={(value) =>
                        setColumnMap((prev) => ({ ...prev, [field]: value }))
                      }
                      allowClear
                    >
                      {headers.map((h) => (
                        <Select.Option key={h} value={h}>
                          {h}
                        </Select.Option>
                      ))}
                    </Select>
                  </div>
                </Col>
              )
            })}
          </Row>

          <Divider />

          <div style={{ marginBottom: '24px' }}>
            <Text strong>預覽資料（前 5 列）</Text>
            <Table
              style={{ marginTop: 12 }}
              dataSource={csvData.slice(0, 5).map((r, i) => ({ ...r, _key: i }))}
              rowKey="_key"
              columns={headers.map((h) => ({
                title: h,
                dataIndex: h,
                width: 130,
                ellipsis: { showTitle: false },
              }))}
              pagination={false}
              size="small"
              scroll={{ x: 'max-content' }}
            />
          </div>

          <Space>
            <Button onClick={() => setStep(0)}>上一步</Button>
            <Button type="primary" onClick={validateData}>
              驗證資料
            </Button>
          </Space>
        </Card>
      )}

      {/* Step 2: 驗證 & 導入 */}
      {step === 2 && (
        <Card title="步驟 3：驗證結果">
          <Alert
            message={`共 ${csvData.length} 筆資料，${Object.keys(validationErrors).length} 筆有錯誤`}
            type={Object.keys(validationErrors).length === 0 ? 'success' : 'warning'}
            showIcon
            style={{ marginBottom: '16px' }}
          />

          {Object.keys(validationErrors).length > 0 && (
            <Table
              columns={[
                {
                  title: '列號',
                  key: 'rowIdx',
                  width: 70,
                  render: (_: any, __: any, idx: number) => idx + 1,
                },
                {
                  title: '錯誤訊息',
                  key: 'errors',
                  dataIndex: 'errors',
                  render: (errors: string[]) => (
                    <div>
                      {errors.map((err, i) => (
                        <div key={i} style={{ color: '#FF4D4F' }}>⚠️ {err}</div>
                      ))}
                    </div>
                  ),
                },
              ]}
              dataSource={Object.entries(validationErrors).map(([rowIndex, errors]) => ({
                rowIndex: parseInt(rowIndex),
                errors,
                key: rowIndex,
              }))}
              pagination={false}
              size="small"
              style={{ marginBottom: '24px' }}
            />
          )}

          {Object.keys(validationErrors).length === 0 && (
            <Alert
              message={`將導入 ${csvData.length} 筆合約資料`}
              type="success"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Space>
            <Button onClick={() => setStep(1)}>上一步</Button>
            <Button
              type="primary"
              loading={loading}
              disabled={Object.keys(validationErrors).length > 0}
              onClick={handleImport}
            >
              開始導入
            </Button>
          </Space>
        </Card>
      )}

      {/* Step 3: 結果 */}
      {step === 3 && importSummary && (
        <Card title="步驟 4：導入完成">
          <Row gutter={16} style={{ marginBottom: '24px' }}>
            <Col xs={24} sm={8}>
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <div style={{ fontSize: 36, fontWeight: 'bold', color: '#52C41A' }}>
                  {importSummary.success}
                </div>
                <div style={{ color: '#666', marginTop: 4 }}>成功導入</div>
              </div>
            </Col>
            <Col xs={24} sm={8}>
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <div style={{ fontSize: 36, fontWeight: 'bold', color: '#FF4D4F' }}>
                  {importSummary.failed}
                </div>
                <div style={{ color: '#666', marginTop: 4 }}>導入失敗</div>
              </div>
            </Col>
            <Col xs={24} sm={8}>
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <div style={{ fontSize: 36, fontWeight: 'bold', color: '#4BA8E8' }}>
                  {importSummary.total}
                </div>
                <div style={{ color: '#666', marginTop: 4 }}>總筆數</div>
              </div>
            </Col>
          </Row>

          {importResults.length > 0 && (
            <Table
              columns={resultColumns}
              dataSource={importResults.map((r, i) => ({ ...r, key: i }))}
              pagination={{ pageSize: 20 }}
              size="small"
              style={{ marginBottom: '24px' }}
            />
          )}

          <Space>
            <Button onClick={handleReset} icon={<UploadOutlined />}>
              再次導入
            </Button>
          </Space>
        </Card>
      )}
    </div>
  )
}
