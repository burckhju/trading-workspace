import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';

import { realizedGrossReport, reportItem } from '../../../test/realizedGrossFixtures';
import { RealizedGrossVisualization } from './RealizedGrossVisualization';

vi.mock('./RealizedGrossPlot', () => {
  throw new Error('Synthetic missing SELL chart chunk');
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it('keeps all original SELL rows, dates and source actions available when the optional chart import fails', async () => {
  const user = userEvent.setup();
  const report = realizedGrossReport({
    items: [
      ...Array.from({ length: 20 }, (_, index) => reportItem(`sale-${index + 1}`)),
      reportItem('last-date-only-sale', {
        time_precision: 'DATE_ONLY',
        executed_at: null,
        executed_on: '2026-09-10',
        execution_timezone: 'America/New_York',
        realized_gross_pnl_delta: '0.12345678901234567890',
        realized_gross_pnl_delta_display: '0.12',
      }),
    ],
  });
  const original = structuredClone(report);
  const onOpenSources = vi.fn();
  const logged = vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.stubGlobal('fetch', vi.fn());
  render(<RealizedGrossVisualization report={report} onOpenSources={onOpenSources} />);

  expect(await screen.findByText(/Das Diagramm konnte nicht geladen werden/)).toBeVisible();
  expect(screen.getAllByText(/Das Diagramm konnte nicht geladen werden/)).toHaveLength(1);
  expect(screen.queryByText(/Keine grafisch darstellbaren Geldpunkte/)).not.toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(logged.mock.calls.flat()).toContainEqual(
    expect.objectContaining({ message: 'Optional SELL plot could not load.' }),
  );
  const table = screen.getByRole('region', { name: 'SELL-Datentabelle' });
  expect(within(table).getAllByRole('row')).toHaveLength(21);
  table.focus();
  await user.tab();
  expect(screen.getByRole('button', { name: 'Originalquellen zu SELL 1' })).toHaveFocus();
  screen.getByRole('button', { name: 'Nächste Grafikseite' }).focus();
  await user.keyboard('{Enter}');
  expect(within(table).getAllByRole('row')).toHaveLength(2);
  expect(within(table).getByText('last-date-only-sale')).toBeVisible();
  expect(within(table).getByText('0.12345678901234567890')).toBeVisible();
  expect(within(table).getByText('0,12 EUR')).toBeVisible();
  expect(
    within(table).getByText('2026-09-10 · Uhrzeit unbekannt · America/New_York'),
  ).toBeVisible();
  expect(screen.getAllByText(/Das Diagramm konnte nicht geladen werden/)).toHaveLength(1);
  screen.getByRole('button', { name: 'Originalquellen zu SELL 21' }).focus();
  await user.keyboard(' ');
  expect(onOpenSources).toHaveBeenCalledExactlyOnceWith(report.items[20]);
  expect(report).toEqual(original);
  expect(fetch).not.toHaveBeenCalled();
});
