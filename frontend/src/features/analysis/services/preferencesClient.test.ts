import { beforeEach, describe, expect, it, vi } from 'vitest';

import { analysisPreferenceClient } from './preferencesClient';
import { requestJson } from '../../market/services/http';

vi.mock('../../market/services/http', () => ({
  requestJson: vi.fn(),
}));

const requestJsonMock = vi.mocked(requestJson);

describe('analysisPreferenceClient', () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
  });

  it('loads and maps persisted analysis overview views', async () => {
    const signal = new AbortController().signal;

    requestJsonMock.mockResolvedValue([
      {
        id: 'preference-1',
        kind: 'analysis-overview-view',
        name: 'Meine Ansicht',
        value: {
          underlyingId: 'underlying-1',
          underlyingLabel: 'Siemens AG',
          status: 'COMPLETED',
          qualityStatus: 'GOOD',
          analysisTimeFrom: '',
          analysisTimeTo: '',
          sortBy: 'created_at',
          sortDirection: 'desc',
        },
        created_at: '2026-08-07T10:00:00Z',
        updated_at: '2026-08-07T10:00:00Z',
      },
    ]);

    await expect(analysisPreferenceClient.list(signal)).resolves.toEqual([
      {
        id: 'preference-1',
        name: 'Meine Ansicht',
        underlyingId: 'underlying-1',
        underlyingLabel: 'Siemens AG',
        status: 'COMPLETED',
        qualityStatus: 'GOOD',
        analysisTimeFrom: '',
        analysisTimeTo: '',
        sortBy: 'created_at',
        sortDirection: 'desc',
      },
    ]);

    expect(requestJsonMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/user-preferences/analysis-overview-view'),
      { signal },
    );
  });

  it('creates and deletes persisted views', async () => {
    const view = {
      name: 'Meine Ansicht',
      underlyingId: 'underlying-1',
      underlyingLabel: 'Siemens AG',
      status: '',
      qualityStatus: '',
      analysisTimeFrom: '',
      analysisTimeTo: '',
      sortBy: 'created_at',
      sortDirection: 'desc',
    };

    requestJsonMock.mockResolvedValueOnce({
      id: 'preference-1',
      kind: 'analysis-overview-view',
      name: view.name,
      value: {
        underlyingId: view.underlyingId,
        underlyingLabel: view.underlyingLabel,
        status: view.status,
        qualityStatus: view.qualityStatus,
        analysisTimeFrom: view.analysisTimeFrom,
        analysisTimeTo: view.analysisTimeTo,
        sortBy: view.sortBy,
        sortDirection: view.sortDirection,
      },
      created_at: '2026-08-07T10:00:00Z',
      updated_at: '2026-08-07T10:00:00Z',
    });

    await expect(analysisPreferenceClient.create(view)).resolves.toMatchObject({
      id: 'preference-1',
      name: 'Meine Ansicht',
      underlyingId: 'underlying-1',
    });

    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/api/v1/user-preferences/analysis-overview-view'),
      {
        method: 'POST',
        body: {
          name: 'Meine Ansicht',
          value: {
            underlyingId: 'underlying-1',
            underlyingLabel: 'Siemens AG',
            status: '',
            qualityStatus: '',
            analysisTimeFrom: '',
            analysisTimeTo: '',
            sortBy: 'created_at',
            sortDirection: 'desc',
          },
        },
      },
    );

    requestJsonMock.mockResolvedValueOnce(undefined);

    await analysisPreferenceClient.delete('preference-1');

    expect(requestJsonMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/api/v1/user-preferences/analysis-overview-view/preference-1'),
      { method: 'DELETE' },
    );
  });
});
