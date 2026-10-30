import { requestJson } from '../../market/services/http';
import { positionPriceHistory } from '../../../test/positionPriceHistoryFixtures';
import { readPositionPriceHistory } from './positionPriceHistory';
import { historyPrice, historyTime, priceHistoryLabel } from './priceHistoryPresentation';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));

it('reads all stored history by default and passes bounded windows and cancellation unchanged', async () => {
  const report = positionPriceHistory({ trade_id: 'trade/a' });
  vi.mocked(requestJson).mockResolvedValue(report);
  const signal = new AbortController().signal;
  expect(await readPositionPriceHistory('trade/a', 'position-1', 'all', signal)).toBe(report);
  expect(requestJson).toHaveBeenLastCalledWith(
    expect.stringMatching(/\/trade-position\/trades\/trade%2Fa\/price-history$/),
    { signal },
  );
  await readPositionPriceHistory('trade/a', 'position-1', '31', signal);
  expect(requestJson).toHaveBeenLastCalledWith(expect.stringMatching(/price-history\?days=31$/), {
    signal,
  });
});

it('rejects wrong identities and unknown shapes rather than presenting empty history', async () => {
  for (const invalid of [
    null,
    [],
    positionPriceHistory({ trade_id: 'other' }),
    positionPriceHistory({ position_id: 'other' }),
    { ...positionPriceHistory(), series: null },
    { ...positionPriceHistory(), events: null },
    { ...positionPriceHistory(), excluded: null },
    { ...positionPriceHistory(), series: [{ points: null }] },
  ]) {
    vi.mocked(requestJson).mockResolvedValueOnce(invalid);
    await expect(readPositionPriceHistory('trade-1', 'position-1', 'all')).rejects.toThrow(
      'nicht sicher zuordnen',
    );
  }
});

it('does not round original decimal evidence and uses explicit UTC labels', () => {
  expect(historyPrice('0.2312345678')).toBe('0,2312345678');
  expect(historyTime('2026-10-25T02:30:00+02:00')).toBe('25.10.2026, 00:30:00 UTC');
  expect(historyTime(null)).toBe('Unbekannt');
  expect(priceHistoryLabel('TIMESTAMP_UNKNOWN')).toBe('Originalkurszeit unbekannt');
  expect(priceHistoryLabel('NEW_CODE')).toBe('NEW_CODE');
});
