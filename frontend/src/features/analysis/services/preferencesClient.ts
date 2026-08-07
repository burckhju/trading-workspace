import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { AnalysisOverviewView } from './savedViews';

const kind = 'analysis-overview-view';
const baseUrl = `${environment.apiBaseUrl}/api/v1/user-preferences/${kind}`;

export type PreferenceResponse = {
  id: string;
  kind: string;
  name: string;
  value: Omit<AnalysisOverviewView, 'id' | 'name'>;
  created_at: string;
  updated_at: string;
};

function toView(item: PreferenceResponse): AnalysisOverviewView {
  return { id: item.id, name: item.name, ...item.value };
}

export const analysisPreferenceClient = {
  async list(signal?: AbortSignal): Promise<AnalysisOverviewView[]> {
    const items = await requestJson<PreferenceResponse[]>(baseUrl, { signal });
    return items.map(toView);
  },
  async create(view: Omit<AnalysisOverviewView, 'id'>): Promise<AnalysisOverviewView> {
    const { name, ...value } = view;
    const item = await requestJson<PreferenceResponse>(baseUrl, {
      method: 'POST',
      body: { name, value },
    });
    return toView(item);
  },
  async delete(id: string): Promise<void> {
    await requestJson<void>(`${baseUrl}/${id}`, { method: 'DELETE' });
  },
};
