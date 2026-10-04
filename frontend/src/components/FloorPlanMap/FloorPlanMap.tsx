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
  floor, imageUrl, points, selectedId, editing, placing, height = 640, onSelect, onMove, onPlace,
}: FloorPlanMapProps) {
  const W = floor.width
  const H = floor.height
  const bounds = useMemo<L.LatLngBoundsExpression>(() => [[0, 0], [H, W]], [H, W])

  const toLatLng = (p: Ratio): L.LatLngExpression => [(1 - p.y) * H, p.x * W]
  const toRatio  = (ll: L.LatLng): Ratio => ({
    x: Math.min(1, Math.max(0, ll.lng / W)),
    y: Math.min(1, Math.max(0, 1 - ll.lat / H)),
  })

  return (
    <div className={`fpm-map${placing ? ' fpm-placing' : ''}`} style={{ height }}>
      <style>{`
        .fpm-map { background: #fff; border-radius: 6px; }
        .fpm-map .leaflet-container { background: #fff; border-radius: 6px; }
        .fpm-marker { background: transparent; border: none; }
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
      ) : (
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin tip="載入底圖…"><div style={{ width: 120, height: 60 }} /></Spin>
        </div>
      )}
    </div>
  )
}
