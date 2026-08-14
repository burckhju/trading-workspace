import { beforeEach, describe, expect, it, vi } from 'vitest';

import { requestJson } from '../../market/services/http';
import { topDownAdminClient } from './topDownAdminClient';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
const mockedRequestJson = vi.mocked(requestJson);

describe('topDownAdminClient', () => {
  beforeEach(() => {
    mockedRequestJson.mockReset();
    mockedRequestJson.mockResolvedValue({} as never);
  });

  it('covers read methods', async () => {
    await topDownAdminClient.references();
    await topDownAdminClient.sectors();
    await topDownAdminClient.mappings();
    expect(mockedRequestJson).toHaveBeenCalledTimes(3);
  });

  it('covers assignment and activation methods', async () => {
    await topDownAdminClient.assignBenchmark('u1', 'r1');
    await topDownAdminClient.assignSector('u1', 's1');
    await topDownAdminClient.assignSectorReference('s1', 'r2');
    await topDownAdminClient.assignReferenceListing('r2', 'l1');
    await topDownAdminClient.createMapping('l1', 'SAP', 'XETRA');
    await topDownAdminClient.validateMapping('m1');
    await topDownAdminClient.venueReconciliation('m1');
    await topDownAdminClient.activateReference('r1');
    await topDownAdminClient.activateSector('s1');
    expect(mockedRequestJson).toHaveBeenCalledTimes(9);
  });

  it('covers import and analysis methods', async () => {
    mockedRequestJson
      .mockResolvedValueOnce({} as never)
      .mockResolvedValueOnce({ id: 'a1', underlying_id: 'u1', listing_id: 'l1' } as never)
      .mockResolvedValueOnce({} as never);

    await topDownAdminClient.importHistory('l1', 'm1', '2026-01-01', '2026-08-01');
    const analysis = await topDownAdminClient.createAnalysis('u1', 'l1');
    await topDownAdminClient.runAnalysis(analysis.id, '2026-01-01', '2026-08-01');

    expect(analysis.id).toBe('a1');
    expect(mockedRequestJson).toHaveBeenCalledTimes(3);
  });
});
