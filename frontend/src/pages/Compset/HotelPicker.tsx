/**
 * 競品分析 — 從地圖／清單挑選競爭組成員
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §9.4c
 *
 * 【這個元件在解決什麼】
 *   手抄 `google_property_token`（40 字元亂碼）。抄錯的症狀是
 *   「這家 A 級永遠抓不到」，而畫面上唯一的線索只是一個「僅遠期」標籤 ——
 *   極難查。從搜尋結果帶入就不會抄錯。
 *
 * ══════════════════════════════════════════════════════════════════════
 * ⚠️⚠️ 這個畫面**會花錢**
 * ══════════════════════════════════════════════════════════════════════
 * 每按一次「搜尋」＝ 每頁 1 次 SerpApi 查詢 ＝ 真的錢。所以：
 *
 * · **不做「拖曳地圖就重新搜尋」。** 那是地圖的直覺操作，但每動一下就是錢。
 *   地圖可以自由拖曳縮放（純前端），要換資料一律得按按鈕。
 * · 搜尋鈕上寫明會扣幾次配額，剩餘額度就放在旁邊。
 * · 打開 Modal **不會**自動搜尋 —— 使用者要先看到成本才決定。
 *
 * ⚠️ **搜尋不到的家仍然要手動新增。** 地圖不是完整世界地圖，是「這次查詢回了什麼」。
 *    P0 實測五月家青年旅舍台大館不在前 38 名裡。所以這個元件是**多一個入口**，
 *    不是取代手動新增。
 *
 * ⚠️ 地點查詢**沒有地址也沒有房數**（只有 token 路徑有地址）。帶入之後那兩欄
 *    一定是空的，畫面要講，不要讓人以為系統漏填。
 */
import React, { useCallback, useMemo, useRef, useState } from 'react'
import {
  Alert, Button, Empty, Input, InputNumber, Modal, Space, Table, Tag,
  Tooltip, Typography, message,
} from 'antd'
import { EnvironmentOutlined, SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import { searchHotels } from '@/api/compset'
import type { HotelCandidate, HotelSearchResult } from '@/types/compset'
import { fmtMoney } from './components'

const { Text, Paragraph } = Typography

/**
 * ⚠️ Leaflet 預設的 marker 圖檔是用相對路徑抓的，經過 Vite 打包後會 404
 * （畫面上就是「地圖有了但一個點都看不到」，而且 console 只有靜靜的 404）。
 * 這裡改用 `divIcon` 純 CSS 畫氣泡 —— 不依賴任何圖檔，順便可以把價格寫在上面，
 * 這也正是使用者想要的「地圖上直接看到價格」。
 */
function priceIcon(c: HotelCandidate, isSelf: boolean): L.DivIcon {
  const price = c.price_gross ?? c.price_pretax
  const bg = isSelf ? '#1B3A5C' : c.in_compset ? '#8c8c8c' : '#cf1322'
  const label = price ? `$${Math.round(price).toLocaleString('en-US')}` : '無價'
  return L.divIcon({
    className: '',
    html: `<div style="
      background:${bg};color:#fff;font-size:12px;font-weight:600;
      padding:2px 6px;border-radius:10px;white-space:nowrap;
      box-shadow:0 1px 4px rgba(0,0,0,.35);transform:translate(-50%,-50%);
      display:inline-block;">${label}</div>`,
    iconSize: [0, 0],
  })
}

/** 資料換了就把地圖拉到涵蓋所有點的範圍。 */
const FitBounds: React.FC<{ points: [number, number][] }> = ({ points }) => {
  const map = useMap()
  const key = points.map((p) => p.join(',')).join('|')
  React.useEffect(() => {
    if (points.length === 0) return
    if (points.length === 1) map.setView(points[0], 15)
    else map.fitBounds(L.latLngBounds(points), { padding: [40, 40] })
    // key 就是所有座標的指紋 —— points 每次 render 都是新陣列，不能當依賴
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return null
}

const CompsetHotelPicker: React.FC<{
  open: boolean
  onClose: () => void
  /** 使用者挑了一家 → 帶著預填值開新增表單 */
  onPick: (c: HotelCandidate) => void
  /** 訂閱設定的地點查詢字串，當搜尋框的預設值 */
  defaultQuery?: string
  /** 剩餘配額，顯示在搜尋鈕旁邊 */
  quotaAvailable?: number
}> = ({ open, onClose, onPick, defaultQuery = '', quotaAvailable }) => {
  const [q, setQ] = useState(defaultQuery)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<HotelSearchResult | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const searched = useRef(false)

  const doSearch = useCallback(async () => {
    setLoading(true)
    try {
      const res = await searchHotels({ q: q.trim(), pages })
      setData(res)
      searched.current = true
      if (res.items.length === 0) {
        message.warning('這個查詢沒有回傳任何飯店，換個關鍵字試試。')
      }
    } catch (e: any) {
      // 402 ＝ 配額不足。那不是壞掉，是狀態 —— 訊息本身講得很清楚，直接顯示。
      message.error(e?.response?.data?.detail || '搜尋失敗')
    } finally {
      setLoading(false)
    }
  }, [q, pages])

  const points = useMemo<[number, number][]>(
    () => (data?.items ?? [])
      .filter((i) => i.latitude != null && i.longitude != null)
      .map((i) => [i.latitude as number, i.longitude as number]),
    [data],
  )

  const selfPoint = data?.self && data.self.latitude != null
    ? [data.self.latitude, data.self.longitude as number] as [number, number]
    : null

  const columns: ColumnsType<HotelCandidate> = [
    {
      title: '飯店', dataIndex: 'name',
      render: (v: string, r) => (
        <Space direction="vertical" size={0}>
          <Space size={4}>
            <Text strong={!r.in_compset}>{v}</Text>
            {r.in_compset && <Tag>已在競爭組</Tag>}
            {r.latitude == null && (
              <Tooltip title="這家沒有座標，不會出現在地圖上，但仍然可以加入競爭組。">
                <Tag color="orange">無座標</Tag>
              </Tooltip>
            )}
          </Space>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {r.hotel_class ? `${r.hotel_class} 星　` : ''}
            {r.overall_rating ? `評分 ${r.overall_rating}` : ''}
            {r.reviews ? `（${r.reviews} 則）` : ''}
          </Text>
        </Space>
      ),
    },
    {
      title: '距離', dataIndex: 'distance_km', width: 90, align: 'right',
      render: (v: number | null) => (v == null
        ? <Text type="secondary">—</Text>
        : <Tooltip title="與「自己」那一家的直線距離">{v.toFixed(2)} km</Tooltip>),
    },
    {
      title: '參考價', width: 100, align: 'right',
      render: (_, r) => (
        <Tooltip title="搜尋當下該日的最低可訂價（含稅），只是拿來判斷價位帶，不會寫進競爭組。">
          {fmtMoney(r.price_gross ?? r.price_pretax)}
        </Tooltip>
      ),
    },
    {
      title: '', width: 90, align: 'right',
      render: (_, r) => (r.in_compset
        ? <Text type="secondary" style={{ fontSize: 12 }}>已加入</Text>
        : <Button size="small" type="primary" onClick={() => onPick(r)}>加入</Button>),
    },
  ]

  return (
    <Modal open={open} onCancel={onClose} footer={null} width={980}
      title="從搜尋結果挑選競爭組成員" destroyOnClose>

      <Alert type="warning" showIcon style={{ marginBottom: 12 }}
        message="每按一次搜尋都會扣配額"
        description={<>
          每頁 1 次 SerpApi 查詢，是**真的費用**。地圖可以自由拖曳縮放（不花錢），
          但要換一批資料就得重新搜尋。
          <br />
          ⚠️ 搜尋結果<b>不是完整的世界地圖</b>，是「這次查詢回了什麼」——
          找不到的飯店仍然可以用「手動新增」加進來。
        </>} />

      <Space wrap style={{ marginBottom: 12, width: '100%' }}>
        <Input
          value={q} onChange={(e) => setQ(e.target.value)}
          onPressEnter={doSearch} style={{ width: 300 }}
          placeholder="地點關鍵字，例如：公館 台北 飯店"
          prefix={<EnvironmentOutlined />} allowClear />
        <Tooltip title="每一頁都是一次查詢、一次費用。先用 1 頁看看夠不夠。">
          <InputNumber value={pages} onChange={(v) => setPages(v || 1)}
            min={1} max={3} addonAfter="頁" style={{ width: 110 }} />
        </Tooltip>
        <Button type="primary" icon={<SearchOutlined />}
          loading={loading} onClick={doSearch}>
          搜尋（扣 {pages} 次配額）
        </Button>
        {quotaAvailable != null && (
          <Text type={quotaAvailable < pages ? 'danger' : 'secondary'}>
            剩餘 {quotaAvailable} 次
          </Text>
        )}
      </Space>

      {(data?.warnings ?? []).length > 0 && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message={<ul style={{ margin: 0, paddingLeft: 18 }}>
            {data!.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>} />
      )}

      {!searched.current && !loading && (
        <Empty style={{ padding: '32px 0' }}
          description="輸入地點後按搜尋。打開這個視窗不會自動查詢 —— 查詢要花錢，先讓你看到成本。" />
      )}

      {searched.current && (
        <div style={{ display: 'flex', gap: 12, alignItems: 'stretch' }}>
          <div style={{ flex: '1 1 55%', minWidth: 380, height: 420 }}>
            {points.length === 0
              ? <Empty style={{ paddingTop: 120 }} description="沒有帶座標的結果" />
              : (
                <MapContainer center={selfPoint ?? points[0]} zoom={15}
                  style={{ height: '100%', width: '100%', borderRadius: 6 }}
                  scrollWheelZoom>
                  {/* OpenStreetMap 免費圖磚，不需要 API key。
                      ⚠️ attribution 是使用條款要求，不可移除。 */}
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <FitBounds points={selfPoint ? [...points, selfPoint] : points} />
                  {selfPoint && (
                    <Marker position={selfPoint}
                      icon={L.divIcon({
                        className: '',
                        html: `<div style="background:#1B3A5C;color:#fff;font-size:12px;
                          font-weight:700;padding:3px 8px;border-radius:10px;
                          border:2px solid #fff;box-shadow:0 1px 6px rgba(0,0,0,.4);
                          transform:translate(-50%,-50%);display:inline-block;">自己</div>`,
                        iconSize: [0, 0],
                      })} />
                  )}
                  {(data?.items ?? [])
                    .filter((i) => i.latitude != null && i.longitude != null)
                    .map((i) => (
                      <Marker key={i.property_token || i.name}
                        position={[i.latitude as number, i.longitude as number]}
                        icon={priceIcon(i, false)}
                        eventHandlers={{
                          mouseover: () => setHovered(i.property_token || i.name),
                        }}>
                        <Popup>
                          <div style={{ minWidth: 170 }}>
                            <div><b>{i.name}</b></div>
                            <div>{fmtMoney(i.price_gross ?? i.price_pretax)}
                              {i.distance_km != null && `　${i.distance_km.toFixed(2)} km`}</div>
                            <div style={{ marginTop: 6 }}>
                              {i.in_compset
                                ? <Tag>已在競爭組</Tag>
                                : <Button size="small" type="primary"
                                    onClick={() => onPick(i)}>加入競爭組</Button>}
                            </div>
                          </div>
                        </Popup>
                      </Marker>
                    ))}
                </MapContainer>
              )}
          </div>

          <div style={{ flex: '1 1 45%', minWidth: 320, maxHeight: 420, overflow: 'auto' }}>
            <Table<HotelCandidate>
              rowKey={(r) => r.property_token || r.name}
              size="small" pagination={false} columns={columns}
              dataSource={data?.items ?? []}
              rowClassName={(r) => ((r.property_token || r.name) === hovered
                ? 'ant-table-row-selected' : '')}
              locale={{ emptyText: <Empty description="沒有結果" /> }} />
          </div>
        </div>
      )}

      <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
        帶入的欄位：<b>名稱</b>與 <b>property_token</b>（最容易抄錯的那一個）、經緯度。
        <b>地址與房數要自己補</b> —— 地點查詢的回應裡沒有這兩個欄位。
      </Paragraph>
    </Modal>
  )
}

export default CompsetHotelPicker
