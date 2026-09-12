import { environment } from '../../../services/environment';
import { requestJson } from './http';

export interface CatalogEntry {
  code: string;
  name: string;
  numeric_code: string;
  minor_unit: number;
  kind: 'CURRENCY';
}
export interface CurrencyCatalog {
  schema_version: 1;
  version: string;
  source_url: string;
  source_sha256: string;
  source_published_on: string;
  scope: string;
  entries: CatalogEntry[];
}
export interface AdminCurrency {
  code: string;
  name: string;
  minor_unit: number;
  catalog_name: string | null;
  catalog_minor_unit: number | null;
  numeric_code: string | null;
  local_exists: boolean;
  is_active: boolean;
  catalog_available: boolean;
  minor_unit_conflict: boolean;
  can_activate: boolean;
  reference_version: string | null;
  state_token: string;
}
export interface CurrencyAdminResponse {
  catalog: CurrencyCatalog | null;
  catalog_checksum: string | null;
  items: AdminCurrency[];
}
export interface CatalogPreview {
  catalog: CurrencyCatalog;
  checksum: string;
  current_version: string | null;
  already_current: boolean;
  preview_token: string;
  changes: {
    code: string;
    change: 'NEW' | 'UNCHANGED' | 'CHANGED' | 'NOT_IN_NEW_CATALOG';
    before: CatalogEntry | null;
    after: CatalogEntry | null;
  }[];
}
export interface CurrencyAudit {
  id: string;
  occurred_at: string;
  actor: string;
  action: string;
  aggregate_type: string;
  changes: Record<string, { old: unknown; new: unknown }>;
}

const root = `${environment.apiBaseUrl}/api/v1/market-reference-data/currencies`;
export const currencyAdminClient = {
  list: (signal?: AbortSignal) => requestJson<CurrencyAdminResponse>(`${root}/admin`, { signal }),
  history: (signal?: AbortSignal) =>
    requestJson<{ items: CurrencyAudit[] }>(`${root}/admin/history`, { signal }),
  preview: (catalogJson: string | null) =>
    requestJson<CatalogPreview>(`${root}/catalog/preview`, {
      method: 'POST',
      body: { catalog_json: catalogJson },
    }),
  import: (catalogJson: string | null, token: string) =>
    requestJson<{ applied: boolean; version: string; checksum: string }>(`${root}/catalog/import`, {
      method: 'POST',
      body: { catalog_json: catalogJson, expected_preview_token: token, reviewed: true },
    }),
  changeStatus: (code: string, active: boolean, token: string) =>
    requestJson<{ code: string; is_active: boolean; changed: boolean }>(
      `${root}/${encodeURIComponent(code)}/${active ? 'activate' : 'deactivate'}`,
      { method: 'POST', body: { expected_token: token } },
    ),
};
