/**
 * SQL 查詢工具（SQL Console）— 僅系統管理員
 *
 * 中文名稱：SQL 查詢工具　英文名稱：SQL Console
 * 前端路徑：/settings/sql-console（系統設定 選單下）
 * 後端 router：backend/app/routers/sql_console.py（前綴 /api/v1/settings/sql-console）
 * 資料來源：直接查詢 Portal 的 PostgreSQL；無對應 Excel 表（本頁不產生業務資料）。
 * TAB：查詢 → 操作紀錄（工具頁，沒有 Dashboard TAB）
 *
 * 規則（後端強制，前端只是提示）：
 *   · 只能 SELECT／WITH／EXPLAIN 與「有 WHERE 的單表 DELETE」
 *   · 禁止 DROP／TRUNCATE／ALTER／CREATE／INSERT／UPDATE，禁止刪整張表（無 WHERE、WHERE 1=1）
 *   · DELETE 兩段式：先預覽筆數與資料（交易內執行後復原），輸入資料表名稱確認後才真的刪除；
 *     被刪資料完整備份在「操作紀錄」。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert, Button, Card, Col, Input, Modal, Row, Select, Space, Table, Tabs, Tag,
  Tooltip, Tree, Typography, message,
} from 'antd'
import type { TextAreaRef } from 'antd/es/input/TextArea'
import {
  CaretRightOutlined, ClearOutlined, ConsoleSqlOutlined, DatabaseOutlined,
  FileExcelOutlined, FileTextOutlined, FullscreenExitOutlined, FullscreenOutlined,
  ReloadOutlined, SafetyCertificateOutlined,
} from '@ant-design/icons'
import {
  sqlConsoleApi, sqlErrMsg,
  TableInfo, SelectResult, DeletePreview, SqlLogRow, SqlLogDetail,
} from '@/api/sqlConsole'

const { Text } = Typography

const MONO = 'Consolas, "Courier New", monospace'
const LIMIT_OPTIONS = [100, 500, 1000, 5000]

const ACTION_TAG: Record<string, { color: string; label: string }> = {
  select:  { color: 'blue',    label: '查詢' },
  export:  { color: 'cyan',    label: '匯出' },
  delete:  { color: 'red',     label: '刪除' },
  blocked: { color: 'orange',  label: '被擋下' },
}

function cell(v: any) {
  if (v === null || v === undefined) return <Text type="secondary" style={{ fontStyle: 'italic' }}>NULL</Text>
  if (typeof v === 'boolean') return String(v)
  return String(v)
}

/** 結果集 → AntD Table（欄名可能重複，所以用欄位順序當 key） */
function ResultTable({ columns, rows, height = 420 }: { columns: string[]; rows: any[][]; height?: number }) {
  const cols = useMemo(
    () => [
      {
        title: '#', key: '__no', width: 56, fixed: 'left' as const,
        render: (_: any, __: any, i: number) => <Text type="secondary">{i + 1}</Text>,
      },
      ...columns.map((c, i) => ({
        title: c, key: `c${i}`,
        width: Math.min(Math.max(c.length * 12 + 40, 110), 320),
        ellipsis: true,
        render: (_: any, row: any[]) => {
          const v = row[i]
          const t = v === null || v === undefined ? 'NULL' : String(v)
          return <span title={t} style={{ fontFamily: MONO, fontSize: 12 }}>{cell(v)}</span>
        },
      })),
    ],
    [columns],
  )
  return (
    <Table
      size="small"
      bordered
      columns={cols}
      dataSource={rows}
      rowKey={(_, i) => String(i)}
      scroll={{ x: 'max-content', y: height }}
      pagination={{ pageSize: 50, showSizeChanger: true, pageSizeOptions: [20, 50, 100, 200], showTotal: (t) => `共 ${t} 筆` }}
    />
  )
}

export default function SqlConsolePage() {
  const [sql, setSql] = useState('SELECT * FROM audit_sheet_departments ORDER BY id LIMIT 100')
  const [limit, setLimit] = useState(1000)
  const [running, setRunning] = useState(false)
  const [exporting, setExporting] = useState<'xlsx' | 'csv' | null>(null)
  const [result, setResult] = useState<SelectResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const taRef = useRef<TextAreaRef>(null)

  // 全畫面：蓋住側邊欄／標題列的固定版面（CSS），同時盡量進入瀏覽器全螢幕；Esc 離開
  const [full, setFull] = useState(false)
  const [vh, setVh] = useState(window.innerHeight)
  useEffect(() => {
    const onResize = () => setVh(window.innerHeight)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  useEffect(() => {
    // 使用者按 Esc 讓瀏覽器離開全螢幕時，同步收起版面
    const onFs = () => { if (!document.fullscreenElement) setFull(false) }
    document.addEventListener('fullscreenchange', onFs)
    return () => document.removeEventListener('fullscreenchange', onFs)
  }, [])
  useEffect(() => {
    if (!full) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setFull(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [full])
  const toggleFull = () => {
    if (!full) {
      setFull(true)
      document.documentElement.requestFullscreen?.().catch(() => { /* 被拒絕就只用版面全畫面 */ })
    } else {
      setFull(false)
      if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {})
    }
  }

  // 刪除確認
  const [pending, setPending] = useState<{ preview: DeletePreview; sql: string } | null>(null)
  const [confirmText, setConfirmText] = useState('')
  const [deleting, setDeleting] = useState(false)

  // 資料表結構
  const [tables, setTables] = useState<TableInfo[]>([])
  const [tablesLoading, setTablesLoading] = useState(false)
  const [tableSearch, setTableSearch] = useState('')

  // 操作紀錄
  const [tab, setTab] = useState('query')
  const [logs, setLogs] = useState<SqlLogRow[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [backup, setBackup] = useState<SqlLogDetail | null>(null)

  const loadTables = useCallback(async () => {
    setTablesLoading(true)
    try {
      const { data } = await sqlConsoleApi.tables()
      setTables(data.tables)
    } catch (e) {
      message.error(await sqlErrMsg(e))
    } finally {
      setTablesLoading(false)
    }
  }, [])

  const loadLogs = useCallback(async () => {
    setLogsLoading(true)
    try {
      const { data } = await sqlConsoleApi.logs(200)
      setLogs(data.logs)
    } catch (e) {
      message.error(await sqlErrMsg(e))
    } finally {
      setLogsLoading(false)
    }
  }, [])

  useEffect(() => { loadTables() }, [loadTables])
  useEffect(() => { if (tab === 'logs') loadLogs() }, [tab, loadLogs])

  /** 有選取文字就只跑選取的部分（同 pgAdmin），否則跑整個編輯區 */
  const currentSql = (): string => {
    const el = taRef.current?.resizableTextArea?.textArea
    if (el && el.selectionStart !== el.selectionEnd) {
      const picked = el.value.substring(el.selectionStart, el.selectionEnd).trim()
      if (picked) return picked
    }
    return sql.trim()
  }

  const run = async () => {
    const q = currentSql()
    if (!q) { message.warning('請輸入 SQL'); return }
    setRunning(true); setError(null); setNotice(null)
    try {
      const { data } = await sqlConsoleApi.execute(q, limit)
      if (data.kind === 'select') {
        setResult(data)
      } else if (data.kind === 'delete_preview') {
        setPending({ preview: data, sql: q })
        setConfirmText('')
      }
    } catch (e) {
      setResult(null)
      setError(await sqlErrMsg(e))
    } finally {
      setRunning(false)
    }
  }

  const confirmDelete = async () => {
    if (!pending) return
    setDeleting(true)
    try {
      const { data } = await sqlConsoleApi.execute(pending.sql, limit, pending.preview.token)
      if (data.kind === 'delete_done') {
        setNotice(`已從 ${data.table} 刪除 ${data.affected} 筆。被刪資料已備份在「操作紀錄」。`)
        message.success(`已刪除 ${data.affected} 筆`)
        setResult(null)
        setPending(null)
        loadTables()
      }
    } catch (e) {
      message.error(await sqlErrMsg(e), 6)
      setPending(null)
    } finally {
      setDeleting(false)
    }
  }

  const doExport = async (format: 'xlsx' | 'csv') => {
    const q = currentSql()
    if (!q) { message.warning('請輸入 SQL'); return }
    setExporting(format)
    try {
      const res = await sqlConsoleApi.exportFile(q, format)
      const cd: string = res.headers['content-disposition'] ?? ''
      const m = /filename="?([^";]+)"?/i.exec(cd)
      const filename = m?.[1] ?? `sql_result.${format}`
      const url = window.URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      if (res.headers['x-truncated'] === '1') {
        message.warning(`結果超過上限，只匯出前 ${res.headers['x-row-count']} 筆；請加上更精確的條件`, 6)
      } else {
        message.success(`已匯出 ${res.headers['x-row-count']} 筆`)
      }
    } catch (e) {
      message.error(await sqlErrMsg(e))
    } finally {
      setExporting(null)
    }
  }

  const insertAtCursor = (txt: string) => {
    const el = taRef.current?.resizableTextArea?.textArea
    if (!el) { setSql((s) => s + txt); return }
    const s = el.selectionStart ?? sql.length
    const e = el.selectionEnd ?? sql.length
    const next = sql.slice(0, s) + txt + sql.slice(e)
    setSql(next)
    requestAnimationFrame(() => {
      el.focus()
      el.selectionStart = el.selectionEnd = s + txt.length
    })
  }

  const treeData = useMemo(() => {
    const kw = tableSearch.trim().toLowerCase()
    return tables
      .filter((t) => !kw || t.table.toLowerCase().includes(kw) || t.columns.some((c) => c.name.toLowerCase().includes(kw)))
      .map((t) => ({
        key: `t:${t.table}`,
        title: (
          <span>
            <DatabaseOutlined style={{ marginRight: 4, color: '#4BA8E8' }} />
            <span style={{ fontFamily: MONO }}>{t.table}</span>
            <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>≈{t.est_rows.toLocaleString()}</Text>
          </span>
        ),
        children: t.columns.map((c) => ({
          key: `c:${t.table}.${c.name}`,
          isLeaf: true,
          title: (
            <span style={{ fontFamily: MONO, fontSize: 12 }}>
              {c.name} <Text type="secondary" style={{ fontSize: 11 }}>{c.type}</Text>
            </span>
          ),
        })),
      }))
  }, [tables, tableSearch])

  const openBackup = async (id: string) => {
    try {
      const { data } = await sqlConsoleApi.logDetail(id)
      setBackup(data)
    } catch (e) {
      message.error(await sqlErrMsg(e))
    }
  }

  const logColumns = [
    { title: '時間', dataIndex: 'created_at', width: 160 },
    { title: '帳號', dataIndex: 'email', width: 190, ellipsis: true },
    {
      title: '動作', dataIndex: 'action', width: 90,
      render: (a: string) => <Tag color={ACTION_TAG[a]?.color}>{ACTION_TAG[a]?.label ?? a}</Tag>,
    },
    { title: '資料表', dataIndex: 'table', width: 160, render: (v: string | null) => v ?? '—' },
    {
      title: '筆數', width: 80, align: 'right' as const,
      render: (_: any, r: SqlLogRow) => r.affected ?? r.row_count ?? '—',
    },
    {
      title: 'SQL／原因', key: 'sql',
      render: (_: any, r: SqlLogRow) => (
        <Tooltip title={<pre style={{ margin: 0, whiteSpace: 'pre-wrap', maxWidth: 560 }}>{r.sql}</pre>}>
          <div style={{ fontFamily: MONO, fontSize: 12, maxWidth: 520, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {r.sql}
          </div>
          {r.reason && <Text type="danger" style={{ fontSize: 12 }}>{r.reason}</Text>}
        </Tooltip>
      ),
    },
    {
      title: '', key: 'op', width: 150,
      render: (_: any, r: SqlLogRow) => (
        <Space size={4}>
          <Button size="small" type="link" onClick={() => { if (r.sql) { setSql(r.sql); setTab('query') } }}>載入</Button>
          {r.has_backup && <Button size="small" type="link" danger onClick={() => openBackup(r.id)}>被刪資料</Button>}
        </Space>
      ),
    },
  ]

  const queryTab = (
    <>
      <Input.TextArea
        ref={taRef}
        value={sql}
        onChange={(e) => setSql(e.target.value)}
        onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); run() } }}
        rows={full ? 12 : 9}
        spellCheck={false}
        placeholder="輸入 SQL，Ctrl+Enter 執行；選取一段文字則只執行選取的部分"
        style={{ fontFamily: MONO, fontSize: 13 }}
      />
      <Space wrap style={{ margin: '10px 0' }}>
        <Button type="primary" icon={<CaretRightOutlined />} loading={running} onClick={run}>執行</Button>
        <Button icon={<FileExcelOutlined />} loading={exporting === 'xlsx'} onClick={() => doExport('xlsx')}>匯出 Excel</Button>
        <Button icon={<FileTextOutlined />} loading={exporting === 'csv'} onClick={() => doExport('csv')}>匯出 CSV</Button>
        <Button icon={<ClearOutlined />} onClick={() => { setSql(''); setResult(null); setError(null); setNotice(null) }}>清除</Button>
        <span>
          <Text type="secondary">顯示上限　</Text>
          <Select size="middle" value={limit} onChange={setLimit} style={{ width: 100 }}
            options={LIMIT_OPTIONS.map((n) => ({ value: n, label: `${n} 筆` }))} />
        </span>
        <Text type="secondary" style={{ fontSize: 12 }}>Ctrl+Enter 執行｜匯出最多 50,000 筆</Text>
      </Space>

      {error && <Alert type="error" showIcon style={{ marginBottom: 10 }} message="執行失敗"
        description={<pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: MONO, fontSize: 12 }}>{error}</pre>} />}
      {notice && <Alert type="success" showIcon style={{ marginBottom: 10 }} message={notice} closable onClose={() => setNotice(null)} />}

      {result && (
        <>
          <div style={{ marginBottom: 8 }}>
            <Text strong>{result.row_count.toLocaleString()} 筆</Text>
            <Text type="secondary">　耗時 {result.elapsed_ms} ms</Text>
            {result.truncated && (
              <Tag color="orange" style={{ marginLeft: 8 }}>已達顯示上限 {result.limit} 筆，還有更多資料（可匯出，或加條件）</Tag>
            )}
          </div>
          <ResultTable columns={result.columns} rows={result.rows} height={full ? Math.max(300, vh - 470) : 420} />
        </>
      )}
    </>
  )

  return (
    <div style={full ? { position: 'fixed', inset: 0, zIndex: 999, background: '#f0f4f8', padding: 12, overflow: 'auto' } : undefined}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
      <Space align="center">
        <ConsoleSqlOutlined style={{ fontSize: 22, color: '#1B3A5C' }} />
        <Typography.Title level={4} style={{ margin: 0 }}>SQL 查詢工具</Typography.Title>
        <Tag icon={<SafetyCertificateOutlined />} color="red">僅系統管理員</Tag>
      </Space>
      <Button icon={full ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={toggleFull}>
        {full ? '離開全畫面（Esc）' : '全畫面'}
      </Button>
      </div>

      <Alert
        type="info" showIcon style={{ marginBottom: 12 }}
        message="安全規則"
        description={
          <div style={{ fontSize: 13 }}>
            只能執行 <b>SELECT</b> 與<b>有 WHERE 的 DELETE</b>（一次一個敘述）。
            禁止 DROP／TRUNCATE／ALTER／CREATE／INSERT／UPDATE，禁止刪整張表（沒有 WHERE、WHERE 1=1）；
            users、roles、role_permissions、system_settings、audit_logs 等資料表不可刪除。
            DELETE 會先預覽筆數（單次上限 1,000 筆），確認後才真的刪，被刪資料備份在「操作紀錄」。
            所有操作都會留下紀錄。
          </div>
        }
      />

      <Row gutter={12} wrap={false}>
        <Col flex="300px">
          <Card
            size="small" title="資料表" loading={tablesLoading}
            extra={<Button size="small" type="text" icon={<ReloadOutlined />} onClick={loadTables} />}
            styles={{ body: { padding: 8 } }}
          >
            <Input.Search size="small" allowClear placeholder="搜尋資料表／欄位" value={tableSearch}
              onChange={(e) => setTableSearch(e.target.value)} style={{ marginBottom: 6 }} />
            <div style={{ maxHeight: full ? vh - 220 : 640, overflow: 'auto' }}>
              <Tree
                blockNode
                treeData={treeData}
                selectable
                onSelect={(_, info) => {
                  const k = String(info.node.key)
                  if (k.startsWith('t:')) {
                    setSql(`SELECT * FROM ${k.slice(2)} LIMIT 100`)
                  } else if (k.startsWith('c:')) {
                    insertAtCursor(k.slice(2).split('.')[1])
                  }
                }}
              />
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>點資料表＝產生 SELECT；點欄位＝插入欄位名</Text>
          </Card>
        </Col>
        <Col flex="auto" style={{ minWidth: 0 }}>
          <Card size="small">
            <Tabs
              activeKey={tab}
              onChange={setTab}
              items={[
                { key: 'query', label: '查詢', children: queryTab },
                {
                  key: 'logs', label: '操作紀錄',
                  children: (
                    <>
                      <Button size="small" icon={<ReloadOutlined />} onClick={loadLogs} style={{ marginBottom: 8 }}>重新整理</Button>
                      <Table size="small" rowKey="id" loading={logsLoading} columns={logColumns} dataSource={logs}
                        pagination={{ pageSize: 20 }} scroll={{ x: 'max-content' }} />
                    </>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* DELETE 二次確認 */}
      <Modal
        open={!!pending}
        title={<span style={{ color: '#cf1322' }}>確認刪除資料</span>}
        width={860}
        onCancel={() => setPending(null)}
        okText="確認刪除"
        cancelText="取消"
        okButtonProps={{ danger: true, loading: deleting, disabled: !pending || confirmText.trim() !== pending.preview.table }}
        onOk={confirmDelete}
        maskClosable={false}
        destroyOnClose
      >
        {pending && (
          <>
            <Alert
              type="warning" showIcon style={{ marginBottom: 10 }}
              message={<span>將從 <b>{pending.preview.table}</b> 刪除 <b style={{ color: '#cf1322' }}>{pending.preview.affected}</b> 筆資料</span>}
              description={
                <div style={{ fontSize: 12 }}>
                  這是預覽（已復原，尚未真的刪除）。只計算此資料表本身的筆數；若有設定 ON DELETE CASCADE 的子表資料也會一併被刪。
                  確認後會把被刪的資料完整備份到「操作紀錄」。確認碼 {Math.round(pending.preview.expires_in / 60)} 分鐘內有效。
                </div>
              }
            />
            <pre style={{ background: '#f6f8fa', padding: 8, borderRadius: 4, fontFamily: MONO, fontSize: 12, maxHeight: 120, overflow: 'auto', whiteSpace: 'pre-wrap' }}>
              {pending.sql}
            </pre>
            {pending.preview.affected === 0 ? (
              <Alert type="info" message="沒有符合條件的資料，不會刪除任何東西。" />
            ) : (
              <>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  即將刪除的資料（前 {pending.preview.sample_size} 筆，共 {pending.preview.affected} 筆）
                </Text>
                <ResultTable columns={pending.preview.columns} rows={pending.preview.sample_rows} height={220} />
              </>
            )}
            <div style={{ marginTop: 12 }}>
              <Text>請輸入資料表名稱 <b style={{ fontFamily: MONO }}>{pending.preview.table}</b> 以確認：</Text>
              <Input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} style={{ marginTop: 6, fontFamily: MONO }}
                placeholder={pending.preview.table} autoFocus />
            </div>
          </>
        )}
      </Modal>

      {/* 被刪資料備份 */}
      <Modal open={!!backup} title={backup ? `被刪資料備份：${backup.table}（${backup.affected} 筆）` : ''}
        width={960} footer={null} onCancel={() => setBackup(null)} destroyOnClose>
        {backup && (
          <>
            <pre style={{ background: '#f6f8fa', padding: 8, borderRadius: 4, fontFamily: MONO, fontSize: 12, whiteSpace: 'pre-wrap' }}>{backup.sql}</pre>
            <ResultTable columns={backup.columns} rows={backup.rows} height={360} />
          </>
        )}
      </Modal>
    </div>
  )
}
