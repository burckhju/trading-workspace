import { position } from '../../../test/positionFixture';
import {
  decimalUnits,
  defaultPositionsView,
  hasDataProblem,
  portfolioTotals,
  visiblePositions,
} from './positionsView';

const qualified = (id: string, pnl: string) => ({
  ...position({ position_id: id, product_name: id, unrealized_gross_pnl: pnl }),
  unrealized_pnl_usable: true,
  unrealized_pnl_reason: 'COST_BASIS_CURRENCY_MATCHED',
});

it.each([
  'COST_BASIS_CURRENCY_UNKNOWN',
  'COST_BASIS_CURRENCY_MIXED',
  'COST_BASIS_CURRENCY_MISMATCH',
])('excludes %s from PnL decisions and totals while preserving market value', (reason) => {
  // Deliberately retain the former erroneous number: every consumer must fail closed.
  const blocked = {
    ...qualified('Blocked', '999'),
    unrealized_pnl_usable: false,
    unrealized_pnl_reason: reason,
  };
  const gain = qualified('Gain', '5');
  const loss = qualified('Loss', '-2');
  const neutral = qualified('Neutral', '0E-10');
  const rows = [blocked, gain, loss, neutral];

  expect(hasDataProblem(blocked)).toBe(true);
  expect(visiblePositions(rows, { ...defaultPositionsView, filter: 'gains' })).toEqual([gain]);
  expect(visiblePositions(rows, { ...defaultPositionsView, filter: 'losses' })).toEqual([loss]);
  for (const descending of [false, true]) {
    expect(
      visiblePositions(rows, { ...defaultPositionsView, sort: 'pnl', descending }).at(-1),
    ).toBe(blocked);
  }
  expect(portfolioTotals(rows)).toEqual([
    [
      'EUR',
      expect.objectContaining({
        count: 4,
        valued: 4,
        value: decimalUnits('100'),
        pnlCount: 3,
        pnl: decimalUnits('3'),
      }),
    ],
  ]);
});

it('requires explicit PnL qualification and does not turn an entirely uncovered sum into zero', () => {
  const missing = position();
  Reflect.deleteProperty(missing, 'unrealized_pnl_usable');
  const blockedLoss = {
    ...qualified('Unqualified loss', '-5'),
    unrealized_pnl_usable: false,
    unrealized_pnl_reason: 'COST_BASIS_CURRENCY_UNKNOWN',
  };
  const rows = [missing, blockedLoss];
  expect(visiblePositions(rows, { ...defaultPositionsView, filter: 'gains' })).toEqual([]);
  expect(visiblePositions(rows, { ...defaultPositionsView, filter: 'losses' })).toEqual([]);
  expect(portfolioTotals(rows)[0][1]).toMatchObject({ valued: 2, pnlCount: 0 });
});
