/**
 * F1/F2 — 基礎參考資料 API
 * 公司別 / 部門別 / 計價規格
 * 對應後端 /api/v1/settings/companies  /departments  /pricing-specs
 */
import client from './client'

// ── 型別 ──────────────────────────────────────────────────────────────────

export interface CompanyRecord {
  id: number
  name: string
  is_active: boolean
  created_at: string
}

export interface CompanyOption {
  value: string  // 公司名稱（存 DB）
  label: string  // 顯示文字
  id: number     // 供部門下拉過濾
}

export interface DepartmentRecord {
  id: number
  name: string
  company_id: number
  company_name: string
  is_active: boolean
  created_at: string
}

export interface DepartmentOption {
  value: string
  label: string
}

export interface PricingSpecRecord {
  id: number
  name: string
  is_active: boolean
  created_at: string
}

export interface PricingSpecOption {
  value: string
  label: string
}

// ── 公司別 ────────────────────────────────────────────────────────────────

export const companiesApi = {
  list: () =>
    client.get<CompanyRecord[]>('/settings/companies'),
  options: () =>
    client.get<CompanyOption[]>('/settings/companies/options'),
  create: (name: string) =>
    client.post<CompanyRecord>('/settings/companies', { name }),
  update: (id: number, name: string) =>
    client.put<CompanyRecord>(`/settings/companies/${id}`, { name }),
  toggle: (id: number) =>
    client.patch<CompanyRecord>(`/settings/companies/${id}/toggle`),
}

// ── 部門別 ────────────────────────────────────────────────────────────────

export const departmentsApi = {
  list: (companyId?: number) =>
    client.get<DepartmentRecord[]>('/settings/departments', {
      params: companyId != null ? { company_id: companyId } : undefined,
    }),
  options: (companyId?: number) =>
    client.get<DepartmentOption[]>('/settings/departments/options', {
      params: companyId != null ? { company_id: companyId } : undefined,
    }),
  create: (name: string, companyId: number) =>
    client.post<DepartmentRecord>('/settings/departments', { name, company_id: companyId }),
  update: (id: number, name: string, companyId?: number) =>
    client.put<DepartmentRecord>(`/settings/departments/${id}`, {
      name,
      ...(companyId != null ? { company_id: companyId } : {}),
    }),
  toggle: (id: number) =>
    client.patch<DepartmentRecord>(`/settings/departments/${id}/toggle`),
}

// ── 計價規格 ──────────────────────────────────────────────────────────────

export const pricingSpecsApi = {
  list: () =>
    client.get<PricingSpecRecord[]>('/settings/pricing-specs'),
  options: () =>
    client.get<PricingSpecOption[]>('/settings/pricing-specs/options'),
  create: (name: string) =>
    client.post<PricingSpecRecord>('/settings/pricing-specs', { name }),
  update: (id: number, name: string) =>
    client.put<PricingSpecRecord>(`/settings/pricing-specs/${id}`, { name }),
  toggle: (id: number) =>
    client.patch<PricingSpecRecord>(`/settings/pricing-specs/${id}/toggle`),
}

// ── SLA 指標類型 ──────────────────────────────────────────────────────────────

export interface SlaMetricTypeRecord {
  id: number
  name: string
  description?: string
  is_active: boolean
  created_at: string
}

export interface SlaMetricTypeOption {
  value: string
  label: string
}

export const slaMetricTypesApi = {
  list: () =>
    client.get<SlaMetricTypeRecord[]>('/settings/sla-metric-types'),
  options: () =>
    client.get<SlaMetricTypeOption[]>('/settings/sla-metric-types/options'),
  create: (name: string, description?: string) =>
    client.post<SlaMetricTypeRecord>('/settings/sla-metric-types', { name, description }),
  update: (id: number, name: string, description?: string) =>
    client.put<SlaMetricTypeRecord>(`/settings/sla-metric-types/${id}`, { name, description }),
  toggle: (id: number) =>
    client.patch<SlaMetricTypeRecord>(`/settings/sla-metric-types/${id}/toggle`),
}
