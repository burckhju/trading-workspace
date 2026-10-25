import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';

import {
  closedTradeFilters,
  closedTradeItem,
  closedTradeReport,
} from '../../../test/closedTradesFixtures';
import { TradeManagementPage } from '../../trade/pages/TradeManagementPage';
import { performanceApiClient } from '../services/client';
import { closedListUrl, closedTradeSourceLink } from '../services/closedReportContext';
import { ClosedTradesPage } from './ClosedTradesPage';

vi.mock('../services/client', () => ({ performanceApiClient: { closedTrades: vi.fn() } }));
const api = vi.mocked(performanceApiClient);
const A = '10000000-0000-4000-8000-000000000021';
const R1 = '20000000-0000-4000-8000-000000000001';
const J1 = '30000000-0000-4000-8000-000000000001';
const NOW = '2026-10-21T16:00:00Z';
const context = {
  filters: closedTradeFilters,
  view: 'all' as const,
  page: 1,
  basis: 'a'.repeat(64),
};
let optionalError = false;
let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>;
function report() {
  const value = closedTradeReport();
  value.items = Array.from({ length: 21 }, (_, index) =>
    closedTradeItem(`10000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`),
  );
  value.sources = value.sources.map((s) => ({ ...s, trade_id: A }));
  return value;
}
function Navigation() {
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <>
      <button
        onClick={() => {
          void navigate(-1);
        }}
      >
        Browser zurück
      </button>
      <output aria-label="route">
        {location.pathname}
        {location.search}
      </output>
      <Routes>
        <Route path="/performance/closed-trades" element={<ClosedTradesPage />} />
        <Route path="/trade-management" element={<TradeManagementPage />} />
      </Routes>
    </>
  );
}
function mount(path = closedListUrl(context)) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Navigation />
    </MemoryRouter>,
  );
}
const amount = () =>
  within(screen.getByRole('region', { name: 'Wirtschaftliches Gesamtergebnis' }));
const route = () => screen.getByLabelText('route').textContent!;
beforeEach(() => {
  vi.resetAllMocks();
  optionalError = false;
  api.closedTrades.mockImplementation(() => Promise.resolve(report()));
  fetchMock = vi.fn<typeof fetch>((input) => {
    const url = new URL(input instanceof Request ? input.url : String(input), 'http://localhost');
    const match = /trades\/([^/]+)\/sources(?:\/([^/?]+))?$/.exec(url.pathname);
    if (!match) throw new Error(`Unexpected owner call ${url}`);
    const [, id, section] = match;
    let data: unknown;
    if (!section)
      data = {
        trade: { id, product_id: 'product-1', origin: 'EXTERNAL' },
        product_name: 'Synthetic trade',
        state: 'CLOSED',
        open_quantity: 0,
        timeline: [],
        currency_history: [],
      };
    else if (section === 'plan') data = null;
    else if (section === 'evidence') data = [];
    else if (section === 'reviews') {
      const version = {
        id: R1,
        version: 1,
        status: 'FINALIZED',
        currentness: 'CURRENT',
        timing: 'IMPROVABLE',
        process_adherence: 'NOT_ASSESSABLE',
        risk_decision: null,
        overall_exit_decision: 'IMPROVABLE',
        rationale: 'Independent stored judgment',
        created_at: NOW,
        finalized_at: NOW,
      };
      data = {
        selected: { version },
        history: [{ version }],
        source_currentness: 'STALE',
        checked_at: NOW,
      };
    } else if (section === 'journal') {
      if (optionalError)
        return Promise.resolve(
          new Response(JSON.stringify({ message: 'Synthetic read outage' }), { status: 503 }),
        );
      const journal = {
        id: J1,
        version: 1,
        edit_revision: 2,
        status: 'DRAFT',
        source_exit_review_version_id: R1,
        what_went_well: 'Stored draft',
        would_do_differently: null,
        additional_notes: null,
        created_at: NOW,
        updated_at: NOW,
        finalized_at: null,
      };
      data = {
        selected: journal,
        history: [journal],
        source_currentness: 'STALE',
        checked_at: NOW,
      };
    } else throw new Error(`Unexpected section ${section}`);
    return Promise.resolve(
      new Response(JSON.stringify({ data, read_started_at: NOW, read_completed_at: NOW }), {
        status: 200,
      }),
    );
  });
  vi.stubGlobal('fetch', fetchMock);
});

it('connects the actual list and source routes, preserves page/filter/pins through return, browser Back and reload', async () => {
  let mounted = mount();
  const entry = await screen.findByRole('link', { name: `Trade ${A} prüfen` });
  expect(screen.getByRole('navigation', { name: 'Berichtsseiten' })).toHaveTextContent(
    'Seite 2 von 2',
  );
  fireEvent.click(entry);
  expect(
    await within(
      await screen.findByRole('region', { name: 'Wirtschaftliches Gesamtergebnis' }),
    ).findByText('50,00 EUR'),
  ).toBeVisible();
  expect(await screen.findByText('Stored draft')).toBeVisible();
  const reviews = screen.getByRole('region', { name: 'Dokumentierte Exit-Bewertung' });
  expect(reviews).toHaveTextContent('IMPROVABLE');
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('link', { name: 'Journalversion 1 · DRAFT · Revision 2' }));
  await waitFor(() => expect(route()).toContain(`journal_version_id=${J1}`));
  expect(
    await within(
      await screen.findByRole('region', { name: 'Wirtschaftliches Gesamtergebnis' }),
    ).findByText('50,00 EUR'),
  ).toBeVisible();
  expect(route()).toContain('report_page=2');
  expect(route()).toContain(`report_basis=${'a'.repeat(64)}`);
  const pinned = route();
  fireEvent.click(screen.getByRole('link', { name: 'Zur ursprünglichen Abschlussauswahl' }));
  expect(await screen.findByRole('link', { name: `Trade ${A} prüfen` })).toBeVisible();
  expect(screen.getByLabelText('Zeilen anzeigen')).toHaveValue('all');
  expect(screen.getByLabelText('Von (einschließlich)')).toHaveValue(closedTradeFilters.from_date);
  expect(screen.getByLabelText('Bis (einschließlich)')).toHaveValue(closedTradeFilters.to_date);
  expect(screen.getByLabelText('Berichtswährung')).toHaveValue('EUR');
  expect(screen.getByLabelText('Berichtszeitzone (IANA)')).toHaveValue('Europe/Berlin');
  expect(screen.getByRole('navigation', { name: 'Berichtsseiten' })).toHaveTextContent(
    'Seite 2 von 2',
  );
  fireEvent.click(screen.getByRole('button', { name: 'Browser zurück' }));
  expect(
    await within(
      await screen.findByRole('region', { name: 'Wirtschaftliches Gesamtergebnis' }),
    ).findByText('50,00 EUR'),
  ).toBeVisible();
  expect(route()).toBe(pinned);
  mounted.unmount();
  mounted = mount(pinned);
  expect(await screen.findByText('Stored draft')).toBeVisible();
  expect(
    await within(
      await screen.findByRole('region', { name: 'Wirtschaftliches Gesamtergebnis' }),
    ).findByText('50,00 EUR'),
  ).toBeVisible();
  expect(route()).toBe(pinned);
  expect(
    fetchMock.mock.calls.every(([, options]) => !options?.method || options.method === 'GET'),
  ).toBe(true);
  mounted.unmount();
});

it('keeps qualified money during an optional journal error and explicit retry, without rereading the financial owner', async () => {
  optionalError = true;
  mount(closedTradeSourceLink(A, context));
  expect(await screen.findByText('50,00 EUR')).toBeVisible();
  const journal = within(screen.getByRole('region', { name: 'Journal' }));
  expect(await journal.findByRole('alert')).toHaveTextContent('Quelle konnte nicht gelesen werden');
  optionalError = false;
  fireEvent.click(journal.getByRole('button', { name: 'Journal neu lesen' }));
  expect(await journal.findByText('Stored draft')).toBeVisible();
  expect(amount().getByText('50,00 EUR')).toBeVisible();
  expect(api.closedTrades).toHaveBeenCalledTimes(1);
});

it('keeps historical reflection visible when the financial read fails, and never uses raw positions or URL amounts', async () => {
  api.closedTrades.mockRejectedValue(new Error('Financial reader unavailable'));
  mount(closedTradeSourceLink(A, context) + '&total=12345&returnTo=https%3A%2F%2Fevil.invalid');
  expect(await screen.findByText('Stored draft')).toBeVisible();
  expect(await amount().findByRole('alert')).toHaveTextContent(
    'weder Null noch fehlende Reflexion',
  );
  expect(amount().queryByText(/12345/)).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Zur ursprünglichen Abschlussauswahl' })).toHaveAttribute(
    'href',
    closedListUrl(context),
  );
});

it('announces an unavailable return page after a source change instead of pretending to restore an old dataset', async () => {
  const value = report();
  value.items = value.items.slice(0, 1);
  value.basis.id = 'b'.repeat(64);
  value.statistics.report_basis_id = value.basis.id;
  api.closedTrades.mockResolvedValue(value);
  mount();
  expect(await screen.findByText(/Die ursprüngliche Seite 2/)).toBeVisible();
  expect(screen.getByRole('navigation', { name: 'Berichtsseiten' })).toHaveTextContent(
    'Seite 1 von 1',
  );
  expect(screen.getByText(/Der Quellenstand hat sich/)).toBeVisible();
});

it('does not repair duplicate context by silently choosing one value through a journal-review link', async () => {
  mount(closedTradeSourceLink(A, context) + '&report_page=3');
  expect(await screen.findByText('Stored draft')).toBeVisible();
  expect(amount().getByRole('alert')).toHaveTextContent('Ungültiger');
  fireEvent.click(screen.getByRole('link', { name: 'Exakte Journal-Reviewquelle lesen' }));
  expect(await screen.findByText('Stored draft')).toBeVisible();
  expect(amount().getByRole('alert')).toHaveTextContent('Ungültiger');
  expect(api.closedTrades).not.toHaveBeenCalled();
});
