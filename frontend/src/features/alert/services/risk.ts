import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { RiskParameters, RiskView } from '../types/risk';
const url = (id: string) =>
  `${environment.apiBaseUrl}/api/v1/position-monitoring/trades/${encodeURIComponent(id)}/risk`;
export const riskApi = {
  read: async (id: string, signal?: AbortSignal) => {
    const value = await requestJson<RiskView>(url(id), { signal });
    if (!value || value.trade_id !== id || !value.configuration || !value.metrics) {
      throw new Error('Unvollständige oder fremde Risikoauswertung');
    }
    return value;
  },
  history: (id: string, signal?: AbortSignal) =>
    requestJson<RiskView[]>(`${url(id)}/history`, { signal }),
  evaluate: (id: string) => requestJson<RiskView>(`${url(id)}/evaluations`, { method: 'POST' }),
  preview: (id: string, parameters: RiskParameters) =>
    requestJson<RiskView>(`${url(id)}/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: { parameters },
    }),
  configure: (
    id: string,
    view: Pick<RiskView, 'configuration'>,
    parameters: RiskParameters,
    enabled: boolean,
  ) =>
    requestJson(`${url(id)}/configuration`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: {
        parameters,
        enabled,
        expected_revision: view.configuration.revision,
        confirmation: 'CONFIRM_POSITION_RISK_CONFIGURATION',
      },
    }),
};
