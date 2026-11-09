import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { ChartWatchlist } from '../types/watchlist';

const base = environment.apiBaseUrl + '/api/v1/market-charts/watchlist';

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function nullableText(value: unknown): boolean {
  return value === null || typeof value === 'string';
}

function fields(value: unknown, keys: string[], accepts: (value: unknown) => boolean): boolean {
  return record(value) && keys.every((key) => accepts(value[key]));
}

function readContract(value: unknown): ChartWatchlist {
  if (
    !record(value) ||
    typeof value.catalog_version !== 'string' ||
    !value.catalog_version ||
    typeof value.name !== 'string' ||
    typeof value.enabled !== 'boolean' ||
    !Array.isArray(value.items) ||
    !value.items.length ||
    !record(value.scheduler) ||
    !fields(
      value.scheduler,
      ['enabled', 'running', 'leader'],
      (item) => typeof item === 'boolean',
    ) ||
    !nullableText(value.scheduler.last_error) ||
    (value.scheduler.provider_enabled !== undefined &&
      typeof value.scheduler.provider_enabled !== 'boolean')
  )
    throw new Error('Der gespeicherte Marktübersichtsstand ist unvollständig.');

  const codes = new Set<string>();
  for (const item of value.items) {
    if (
      !record(item) ||
      typeof item.code !== 'string' ||
      !item.code ||
      codes.has(item.code) ||
      !['INDEX', 'ETF'].includes(String(item.kind)) ||
      !['name', 'group', 'source_url'].every((key) => typeof item[key] === 'string') ||
      ![
        'isin',
        'mic',
        'currency',
        'ticker',
        'setup_reason',
        'last_attempt_at',
        'setup_completed_at',
      ].every((key) => nullableText(item[key])) ||
      !(
        item.target_key === null ||
        (typeof item.target_key === 'string' &&
          item.target_key.startsWith(item.kind === 'INDEX' ? 'reference:' : 'listing:'))
      ) ||
      !['PENDING', 'CONFIGURED', 'BLOCKED'].includes(String(item.setup_status)) ||
      !record(item.history) ||
      !fields(item.history, ['first_date', 'last_date', 'last_received_at'], nullableText) ||
      !Number.isInteger(item.history.observation_count) ||
      Number(item.history.observation_count) < 0 ||
      !(
        item.refresh == null ||
        (record(item.refresh) &&
          item.refresh.scope === 'PROCESS_LOCAL' &&
          typeof item.refresh.status === 'string' &&
          item.refresh.status.length > 0 &&
          fields(
            item.refresh,
            ['reason', 'checked_at', 'last_success_at', 'next_run_at'],
            nullableText,
          ))
      ) ||
      !(
        item.mapping === null ||
        (record(item.mapping) &&
          fields(
            item.mapping,
            ['id', 'status', 'provider_symbol', 'provider_exchange_code'],
            (field) => typeof field === 'string',
          ) &&
          Number.isInteger(item.mapping.version) &&
          Number(item.mapping.version) >= 1 &&
          nullableText(item.mapping.validated_at))
      )
    )
      throw new Error(
        'Eine Marktübersichtsreihe enthält unvollständige oder widersprüchliche Identitätsdaten.',
      );
    codes.add(item.code);
  }
  return value as unknown as ChartWatchlist;
}

export const watchlistClient = {
  read: async (signal?: AbortSignal) => readContract(await requestJson<unknown>(base, { signal })),
  activate: async (catalogVersion: string) => {
    const result = readContract(
      await requestJson<unknown>(base + '/activate', {
        method: 'POST',
        body: { catalog_version: catalogVersion, confirmed: true },
      }),
    );
    if (!result.enabled || result.catalog_version !== catalogVersion) {
      throw new Error('Die Aktivierungsantwort bestätigt nicht den geprüften Katalog.');
    }
    return result;
  },
};
