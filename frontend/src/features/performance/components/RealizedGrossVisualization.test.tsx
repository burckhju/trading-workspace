import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  realizedGrossReport,
  reportFilters,
  reportItem,
  reportSource,
} from '../../../test/realizedGrossFixtures';
import { PerformanceWorkspace } from '../pages/PerformanceWorkspace';
import { performanceApiClient } from '../services/client';
import type { RealizedGrossItem, RealizedGrossReport } from '../types/api';
import type { SellPlotEntry } from './RealizedGrossPlot';
import { RealizedGrossVisualization } from './RealizedGrossVisualization';

const renderer = vi.hoisted(() => ({ render: vi.fn(), fail: false }));
vi.mock('./RealizedGrossPlot', () => ({
  RealizedGrossPlot: (props: { entries: SellPlotEntry[]; ordinals: number[]; extent: number }) => {
    renderer.render(props);
    if (renderer.fail) throw new Error('Synthetic SELL plot render failure');
    return <div data-testid="sell-plot" aria-hidden="true" />;
  },
}));
vi.mock('../services/client', () => ({
  performanceApiClient: { realizedGross: vi.fn(), closedTrades: vi.fn() },
}));
const api = vi.mocked(performanceApiClient);

function visualization() {
  return screen.getByRole('region', { name: 'Einzelne SELL-Beiträge' });
}

function row(id: string) {
  const table = screen.getByRole('table', { name: 'SELL-Beiträge und Originalwerte' });
  return within(within(table).getByText(id, { exact: true }).closest('tr')!);
}

function lastPlot() {
  return renderer.render.mock.lastCall![0] as {
    entries: SellPlotEntry[];
    ordinals: number[];
    extent: number;
  };
}

function manySales(): RealizedGrossReport {
  const items = Array.from({ length: 21 }, (_, index) =>
    reportItem(`sell-${index + 1}`, {
      realized_gross_pnl_delta: index === 20 ? '-80.0000000000' : '30.0000000000',
      realized_gross_pnl_delta_display: index === 20 ? '-80.00' : '30.00',
    }),
  );
  return realizedGrossReport({
    items,
    sources: [
      reportSource('buy-august'),
      reportSource('sell-august', { side: 'SELL' }),
      ...items.map((item) =>
        reportSource(item.execution_id, {
          side: 'SELL',
          quantity: item.quantity,
          price_per_unit: item.price_per_unit,
          executed_at: item.executed_at,
        }),
      ),
    ],
    summary: {
      status: 'COMPLETE',
      total: '520.0000000000',
      total_display: '520.00',
      subtotal: null,
      subtotal_display: null,
      rounding_difference: '0.00',
      rounding_difference_display: '0.00',
    },
    counts: {
      examined: 21,
      in_period: 21,
      outside_period: 0,
      period_ambiguous: 0,
      period_unknown: 0,
      candidates: 21,
      usable: 21,
      unresolved: 0,
      excluded: 0,
      cancelled: 0,
    },
  });
}

function mountWorkspace() {
  const router = createMemoryRouter(
    [
      {
        path: '/performance/realized-gross',
        element: <PerformanceWorkspace kind="realized-gross" />,
      },
    ],
    {
      initialEntries: [
        `/performance/realized-gross?${new URLSearchParams({
          report_context: 'realized-gross',
          ...reportFilters,
          report_view: 'candidates',
          report_page: '1',
          report_basis: 'a'.repeat(64),
        })}`,
      ],
    },
  );
  return { router, ...render(<RouterProvider router={router} />) };
}

beforeEach(() => {
  renderer.fail = false;
  renderer.render.mockClear();
  api.realizedGross.mockReset();
  api.closedTrades.mockReset();
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Unexpected visualization request')));
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('SELL event visualization and equivalent original table', () => {
  it('labels the SELL population, reporting period and currency without creating a time axis or closed-trade statistics', async () => {
    const items: RealizedGrossItem[] = [
      reportItem('date-only', {
        time_precision: 'DATE_ONLY',
        executed_at: null,
        executed_on: '2026-09-10',
        execution_timezone: 'America/New_York',
        possible_start_at: '2026-09-10T04:00:00Z',
        possible_end_at: '2026-09-11T04:00:00Z',
      }),
      reportItem('exact-zero', {
        realized_gross_pnl_delta: '0.0000000000',
        realized_gross_pnl_delta_display: '0.00',
      }),
      reportItem('unknown-sale', {
        status: 'NOT_COMPUTABLE',
        currency_code: null,
        realized_gross_pnl_delta: null,
        realized_gross_pnl_delta_display: null,
        reasons: ['CURRENCY_UNKNOWN'],
      }),
      reportItem('excluded-sale', {
        status: 'EXCLUDED',
        period_status: 'OUTSIDE_PERIOD',
        reasons: ['OUTSIDE_PERIOD'],
      }),
    ];
    const report = realizedGrossReport({
      items,
      counts: {
        ...realizedGrossReport().counts,
        examined: 4,
        in_period: 3,
        usable: 2,
        unresolved: 1,
        excluded: 1,
        candidates: 3,
        outside_period: 1,
      },
      summary: {
        status: 'PARTIAL',
        total: null,
        total_display: null,
        subtotal: '30.0000000000',
        subtotal_display: '30.00',
        rounding_difference: '0.00',
        rounding_difference_display: '0.00',
      },
    });
    const original = structuredClone(report);
    render(<RealizedGrossVisualization report={report} onOpenSources={vi.fn()} />);
    await screen.findByTestId('sell-plot');

    const section = within(visualization());
    expect(section.getByText(/Auch Teilverkäufe offener Trades/)).toBeVisible();
    expect(section.getByText(/2026-09-01 bis einschließlich 2026-09-30/)).toHaveTextContent(
      'Europe/Berlin · EUR · keine Währungsumrechnung',
    );
    expect(section.getByText(/4 wirksame SELLs geprüft/)).toHaveTextContent(
      '2 verwendbare Beiträge · 1 ungeklärte Fälle · 1 ausgeschlossene SELLs',
    );
    expect(section.getByText(/4 wirksame SELLs geprüft/)).toHaveTextContent(
      'überlappende Sichten und werden nicht addiert',
    );
    expect(section.getByText(/Die vollständige Bruttosumme ist unbekannt/)).toBeVisible();
    expect(section.getByText(/Abstände sind keine Zeitabstände/)).toHaveTextContent(
      'keine Tages- oder Monatssummen',
    );
    expect(lastPlot()).toEqual({
      entries: [
        { ordinal: 1, executionId: 'date-only', value: 30 },
        { ordinal: 2, executionId: 'exact-zero', value: 0 },
      ],
      ordinals: [1, 2, 3, 4],
      extent: 30,
    });
    expect(
      row('date-only').getByText('2026-09-10 · Uhrzeit unbekannt · America/New_York'),
    ).toBeVisible();
    expect(row('date-only').queryByText(/00:00|04:00/)).not.toBeInTheDocument();
    expect(row('exact-zero').getByText('0,00 EUR')).toBeVisible();
    expect(row('exact-zero').getByText(/Exakter Nullbeitrag/)).toBeVisible();
    expect(row('unknown-sale').getByText('Nicht berechenbar')).toBeVisible();
    expect(row('unknown-sale').getByText('Nicht vorhanden')).toBeVisible();
    expect(row('unknown-sale').queryByText('0,00 EUR')).not.toBeInTheDocument();
    expect(row('unknown-sale').getByText('Ungeklärt · kein Geldpunkt')).toBeVisible();
    expect(row('excluded-sale').getByText('Nicht in der Summe')).toBeVisible();
    expect(row('excluded-sale').getByText('Ausgeschlossen · kein Punkt')).toBeVisible();
    expect(section.queryByText(/Trefferquote|Median|Profit-Faktor/)).not.toBeInTheDocument();
    expect(report).toEqual(original);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('keeps long raw values and server half-even display strings while excluding graphical over- and underflow', async () => {
    const raw = '12345678901234567890.12345678901234567890';
    const report = realizedGrossReport({
      items: [
        reportItem('long', {
          realized_gross_pnl_delta: raw,
          realized_gross_pnl_delta_display: '12345678901234567890.12',
        }),
        reportItem('half-even', {
          realized_gross_pnl_delta: '0.005',
          realized_gross_pnl_delta_display: '0.00',
        }),
        reportItem('negative-half-even', {
          realized_gross_pnl_delta: '-0.005',
          realized_gross_pnl_delta_display: '-0.00',
        }),
        reportItem('overflow', {
          realized_gross_pnl_delta: '1e400',
          realized_gross_pnl_delta_display: '1e400',
        }),
        reportItem('underflow', {
          realized_gross_pnl_delta: '-1e-400',
          realized_gross_pnl_delta_display: '-0.00',
        }),
      ],
    });
    const original = structuredClone(report);
    render(<RealizedGrossVisualization report={report} onOpenSources={vi.fn()} />);
    await screen.findByTestId('sell-plot');

    expect(row('long').getByText(raw)).toBeVisible();
    expect(row('long').getByText('12345678901234567890,12 EUR')).toBeVisible();
    expect(row('half-even').getByText('0.005')).toBeVisible();
    expect(row('half-even').getByText('0,00 EUR')).toBeVisible();
    expect(row('negative-half-even').getByText('-0,00 EUR')).toBeVisible();
    expect(row('overflow').getByText('1e400')).toBeVisible();
    expect(row('underflow').getByText('-1e-400')).toBeVisible();
    expect(row('underflow').queryByText(/Exakter Nullbeitrag/)).not.toBeInTheDocument();
    expect(row('underflow').getByText(/Außerhalb der grafischen Zahlendarstellung/)).toBeVisible();
    expect(screen.getByText(/Grafikgrenze für den absoluten Betrag/)).toHaveTextContent(
      '1e-100 bis 1e100 EUR; exakte Null bleibt ebenfalls darstellbar',
    );
    expect(screen.getByText(/Sehr kleine Beträge können bei dieser Skala/)).toHaveTextContent(
      'der Originalwert in der Tabelle entscheidet',
    );
    expect(lastPlot().entries).toEqual([
      { ordinal: 1, executionId: 'long', value: 12345678901234567000 },
      { ordinal: 2, executionId: 'half-even', value: 0.005 },
      { ordinal: 3, executionId: 'negative-half-even', value: -0.005 },
    ]);
    expect(report).toEqual(original);
  });

  it('keeps a confirmed empty selection and its excluded evidence distinct from an unresolved selection', () => {
    const report = realizedGrossReport({
      items: [reportItem('outside', { status: 'EXCLUDED', period_status: 'OUTSIDE_PERIOD' })],
      summary: {
        status: 'EMPTY',
        total: '0',
        total_display: '0.00',
        subtotal: null,
        subtotal_display: null,
        rounding_difference: null,
        rounding_difference_display: null,
      },
    });
    const view = render(<RealizedGrossVisualization report={report} onOpenSources={vi.fn()} />);
    expect(screen.getByText(/Geprüfte leere Auswahl/)).toBeVisible();
    expect(row('outside').getByText('Nicht in der Summe')).toBeVisible();
    expect(screen.queryByTestId('sell-plot')).not.toBeInTheDocument();
    expect(renderer.render).not.toHaveBeenCalled();
    expect(
      screen.queryByText(/Die vollständige Bruttosumme ist unbekannt/),
    ).not.toBeInTheDocument();

    view.rerender(
      <RealizedGrossVisualization
        report={realizedGrossReport({
          items: [
            reportItem('unknown', {
              status: 'NOT_COMPUTABLE',
              realized_gross_pnl_delta: null,
              realized_gross_pnl_delta_display: null,
            }),
          ],
          summary: {
            ...report.summary,
            status: 'NOT_COMPUTABLE',
            total: null,
            total_display: null,
          },
        })}
        onOpenSources={vi.fn()}
      />,
    );
    expect(screen.queryByText(/Geprüfte leere Auswahl/)).not.toBeInTheDocument();
    expect(screen.getByText(/Die vollständige Bruttosumme ist unbekannt/)).toBeVisible();
    expect(row('unknown').getByText('Nicht berechenbar')).toBeVisible();
    expect(screen.queryByTestId('sell-plot')).not.toBeInTheDocument();
  });

  it('keeps all 21 original rows keyboard accessible with a stable whole-report scale and no reads', async () => {
    const user = userEvent.setup();
    const report = manySales();
    const original = structuredClone(report);
    const onOpenSources = vi.fn();
    render(<RealizedGrossVisualization report={report} onOpenSources={onOpenSources} />);
    await screen.findByTestId('sell-plot');

    const region = screen.getByRole('region', { name: 'SELL-Datentabelle' });
    expect(region).toHaveAttribute('tabindex', '0');
    expect(region).toHaveClass('overflow-x-auto');
    expect(within(region).getAllByRole('row')).toHaveLength(21);
    expect(screen.getByTestId('sell-visualization-scope')).toHaveTextContent('1–20 von 21');
    expect(lastPlot().entries).toHaveLength(20);
    expect(lastPlot().extent).toBe(80);
    region.focus();
    await user.tab();
    expect(screen.getByRole('button', { name: 'Originalquellen zu SELL 1' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(onOpenSources).toHaveBeenCalledExactlyOnceWith(report.items[0]);

    screen.getByRole('button', { name: 'Nächste Grafikseite' }).focus();
    await user.keyboard('{Enter}');
    expect(screen.getByText('Seite 2 von 2 · 21 SELL-Zeilen insgesamt')).toBeVisible();
    expect(screen.getByTestId('sell-visualization-scope')).toHaveTextContent('21–21 von 21');
    expect(lastPlot()).toEqual({
      entries: [{ ordinal: 21, executionId: 'sell-21', value: -80 }],
      ordinals: [21],
      extent: 80,
    });
    expect(within(region).getAllByRole('row')).toHaveLength(2);
    expect(screen.getByRole('button', { name: 'Nächste Grafikseite' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Vorherige Grafikseite' })).toBeEnabled();
    expect(row('sell-21').getByText('-80,00 EUR')).toBeVisible();
    screen.getByRole('button', { name: 'Originalquellen zu SELL 21' }).focus();
    await user.keyboard(' ');
    expect(onOpenSources).toHaveBeenLastCalledWith(report.items[20]);
    await user.click(screen.getByRole('button', { name: 'Vorherige Grafikseite' }));
    expect(screen.getByTestId('sell-visualization-scope')).toHaveTextContent('1–20 von 21');
    expect(lastPlot().extent).toBe(80);
    expect(report).toEqual(original);
    expect(fetch).not.toHaveBeenCalled();
    expect(api.realizedGross).not.toHaveBeenCalled();
  });
});

describe('existing PerformanceWorkspace integration', () => {
  it('preserves the graphical page under the source-card filter and focuses the exact source card without another read', async () => {
    const user = userEvent.setup();
    const report = manySales();
    const original = structuredClone(report);
    api.realizedGross.mockResolvedValue(report);
    const { router } = mountWorkspace();
    await screen.findByTestId('sell-plot');
    await user.click(screen.getByRole('button', { name: 'Nächste Grafikseite' }));
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Zeilen anzeigen' }),
      'unresolved',
    );
    expect(screen.getByTestId('sell-visualization-scope')).toHaveTextContent('21–21 von 21');
    expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('520,00 EUR');

    screen.getByRole('button', { name: 'Originalquellen zu SELL 21' }).focus();
    await user.keyboard('{Enter}');
    const source = await screen.findByRole('article', { name: 'Verkauf sell-21' });
    await waitFor(() => expect(source).toHaveFocus());
    expect(screen.getByRole('region', { name: 'Herkunft SELL sell-21' })).toBeVisible();
    expect(screen.getByRole('combobox', { name: 'Zeilen anzeigen' })).toHaveValue('all');
    const query = new URLSearchParams(router.state.location.search);
    expect(query.get('report_view')).toBe('all');
    expect(query.get('report_page')).toBe('2');
    expect(query.get('report_basis')).toBe(report.basis.id);
    expect(screen.getByTestId('sell-visualization-scope')).toHaveTextContent('21–21 von 21');
    // A consumed explicit jump must not refocus this card on subsequent ordinary navigation.
    await user.click(screen.getByRole('button', { name: 'Vorherige Seite' }));
    await user.click(screen.getByRole('button', { name: 'Nächste Seite' }));
    expect(screen.getByRole('article', { name: 'Verkauf sell-21' })).not.toHaveFocus();
    await user.click(screen.getByRole('button', { name: 'Originalquellen zu SELL 21' }));
    await waitFor(() =>
      expect(screen.getByRole('article', { name: 'Verkauf sell-21' })).toHaveFocus(),
    );
    expect(api.realizedGross).toHaveBeenCalledExactlyOnceWith(
      reportFilters,
      expect.any(AbortSignal),
    );
    expect(api.closedTrades).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
    expect(report).toEqual(original);
  });

  it.each([
    { name: 'changed source basis', basis: 'b'.repeat(64) },
    { name: 'explicit reload of the same source basis', basis: 'a'.repeat(64) },
  ])(
    'resets the 21-row graphical page at the actual host boundary for $name',
    async ({ basis }) => {
      const user = userEvent.setup();
      const first = manySales();
      const next = realizedGrossReport({
        items: [reportItem('new-only-sale')],
        basis: { ...first.basis, id: basis },
      });
      api.realizedGross.mockResolvedValueOnce(first).mockResolvedValueOnce(next);
      mountWorkspace();
      await screen.findByTestId('sell-plot');
      await user.click(screen.getByRole('button', { name: 'Nächste Grafikseite' }));
      expect(screen.getByTestId('sell-visualization-scope')).toHaveTextContent('21–21 von 21');

      await user.click(screen.getByRole('button', { name: 'Bericht lesen' }));
      await screen.findByText('new-only-sale', { selector: 'code' });
      expect(screen.getByTestId('sell-visualization-scope')).toHaveTextContent('1–1 von 1');
      expect(
        within(visualization()).getByText('Seite 1 von 1 · 1 SELL-Zeilen insgesamt'),
      ).toBeVisible();
      expect(screen.getByRole('button', { name: 'Vorherige Grafikseite' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Nächste Grafikseite' })).toBeDisabled();
      expect(screen.queryByText('sell-21', { selector: 'code' })).not.toBeInTheDocument();
      expect(api.realizedGross).toHaveBeenCalledTimes(2);
      expect(fetch).not.toHaveBeenCalled();
    },
  );

  it.each(['definition', 'currency', 'period', 'timezone'] as const)(
    'does not mount a chart or its table for a response rejected by the existing %s guard',
    async (mismatch) => {
      const report = realizedGrossReport();
      if (mismatch === 'definition') report.definition_version = 'closed-trade-gross-v1';
      if (mismatch === 'currency') report.currency.code = 'USD';
      if (mismatch === 'period') report.filters.from_date = '2026-08-01';
      if (mismatch === 'timezone') report.filters.report_timezone = 'America/New_York';
      api.realizedGross.mockResolvedValue(report);
      mountWorkspace();

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Die Antwort gehört nicht zum gewählten Verkaufsbericht',
      );
      expect(
        screen.queryByRole('region', { name: 'Einzelne SELL-Beiträge' }),
      ).not.toBeInTheDocument();
      expect(renderer.render).not.toHaveBeenCalled();
      expect(api.realizedGross).toHaveBeenCalledOnce();
      expect(fetch).not.toHaveBeenCalled();
    },
  );

  it('keeps keyboard evidence after a render failure and recovers only when its host reads a new context', async () => {
    const user = userEvent.setup();
    const report = manySales();
    const original = structuredClone(report);
    renderer.fail = true;
    const logged = vi.spyOn(console, 'error').mockImplementation(() => {});
    api.realizedGross
      .mockResolvedValueOnce(report)
      .mockResolvedValueOnce({ ...report, basis: { ...report.basis, id: 'b'.repeat(64) } });
    mountWorkspace();

    expect(await screen.findByText(/Das Diagramm konnte nicht dargestellt werden/)).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(logged.mock.calls.flat()).toContainEqual(
      expect.objectContaining({ message: 'Synthetic SELL plot render failure' }),
    );
    expect(screen.getByTestId('realized-gross-total')).toHaveTextContent('520,00 EUR');
    renderer.fail = false;
    screen.getByRole('button', { name: 'Nächste Grafikseite' }).focus();
    await user.keyboard('{Enter}');
    expect(row('sell-21').getByText('-80.0000000000')).toBeVisible();
    expect(screen.getAllByText(/Das Diagramm konnte nicht dargestellt werden/)).toHaveLength(1);
    expect(screen.queryByTestId('sell-plot')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Originalquellen zu SELL 21' }));
    expect(await screen.findByRole('region', { name: 'Herkunft SELL sell-21' })).toBeVisible();
    expect(api.realizedGross).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole('button', { name: 'Bericht lesen' }));
    await screen.findByTestId('sell-plot');
    expect(
      screen.queryByText(/Das Diagramm konnte nicht dargestellt werden/),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId('sell-visualization-scope')).toHaveTextContent('1–20 von 21');
    expect(api.realizedGross).toHaveBeenCalledTimes(2);
    expect(report).toEqual(original);
    expect(fetch).not.toHaveBeenCalled();
  });
});
