import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';

import {
  closedTradeItem,
  closedTradeReport,
  closedTradeStatistics,
  unavailableClosedTradeStatistics,
} from '../../../test/closedTradesFixtures';
import type { ClosedTradeReport } from '../types/api';
import { ClosedTradeStatistics } from './ClosedTradeStatistics';

const metricIds = ['win-rate', 'average-gross-pnl', 'median-gross-pnl', 'gross-profit-factor'];

function referenceReport(): ClosedTradeReport {
  const report = closedTradeReport();
  return {
    ...report,
    items: [
      closedTradeItem('positive-100', {
        realized_gross_pnl: '100',
        realized_gross_pnl_display: '100.00',
        classification: 'POSITIVE',
      }),
      closedTradeItem('negative-50', {
        realized_gross_pnl: '-50',
        realized_gross_pnl_display: '-50.00',
        classification: 'NEGATIVE',
      }),
      closedTradeItem('neutral', {
        realized_gross_pnl: '0',
        realized_gross_pnl_display: '0.00',
        classification: 'NEUTRAL',
      }),
      closedTradeItem('positive-200', {
        realized_gross_pnl: '200',
        realized_gross_pnl_display: '200.00',
        classification: 'POSITIVE',
      }),
    ],
    summary: { ...report.summary, total: '250', total_display: '250.00' },
    counts: {
      ...report.counts,
      examined: 4,
      in_period: 4,
      qualified: 4,
      positive: 2,
      negative: 1,
      neutral: 1,
    },
    statistics: closedTradeStatistics({
      population: 4,
      win_rate: { raw: '50', display: '50.00', reason: null },
      average_gross_pnl: { raw: '62.5', display: '62.50', reason: null },
      median_gross_pnl: { raw: '50', display: '50.00', reason: null },
      gross_profit_factor: { raw: '6', display: '6.00', reason: null },
    }),
  };
}

function metricCard(id: string) {
  return screen.getByTestId(`closed-trades-${id}`).parentElement!;
}

it('explains each backend metric with its definition, entire population, closing period and unit', () => {
  render(<ClosedTradeStatistics report={referenceReport()} />);

  expect(screen.getByTestId('closed-trades-win-rate')).toHaveTextContent('50,00 %');
  expect(screen.getByTestId('closed-trades-average-gross-pnl')).toHaveTextContent('62,50 EUR');
  expect(screen.getByTestId('closed-trades-median-gross-pnl')).toHaveTextContent('50,00 EUR');
  expect(screen.getByTestId('closed-trades-gross-profit-factor')).toHaveTextContent('6,00');
  for (const id of metricIds) {
    const card = metricCard(id);
    expect(card).toHaveTextContent('vollständige Tradeergebnisse der gesamten Abschlusskohorte');
    expect(card).toHaveTextContent('N = 4');
    expect(card).toHaveTextContent(
      'Zeitraum des Vollabschlusses: 2026-10-01 bis einschließlich 2026-10-31',
    );
    expect(card).toHaveTextContent('Europe/Berlin');
    expect(card).toHaveTextContent('Kohortenwährung: EUR');
  }
  expect(metricCard('win-rate')).toHaveTextContent('Neutrale Trades zählen zu N');
  expect(metricCard('win-rate')).toHaveTextContent('Einheit: Prozent (%)');
  expect(metricCard('average-gross-pnl')).toHaveTextContent('ungerundete Bruttosumme');
  expect(metricCard('average-gross-pnl')).toHaveTextContent('Einheit: EUR');
  expect(metricCard('median-gross-pnl')).toHaveTextContent('bei geradem N Mittelwert');
  expect(metricCard('median-gross-pnl')).toHaveTextContent('Einheit: EUR');
  expect(metricCard('gross-profit-factor')).toHaveTextContent(
    'Betrag der Summe negativer Ergebnisse',
  );
  expect(metricCard('gross-profit-factor')).toHaveTextContent('Einheit: dimensionslos');
});

it.each(['PARTIAL', 'NOT_COMPUTABLE', 'EMPTY'] as const)(
  'preserves %s reasons and distinguishes unavailable population from an empty population',
  (status) => {
    const report = referenceReport();
    const reason =
      status === 'EMPTY'
        ? 'Keine abgeschlossenen Trades in der Auswahl'
        : 'Berichtsgrundlage unvollständig';
    report.summary = {
      ...report.summary,
      status,
      total: status === 'EMPTY' ? '0' : null,
      total_display: status === 'EMPTY' ? '0.00' : null,
      subtotal: status === 'PARTIAL' ? '100' : null,
      subtotal_display: status === 'PARTIAL' ? '100.00' : null,
    };
    report.statistics = unavailableClosedTradeStatistics(status);
    render(<ClosedTradeStatistics report={report} />);

    const population = status === 'EMPTY' ? '0' : 'nicht bestimmt';
    expect(screen.getByTestId('closed-trades-statistics-population')).toHaveTextContent(
      `Population N = ${population}`,
    );
    for (const id of metricIds) {
      expect(screen.getByTestId(`closed-trades-${id}`)).toHaveTextContent(reason);
      expect(metricCard(id)).toHaveTextContent(`N = ${population}`);
      expect(screen.getByTestId(`closed-trades-${id}`)).not.toHaveTextContent(/0,00|100,00/);
    }

    fireEvent.click(screen.getByText('Präzise Kennzahlen und Herkunft'));
    const table = screen.getByRole('table', { name: /Kennzahlen des Abschlussberichts/ });
    for (const row of within(table).getAllByRole('row').slice(1)) {
      const cells = within(row).getAllByRole('cell');
      expect(cells[0]).toHaveTextContent(reason);
      expect(cells[1]).toHaveTextContent(reason);
    }
  },
);

it('shows a valid zero profit factor and preserves the distinct no-loss reason after replacement', () => {
  const report = closedTradeReport({
    statistics: closedTradeStatistics({
      win_rate: { raw: '0', display: '0.00', reason: null },
      average_gross_pnl: { raw: '-3', display: '-3.00', reason: null },
      median_gross_pnl: { raw: '-3', display: '-3.00', reason: null },
      gross_profit_factor: { raw: '0', display: '0.00', reason: null },
    }),
  });
  const { rerender } = render(<ClosedTradeStatistics report={report} />);
  expect(screen.getByTestId('closed-trades-gross-profit-factor')).toHaveTextContent(/^0,00$/);
  expect(screen.getByTestId('closed-trades-win-rate')).toHaveTextContent(/^0,00 %$/);

  rerender(<ClosedTradeStatistics report={closedTradeReport()} />);
  expect(screen.getByTestId('closed-trades-gross-profit-factor')).toHaveTextContent(
    'Nicht definiert: keine Verlusttrades',
  );
  expect(screen.getByTestId('closed-trades-gross-profit-factor')).not.toHaveTextContent(
    /0,00|Infinity|NaN/,
  );
});

it('keeps exact long decimals and backend HALF_EVEN display strings without parsing or rerounding', () => {
  const report = closedTradeReport({
    statistics: closedTradeStatistics({
      population: 32,
      win_rate: { raw: '3.125', display: '3.12', reason: null },
      average_gross_pnl: {
        raw: '9007199254740993.0000000000000000001',
        display: '9007199254740993.00',
        reason: null,
      },
      median_gross_pnl: { raw: '-0.004', display: '0.00', reason: null },
      gross_profit_factor: { raw: '1.005', display: '1.00', reason: null },
    }),
  });
  render(<ClosedTradeStatistics report={report} />);
  expect(screen.getByTestId('closed-trades-win-rate')).toHaveTextContent('3,12 %');
  expect(screen.getByTestId('closed-trades-average-gross-pnl')).toHaveTextContent(
    '9007199254740993,00 EUR',
  );
  expect(screen.getByTestId('closed-trades-median-gross-pnl')).toHaveTextContent('0,00 EUR');
  expect(screen.getByTestId('closed-trades-gross-profit-factor')).toHaveTextContent('1,00');
  fireEvent.click(screen.getByText('Präzise Kennzahlen und Herkunft'));
  const table = within(screen.getByRole('table', { name: /Kennzahlen des Abschlussberichts/ }));
  expect(table.getByText('9007199254740993.0000000000000000001')).toBeVisible();
  expect(table.getByText('-0.004')).toBeVisible();
  expect(table.getByText('3.125')).toBeVisible();
  expect(table.getByText('1.005')).toBeVisible();
  expect(screen.getByText(/ROUND_HALF_EVEN/)).toBeVisible();
});

it('provides a keyboard-reachable semantic table while replacing metrics, population and context together', async () => {
  const user = userEvent.setup();
  const report = referenceReport();
  const { rerender } = render(<ClosedTradeStatistics report={report} />);
  const detailsToggle = screen.getByText('Präzise Kennzahlen und Herkunft');
  await user.click(detailsToggle);
  await user.tab();
  const scrollRegion = screen.getByRole('region', {
    name: 'Kennzahlentabelle, bei Bedarf horizontal scrollbar',
  });
  expect(scrollRegion).toHaveFocus();
  const table = within(scrollRegion).getByRole('table', {
    name: /Kennzahlen des Abschlussberichts/,
  });
  expect(within(table).getAllByRole('columnheader')).toHaveLength(3);
  expect(within(table).getAllByRole('rowheader')).toHaveLength(4);
  expect(within(table).getByText('62.5')).toBeVisible();

  const replacement = closedTradeReport({
    filters: {
      from_date: '2026-09-01',
      to_date: '2026-09-30',
      report_timezone: 'America/New_York',
      report_currency: 'EUR',
    },
    basis: { ...report.basis, id: 'b'.repeat(64) },
    statistics: closedTradeStatistics({ report_basis_id: 'b'.repeat(64) }),
  });
  rerender(<ClosedTradeStatistics report={replacement} />);
  for (const id of metricIds) {
    expect(metricCard(id)).toHaveTextContent('N = 1');
    expect(metricCard(id)).toHaveTextContent('2026-09-01 bis einschließlich 2026-09-30');
    expect(metricCard(id)).toHaveTextContent('America/New_York');
    expect(metricCard(id)).not.toHaveTextContent('Europe/Berlin');
  }
  expect(screen.getByText('b'.repeat(64))).toBeVisible();
  expect(screen.queryByText('a'.repeat(64))).not.toBeInTheDocument();
  expect(screen.queryByText('62.5')).not.toBeInTheDocument();
  expect(screen.getByTestId('closed-trades-average-gross-pnl')).toHaveTextContent('50,00 EUR');
});

it('labels an absent value explicitly even if its optional reason is not supplied', () => {
  const report = closedTradeReport({
    statistics: closedTradeStatistics({
      gross_profit_factor: { raw: null, display: null, reason: null },
    }),
  });
  render(<ClosedTradeStatistics report={report} />);
  expect(screen.getByTestId('closed-trades-gross-profit-factor')).toHaveTextContent(
    'Nicht verfügbar',
  );
  fireEvent.click(screen.getByText('Präzise Kennzahlen und Herkunft'));
  const table = screen.getByRole('table', { name: /Kennzahlen des Abschlussberichts/ });
  const row = within(table).getAllByRole('row')[4];
  expect(
    within(row)
      .getAllByRole('cell')
      .every((cell) => cell.textContent === 'Nicht verfügbar'),
  ).toBe(true);
});
