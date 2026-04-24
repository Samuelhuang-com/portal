import client from './client';

// ── 舊版 summary（相容保留）────────────────────────────────────────────────────
export interface DashboardSummary {
  tenants: number;
  active_users: number;
  ragic_connections: number;
  recent_syncs: Array<{
    id: string;
    connection_id: string;
    status: string;
    records_fetched?: number;
    started_at?: string;
  }>;
}

// ── 新版 KPI ──────────────────────────────────────────────────────────────────

export interface StatusDistItem {
  name: string;
  value: number;
  color: string;
}

export interface FocusRoom {
  room_no: string;
  work_item: string;
  incomplete: number;
  dept: string;
}

export interface RoomMaintenanceKPI {
  total: number;
  completed: number;
  in_progress: number;
  not_scheduled: number;
  pending: number;
  total_incomplete: number;
  completion_rate: number;
  status_distribution: StatusDistItem[];
  focus_rooms: FocusRoom[];
}

export interface CategoryDistItem {
  name: string;
  skus: number;
  quantity: number;
}

export interface InventoryKPI {
  total_skus: number;
  total_quantity: number;
  category_distribution: CategoryDistItem[];
}

export interface SyncRecord {
  id: string;
  status: string;
  records_fetched?: number;
  started_at?: string;
  triggered_by?: string;
  error_msg?: string;
}

export interface SystemKPI {
  last_sync_at: string | null;
  last_sync_status: string | null;
  last_sync_records: number | null;
  sync_success_rate: number;
  recent_syncs: SyncRecord[];
}

export interface DashboardKPI {
  room_maintenance: RoomMaintenanceKPI;
  inventory: InventoryKPI;
  system: SystemKPI;
}

// ── 趨勢折線型別 ──────────────────────────────────────────────────────────────

export interface TrendPoint {
  date: string
  mall_completion: number
  mall_abnormal: number
  mall_has_data: boolean
  security_completion: number
  security_abnormal: number
  security_has_data: boolean
  hotel_completion: number
  hotel_completed: number
  hotel_total: number
  hotel_abnormal: number
  hotel_has_data: boolean
}

export interface DashboardTrend {
  trend: TrendPoint[]
  days: number
}

// ── 結案率型別 ────────────────────────────────────────────────────────────────

export interface HotelClosureStats {
  total_rooms: number
  issue_count: number
  in_progress: number
  closed: number
  open: number
  closure_rate: number
}

export interface InspectionAbnormalStats {
  period: string
  abnormal_count: number
  note: string
}

export interface ApprovalClosureStats {
  total: number
  pending: number
  approved: number
  rejected: number
  resolved: number
  closure_rate: number
}

export interface ClosureSummary {
  total_anomalies: number
  total_closed: number
  generated_at: string
}

export interface ClosureStats {
  hotel: HotelClosureStats
  mall_inspection: InspectionAbnormalStats
  security_inspection: InspectionAbnormalStats
  approvals: ApprovalClosureStats
  summary: ClosureSummary
}

// ── API 函數 ──────────────────────────────────────────────────────────────────
export const dashboardApi = {
  summary:      () => client.get<DashboardSummary>('/dashboard/summary'),
  kpi:          () => client.get<DashboardKPI>('/dashboard/kpi'),
  trend:        (days = 7) => client.get<DashboardTrend>('/dashboard/trend', { params: { days } }),
  closureStats: () => client.get<ClosureStats>('/dashboard/closure-stats'),
};
