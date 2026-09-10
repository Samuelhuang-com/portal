/**
 * 競品分析 — 競爭組設定
 * Route: /compset/hotels    Permission: compset_hotels_admin
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §9.4、§4.3
 *
 * 【這一頁在做什麼】
 *   維護「要盯哪幾家」。業主自己圈（SPEC D6）—— 不由系統依距離自動抓，
 *   因為「競爭對手」是商業判斷不是地理判斷（隔壁的青旅不是競品，
 *   兩公里外同價位的商旅才是）。
 *
 * ── 三個一定要講清楚的坑 ─────────────────────────────────────────────────
 * ① **`is_self` 有且只能有一家**。指數 ＝ 自己 ÷ 競品中位數，沒有自己就算不出來，
 *    兩家自己則會算出無意義的數字。後端 `_assert_exactly_one_self()` 會擋，
 *    但畫面要先講，不要讓人存了才被退。
 * ② **沒有 `property_token` 的家，A 級抓不到**。A 級是逐家查詢，靠 token 定位；
 *    B／C 級走地點查詢不需要 token。所以缺 token 不是壞掉，是「只有遠期資料」。
 * ③ **停用不等於刪除**。停用只是不再抓，歷史資料留著（矩陣回看舊快照仍會出現）。
 *    真的刪掉會讓過去的指數重算後對不起來。
 *
 * 這一頁同時是 CSV 備援匯入的入口（SPEC §6.4）—— SerpApi 掛掉、
 * 額度用完、或要補歷史資料時的唯一辦法。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Space,
  Switch, Table, Tag, Tooltip, Typography, Upload, message,
} from 'antd'
import {
  DeleteOutlined, DownloadOutlined, EditOutlined, EnvironmentOutlined,
  InboxOutlined, PlusOutlined, ReloadOutlined, UploadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import {
  createHotel, deleteHotel, downloadBlob, downloadImportTemplate,
  fetchHotels, importRatesCsv, updateHotel,
} from '@/api/compset'
import type {
  CompsetHotelRow, HotelCandidate, ImportResult,
} from '@/types/compset'
import CompsetHotelPicker from '../HotelPicker'

const { Text, Paragraph } = Typography
const { Dragger } = Upload

const EMPTY: Partial<CompsetHotelRow> = {
  hotel_code: '', display_name: '', short_name: '', google_property_token: '',
  google_query_name: '', registered_address: '', note: '',
  is_self: false, is_enabled: true, sort_order: 0, room_count: null,
}

const CompsetHotelsPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [rows, setRows] = useState<CompsetHotelRow[]>([])
  const [editing, setEditing] = useState<CompsetHotelRow | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  /**
   * 從搜尋結果帶入的預填值。
   * ⚠️ 這是 `Partial` 不是完整一筆 —— 地點查詢**沒有地址也沒有房數**，
   *    那兩欄一定要人自己補（表單上有提示）。
   */
  const [prefill, setPrefill] = useState<Partial<CompsetHotelRow> | null>(null)
  const [pickerOpen, setPickerOpen] = useState(false)

  const [importOpen, setImportOpen] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchHotels()
      setRows(data.items ?? [])
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const selfCount = rows.filter((r) => r.is_self).length
  const noTokenCount = rows.filter((r) => r.is_enabled && !r.has_token).length

  /**
   * ⚠️ **不要在這裡 `form.setFieldsValue()`**。
   *
   * Modal 有 `destroyOnClose`，所以此刻 Form 是**卸載狀態**。
   * rc-field-form 在卸載時會把所有 `preserve: false` 的欄位記進
   * `prevWithoutPreserves`；Form 重新掛載時 `setInitialValues(initialValues, true)`
   * 會拿 `initialValues` 把那些欄位**全部覆寫回去** ——
   * 於是先寫進去的值在下一個 tick 被抹掉。
   *
   * 症狀非常難查：**第一次開是好的**（沒有東西被卸載過），第二次開才變空白。
   * 使用者看到空白的「編輯」表單，把名稱補回去就存檔，
   * 結果 `google_property_token` 被寫成空字串 —— 那家從此在 A 級消失，
   * 而畫面上唯一的線索只是一個「僅遠期」標籤。
   *
   * 正確做法：讓 `initialValues` 成為唯一的資料來源。
   * `destroyOnClose` 保證每次開啟都是全新掛載，掛載時 `editing` 已經設好了。
   */
  const openModal = (row?: CompsetHotelRow) => {
    setEditing(row ?? null)
    setPrefill(null)
    setModalOpen(true)
  }

  /**
   * 從搜尋結果挑了一家 → 關掉地圖、開新增表單並帶入。
   *
   * ⚠️ 只帶「機器抄不會錯、人抄容易錯」的欄位：名稱、**property_token**、經緯度。
   *    簡稱用名稱前 4 字當草稿（使用者一定會想改），
   *    地址與房數留空 —— 地點查詢的回應裡沒有這兩欄，硬掰一個更糟。
   */
  const pickFromSearch = (c: HotelCandidate) => {
    setPickerOpen(false)
    setEditing(null)
    setPrefill({
      display_name: c.name,
      google_query_name: c.name,
      google_property_token: c.property_token,
      short_name: c.name.replace(/\s*[-–—(（].*$/, '').slice(0, 4),
      latitude: c.latitude,
      longitude: c.longitude,
      is_self: false,
      is_enabled: true,
      sort_order: rows.length,
      room_count: null,
      registered_address: '',
      hotel_code: '',
      note: `從搜尋結果加入${c.distance_km != null
        ? `（距離自己 ${c.distance_km.toFixed(2)} km）` : ''}`,
    })
    setModalOpen(true)
  }

  const save = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      if (editing) await updateHotel(editing.id, values)
      else await createHotel(values)
      message.success(editing ? '已更新' : '已新增')
      setModalOpen(false)
      load()
    } catch (e: any) {
      // 後端 `_assert_exactly_one_self()` 的 400 會走到這裡，訊息本身就講得很清楚
      message.error(e?.response?.data?.detail || '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (row: CompsetHotelRow) => {
    try {
      await deleteHotel(row.id)
      message.success('已刪除')
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '刪除失敗')
    }
  }

  const doImport = async (file: File) => {
    setImporting(true)
    setImportResult(null)
    try {
      const res = await importRatesCsv(file)
      setImportResult(res)
      if (res.inserted > 0) message.success(`已匯入 ${res.inserted} 筆`)
      else message.warning('沒有任何一筆匯入成功，請看下方錯誤')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '匯入失敗')
    } finally {
      setImporting(false)
    }
  }

  /**
   * ⚠️ **必須是同步函式、且同步回傳 `false`**（比照 `pages/OTA/Sources`）。
   *
   * antd 只有在 `beforeUpload` **同步**回傳 `false` 時才會取消自己的上傳。
   * 寫成 `async` 的話回傳的是 `Promise<false>` —— antd 會 await 它，
   * 然後**照樣**用自己的 XHR 送一次；而這個 Dragger 沒有 `action`，
   * 那一次會打到當前頁面網址。使用者看不到（`showUploadList={false}`），
   * 但每匯入一次就多一個無意義的請求。
   */
  const beforeUpload = (file: File): false => {
    void doImport(file)
    return false
  }

  const columns: ColumnsType<CompsetHotelRow> = [
    { title: '順序', dataIndex: 'sort_order', width: 70, align: 'center' },
    {
      title: '飯店', dataIndex: 'display_name', width: 240,
      render: (v: string, r) => (
        <Space direction="vertical" size={0}>
          <Space size={4}>
            {r.is_self && <Tag color="blue">自己</Tag>}
            <Text strong={r.is_self}>{v}</Text>
          </Space>
          <Space size={4}>
            {/* 簡稱沒填時標出來 —— 表格與標籤會退回全名，中文全名會擠版 */}
            {r.short_name
              ? <Tag style={{ marginInlineEnd: 0 }}>{r.short_name}</Tag>
              : <Tooltip title="沒有簡稱，價格矩陣的欄位標題與 Dashboard 的滿房標籤會顯示全名，中文全名通常會擠版。">
                  <Text type="warning" style={{ fontSize: 11 }}>未設簡稱</Text>
                </Tooltip>}
            {r.hotel_code && <Text type="secondary" style={{ fontSize: 11 }}>{r.hotel_code}</Text>}
          </Space>
        </Space>
      ),
    },
    {
      title: '房數', dataIndex: 'room_count', width: 80, align: 'right',
      render: (v: number | null) => (v ?? <Text type="secondary">—</Text>),
    },
    {
      title: (
        <Tooltip title="Google 的飯店識別碼。有 token 才能做 A 級逐家查詢（也才判得出滿房）。">
          A 級可用
        </Tooltip>
      ),
      dataIndex: 'has_token', width: 110, align: 'center',
      render: (v: boolean) => (v
        ? <Tag color="green">可</Tag>
        : <Tooltip title="沒有 property_token，A 級（近期逐日）抓不到這一家，只會有 B／C 級的遠期資料。不是故障。">
            <Tag color="orange">僅遠期</Tag>
          </Tooltip>),
    },
    {
      title: '地點查詢用名稱', dataIndex: 'google_query_name', width: 180,
      render: (v: string) => (v || <Text type="secondary">（同顯示名稱）</Text>),
    },
    {
      title: '啟用', dataIndex: 'is_enabled', width: 90, align: 'center',
      render: (v: boolean) => (v
        ? <Tag color="green">啟用</Tag>
        : <Tooltip title="停用只是不再抓，歷史資料保留"><Tag>停用</Tag></Tooltip>),
    },
    { title: '備註', dataIndex: 'note', ellipsis: true },
    {
      title: '操作', width: 130, fixed: 'right',
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openModal(r)}>編輯</Button>
          <Popconfirm title="確定刪除？"
            description="歷史快照會留著，但這一家不再出現在新的矩陣裡。建議改用「停用」。"
            onConfirm={() => remove(r)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space direction="vertical" size={0}>
          <Typography.Title level={4} style={{ margin: 0 }}>競爭組設定</Typography.Title>
          <Text type="secondary">要盯哪幾家，由你自己圈。共 {rows.length} 家</Text>
        </Space>
        <Space>
          <Button icon={<UploadOutlined />} onClick={() => setImportOpen(true)}>
            CSV 備援匯入
          </Button>
          <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
          {/* ⚠️ 這個入口**會扣配額**，所以文字要寫出來，不能只寫「從地圖挑選」 */}
          <Tooltip title="搜尋周邊飯店並從地圖挑選。⚠️ 每次搜尋都會扣配額（真的費用）。">
            <Button icon={<EnvironmentOutlined />} onClick={() => setPickerOpen(true)}>
              從地圖挑選（會扣配額）
            </Button>
          </Tooltip>
          {/* ⚠️ 手動新增**不能拿掉** —— 搜尋不到的家只能靠它
              （P0 實測五月家不在前 38 名裡） */}
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal()}>
            手動新增
          </Button>
        </Space>
      </Space>

      {/* ① 自己有且只有一家 —— 這是最嚴重的設定錯誤，整個模組會算不出指數 */}
      {selfCount !== 1 && (
        <Alert type="error" showIcon style={{ marginBottom: 16 }}
          message={selfCount === 0 ? '沒有標記「自己」' : `標記了 ${selfCount} 家「自己」`}
          description="價格指數 ＝ 自己 ÷ 競品中位數，必須剛好有一家標記為自己。
            現在的狀態會讓 Dashboard 與矩陣的指數、名次全部算不出來。" />
      )}

      {/* ② 缺 token 是設定事實，不是故障 —— 用 info 不用 warning */}
      {noTokenCount > 0 && (
        <Alert type="info" showIcon style={{ marginBottom: 16 }}
          message={`有 ${noTokenCount} 家沒有 property_token`}
          description="這些家 A 級（未來 14 天、每日、可判滿房）抓不到，只會出現在
            B／C 級的遠期資料裡。這不是故障 —— 想補的話，到 Google Travel 搜到該飯店，
            從網址或 SerpApi 回應取得 property_token 後填入即可。" />
      )}

      <Card>
        <Table<CompsetHotelRow>
          rowKey="id" size="small" loading={loading} columns={columns}
          dataSource={rows} pagination={false} scroll={{ x: 1100 }} />
        <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
          排序影響矩陣的欄位順序（自己永遠排最前面，其餘依此欄）。
          停用的家不再抓取，但歷史快照保留，回看舊日期時仍會出現。
        </Paragraph>
      </Card>

      {/* ── 編輯 ─────────────────────────────────────────────────────── */}
      <Modal open={modalOpen}
        title={editing ? '編輯競爭組成員'
          : prefill ? '新增競爭組成員（已從搜尋帶入）' : '新增競爭組成員'}
        onOk={save} confirmLoading={saving} onCancel={() => setModalOpen(false)}
        width={620} destroyOnClose>
        {/* initialValues 是唯一的資料來源（見 openModal 的說明）。
            key 讓「編輯 A → 關閉 → 編輯 B」一定重新掛載，不吃殘值。 */}
        {prefill && (
          <Alert type="info" showIcon style={{ marginBottom: 16 }}
            message="已從搜尋結果帶入"
            description="名稱、property_token 與經緯度已填好。
              ⚠️ 地址與房數要自己補 —— 地點查詢的回應裡沒有這兩個欄位
              （當初是人工去觀光署旅宿網查的）。" />
        )}
        <Form form={form} layout="vertical"
          key={editing?.id ?? (prefill ? 'prefill' : 'new')}
          initialValues={editing ?? prefill ?? EMPTY} preserve={false}>
          <Form.Item name="display_name" label="顯示名稱"
            rules={[{ required: true, message: '請填顯示名稱' }]}>
            <Input placeholder="例：承攜行旅" />
          </Form.Item>
          <Form.Item name="short_name" label="簡稱"
            tooltip="價格矩陣的欄位標題與 Dashboard 的滿房標籤會用這個。留空會退回全名 —— 中文全名通常 8～12 字，會把表格擠爛。"
            rules={[{ max: 20, message: '最多 20 字' }]}>
            <Input placeholder="例：承攜（留空 ＝ 用全名）" maxLength={20} showCount />
          </Form.Item>
          <Form.Item name="hotel_code" label="內部代碼"
            tooltip="自訂的短代碼，方便對照。可留空。">
            <Input placeholder="例：CHENGXI" />
          </Form.Item>
          <Form.Item name="google_property_token" label="Google property_token"
            tooltip="有填才能做 A 級逐家查詢（近期逐日、可判滿房）。留空則只有 B／C 級遠期資料。">
            <Input placeholder="留空 ＝ 只做 B／C 級" />
          </Form.Item>
          <Form.Item name="google_query_name" label="地點查詢用名稱"
            tooltip="B／C 級的地點查詢是靠名稱比對回傳結果。若 Google 上的名稱與顯示名稱不同，填這裡。留空則用顯示名稱。">
            <Input placeholder="留空 ＝ 同顯示名稱" />
          </Form.Item>
          <Space style={{ display: 'flex' }} align="start">
            <Form.Item name="room_count" label="房數" style={{ flex: 1 }}
              tooltip="規模相近才是真競品。只是參考欄位，不影響計算。">
              <InputNumber min={1} style={{ width: '100%' }} placeholder="例：92" />
            </Form.Item>
            <Form.Item name="sort_order" label="排序" style={{ flex: 1 }}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Form.Item name="registered_address" label="地址">
            <Input />
          </Form.Item>
          <Space style={{ display: 'flex' }} align="start">
            <Form.Item name="latitude" label="緯度" style={{ flex: 1 }}
              tooltip="從搜尋結果帶入時自動填。用來算「距離自己幾公里」與畫地圖。留空也可以。">
              <InputNumber style={{ width: '100%' }} step={0.0000001}
                placeholder="留空 ＝ 不上地圖" />
            </Form.Item>
            <Form.Item name="longitude" label="經度" style={{ flex: 1 }}>
              <InputNumber style={{ width: '100%' }} step={0.0000001}
                placeholder="留空 ＝ 不上地圖" />
            </Form.Item>
          </Space>
          <Form.Item name="note" label="備註">
            <Input.TextArea rows={2} placeholder="例：地緣最近／上檔天花板／地板錨點" />
          </Form.Item>
          <Space size={32}>
            <Form.Item name="is_self" label="這是我自己" valuePropName="checked"
              tooltip="整組有且只能有一家勾這個。指數就是拿這一家去除以其餘家的中位數。">
              <Switch />
            </Form.Item>
            <Form.Item name="is_enabled" label="啟用" valuePropName="checked"
              tooltip="停用只是不再抓，歷史資料保留">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      <CompsetHotelPicker
        open={pickerOpen} onClose={() => setPickerOpen(false)}
        onPick={pickFromSearch} />

      {/* ── CSV 備援匯入（SPEC §6.4）─────────────────────────────────── */}
      <Modal open={importOpen} title="CSV 備援匯入" footer={null}
        onCancel={() => { setImportOpen(false); setImportResult(null) }} width={640}>
        <Alert type="info" showIcon style={{ marginBottom: 16 }}
          message="這條路不會因為自動抓取上線而移除"
          description={<>
            SerpApi 改版、額度用完、或要補一段歷史資料時，這是唯一的入口。
            <br />
            ⚠️ 同一天同一家若已經有 SerpApi 的資料，<b>SerpApi 優先</b>（SPEC D16）——
            手動匯入不會蓋掉自動抓到的價格。
          </>} />

        <Space style={{ marginBottom: 16 }}>
          <Button icon={<DownloadOutlined />} onClick={async () => {
            try {
              downloadBlob(await downloadImportTemplate(), 'compset_import_template.csv')
            } catch { message.error('下載範本失敗') }
          }}>
            下載 CSV 範本
          </Button>
        </Space>

        <Dragger accept=".csv" maxCount={1} disabled={importing}
          beforeUpload={(f) => beforeUpload(f as unknown as File)}
          showUploadList={false}>
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">點擊或拖曳 CSV 檔到這裡</p>
          <p className="ant-upload-hint">
            欄位：快照日期／入住日期／飯店／含稅價／稅前價／幣別／含稅／是否滿房／通路／房型／入住人數
          </p>
        </Dragger>

        {/* ⚠️ 逐列匯入（SPEC D17）：壞掉的列跳過、好的列照進，錯誤逐列列出。
            整批 rollback 的話，一個錯字就要重來一次。 */}
        {importResult && (
          <div style={{ marginTop: 16 }}>
            <Alert
              type={importResult.errors.length > 0 ? 'warning' : 'success'} showIcon
              message={`共 ${importResult.total_rows} 列：`
                + `匯入 ${importResult.inserted} 筆、`
                + `略過 ${importResult.skipped} 筆、`
                + `錯誤 ${importResult.errors.length} 筆`} />
            {importResult.warnings.length > 0 && (
              <Card size="small" title="提醒" style={{ marginTop: 12 }}>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {importResult.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </Card>
            )}
            {importResult.errors.length > 0 && (
              <Card size="small" title="錯誤明細（這些列沒有匯入）" style={{ marginTop: 12 }}>
                <ul style={{ margin: 0, paddingLeft: 18, maxHeight: 200, overflow: 'auto' }}>
                  {importResult.errors.map((e, i) =>
                    <li key={i}><Text type="danger">{e}</Text></li>)}
                </ul>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default CompsetHotelsPage
