/**
 * 整棟巡檢 — 共用「樓層巡檢紀錄」清單 + 明細 Drawer
 *
 * 兩個地方共用，勿在任一端重刻：
 *   1. pages/FullBuildingInspection/index.tsx        Dashboard 頁的 RF/B4F/B2F/B1F 四個 Tab
 *   2. pages/FullBuildingInspection/InspectionFloorPage.tsx  四條獨立路由的「巡檢紀錄」Tab
 *
 * 明細 Drawer 依 CLAUDE.md §7 / WORK_JOURNAL_SPEC.md §9 實作
 * （寬 480px、標題列含 Ragic 連結、分基本欄位與明細兩區）。
 *
 * ⚠️ 資料來源的 API prefix 是 /mall/{key}-inspection，不是 /full-building-inspection/
 *    （見 api/fullBuildingInspection.ts 內的說明）。
 */
import { useState, useCallback, useEffect } from 'react'
import {
  Row, Col, Table, Tag, Button, Space, Typography,
  Alert, DatePicker, Badge, message, Progress, Drawer, Descriptions,
  Image, Divider, Spin,
} from 'antd'
import { ReloadOutlined, LinkOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { FULL_BUILDING_INSPECTION_SHEETS } from '@/constants/fullBuildingInspection'
import {
  fetchFloorBatches,
  fetchFloorBatchDetail,
  fetchFloorBatchImages,
  type FloorBatchRow,
  type FloorBatchDetail,
  type FloorImage,
} from '@/api/fullBuildingInspection'

const { Text } = Typography

// ── Ragic 動態欄位偵測的副作用：非設備欄位也會被收成 item ────────────────────
//
// 各樓層 sync 的 _extract_check_items() 只排除場次 metadata（巡檢人員／開始／
// 結束／工時），其餘欄位一律當成設備巡檢項目。於是「拍照」「拍照1」「拍照2」
// 「異常說明」「建立日期」「建立年份」「月份」也進了 *_inspection_item，而
// _normalize_result_status() 對「非空但不在對照表裡」的值一律判成 abnormal ——
// 「2026/01/01」「檔名.jpg」就這樣被畫成紅色的「異常」Tag。
//
// 這裡在**呈現層**把它們分流：附件欄位走附圖區，附註欄位走「其他欄位」區並以
// 純文字顯示（不套狀態色）。
//
// ⚠️ 這份規則與後端 app/services/inspection_field_rules.py **必須等價**，
//    兩邊要一起改，否則會出現「明細把檔名當成異常狀態」或「附圖區空白」。
// ⚠️ 不可改回寫死的欄位名清單：Ragic 的附件欄位命名沒有統一（拍照／拍照1／
//    拍照2／照片／附件…），Sheet 新增一個「拍照3」就會靜默漏掉，
//    而症狀只是「多一個紅色異常 Tag」，沒有人會發現。
//    值規則（副檔名）是名稱規則的保險：欄位叫什麼都好，值長得像檔名就是附件。
const IMAGE_FIELD_RE = /^(拍照|照片|相片|圖片|圖檔|附件|附圖|上傳圖片)\s*\d*$/
const FILE_VALUE_RE  = /\.(jpe?g|png|gif|bmp|webp|heic|heif|pdf)\s*$/i
const META_FIELD_RE  = /^(異常說明|備註|說明|建立日期|建立年份|建立時間|年份|月份)\s*\d*$/

function isImageField(itemName: string, resultRaw: string): boolean {
  if (IMAGE_FIELD_RE.test((itemName ?? '').trim())) return true
  const value = (resultRaw ?? '').trim()
  if (!value) return false
  return value.split(/[\n,;]/).some((part) => FILE_VALUE_RE.test(part.trim()))
}

const isMetaField = (itemName: string) => META_FIELD_RE.test((itemName ?? '').trim())

export default function FloorInspectionList({ sheetKey }: { sheetKey: string }) {
  const sheet = FULL_BUILDING_INSPECTION_SHEETS[sheetKey]
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [loading,   setLoading]   = useState(false)
  const [rows,      setRows]      = useState<FloorBatchRow[]>([])
  const [error,     setError]     = useState<string | null>(null)

  // ── 明細 Drawer（CLAUDE.md §7 強制規範）─────────────────────────────────
  const [drawerOpen,   setDrawerOpen]   = useState(false)
  const [detail,       setDetail]       = useState<FloorBatchDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [images,       setImages]       = useState<FloorImage[]>([])
  const [imagesLoading, setImagesLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setRows(await fetchFloorBatches(sheetKey, yearMonth))
    } catch (e) {
      setRows([])
      setError(e instanceof Error ? e.message : '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [sheetKey, yearMonth])

  useEffect(() => { load() }, [load])

  const openDetail = useCallback(async (ragicId: string) => {
    setDrawerOpen(true)
    setDetailLoading(true)
    setDetail(null)
    setImages([])
    try {
      setDetail(await fetchFloorBatchDetail(sheetKey, ragicId))
    } catch {
      message.error('載入場次明細失敗')
      setDrawerOpen(false)
      setDetailLoading(false)
      return
    }
    setDetailLoading(false)

    // 附圖另外抓，失敗不影響明細本體（沒有附圖是常態，不該跳錯誤訊息）
    setImagesLoading(true)
    try {
      setImages(await fetchFloorBatchImages(sheetKey, ragicId))
    } catch {
      setImages([])
    } finally {
      setImagesLoading(false)
    }
  }, [sheetKey])

  // Ragic 單筆連結：常數裡的 ragicUrl 帶了 ?PAGEID=，要去掉才能接 record id
  const ragicRecordUrl = (ragicId: string) =>
    sheet ? `${sheet.ragicUrl.split('?')[0]}/${ragicId}` : ''

  const columns = [
    {
      title: '巡檢日期',
      width: 110,
      render: (_: unknown, r: FloorBatchRow) => r.batch.inspection_date || '—',
      sorter: (a: FloorBatchRow, b: FloorBatchRow) =>
        a.batch.inspection_date.localeCompare(b.batch.inspection_date),
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '巡檢人員',
      width: 100,
      render: (_: unknown, r: FloorBatchRow) => r.batch.inspector_name || '—',
    },
    {
      title: '狀態',
      width: 90,
      render: (_: unknown, r: FloorBatchRow) => {
        const k = r.kpi
        if (k.abnormal > 0) return <Tag color="#FF4D4F">有異常</Tag>
        if (k.pending  > 0) return <Tag color="#FAAD14">待處理</Tag>
        if (k.unchecked === 0 && k.total > 0) return <Tag color="#52C41A">已完成</Tag>
        return <Tag color="#4BA8E8">巡檢中</Tag>
      },
    },
    {
      title: '巡檢進度',
      width: 200,
      render: (_: unknown, r: FloorBatchRow) => (
        <div>
          <Progress
            percent={r.kpi.completion_rate}
            size="small"
            strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
            format={() => `${r.kpi.completion_rate}%`}
          />
          <Text type="secondary" style={{ fontSize: 11 }}>
            {r.kpi.total - r.kpi.unchecked} / {r.kpi.total} 已巡檢
          </Text>
        </div>
      ),
    },
    {
      title: '工時',
      width: 90,
      render: (_: unknown, r: FloorBatchRow) =>
        r.batch.work_hours || <Text type="secondary">—</Text>,
    },
    {
      title: '異常',
      width: 65,
      align: 'center' as const,
      render: (_: unknown, r: FloorBatchRow) =>
        r.kpi.abnormal > 0
          ? <Badge count={r.kpi.abnormal} color="#FF4D4F" />
          : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理',
      width: 65,
      align: 'center' as const,
      render: (_: unknown, r: FloorBatchRow) =>
        r.kpi.pending > 0
          ? <Badge count={r.kpi.pending} color="#FAAD14" />
          : <Text type="secondary">—</Text>,
    },
  ]

  const STATUS_TAG: Record<string, { color: string; label: string }> = {
    normal:    { color: '#52C41A', label: '正常' },
    abnormal:  { color: '#FF4D4F', label: '異常' },
    pending:   { color: '#FAAD14', label: '待處理' },
    unchecked: { color: '#d9d9d9', label: '未填' },
    // 量測/程度型欄位的記錄值（高/中/低、電壓範圍…）—— 不是異常也不是合格
    measure:   { color: '#4BA8E8', label: '記錄值' },
  }

  // 明細分流：附件欄位不進任何列表（走附圖區），附註欄位進「其他欄位」
  const allItems       = detail?.items ?? []
  const equipmentItems = allItems.filter(
    (it) => !isImageField(it.item_name, it.result_raw) && !isMetaField(it.item_name),
  )
  const metaItems = allItems.filter(
    (it) => !isImageField(it.item_name, it.result_raw) && isMetaField(it.item_name),
  )

  // §7：有附圖 640px，無附圖 480px
  const drawerWidth = images.length > 0 ? 640 : 480

  return (
    <div>
      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 16 }}
               closable onClose={() => setError(null)} />
      )}
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <DatePicker
            picker="month"
            value={dayjs(yearMonth, 'YYYY/MM')}
            format="YYYY/MM"
            allowClear={false}
            onChange={(d) => { if (d) setYearMonth(d.format('YYYY/MM')) }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            重新整理
          </Button>
        </Col>
        <Col flex="auto" style={{ textAlign: 'right' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>點擊任一列查看該場次的設備明細</Text>
        </Col>
      </Row>
      <Table<FloorBatchRow>
        dataSource={rows}
        rowKey={(r) => r.batch.ragic_id}
        columns={columns}
        loading={loading}
        size="middle"
        onRow={(r) => ({
          onClick: () => openDetail(r.batch.ragic_id),
          style:   { cursor: 'pointer' },
        })}
        pagination={{ pageSize: 30, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '本月尚無巡檢紀錄' }}
      />

      {/* ── 明細 Drawer（CLAUDE.md §7 / WORK_JOURNAL_SPEC.md §9）───────────── */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={drawerWidth}
        title={
          <Space size={8} wrap>
            <Tag color={sheet?.color}>{sheet?.floor}</Tag>
            <span style={{ fontWeight: 600 }}>
              {sheet?.title}：{detail?.batch.ragic_id ?? ''}
            </span>
            {detail && (
              <a
                href={ragicRecordUrl(detail.batch.ragic_id)}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#4BA8E8', fontSize: 12 }}
              >
                <LinkOutlined /> 在 Ragic 查看
              </a>
            )}
          </Space>
        }
      >
        {detailLoading && <Text type="secondary">載入中…</Text>}
        {detail && (
          <>
            <Descriptions column={1} size="small" bordered
                          labelStyle={{ width: 110, background: '#f5f7fa', fontWeight: 500 }} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="巡檢日期">
                <b>{detail.batch.inspection_date || '—'}</b>
              </Descriptions.Item>
              <Descriptions.Item label="巡檢人員">{detail.batch.inspector_name || '—'}</Descriptions.Item>
              <Descriptions.Item label="開始巡檢時間">{detail.batch.start_time || '—'}</Descriptions.Item>
              <Descriptions.Item label="巡檢結束時間">{detail.batch.end_time || '—'}</Descriptions.Item>
              <Descriptions.Item label="工時計算">{detail.batch.work_hours || '—'}</Descriptions.Item>
              <Descriptions.Item label="巡檢進度">
                <b>{detail.kpi.completion_rate}%</b>
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                  （{detail.kpi.total - detail.kpi.unchecked} / {detail.kpi.total} 項）
                </Text>
                {/* 2026-08-24 起分母只算「設備項目」—— 附圖與「其他欄位」
                    已排除在 KPI 之外，所以這個分母應等於下方設備明細的項數。*/}
              </Descriptions.Item>
              <Descriptions.Item label="異常 / 待處理">
                {detail.kpi.abnormal > 0
                  ? <Tag color="#FF4D4F">異常 {detail.kpi.abnormal}</Tag> : null}
                {detail.kpi.pending > 0
                  ? <Tag color="#FAAD14">待處理 {detail.kpi.pending}</Tag> : null}
                {detail.kpi.abnormal === 0 && detail.kpi.pending === 0
                  ? <Text type="secondary">—</Text> : null}
              </Descriptions.Item>
            </Descriptions>

            {/* ② 設備巡檢明細（排除圖片欄位與附註欄位）*/}
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              設備巡檢明細（{equipmentItems.length} 項）
            </Text>
            <Descriptions column={1} size="small" bordered
                          labelStyle={{ width: 200, background: '#f5f7fa', fontWeight: 500 }}>
              {equipmentItems.map((it) => {
                const st = STATUS_TAG[it.result_status] ?? STATUS_TAG.unchecked
                return (
                  <Descriptions.Item key={it.ragic_id} label={it.item_name}>
                    <Tag color={st.color}>{it.result_raw || st.label}</Tag>
                  </Descriptions.Item>
                )
              })}
            </Descriptions>

            {/* ③ 其他欄位：純文字，不套狀態色（它們不是巡檢結果）*/}
            {metaItems.length > 0 && (
              <>
                <Divider style={{ margin: '16px 0 8px' }} />
                <Text strong style={{ display: 'block', marginBottom: 8 }}>
                  其他欄位（{metaItems.length} 項）
                </Text>
                <Descriptions column={1} size="small" bordered
                              labelStyle={{ width: 200, background: '#f5f7fa', fontWeight: 500 }}>
                  {metaItems.map((it) => (
                    <Descriptions.Item key={it.ragic_id} label={it.item_name}>
                      {it.result_raw
                        ? <Text>{it.result_raw}</Text>
                        : <Text type="secondary">—</Text>}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </>
            )}

            {/* ④ 附圖：Image.PreviewGroup（§7：禁止另開新視窗）*/}
            {(imagesLoading || images.length > 0) && (
              <>
                <Divider style={{ margin: '16px 0 8px' }} />
                <Text strong style={{ display: 'block', marginBottom: 8 }}>
                  附圖{images.length > 0 ? `（${images.length} 張）` : ''}
                </Text>
                {imagesLoading ? (
                  <div style={{ textAlign: 'center', padding: 16 }}><Spin size="small" /></div>
                ) : (
                  <Image.PreviewGroup>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {images.map((img, i) => (
                        <Image
                          key={img.url}
                          src={img.url}
                          alt={img.filename || `圖片 ${i + 1}`}
                          width={120}
                          height={90}
                          style={{
                            objectFit: 'cover', borderRadius: 4,
                            border: '1px solid #e8e8e8', cursor: 'pointer',
                          }}
                          fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                        />
                      ))}
                    </div>
                  </Image.PreviewGroup>
                )}
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  )
}
