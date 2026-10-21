import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TradeManagementPage } from '../pages/TradeManagementPage';
import { sourceLink, sourceQueryError } from '../services/sourceView';

const A = '10000000-0000-4000-8000-000000000001';
const B = '10000000-0000-4000-8000-000000000002';
const R1 = '20000000-0000-4000-8000-000000000001';
const R2 = '20000000-0000-4000-8000-000000000002';
const J1 = '30000000-0000-4000-8000-000000000001';
const L1 = '40000000-0000-4000-8000-000000000001';
const NOW = '2026-10-21T16:00:00Z';
const snapshot = (data: unknown) => ({ data, read_started_at: NOW, read_completed_at: NOW });
const response = (data: unknown) => new Response(JSON.stringify(snapshot(data)), { status: 200 });
const failure = () =>
  new Response(JSON.stringify({ message: 'Quelle nicht verfügbar' }), { status: 503 });
const requestUrl = (value: RequestInfo | URL): string =>
  value instanceof Request ? value.url : String(value);

function core(id = A) {
  return {
    trade: {
      id,
      product_id: 'product',
      origin: 'EXTERNAL',
      trade_plan_id: null,
      trade_plan_version_id: null,
    },
    product_name: `Synthetic ${id === A ? 'A' : 'B'}`,
    state: 'CLOSED',
    open_quantity: 0,
    realized_gross_pnl: '987654.00',
    currency_history: [],
    timeline: [
      {
        id: 'buy',
        kind: 'EXECUTION',
        execution_side: 'BUY',
        quantity: 10,
        price_per_unit: '2.00',
        numeric_value: null,
        text_value: null,
        supersedes_id: null,
        occurred_at: '2026-08-04T22:00:00Z',
        executed_on: '2026-08-05',
        execution_timezone: 'Europe/Berlin',
        recorded_at: NOW,
        currency_resolution: {
          currency_code: null,
          source: 'UNKNOWN',
          source_execution_ids: [],
          confirmation_ids: [],
        },
      },
    ],
  };
}
function review(id = R1, value: string | null = 'IMPROVABLE', status = 'FINALIZED') {
  return {
    version: {
      id,
      exit_review_id: 'review-root',
      version: id === R1 ? 1 : 2,
      status,
      currentness: 'CURRENT',
      timing: value,
      process_adherence: 'NOT_ASSESSABLE',
      risk_decision: null,
      overall_exit_decision: value,
      rationale: 'Synthetic reflection <script>unsafe()</script>',
      created_at: NOW,
      finalized_at: status === 'FINALIZED' ? NOW : null,
      supersedes_version_id: null,
      stale_reason: null,
    },
  };
}
function journal(status = 'DRAFT') {
  return {
    id: J1,
    trade_journal_id: 'journal-root',
    version: 1,
    edit_revision: 3,
    status,
    source_exit_review_version_id: R1,
    what_went_well: 'Eine eigene Reflexion',
    would_do_differently: null,
    additional_notes: null,
    created_at: NOW,
    updated_at: NOW,
    finalized_at: status === 'FINALIZED' ? NOW : null,
    supersedes_version_id: null,
  };
}
let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>;
let override: (url: URL) => Response | Promise<Response> | undefined;
let reviewValue = review();
let journalValue = journal();
function defaults(url: URL): Response {
  const match = /trades\/([^/]+)\/sources(?:\/([^/?]+))?$/.exec(url.pathname);
  if (!match) throw new Error(`Unexpected request: ${url}`);
  const [, id, section] = match;
  switch (section) {
    case undefined:
      return response(core(id));
    case 'plan':
      return response(null);
    case 'reviews':
      return response({
        history: [reviewValue],
        selected: reviewValue,
        source_currentness: 'STALE',
        checked_at: NOW,
      });
    case 'journal':
      return response({
        history: [journalValue],
        selected: journalValue,
        source_currentness: 'STALE',
        checked_at: NOW,
      });
    case 'evidence':
      return response([]);
    default:
      throw new Error(`Unexpected section: ${section}`);
  }
}
function Navigation() {
  const navigate = useNavigate();
  const location = useLocation();
  return (
    <>
      <button
        onClick={() => {
          void navigate(sourceLink(new URLSearchParams({ trade_id: B })));
        }}
      >
        visit B
      </button>
      <button
        onClick={() => {
          void navigate(sourceLink(new URLSearchParams({ trade_id: A })));
        }}
      >
        visit A
      </button>
      <button
        onClick={() => {
          void navigate(sourceLink(new URLSearchParams({ trade_id: A }), 'review_version_id', R2));
        }}
      >
        visit R2
      </button>
      <output aria-label="route">
        {location.pathname}
        {location.search}
      </output>
      <TradeManagementPage />
    </>
  );
}
function mount(search = `trade_id=${A}&view=sources`) {
  return render(
    <MemoryRouter initialEntries={[`/trade-management?${search}`]}>
      <Navigation />
    </MemoryRouter>,
  );
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
beforeEach(() => {
  reviewValue = review();
  journalValue = journal();
  override = () => undefined;
  fetchMock = vi.fn(async (input, options) => {
    expect(options?.method).toBe('GET');
    expect(options?.body).toBeUndefined();
    const url = new URL(requestUrl(input), 'http://localhost');
    return override(url) ?? defaults(url);
  });
  vi.stubGlobal('fetch', fetchMock);
});

describe('read-only trade sources', () => {
  it('reads five endpoints without editors, raw monetary totals or HTML execution', async () => {
    mount();
    await screen.findByText('Eine eigene Reflexion');
    expect(fetchMock).toHaveBeenCalledTimes(5);
    expect(
      screen.getByText(/In diesem unabhängigen Quellenweg noch nicht angebunden/),
    ).toBeVisible();
    expect(screen.queryByText(/987654/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /speichern|finalisieren|revalidieren/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText('Synthetic reflection <script>unsafe()</script>', { exact: false }),
    ).toBeVisible();
    expect(document.querySelector('script')).toBeNull();
    expect(screen.getAllByText('IMPROVABLE')).toHaveLength(2);
    expect(screen.getByText(/NOT_ASSESSABLE – ausdrücklich nicht beurteilbar/)).toBeVisible();
    expect(screen.getByText(/Uhrzeit unbekannt/)).toBeVisible();
    expect(screen.queryByText(/2026-08-04T22:00:00/)).toBeNull();
    expect(screen.getByText(/Eigener EXTERNAL-Trade/)).toBeVisible();
  });
  it('keeps DRAFT, missing assessment, saved currentness and inspected currentness distinct', async () => {
    reviewValue = review(R1, null, 'DRAFT');
    mount();
    await screen.findByText(/Vorläufiger, veränderlicher Entwurf/);
    const region = screen.getByRole('region', { name: 'Dokumentierte Exit-Bewertung' });
    expect(within(region).getAllByText('Nicht dokumentiert')).toHaveLength(3);
    expect(
      within(region).getByText(/Gespeicherte Currentness: CURRENT. Heutige Quellenprüfung: STALE/),
    ).toBeVisible();
  });
  it('shows GOOD independently of unavailable monetary qualification', async () => {
    reviewValue = review(R1, 'GOOD');
    mount();
    await screen.findByText('Eine eigene Reflexion');
    expect(screen.getAllByText('GOOD')).toHaveLength(2);
    expect(screen.queryByText(/Gesamtqualität des Trades: GOOD/)).toBeNull();
  });
  it('keeps core facts visible when optional sources are not documented', async () => {
    override = (url) =>
      /\/(reviews|journal)$/.test(url.pathname)
        ? response({ selected: null, history: [], source_currentness: 'UNKNOWN', checked_at: NOW })
        : undefined;
    mount();
    await screen.findByText('Journal nicht dokumentiert.');
    expect(screen.getByText('Exit-Bewertung nicht dokumentiert.')).toBeVisible();
    expect(screen.getByRole('heading', { name: /Synthetic A/ })).toBeVisible();
    expect(screen.getByText('Kauf')).toBeVisible();
  });
  it('shows empty FINALIZED and journal revision', async () => {
    journalValue = { ...journal('FINALIZED'), what_went_well: '' };
    mount();
    await screen.findByText('Finales Journal ohne Reflexionstext.');
    expect(screen.getByText(/Bearbeitungsrevision 3/)).toBeVisible();
  });
  it('preserves R1 through reload despite a newer R2', async () => {
    override = (url) =>
      url.pathname.endsWith('/reviews')
        ? response({
            history: [review(R2, 'GOOD'), review()],
            selected: url.searchParams.get('version_id') === R1 ? review() : review(R2, 'GOOD'),
            source_currentness: 'STALE',
            checked_at: NOW,
          })
        : undefined;
    const query = `trade_id=${A}&view=sources&review_version_id=${R1}`;
    const first = mount(query);
    await screen.findAllByText('IMPROVABLE');
    expect(screen.queryByText('GOOD')).toBeNull();
    first.unmount();
    mount(query);
    await screen.findAllByText('IMPROVABLE');
    expect(screen.getByText(/Exakt angeforderte Version/)).toBeVisible();
    expect(
      fetchMock.mock.calls
        .filter(([url]) => requestUrl(url).includes('/reviews'))
        .every(([url]) => requestUrl(url).includes(`version_id=${R1}`)),
    ).toBe(true);
  });
  it('does not fall back after a failed historical pin', async () => {
    override = (url) =>
      url.pathname.endsWith('/reviews')
        ? new Response('Unknown version', { status: 404 })
        : undefined;
    mount(`trade_id=${A}&view=sources&review_version_id=${R2}`);
    await screen.findByText('Eine eigene Reflexion');
    await screen.findByRole('alert');
    expect(screen.queryByText('Exit-Bewertung nicht dokumentiert.')).toBeNull();
    expect(
      fetchMock.mock.calls.filter(([url]) => requestUrl(url).includes('/reviews')),
    ).toHaveLength(1);
  });
  it('retries only a failed optional section', async () => {
    let fail = true;
    override = (url) => (url.pathname.endsWith('/journal') && fail ? failure() : undefined);
    mount();
    await screen.findByRole('alert');
    expect(screen.getByRole('heading', { name: /Synthetic A/ })).toBeVisible();
    fail = false;
    fireEvent.click(screen.getByRole('button', { name: 'Journal neu lesen' }));
    await screen.findByText('Eine eigene Reflexion');
    expect(fetchMock).toHaveBeenCalledTimes(6);
    expect(screen.queryByRole('alert')).toBeNull();
  });
  it('blocks child reads on mismatched core identity', async () => {
    override = (url) => (url.pathname.endsWith('/sources') ? response(core(B)) : undefined);
    mount();
    await screen.findByRole('alert');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('Eine eigene Reflexion')).toBeNull();
  });
  it('blocks child reads on core failure', async () => {
    override = () => failure();
    mount();
    await screen.findByRole('alert');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it('ignores old A success across A → B → A', async () => {
    const oldA = deferred<Response>();
    let first = true;
    override = (url) => {
      if (url.pathname.endsWith(`${A}/sources`) && first) {
        first = false;
        return oldA.promise;
      }
      return undefined;
    };
    mount();
    fireEvent.click(screen.getByText('visit B'));
    await screen.findByRole('heading', { name: /Synthetic B/ });
    fireEvent.click(screen.getByText('visit A'));
    await screen.findByRole('heading', { name: /Synthetic A/ });
    await act(async () => {
      oldA.resolve(response({ ...core(A), product_name: 'OBSOLETE A' }));
      await oldA.promise;
    });
    expect(screen.queryByText(/OBSOLETE/)).toBeNull();
    expect(fetchMock.mock.calls[0][1]?.signal?.aborted).toBe(true);
  });
  it('ignores late optional success after version change', async () => {
    const old = deferred<Response>();
    let first = true;
    override = (url) => {
      if (url.pathname.endsWith('/reviews') && first) {
        first = false;
        return old.promise;
      }
      if (url.pathname.endsWith('/reviews'))
        return response({
          history: [review(R2, 'GOOD')],
          selected: review(R2, 'GOOD'),
          source_currentness: 'CURRENT',
          checked_at: NOW,
        });
      return undefined;
    };
    mount();
    await screen.findByText('Eine eigene Reflexion');
    fireEvent.click(screen.getByText('visit R2'));
    await screen.findAllByText('GOOD');
    await act(async () => {
      old.resolve(
        response({
          history: [review()],
          selected: review(),
          source_currentness: 'STALE',
          checked_at: NOW,
        }),
      );
      await old.promise;
    });
    expect(screen.queryByText('IMPROVABLE')).toBeNull();
    expect(screen.getByLabelText('route')).toHaveTextContent(R2);
  });
  it('ignores obsolete errors and aborts all requests on unmount', async () => {
    const old = deferred<Response>();
    let first = true;
    override = (url) => {
      if (url.pathname.endsWith('/journal') && first) {
        first = false;
        return old.promise;
      }
      return undefined;
    };
    const view = mount();
    await screen.findAllByText('IMPROVABLE');
    fireEvent.click(screen.getByText('visit B'));
    await screen.findByText('Eine eigene Reflexion');
    await act(async () => {
      old.reject(new Error('OLD ERROR'));
      await old.promise.catch(() => undefined);
    });
    expect(screen.queryByText(/OLD ERROR/)).toBeNull();
    view.unmount();
    expect(fetchMock.mock.calls.every(([, options]) => options?.signal?.aborted)).toBe(true);
  });
  it('keeps contradictory exact lesson-version links and journal pins', async () => {
    override = (url) =>
      url.pathname.endsWith('/evidence')
        ? response([
            {
              evidence_id: 'evidence',
              evidence_type: 'TRADE_JOURNAL_VERSION',
              created_at: NOW,
              journal_version_id: J1,
              review_version_id: null,
              source_bound: true,
              lesson_links: ['SUPPORTS', 'CONTRADICTS'].map((relation, i) => ({
                link_id: `link-${i}`,
                lesson_id: 'lesson',
                lesson_title: 'Interpretation',
                lesson_version_id: L1,
                lesson_version: 1,
                relation,
                is_current_version: false,
              })),
            },
          ])
        : undefined;
    mount();
    await screen.findByRole('link', { name: /Interpretation.*CONTRADICTS/ });
    for (const relation of ['SUPPORTS', 'CONTRADICTS'])
      expect(
        screen.getByRole('link', { name: new RegExp(`Interpretation.*${relation}`) }),
      ).toHaveAttribute('href', `/lessons/lesson?lesson_version_id=${L1}#lesson-history`);
    fireEvent.click(screen.getByRole('link', { name: 'Exakte Evidence-Journalquelle lesen' }));
    await waitFor(() =>
      expect(screen.getByLabelText('route')).toHaveTextContent(`journal_version_id=${J1}`),
    );
    await screen.findByText('Eine eigene Reflexion');
  });
  it('shows P1 and its approval without reading latest plan or inferring a violation', async () => {
    override = (url) =>
      url.pathname.endsWith('/plan')
        ? response({
            plan: { id: 'plan' },
            approval: {
              approval_id: 'approval-1',
              trade_plan_version_id: 'P1',
              actor: 'synthetic-user',
              approved_at: NOW,
            },
            events: [],
            candidate_evaluation: null,
            version: {
              id: 'P1',
              version: 1,
              status: 'SUPERSEDED',
              thesis: 'P1 original',
              created_at: NOW,
              created_by: 'user',
              entry: { type: 'PRICE', price: '100', currency: 'EUR' },
              invalidation: { stop_price: '95' },
              targets: [{ sequence: 1, price: '110' }],
              risk_assumptions: { thesis_risk: 'Original risk' },
            },
          })
        : undefined;
    mount();
    await screen.findByText('These: P1 original');
    expect(screen.getByText(/Ursprünglich referenzierte Planversion 1/)).toBeVisible();
    expect(screen.getByText(/Gespeicherte Freigabe/)).toBeVisible();
    expect(screen.getByText(/Daraus folgt kein automatischer Regelverstoß/)).toBeVisible();
    expect(fetchMock.mock.calls.every(([url]) => !requestUrl(url).includes('/trade-plans/'))).toBe(
      true,
    );
  });
  it('shows cancellation as no sale and keeps replaced facts', async () => {
    const data = core();
    override = (url) =>
      url.pathname.endsWith('/sources')
        ? response({
            ...data,
            state: 'CANCELLED',
            open_quantity: null,
            timeline: [
              ...data.timeline,
              { ...data.timeline[0], id: 'correction', supersedes_id: 'buy' },
              {
                ...data.timeline[0],
                id: 'cancellation',
                kind: 'CANCELLATION',
                executed_on: null,
                execution_side: null,
              },
            ],
          })
        : undefined;
    mount();
    await screen.findByText('Storno – kein Verkauf');
    expect(screen.getByText('Historisch ersetzt')).toBeVisible();
    expect(screen.queryByText('Verkauf')).toBeNull();
  });
  it.each([
    'trade_id=invalid',
    `trade_id=${A}&review_version_id=`,
    `trade_id=${A}&journal_version_id=bad`,
    `trade_id=${A}&review_version_id=${R1}&review_version_id=${R2}`,
    `trade_id=${A}&trade_id=${B}`,
  ])('rejects invalid selectors %s before reads', async (query) => {
    mount(`${query}&view=sources`);
    expect(screen.getByRole('alert')).toBeVisible();
    await act(async () => {});
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it('discards external/nested returnTo and untrusted money parameters', async () => {
    const query = new URLSearchParams({
      trade_id: A,
      view: 'sources',
      returnTo: 'https://evil.invalid/?returnTo=//elsewhere',
      money: '100',
    });
    expect(sourceQueryError(query)).toBeNull();
    expect(sourceLink(query, 'journal_version_id', J1)).not.toMatch(/evil|returnTo|money/);
    mount(query.toString());
    await screen.findByText('Eine eigene Reflexion');
    expect(screen.getByRole('link', { name: 'Zur Tradeverwaltung' })).toHaveAttribute(
      'href',
      `/trade-management?trade_id=${A}`,
    );
    expect(
      [...document.querySelectorAll('a')].every(
        (link) => !link.getAttribute('href')?.includes('evil'),
      ),
    ).toBe(true);
  });
});
