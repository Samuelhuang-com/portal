import client from './client';
import type { Tenant } from '../types';

export const tenantsApi = {
  list: () => client.get<Tenant[]>('/tenants'),
  create: (data: { code: string; name: string; type: string }) =>
    client.post<Tenant>('/tenants', data),
};
