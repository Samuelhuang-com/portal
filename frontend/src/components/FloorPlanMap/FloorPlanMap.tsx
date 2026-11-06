/**
 * 純地圖：底圖＋點位（Leaflet CRS.Simple）—— DEV_SPEC §7.2
 *
 * 座標：範圍 [[0,0],[H,W]]；Leaflet 是 [lat, lng]＝[y 由下往上, x]。
 *       點位存比例 (x, y)，y 由上往下 → lat = (1 - y) * H、lng = x * W；反算後 clamp 到 0～1。
 * react-leaflet 鎖 4.2.1（React 18；5.x 需 React 19，不得升級）。
 */
import { useEffect, useMemo } from 'react'
import { Spin } from 'antd'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { ImageOverlay, MapContainer, Marker, useMap, useMapEvents } from 'react-leaflet'
import type { FloorMapPoint, FloorPlan } from './api'
import { FLOOR_MAP_STATUS } from './status'

export interface Ratio { x: number; y: number }

const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!))

function markerIcon(p: FloorMapPoint, selected: boolean, editing: boolean): L.DivIcon {
  const st = FLOOR_MAP_STATUS[p.status ?? 'no_record']
  const cls = [
    'fpm-dot',
    selected ? 'fpm-dot--sel' : '',
    p.placement === 'pending' ? 'fpm-dot--pending' : '',
    p.child_ref ? 'fpm-dot--child' : '',
    editing ? 'fpm-dot--edit' : '',
  ].filter(Boolean).join(' ')
  const draft = p.placement === 'draft' ? '<span class="fpm-draft">草稿</span>' : ''
  return L.divIcon({
    className:  'fpm-marker',
    iconSize:   [28, 28],
    iconAnchor: [14, 14],
    html: `<div class="${cls}" style="background:${st.color}">${st.mark}</div>
           <div class="fpm-label">${esc(p.label)}${draft}</div>`,
  })
}

function FitBounds({ bounds }: { bounds: L.LatLngBoundsExpression }) {
  const map = useMap()
  useEffect(() => { map.fitBounds(bounds) }, [map, bounds])
  return null
}

function ClickToPlace({ active, onPlace }: { active: boolean; onPlace: (ll: L.LatLng) => void }) {
  useMapEvents({ click: (e) => { if (active) onPlace(e.latlng) } })
  return null
}

export interface FloorPlanMapProps {
  floor:      FloorPlan
  imageUrl:   string | null
  noImage?:   boolean
  points:     FloorMapPoint[]
  selectedId: number | null
  editing:    boolean
  placing:    boolean
  height?:    number
  onSelect:   (p: FloorMapPoint) => void
  onMove:     (p: FloorMapPoint, to: Ratio) => void
  onPlace:    (at: Ratio) => void
}

export default function FloorPlanMap({
  floor, imageUrl, noImage = false, points, selectedId, editing, placing, height = 640, onSelect, onMove, onPlace,
}: FloorPlanMapProps) {
  // 底圖旋轉（逆時針，度）：點位座標仍是「原圖」比例，只在畫面上換算位置，資料不動
  const W0 = floor.width
  const H0 = floor.height
  const rot = (((floor.rotation ?? 0) % 360) + 360) % 360
  const rad = (rot * Math.PI) / 180
  const cos = Math.cos(rad)
  const sin = Math.sin(rad)
  const W = Math.abs(W0 * cos) + Math.abs(H0 * sin)   // 旋轉後畫布寬
  const H = Math.abs(W0 * sin) + Math.abs(H0 * cos)   // 旋轉後畫布高
  const bounds = useMemo<L.LatLngBoundsExpression>(() => [[0, 0], [H, W]], [H, W])

  // 原圖比例座標 → 畫布座標（以圖心為軸，逆時針旋轉）
  const toLatLng = (p: Ratio): L.LatLngExpression => {
    const dx = p.x * W0 - W0 / 2
    const dy = p.y * H0 - H0 / 2
    const qx = dx * cos + dy * sin + W / 2
    const qy = -dx * sin + dy * cos + H / 2
    return [H - qy, qx]
  }
  // 畫布座標 → 原圖比例座標（與 toLatLng 互逆）
  const toRatio = (ll: L.LatLng): Ratio => {
    const dx = ll.lng - W / 2
    const dy = (H - ll.lat) - H / 2
    const px = dx * cos - dy * sin + W0 / 2
    const py = dx * sin + dy * cos + H0 / 2
    return {
      x: Math.min(1, Math.max(0, px / W0)),
      y: Math.min(1, Math.max(0, py / H0)),
    }
  }

  return (
    <div className={`fpm-map${placing ? ' fpm-placing' : ''}`} style={{ height }}>
      <style>{`
        .fpm-map { background: #fff; border-radius: 6px; }
        .fpm-map .leaflet-container { background: #fff; border-radius: 6px; }
        .fpm-marker { background: transparent; border: none; }
        .fpm-dot--child { box-shadow: 0 0 0 2px #fff, 0 0 0 4px #1B3A5C; }
        .fpm-dot {
          width: 28px; height: 28px; border-radius: 50%; border: 3px solid #fff;
          box-shadow: 0 1px 4px rgba(0,0,0,.45); color: #fff; font-weight: 700; font-size: 13px;
          display: flex; align-items: center; justify-content: center; box-sizing: border-box;
        }
        .fpm-dot--sel     { outline: 3px solid #4BA8E8; outline-offset: 2px; }
        .fpm-dot--pending { border-style: dashed; border-color: #1B3A5C; }
        .fpm-dot--edit    { cursor: move; }
        .fpm-label {
          position: absolute; top: 30px; left: 50%; transform: translateX(-50%);
          white-space: nowrap; font-size: 12px; background: rgba(255,255,255,.92);
          border: 1px solid #d9d9d9; border-radius: 3px; padding: 0 4px; color: #222;
        }
        .fpm-draft { margin-left: 4px; color: #d46b08; font-size: 11px; }
        .fpm-placing .leaflet-container { cursor: crosshair; }
      `}</style>
      {imageUrl ? (
        <MapContainer
          key={floor.key}
          crs={L.CRS.Simple}
          bounds={bounds}
          minZoom={-3}
          maxZoom={2}
          zoomSnap={0.25}
          zoomDelta={0.5}
          attributionControl={false}
          style={{ height: '100%', width: '100%' }}
        >
          <FitBounds bounds={bounds} />
          <ImageOverlay url={imageUrl} bounds={bounds} />
          <ClickToPlace active={editing && placing} onPlace={(ll) => onPlace(toRatio(ll))} />
          {points.map((p) => (
            <Marker
              key={`${p.id}-${p.x}-${p.y}-${editing}`}
              position={toLatLng(p)}
              icon={markerIcon(p, p.id === selectedId, editing)}
              draggable={editing}
              eventHandlers={{
                click:   () => onSelect(p),
                dragend: (e) => onMove(p, toRatio((e.target as L.Marker).getLatLng())),
              }}
            />
          ))}
        </MapContainer>
      ) : noImage ? (
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8c8c8c', fontSize: 16 }}>
          無底圖，待補
        </div>
      ) : (
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin tip="載入底圖…"><div style={{ width: 120, height: 60 }} /></Spin>
        </div>
      )}
    </div>
  )
}
