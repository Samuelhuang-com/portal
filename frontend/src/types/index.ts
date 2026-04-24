export interface User {
  id: string;
  email: string;
  full_name: string;
  tenant_id: string;
  tenant_name: string;
  roles: string[];
  is_active: boolean;
  last_login?: string;
  created_at?: string;
}

export interface Tenant {
  id: string;
  code: string;
  name: string;
  type: string;
  is_active: boolean;
  created_at: string;
}

export interface RagicConnection {
  id: string;
  tenant_id: string;
  display_name: string;
  server: string;
  account_name: string;
  sheet_path: string;
  field_mappings: Record<string, unknown>;
  sync_interval: number;
  is_active: boolean;
  last_synced_at?: string;
  created_at: string;
}

export interface SyncLog {
  id: string;
  connection_id: string;
  started_at: string;
  finished_at?: string;
  records_fetched?: number;
  status: 'running' | 'success' | 'error' | 'partial';
  error_msg?: string;
  triggered_by: string;
}

export const ROLE_LABELS: Record<string, string> = {
  system_admin:   '系統管理員',
  tenant_admin:   '據點管理員',
  module_manager: '模組主管',
  viewer:         '一般使用者',
};

export const TENANT_TYPE_LABELS: Record<string, string> = {
  headquarters: '總公司',
  hotel:        '飯店',
  mall:         '商場',
};
