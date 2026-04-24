/**
 * dashboardGraph.ts
 * GET /api/v1/dashboard/graph — 操作流程關聯圖譜資料封裝
 * v1.26：11 節點 + 8 關係邊（3 群組）
 */
import apiClient from './client'

export interface GraphGroup {
  id: string
  label: string
  color: string
}

export interface GraphNode {
  id: string
  label: string
  group: 'inspection' | 'maintenance' | 'workflow'
  alert: number
  status: 'normal' | 'warning' | 'danger'
  path: string
  sub?: string
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label: string
  weight: number
  /** anomaly = 巡檢→保養(業務邏輯), escalation = →簽核(業務邏輯), workflow = DB直接關聯 */
  type: 'anomaly' | 'escalation' | 'workflow'
}

export interface DashboardGraphData {
  groups: GraphGroup[]
  nodes: GraphNode[]
  edges: GraphEdge[]
  meta: {
    generated_at: string
    total_alerts: number
  }
}

export async function fetchDashboardGraph(): Promise<DashboardGraphData> {
  const { data } = await apiClient.get<DashboardGraphData>('/dashboard/graph')
  return data
}
