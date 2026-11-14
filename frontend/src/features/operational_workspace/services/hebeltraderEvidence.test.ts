import { MarketApiError, requestJson } from '../../market/services/http';
import { hebeltraderEvidence, hebeltraderSource } from '../../../test/hebeltraderEvidenceFixture';
import { readHebeltraderEvidence } from './hebeltraderEvidence';

vi.mock('../../market/services/http', async (original) => ({
  ...(await original<typeof import('../../market/services/http')>()),
  requestJson: vi.fn(),
}));

it('uses only the owner GET with exact position identity and cancellation', async () => {
  const report = hebeltraderEvidence({
    trade_id: 'trade/a',
    position_id: 'position/b',
    source: hebeltraderSource(),
  });
  vi.mocked(requestJson).mockResolvedValueOnce(report);
  const signal = new AbortController().signal;
  expect(await readHebeltraderEvidence('trade/a', 'position/b', signal)).toBe(report);
  expect(requestJson).toHaveBeenCalledOnce();
  expect(requestJson).toHaveBeenCalledWith(
    expect.stringMatching(/trades\/trade%2Fa\/hebeltrader-evidence\?position_id=position%2Fb$/),
    { signal },
  );
});

it('rejects mixed identities, source identities, unknown statuses and malformed rows', async () => {
  for (const invalid of [
    null,
    [],
    hebeltraderEvidence({ trade_id: 'other' }),
    hebeltraderEvidence({ position_id: 'other' }),
    { ...hebeltraderEvidence(), definition_version: 'future-version' },
    { ...hebeltraderEvidence(), implementation_status: 'ACTIVE' },
    { ...hebeltraderEvidence(), operation_status: 'RUNNING' },
    { ...hebeltraderEvidence(), coverage_status: 'HEALTHY' },
    { ...hebeltraderEvidence(), items: null },
    { ...hebeltraderEvidence(), items: [{ ...hebeltraderEvidence().items[0], status: 'HEALTHY' }] },
    { ...hebeltraderEvidence(), items: [{ ...hebeltraderEvidence().items[0], references: null }] },
    hebeltraderEvidence({ source: hebeltraderSource({ product_id: 'other' }) }),
    hebeltraderEvidence({ source: hebeltraderSource({ underlying_id: 'other' }) }),
    { ...hebeltraderEvidence(), assigned_z1_sold_quantity: -1 },
    { ...hebeltraderEvidence(), evidence_revision_id: undefined },
    { ...hebeltraderEvidence(), source: { ...hebeltraderSource(), currentness: 'FUTURE' } },
    { ...hebeltraderEvidence(), source: { ...hebeltraderSource(), recorded_at: undefined } },
    hebeltraderEvidence({
      source: hebeltraderSource({
        underlying: {
          ...hebeltraderSource().underlying,
          binding: { basis: 'WARRANT', instrument_id: 'underlying-1', currency: 'USD' },
        },
      }),
    }),
    {
      ...hebeltraderEvidence(),
      source: {
        ...hebeltraderSource(),
        product: { ...hebeltraderSource().product, scale: 'ADJUSTED' },
      },
    },
    { ...hebeltraderEvidence(), source: {} },
  ]) {
    vi.mocked(requestJson).mockResolvedValueOnce(invalid);
    await expect(readHebeltraderEvidence('trade-1', 'position-1')).rejects.toThrow(
      'nicht sicher zuordnen',
    );
  }
});

it('keeps missing permission separate from unavailable reads', async () => {
  vi.mocked(requestJson).mockRejectedValueOnce(
    new MarketApiError(403, {
      code: 'FORBIDDEN',
      message: 'Forbidden',
      details: [],
      timestamp: '2026-11-14T10:00:00Z',
    }),
  );
  await expect(readHebeltraderEvidence('trade-1', 'position-1')).rejects.toThrow(
    'Keine Berechtigung',
  );
  vi.mocked(requestJson).mockRejectedValueOnce(new Error('unavailable'));
  await expect(readHebeltraderEvidence('trade-1', 'position-1')).rejects.toThrow(
    'Fehlende Belege sind damit nicht festgestellt',
  );
});
