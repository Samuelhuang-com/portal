/**
 * OTA 來源設定
 * Route: /ota/sources    Permission: ota_sources_admin
 *
 * 規格書：`docs/SPEC_ota_reviews.md` §8.3、§6.6
 *
 * 【資料入口有兩條，兩條都要留】
 * ① 自動擷取（P2 起）：Booking 已支援，按「立即同步」或等每日 03:05 排程
 * ② CSV 匯入：OTA 改版／跳 CAPTCHA／Expedia 與 Tripadvisor（P3）時的入口
 *
 * ⚠️ ② **不會因為 ① 上線而移除**。爬蟲是整個模組最脆弱的一環，
 *    沒有 ② 的話爬蟲一掛整個模組就變空殼（規格書 §6.6）。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Select,
  Space, Switch, Table, Tag, Tooltip, Typography, Upload, message,
} from 'antd'
import {
  AppstoreOutlined, CloudDownloadOutlined, DeleteOutlined, DownloadOutlined,
  EditOutlined, InboxOutlined, LinkOutlined, PlusOutlined, ReloadOutlined,
  SyncOutlined, UnlockOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile } from 'antd/es/upload/interface'

import {
  createPlatform, createSource, deletePlatform, deleteSource, downloadBlob,
  downloadImportTemplate, fetchPlatformOptions, fetchPlatforms, fetchSources,
  fetchSyncLogs, fetchSyncStatus, forceUnlockSync, importReviewsCsv, runSync,
  toggleSource,
  updatePlatform, updateSource,
} from '@/api/ota'
import type {
  ImportResult, OtaPlatformInput, OtaPlatformRow, OtaSource, OtaSourceInput,
  PlatformOption, SyncLog, SyncStatusInfo,
} from '@/types/ota'

const { Text, Paragraph } = Typography
const { Dragger } = Upload

const STATUS_META: Record<string, { color: string; label: string }> = {
  never: { color: 'default', label: '尚未同步' },
  running: { color: 'processing', label: '同步中' },
  success: { color: 'success', label: '成功' },
  partial: { color: 'warning', label: '部分成功' },
  captcha: { color: 'warning', label: '被要求驗證' },
  failed: { color: 'error', label: '失敗' },
  // ⚠️ 灰色不是紅色：「這個平台還沒有擷取器」是設定事實，不是壞掉。
  //    畫成紅色「失敗」會讓人以為要去修 bug（2026-08-22 實際造成誤解）。
  unsupported: { color: 'default', label: '需手動匯入' },
}
const PLATFORM_COLOR: Record<string, string> = {
  booking: 'blue', expedia: 'gold', tripadvisor: 'green', agoda: 'purple', google: 'cyan',
}

const EMPTY_FORM: OtaSourceInput = {
  hotel_code: '', hotel_name: '', platform: 'booking', url: '',
  score_scale: 10, is_enabled: true, max_pages: 20, sort_order: 0,
}

const OtaSourcesPage: React.FC = () => {
  const [sources, setSources] = useState<OtaSource[]>([])
  const [platforms, setPlatforms] = useState<PlatformOption[]>([])
  const [logs, setLogs] = useState<SyncLog[]>([])
  const [loading, setLoading] = useState(false)

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<OtaSource | null>(null)
  // Modal 開啟時 Form 才掛載，所以表單初值要走 state 當 initialValues。
  // ⚠️ 型別用 `OtaSourceInput` 不要用 `Record<string, unknown>` ——
  //    interface 沒有 index signature，指派過去會 TS2345（跟 api/ota.ts 那次同一類）。
  const [formValues, setFormValues] = useState<OtaSourceInput>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<OtaSourceInput>()

  const [syncStatus, setSyncStatus] = useState<SyncStatusInfo | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [unlocking, setUnlocking] = useState(false)

  // ⭐ 平台維護（2026-08-23 平台改為資料驅動）
  const [platformModalOpen, setPlatformModalOpen] = useState(false)
  const [platformRows, setPlatformRows] = useState<OtaPlatformRow[]>([])
  const [editingPlatform, setEditingPlatform] = useState<OtaPlatformRow | null>(null)
  const [platformForm] = Form.useForm<OtaPlatformInput>()
  const [platformSaving, setPlatformSaving] = useState(false)

  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, l, st] = await Promise.all([
        fetchSources(), fetchSyncLogs(undefined, 20), fetchSyncStatus(),
      ])
      setSources(s)
      setLogs(l)
      setSyncStatus(st)
      setSyncing(st.is_running)
      // 後端順手收掉了孤兒 running 就講出來 ——
      // 狀態默默從「擷取中」變回「可同步」，人會以為是自己看錯。
      if (st.reaped?.length) {
        message.warning(
          `已自動收掉 ${st.reaped.length} 筆中斷未收尾的擷取紀錄`
          + `（${st.reaped[0].reason}）`,
        )
      }
    } catch {
      message.error('載入來源清單失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    fetchPlatformOptions().then(setPlatforms).catch(() => undefined)
  }, [load])

  /**
   * ⚠️ **不要在這裡用 `form.setFieldsValue()`**（2026-08-23 修）。
   *
   * Modal 有 `destroyOnClose`、Form 有 `preserve={false}` ——
   * 也就是說 **Modal 關著的時候 Form 根本沒有掛載**。
   * `openEdit` 同步呼叫 `setFieldsValue` 時，它設的是那個即將被銷毀的
   * 舊 form instance；等 Modal 開啟、Form 重新掛載時，讀的是
   * `initialValues`，於是欄位全空 —— 編輯任何一筆來源都看不到舊資料。
   *
   * 正確做法：把值放進 state 當成 `initialValues`。Form 掛載的那一刻
   * 才讀它，時序就對了。`key` 再保一層：不關 Modal 直接切換另一筆時
   * 強制重新掛載。
   */
  const openCreate = () => {
    setEditing(null)
    setFormValues(EMPTY_FORM)
    setModalOpen(true)
  }

  const openEdit = (source: OtaSource) => {
    setEditing(source)
    setFormValues({
      hotel_code: source.hotel_code, hotel_name: source.hotel_name,
      platform: source.platform, url: source.url, score_scale: source.score_scale,
      is_enabled: source.is_enabled, max_pages: source.max_pages,
      sort_order: source.sort_order,
    })
    setModalOpen(true)
  }

  const loadPlatforms = useCallback(async () => {
    try {
      setPlatformRows(await fetchPlatforms())
    } catch {
      message.error('載入平台清單失敗')
    }
  }, [])

  const openPlatforms = () => {
    setEditingPlatform(null)
    platformForm.resetFields()
    loadPlatforms()
    setPlatformModalOpen(true)
  }

  const editPlatform = (row: OtaPlatformRow) => {
    setEditingPlatform(row)
    platformForm.setFieldsValue({
      code: row.code, label: row.label, score_scale: row.score_scale,
      domains: row.domains, note: row.note, is_enabled: row.is_enabled,
    })
  }

  const savePlatform = async () => {
    try {
      const values = await platformForm.validateFields()
      setPlatformSaving(true)
      if (editingPlatform) await updatePlatform(editingPlatform.id, values)
      else await createPlatform(values)
      message.success(editingPlatform ? '已更新平台' : '已新增平台')
      setEditingPlatform(null)
      platformForm.resetFields()
      await loadPlatforms()
      // 平台變了，來源設定的下拉選單要跟著更新
      fetchPlatformOptions().then(setPlatforms).catch(() => undefined)
    } catch (err) {
      if ((err as { errorFields?: unknown }).errorFields) return
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || '儲存失敗')
    } finally {
      setPlatformSaving(false)
    }
  }

  const removePlatform = async (row: OtaPlatformRow) => {
    try {
      await deletePlatform(row.id)
      message.success('已刪除')
      await loadPlatforms()
      fetchPlatformOptions().then(setPlatforms).catch(() => undefined)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || '刪除失敗')
    }
  }

  const handleSave = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      if (editing) await updateSource(editing.id, values)
      else await createSource(values)
      message.success(editing ? '已更新' : '已新增')
      setModalOpen(false)
      load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (detail) message.error(detail)
      else if (!(err as { errorFields?: unknown }).errorFields) message.error('儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (source: OtaSource) => {
    try {
      await toggleSource(source.id)
      load()
    } catch {
      message.error('切換失敗')
    }
  }

  const handleDelete = async (source: OtaSource) => {
    try {
      await deleteSource(source.id)
      message.success('已刪除')
      load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || '刪除失敗')
    }
  }

  /**
   * 觸發擷取。
   *
   * ⚠️ 後端是**背景執行、立即回傳** —— 翻 20 頁可能好幾分鐘，
   *    同步等待一定會 HTTP 逾時。所以這裡靠輪詢看結果，
   *    不是等 runSync 的 Promise 拿到最終數字。
   */
  const handleSync = async (sourceIds: number[] = []) => {
    setSyncing(true)
    try {
      const res = await runSync(sourceIds)
      message.info(res.message)
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || (status === 409 ? '已有同步在執行中' : '觸發同步失敗'))
      setSyncing(false)
      return
    }

    // 每 8 秒輪詢一次，最多 10 分鐘（翻頁多的來源真的會跑這麼久）
    const started = Date.now()
    const timer = window.setInterval(async () => {
      try {
        const st = await fetchSyncStatus()
        setSyncStatus(st)
        if (!st.is_running || Date.now() - started > 10 * 60 * 1000) {
          window.clearInterval(timer)
          setSyncing(false)
          load()
        }
      } catch {
        window.clearInterval(timer)
        setSyncing(false)
      }
    }, 8000)
  }

  /**
   * 強制解除卡住的「擷取中」（2026-08-24）。
   *
   * ⚠️ 這顆按鈕在修的不是畫面問題。孤兒 `running` 會讓 `/sync/run`
   *    永遠回 409 —— 整個模組的同步從此按不下去，而畫面上只寫「擷取中…」，
   *    沒有任何線索告訴你為什麼。
   *
   * 只在真的偵測到 running 時才出現：平常看不到，需要時找得到。
   */
  const handleForceUnlock = async () => {
    setUnlocking(true)
    try {
      const res = await forceUnlockSync()
      message.success(res.message)
      setSyncing(false)
      await load()
    } catch {
      message.error('強制解除失敗')
    } finally {
      setUnlocking(false)
    }
  }

  const handleImport = async () => {
    const file = fileList[0]?.originFileObj
    if (!file) {
      message.warning('請先選擇 CSV 檔案')
      return
    }
    setImporting(true)
    setImportResult(null)
    try {
      const result = await importReviewsCsv(file)
      setImportResult(result)
      if (result.errors.length === 0) {
        message.success(`匯入完成：新增 ${result.inserted}、更新 ${result.updated}`)
        setFileList([])
        load()
      }
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || '匯入失敗')
    } finally {
      setImporting(false)
    }
  }

  // 平台已有擷取器、且來源為啟用中 → 可自動同步
  const supported = syncStatus?.supported_platforms ?? []
  const syncable = sources.filter((x) => x.is_enabled && supported.includes(x.platform))
  const unsupported = sources.filter((x) => x.is_enabled && !supported.includes(x.platform))

  const columns: ColumnsType<OtaSource> = [
    { title: '飯店', dataIndex: 'hotel_name', width: 110,
      render: (name: string, row) => name || row.hotel_code },
    {
      title: 'OTA', dataIndex: 'platform', width: 120,
      render: (platform: string) => (
        <Tag color={PLATFORM_COLOR[platform] || 'default'}>
          {platforms.find((p) => p.value === platform)?.label || platform}
        </Tag>
      ),
    },
    {
      title: '分制', dataIndex: 'score_scale', width: 70, align: 'center',
      render: (scale: number) => (
        <Tooltip title={scale === 5
          ? '原站為 5 分制，寫入時自動 ×2 換算成 10 分制'
          : '原站即為 10 分制'}>
          <span>{scale} 分制</span>
        </Tooltip>
      ),
    },
    {
      title: '評論頁', dataIndex: 'url', ellipsis: true,
      render: (url: string) => (
        <a href={url} target="_blank" rel="noopener noreferrer"
           style={{ color: '#4BA8E8' }}>
          <LinkOutlined /> {url}
        </a>
      ),
    },
    {
      title: '已收錄 / 站方公布', key: 'counts', width: 190, align: 'center',
      render: (_, row) => {
        const site = row.review_count_site
        const gap = site !== null && site > 0 && row.stored_count < site * 0.8
        // ⚠️ 差距大時**要說出原因**（2026-08-23）。原本只有一句「多半是翻頁沒抓完」，
        //    看到紅字的人不知道要去改哪裡 —— 實測就是四筆來源全部卡在
        //    max_pages=20（Booking 停在 210、Agoda 停在 500 上下），
        //    使用者跑了 --force 也沒用，因為那只解除當日限制。
        //
        //    ⚠️ 這裡把「還需要幾頁」算給他看：症狀 → 原因 → 數字，一次到位。
        const perPage = row.max_pages > 0 ? row.stored_count / row.max_pages : 0
        const needPages = gap && perPage > 0 && site
          ? Math.ceil(site / perPage) : 0
        return (
          <Tooltip
            title={gap ? (
              <span>
                只抓到站方公布的 {site ? Math.round(row.stored_count / site * 100) : 0}%。
                <br />
                目前翻頁上限 <b>{row.max_pages}</b> 頁，
                每頁約 {perPage.toFixed(0)} 則 —— 抓完約需 <b>{needPages}</b> 頁。
                <br />
                <br />
                ⚠️ 調高上限**不會**讓每日同步變慢：翻頁有「連續 2 頁沒有新評論就停」
                的條件，回補完成後每天只會翻 2~3 頁。
                <br />
                ⚠️ CLI 的 <code>--force</code> 只解除「每日一次」限制，
                不會改翻頁上限。要一次性回補請用
                <code>--max-pages {Math.min(needPages + 10, 500)}</code>。
              </span>
            ) : '已收錄筆數（不含跨站重複）'}
          >
            <Space direction="vertical" size={0}>
              <span style={{ color: gap ? '#cf1322' : undefined }}>
                {row.stored_count.toLocaleString()} / {site === null ? '—' : site.toLocaleString()}
              </span>
              {gap && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  上限 {row.max_pages} 頁・需約 {needPages} 頁
                </Text>
              )}
            </Space>
          </Tooltip>
        )
      },
    },
    {
      title: '狀態', dataIndex: 'last_status', width: 120, align: 'center',
      render: (status: string, row) => {
        // 平台沒有擷取器時，不論資料庫存的是什麼舊狀態，一律顯示「需手動匯入」。
        // 使用者是在問「為什麼失敗」，答案是「這個平台還沒做」，不是「壞了」。
        const effective = supported.length && !supported.includes(row.platform)
          ? 'unsupported' : status
        const meta = STATUS_META[effective] || STATUS_META.never
        const hint = effective === 'unsupported'
          ? `「${row.platform}」尚無自動擷取器。請用下方 CSV 匯入，`
            + `或用 ota_scraper_cli 的 --import-html 匯入瀏覽器另存的 HTML 檔。`
          : row.last_message || (row.last_sync_at ? `最後同步：${row.last_sync_at}` : '')
        return (
          <Tooltip title={hint}>
            <Tag color={row.is_enabled ? meta.color : 'default'}>
              {row.is_enabled ? meta.label : '已停用'}
            </Tag>
          </Tooltip>
        )
      },
    },
    {
      title: '啟用', dataIndex: 'is_enabled', width: 70, align: 'center',
      render: (enabled: boolean, row) => (
        <Switch size="small" checked={enabled} onChange={() => handleToggle(row)} />
      ),
    },
    {
      title: '操作', key: 'action', width: 160, align: 'center',
      render: (_, row) => (
        <Space size={4}>
          {syncStatus?.scraper_available
            && syncStatus.supported_platforms.includes(row.platform) && (
            <Tooltip title={row.is_enabled ? '只擷取這個來源' : '來源已停用'}>
              <Button
                size="small"
                icon={<CloudDownloadOutlined />}
                onClick={() => handleSync([row.id])}
                disabled={syncing || !row.is_enabled}
              />
            </Tooltip>
          )}
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>編輯</Button>
          <Popconfirm
            title="刪除這個來源？"
            description="底下若已有評論會被拒絕。要停止同步請改用「停用」。"
            onConfirm={() => handleDelete(row)}
            okText="刪除" cancelText="取消"
          >
            <Button size="small" danger>刪除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      {unsupported.length > 0 && (
        <Alert
          type="warning" showIcon style={{ marginBottom: 16 }}
          message={`有 ${unsupported.length} 個來源的平台尚未支援自動擷取`}
          description={
            <span>
              {unsupported.map((x) => x.hotel_name || x.hotel_code).join('、')} 的
              {' '}{[...new Set(unsupported.map((x) => (
                platforms.find((p) => p.value === x.platform)?.label || x.platform
              )))].join('／')}
              {' '}目前沒有自動擷取器。這些來源請用下方的 <b>CSV 匯入</b>，或用
              {' '}<code>ota_scraper_cli --import-html</code> 匯入瀏覽器另存的 HTML 檔 ——
              兩者走的都是與爬蟲完全相同的正規化與去重管線，資料品質一致。
              <br />
              這類來源的每日排程會**直接略過**（記為提醒而非錯誤），不會讓同步狀態變成失敗。
            </span>
          }
        />
      )}

      {syncStatus?.browser_mode === 'auto' && (
        <Alert
          type="info" showIcon style={{ marginBottom: 16 }}
          message="首次執行擷取時，系統會自動判斷這台機器能不能跑 Booking"
          description={
            <span>
              Booking 對無頭瀏覽器偵測較嚴。目前是 <b>auto</b> 模式：先試無頭，
              抓不到就自動改開可見視窗。若兩者都失敗（多半是以 Windows 服務執行、
              沒有桌面工作階段），同步紀錄的錯誤訊息會直接寫明改用
              <code> ota_scraper_cli.py </code>＋工作排程器的做法。
            </span>
          }
        />
      )}

      <Card
        size="small"
        title="OTA 來源"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
            {syncStatus?.scraper_available && (
              <Button
                icon={syncing ? <SyncOutlined spin /> : <CloudDownloadOutlined />}
                onClick={() => handleSync()}
                loading={syncing}
                disabled={syncable.length === 0}
              >
                {syncing ? '擷取中…' : '立即同步全部'}
              </Button>
            )}
            {/* ⚠️ 只在真的偵測到 running 時出現（2026-08-24）。
                孤兒 running 會讓 /sync/run 永遠回 409 —— 同步從此按不下去，
                而畫面上只寫「擷取中…」，沒有任何線索指向原因。
                平常看不到這顆，卡住時才找得到。 */}
            {syncing && (
              <Popconfirm
                title="強制解除「擷取中」"
                description={
                  <span style={{ display: 'inline-block', maxWidth: 320 }}>
                    會把所有還掛著 <code>running</code> 的擷取紀錄標成失敗。
                    <br />已經抓進來的評論<b>不會</b>被刪除。
                    <br /><br />⚠️ 若同步其實還在跑，請等它跑完再按 ——
                    兩個行程同時擷取同一批來源會互相排隊。
                  </span>
                }
                okText="確定解除"
                cancelText="取消"
                onConfirm={handleForceUnlock}
              >
                <Button danger icon={<UnlockOutlined />} loading={unlocking}>
                  強制解除
                </Button>
              </Popconfirm>
            )}
            <Button icon={<AppstoreOutlined />} onClick={openPlatforms}>平台管理</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增來源</Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Table<OtaSource>
          rowKey="id" size="small" loading={loading}
          columns={columns} dataSource={sources} pagination={false}
        />
      </Card>

      <Card size="small" title="CSV 匯入" style={{ marginBottom: 16 }}>
        <Paragraph type="secondary" style={{ fontSize: 13 }}>
          匯入前請先建立對應的 OTA 來源（依「飯店代碼 + OTA 平台」比對）；
          對不到來源的資料列會被略過並列在下方，不會讓整批匯入失敗。
          重複匯入同一個檔案是安全的 —— 相同評論會更新而非新增，
          且**已填的警示處理狀態不會被覆蓋**。
        </Paragraph>

        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Button
            icon={<DownloadOutlined />}
            onClick={async () => {
              try {
                downloadBlob(await downloadImportTemplate(), 'OTA評論匯入範本.csv')
              } catch { message.error('下載範本失敗') }
            }}
          >
            下載 CSV 範本
          </Button>

          <Dragger
            accept=".csv"
            maxCount={1}
            fileList={fileList}
            beforeUpload={() => false}
            onChange={({ fileList: fl }) => { setFileList(fl.slice(-1)); setImportResult(null) }}
            onRemove={() => { setFileList([]); setImportResult(null) }}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">點擊或拖曳 CSV 檔案到此處</p>
            <p className="ant-upload-hint">
              編碼支援 UTF-8 / UTF-8 BOM / Big5（cp950），上限 10MB
            </p>
          </Dragger>

          <Button
            type="primary" onClick={handleImport}
            loading={importing} disabled={fileList.length === 0}
          >
            開始匯入
          </Button>

          {importResult && (
            <Alert
              type={importResult.errors.length ? 'error' : 'success'}
              showIcon
              message={
                importResult.errors.length
                  ? '匯入失敗'
                  : `匯入完成：共 ${importResult.total_rows} 列，`
                    + `新增 ${importResult.inserted}、更新 ${importResult.updated}、`
                    + `略過 ${importResult.skipped}、標記跨站重複 ${importResult.marked_duplicate}`
              }
              description={
                <>
                  {importResult.errors.map((e) => (
                    <div key={e} style={{ color: '#cf1322' }}>{e}</div>
                  ))}
                  {importResult.warnings.length > 0 && (
                    <div style={{ marginTop: importResult.errors.length ? 8 : 0 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        以下是提醒（不影響其他資料列）：
                      </Text>
                      {importResult.warnings.slice(0, 20).map((w) => (
                        <div key={w} style={{ fontSize: 12, color: '#8c8c8c' }}>・{w}</div>
                      ))}
                      {importResult.warnings.length > 20 && (
                        <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                          ⋯ 另有 {importResult.warnings.length - 20} 項
                        </div>
                      )}
                    </div>
                  )}
                </>
              }
            />
          )}
        </Space>
      </Card>

      <Card size="small" title="最近同步／匯入紀錄">
        <Table<SyncLog>
          rowKey="id" size="small" dataSource={logs} pagination={false}
          columns={[
            { title: '時間', dataIndex: 'started_at', width: 160 },
            { title: '飯店', dataIndex: 'hotel_name', width: 100 },
            { title: 'OTA', dataIndex: 'platform_label', width: 110 },
            {
              title: '方式', dataIndex: 'trigger_type', width: 80,
              render: (t: string) => ({ schedule: '排程', manual: '手動', import: 'CSV 匯入' }[t] || t),
            },
            {
              title: '結果', dataIndex: 'status', width: 100,
              render: (s: string) => {
                const meta = STATUS_META[s] || STATUS_META.never
                return <Tag color={meta.color}>{meta.label}</Tag>
              },
            },
            {
              title: '新增 / 更新 / 略過', key: 'counts', width: 150,
              render: (_, row) => `${row.inserted_count} / ${row.updated_count} / ${row.skipped_count}`,
            },
            {
              // ⚠️ warnings 用灰字不用紅字：那是「某幾筆略過」不是失敗。
              //    畫成紅色久了就沒人看了（CLAUDE.md §9 規則 8）
              title: '訊息', key: 'message',
              render: (_, row) => (
                row.error_message
                  ? <Text type="danger" style={{ fontSize: 12 }}>{row.error_message}</Text>
                  : row.warnings.length
                    ? (
                      <Tooltip title={row.warnings.join('\n')}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {row.warnings.length} 項提醒
                        </Text>
                      </Tooltip>
                    )
                    : <Text type="secondary">—</Text>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={modalOpen}
        title={editing ? '編輯 OTA 來源' : '新增 OTA 來源'}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        okText="儲存" cancelText="取消"
        destroyOnClose
      >
        <Form
          form={form} layout="vertical" preserve={false}
          key={editing?.id ?? 'new'}
          initialValues={formValues}
        >
          <Form.Item
            name="hotel_code" label="飯店代碼"
            rules={[{ required: true, message: '請輸入飯店代碼' }]}
            extra="與 OPERA 的 property_code 對齊（例：HANNS、HANNS_SUMMER），所有統計以此分組"
          >
            <Input placeholder="HANNS" />
          </Form.Item>
          <Form.Item name="hotel_name" label="飯店顯示名稱">
            <Input placeholder="瀚寓" />
          </Form.Item>
          <Form.Item
            name="platform" label="OTA 平台"
            rules={[{ required: true, message: '請選擇平台' }]}
          >
            <Select
              // ⚠️ 沒有擷取器的平台仍然可選（可以用 CSV／HTML 檔匯入，建檔有意義），
              //    但必須標示清楚 —— 否則使用者選了 Agoda 建完來源，
              //    只會拿到一個看不懂的紅色「失敗」。
              options={platforms.map((p) => ({
                value: p.value,
                label: p.has_parser ? p.label : `${p.label}（無自動擷取，需手動匯入）`,
              }))}
              onChange={(value) => {
                const preset = platforms.find((p) => p.value === value)
                if (preset) form.setFieldValue('score_scale', preset.score_scale)
              }}
            />
          </Form.Item>
          <Form.Item
            name="url" label="評論列表頁網址"
            rules={[
              { required: true, message: '請輸入網址' },
              { pattern: /^https?:\/\//, message: '請輸入完整的 http/https 網址' },
            ]}
            extra="請貼「評論列表頁」，不是搜尋結果頁"
          >
            <Input placeholder="https://www.booking.com/reviews/tw/hotel/xxx.zh-tw.html" />
          </Form.Item>
          <Form.Item
            name="score_scale" label="分制"
            extra="Booking／Agoda 為 10 分制，Tripadvisor／Google 為 5 分制（會自動 ×2 換算）"
          >
            <Select options={[{ value: 10, label: '10 分制' }, { value: 5, label: '5 分制' }]} />
          </Form.Item>
          <Form.Item
            name="max_pages" label="翻頁上限"
            extra="P2 爬蟲上線後生效。每頁約 10 則，20 頁約 200 則"
          >
            <InputNumber min={1} max={200} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="is_enabled" label="啟用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
      {/* ⭐ 平台管理（2026-08-23 平台改為資料驅動） */}
      <Modal
        open={platformModalOpen}
        title="平台管理"
        width={860}
        onCancel={() => { setPlatformModalOpen(false); setEditingPlatform(null) }}
        footer={<Button onClick={() => { setPlatformModalOpen(false); setEditingPlatform(null) }}>關閉</Button>}
      >
        <Alert
          type="info" showIcon style={{ marginBottom: 16 }}
          message="沒有自動擷取器，不代表這個平台不能用"
          description={
            <span>
              有代碼／名稱／分制就能建來源、匯入 CSV、跑分析、進統計。
              「自動擷取器」是另一件事，而且**未必做得到** ——
              Tripadvisor 與 Expedia 都被站方擋，現在就是走
              CSV 匯入或 <Text code>--import-html</Text>。
              <br />
              ⚠️ <b>代碼建立後不可修改</b>，它會寫進每一筆評論並當成統計的分組鍵。
            </span>
          }
        />

        <Table<OtaPlatformRow>
          rowKey="id" size="small" pagination={false}
          dataSource={platformRows}
          style={{ marginBottom: 20 }}
          columns={[
            {
              title: '代碼', dataIndex: 'code', width: 120,
              render: (v: string, row) => (
                <Space size={4}>
                  <Text code>{v}</Text>
                  {row.is_builtin && <Tag>內建</Tag>}
                </Space>
              ),
            },
            { title: '顯示名稱', dataIndex: 'label', width: 130 },
            {
              title: '分制', dataIndex: 'score_scale', width: 70,
              render: (v: number) => `${v} 分制`,
            },
            {
              title: '網域', dataIndex: 'domains',
              render: (v: string) => (
                v
                  ? <Space size={4} wrap>{v.split(',').map((d) => <Tag key={d}>{d}</Tag>)}</Space>
                  : <Text type="secondary">—（不做網址比對）</Text>
              ),
            },
            {
              title: '自動擷取', dataIndex: 'has_parser', width: 100,
              render: (v: boolean) => (
                v ? <Tag color="success">有擷取器</Tag>
                  : <Tooltip title="資料走 CSV 匯入或 --import-html">
                      <Tag>需手動匯入</Tag>
                    </Tooltip>
              ),
            },
            {
              title: '狀態', dataIndex: 'is_enabled', width: 70,
              render: (v: boolean) => (v ? <Tag color="blue">啟用</Tag> : <Tag>停用</Tag>),
            },
            {
              title: '操作', width: 110, align: 'right',
              render: (_, row) => (
                <Space size={4}>
                  <Button size="small" icon={<EditOutlined />} onClick={() => editPlatform(row)} />
                  <Popconfirm
                    title={`刪除「${row.label}」？`}
                    description={row.is_builtin ? '內建平台無法刪除' : '底下還有來源的話會被擋下'}
                    onConfirm={() => removePlatform(row)}
                    okText="刪除" cancelText="取消" disabled={row.is_builtin}
                  >
                    <Button size="small" danger icon={<DeleteOutlined />} disabled={row.is_builtin} />
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />

        <Card size="small" title={editingPlatform ? `修改「${editingPlatform.label}」` : '新增平台'}>
          <Form form={platformForm} layout="vertical" initialValues={{ score_scale: 10, is_enabled: true }}>
            <Space align="start" size={12} style={{ display: 'flex' }}>
              <Form.Item
                name="code" label="代碼" style={{ width: 180 }}
                rules={editingPlatform ? [] : [
                  { required: true, message: '請輸入代碼' },
                  { pattern: /^[a-z0-9_]+$/, message: '只能用小寫英數與底線' },
                ]}
                extra={editingPlatform ? '不可修改' : '例：hotels_com'}
              >
                <Input placeholder="hotels_com" disabled={!!editingPlatform} />
              </Form.Item>
              <Form.Item
                name="label" label="顯示名稱" style={{ width: 180 }}
                rules={[{ required: true, message: '請輸入顯示名稱' }]}
              >
                <Input placeholder="Hotels.com" />
              </Form.Item>
              <Form.Item name="score_scale" label="分制" style={{ width: 110 }}>
                <Select
                  options={[
                    { value: 10, label: '10 分制' },
                    { value: 5, label: '5 分制' },
                  ]}
                />
              </Form.Item>
              <Form.Item name="is_enabled" label="啟用" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Space>
            <Form.Item
              name="domains" label="網域"
              extra="逗號分隔。填了就會擋「網址與平台對不上」的來源；留空則不比對。例：hotels.com, tw.hotels.com"
            >
              <Input placeholder="hotels.com, tw.hotels.com" />
            </Form.Item>
            <Form.Item name="note" label="備註" extra="例：Expedia 集團，站方擋自動存取，走 HTML 匯入">
              <Input placeholder="選填" />
            </Form.Item>
            <Space>
              <Button type="primary" loading={platformSaving} onClick={savePlatform}>
                {editingPlatform ? '儲存' : '新增'}
              </Button>
              {editingPlatform && (
                <Button onClick={() => { setEditingPlatform(null); platformForm.resetFields() }}>
                  取消修改
                </Button>
              )}
            </Space>
          </Form>
        </Card>
      </Modal>

    </div>
  )
}

export default OtaSourcesPage
