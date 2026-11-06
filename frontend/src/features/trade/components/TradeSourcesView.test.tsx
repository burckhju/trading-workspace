import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
function plan() {
  return {
    plan: {
      id: 'historical-plan',
      origin_type: 'CANDIDATE_EVALUATION',
      candidate_id: 'candidate-1',
      candidate_evaluation_id: 'evaluation-3',
    },
    approval: null,
    events: [],
    candidate_evaluation: {
      candidate_id: 'candidate-1',
      evaluation_id: 'evaluation-3',
      evaluation_version: 3,
      direction: 'LONG',
      model_id: 'candidate-model',
      model_version: '2.1',
      qualification: 'QUALIFIED',
      quality_status: 'PARTIAL',
      evaluated_at: '2026-07-01T09:00:00Z',
      sources: [
        {
          role: 'MARKET_CONTEXT',
          source_type: 'MARKET_ANALYSIS',
          source_id: 'historical-analysis',
          source_version: 7,
          model_id: 'analysis-model',
          model_version: '1.4',
        },
        {
          role: 'SUBJECT',
          source_type: 'OTHER_HISTORICAL_SOURCE',
          source_id: 'historical-other-source',
          source_version: 2,
          model_id: 'source-model',
          model_version: '5',
        },
      ],
    },
    version: {
      id: 'historical-plan-v1',
      version: 1,
      status: 'DRAFT',
      thesis: 'Ursprüngliche These',
      created_at: '2026-07-01T10:00:00Z',
      entry: { type: 'PRICE', price: '100', currency: 'EUR' },
      invalidation: { stop_price: '95' },
      targets: [],
      risk_assumptions: { thesis_risk: 'Original risk' },
    },
  };
}
function evidence(bound = false) {
  return {
    evidence_id: 'historical-evidence',
    evidence_type: 'FT011',
    created_at: '2026-09-01T09:00:00Z',
    review_version_id: bound ? R1 : null,
    journal_version_id: null,
    source_bound: bound,
    lesson_links: [
      {
        link_id: 'historical-relation',
        lesson_id: 'lesson',
        lesson_title: 'Historische Interpretation',
        lesson_version_id: L1,
        lesson_version: 1,
        relation: 'CONTRADICTS',
        is_current_version: false,
      },
    ],
  };
}
function plannedCore() {
  const data = core();
  return {
    ...data,
    trade: {
      ...data.trade,
      origin: 'WORKSPACE_SELECTION',
      trade_plan_id: 'historical-plan',
      trade_plan_version_id: 'historical-plan-v1',
    },
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
    expect(screen.getByText(/Kein Abschlussberichtskontext ausgewählt/)).toBeVisible();
    expect(screen.queryByText(/987654/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /speichern|finalisieren|revalidieren/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText('Synthetic reflection <script>unsafe()</script>', { exact: false }),
    ).toBeVisible();
    expect(document.querySelector('script')).toBeNull();
    fireEvent.click(screen.getByRole('link', { name: 'Plan und Quellen' }));
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Ursprünglicher Plan' })).toHaveFocus(),
    );
    expect(fetchMock).toHaveBeenCalledTimes(5);
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
      ).toHaveAttribute(
        'href',
        `/lessons/lesson?trade_id=${A}&trade_return_view=sources&lesson_version_id=${L1}#lesson-history`,
      );
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
    mount(`trade_id=${A}&view=sources&review_version_id=${R1}&journal_version_id=${J1}`);
    await screen.findByText('These: P1 original');
    expect(screen.getByText(/Ursprünglich referenzierte Planversion 1/)).toBeVisible();
    expect(screen.getByText(/Gespeicherte Freigabe/)).toBeVisible();
    const planLink = screen.getByRole('link', { name: 'Gebundene Planversion öffnen' });
    const destination = new URL(planLink.getAttribute('href')!, 'http://localhost');
    expect(destination.pathname).toBe('/trade-plans');
    expect(Object.fromEntries(destination.searchParams)).toEqual({
      trade_plan_id: 'plan',
      trade_plan_version_id: 'P1',
      trade_id: A,
      trade_return_view: 'sources',
      review_version_id: R1,
      journal_version_id: J1,
    });
    expect(planLink).not.toHaveAttribute('target');
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
      `/trade-management?trade_id=${A}#trade-overview`,
    );
    expect(
      [...document.querySelectorAll('a')].every(
        (link) => !link.getAttribute('href')?.includes('evil'),
      ),
    ).toBe(true);
  });
});

describe('lifecycle evidence presentation', () => {
  it('orders six evidence groups without asserting lifecycle completion', async () => {
    mount();
    await screen.findByText('Eine eigene Reflexion');
    const list = screen.getByRole('list', { name: 'Belege im Trade-Lebenszyklus' });
    expect(
      [...list.children].map(
        (item) => within(item as HTMLElement).getAllByRole('heading')[0].textContent,
      ),
    ).toEqual([
      'Analyse / Kandidat',
      'Ursprünglicher Plan',
      'Tatsächliche Ausführungen und Management',
      'Position',
      'Review und Journal',
      'Evidence und Lesson-Versionen',
    ]);
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.queryByText(/6\/6|100\s*%|Analyse abgeschlossen/)).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it('shows historical candidate and source identities without inventing analysis links', async () => {
    override = (url) => {
      if (url.pathname.endsWith('/sources')) return response(plannedCore());
      if (url.pathname.endsWith('/plan')) return response(plan());
      return undefined;
    };
    mount(`trade_id=${A}&view=sources&review_version_id=${R1}&journal_version_id=${J1}`);
    const analysis = await screen.findByRole('region', { name: 'Analyse / Kandidat' });
    await within(analysis).findByText('evaluation-3 · Version 3');
    expect(within(analysis).getByText('candidate-1')).toBeVisible();
    expect(within(analysis).getByText('candidate-model · 2.1')).toBeVisible();
    expect(within(analysis).getByText('QUALIFIED')).toBeVisible();
    expect(within(analysis).getByText('PARTIAL')).toBeVisible();
    expect(within(analysis).getByText(/9:00:00 UTC/)).toBeVisible();
    const sources = within(analysis).getByRole('list', {
      name: 'Historische Analyse- und Kandidatenquellen',
    });
    expect(within(sources).getByText('MARKET_ANALYSIS')).toBeVisible();
    expect(within(sources).getByText('historical-analysis · Version 7')).toBeVisible();
    expect(within(sources).getByText('analysis-model · 1.4')).toBeVisible();
    expect(within(sources).getByText('OTHER_HISTORICAL_SOURCE')).toBeVisible();
    expect(within(sources).getByText('historical-other-source · Version 2')).toBeVisible();
    expect(within(analysis).queryByRole('link')).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(5);
    const boundPlan = screen.getByRole('link', { name: 'Gebundene Planversion öffnen' });
    expect(boundPlan.getAttribute('href')).toContain('trade_plan_version_id=historical-plan-v1');
    expect(boundPlan.getAttribute('href')).toContain(`review_version_id=${R1}`);
    expect(boundPlan.getAttribute('href')).toContain(`journal_version_id=${J1}`);
  });

  it('treats manual origin without analysis as valid and does not infer plan approval from a trade', async () => {
    const data = plan();
    override = (url) => {
      if (url.pathname.endsWith('/sources')) return response(plannedCore());
      if (url.pathname.endsWith('/plan'))
        return response({
          ...data,
          plan: {
            ...data.plan,
            origin_type: 'MANUAL',
            candidate_id: null,
            candidate_evaluation_id: null,
          },
          candidate_evaluation: null,
        });
      return undefined;
    };
    mount();
    await screen.findByText(/Manueller Plan ohne gebundene Kandidatenbewertung/);
    const region = screen.getByRole('region', { name: 'Ursprünglicher Plan' });
    expect(within(region).getByText(/Planversion 1 · Status DRAFT/)).toBeVisible();
    expect(within(region).getByText('Gespeicherte Freigabe: Nicht dokumentiert')).toBeVisible();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it('keeps a missing candidate source explicit and preserves unknown owner codes', async () => {
    const data = plan();
    override = (url) => {
      if (url.pathname.endsWith('/sources')) return response(plannedCore());
      if (url.pathname.endsWith('/plan'))
        return response({
          ...data,
          candidate_evaluation: {
            ...data.candidate_evaluation,
            qualification: 'FUTURE_QUALIFICATION',
            sources: [],
          },
        });
      return undefined;
    };
    mount();
    await screen.findByText('Keine einzelnen historischen Analysequellen dokumentiert.');
    expect(screen.getByText('FUTURE_QUALIFICATION')).toBeVisible();
    expect(
      screen.queryByText(/Analyse abgeschlossen|Analyse freigegeben|alles in Ordnung/),
    ).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it('shares the pending plan read and its single retry between analysis and plan', async () => {
    const pending = deferred<Response>();
    let first = true;
    override = (url) => {
      if (url.pathname.endsWith('/plan')) {
        if (first) {
          first = false;
          return pending.promise;
        }
        return response(plan());
      }
      return undefined;
    };
    mount();
    await screen.findByText('Eine eigene Reflexion');
    const analysis = screen.getByRole('region', { name: 'Analyse / Kandidat' });
    const planRegion = screen.getByRole('region', { name: 'Ursprünglicher Plan' });
    expect(
      within(analysis).getByText('Analyseherkunft wird gemeinsam mit der Planquelle gelesen.'),
    ).toBeVisible();
    expect(within(analysis).queryByRole('status')).toBeNull();
    expect(within(planRegion).getByRole('status')).toHaveTextContent(
      'Ursprünglicher Plan wird gelesen.',
    );
    expect(screen.queryByText(/ohne dokumentierte ursprüngliche Planherkunft/)).toBeNull();
    await act(async () => {
      pending.resolve(failure());
      await pending.promise;
    });
    expect(within(analysis).getByText(/Analyseherkunft konnte nicht geprüft werden/)).toBeVisible();
    expect(screen.getAllByRole('alert')).toHaveLength(1);
    expect(within(planRegion).getByRole('alert')).toBeVisible();
    fireEvent.click(
      within(planRegion).getByRole('button', { name: 'Ursprünglicher Plan neu lesen' }),
    );
    await within(analysis).findByText('evaluation-3 · Version 3');
    expect(within(planRegion).getByText('These: Ursprüngliche These')).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(6);
    expect(fetchMock.mock.calls.filter(([url]) => requestUrl(url).endsWith('/plan'))).toHaveLength(
      2,
    );
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('does not read or claim optional evidence before a successful core read', async () => {
    const pending = deferred<Response>();
    override = (url) => (url.pathname.endsWith('/sources') ? pending.promise : undefined);
    mount();
    expect(
      within(screen.getByRole('region', { name: 'Trade und Quellenstand' })).getByRole('status'),
    ).toHaveTextContent('Trade und Quellenstand wird gelesen.');
    expect(screen.queryByRole('list', { name: 'Belege im Trade-Lebenszyklus' })).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await act(async () => {
      pending.resolve(response(core()));
      await pending.promise;
    });
    await screen.findByText('Eine eigene Reflexion');
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it('retains independent read windows and makes shared windows explicit in UTC', async () => {
    override = (url) => {
      const stamp = url.pathname.endsWith('/plan')
        ? '10:11:12'
        : url.pathname.endsWith('/reviews')
          ? '11:12:13'
          : url.pathname.endsWith('/journal')
            ? '12:13:14'
            : url.pathname.endsWith('/evidence')
              ? '13:14:15'
              : '09:10:11';
      const data = url.pathname.endsWith('/sources')
        ? plannedCore()
        : url.pathname.endsWith('/plan')
          ? plan()
          : url.pathname.endsWith('/reviews')
            ? {
                history: [review()],
                selected: review(),
                source_currentness: 'CURRENT',
                checked_at: NOW,
              }
            : url.pathname.endsWith('/journal')
              ? {
                  history: [journal()],
                  selected: journal(),
                  source_currentness: 'CURRENT',
                  checked_at: NOW,
                }
              : [];
      return new Response(
        JSON.stringify({
          data,
          read_started_at: `2026-10-21T${stamp}Z`,
          read_completed_at: `2026-10-21T${stamp}Z`,
        }),
      );
    };
    mount();
    await screen.findByText('Eine eigene Reflexion');
    for (const [name, time] of [
      ['Analyse / Kandidat', '10:11:12 UTC'],
      ['Ursprünglicher Plan', '10:11:12 UTC'],
      ['Tatsächliche Ausführungen und Management', '09:10:11 UTC'],
      ['Position', '09:10:11 UTC'],
      ['Dokumentierte Exit-Bewertung', '11:12:13 UTC'],
      ['Journal', '12:13:14 UTC'],
      ['Evidence und Lesson-Versionen', '13:14:15 UTC'],
    ]) {
      const region = screen.getByRole('region', { name });
      expect(within(region).getByText(/Lesefenster/)).toHaveTextContent(time);
    }
    expect(
      within(screen.getByRole('region', { name: 'Ursprünglicher Plan' })).getByText(
        /Eigenes Lesefenster der Planquelle, gemeinsam für Analyse und Plan:/,
      ),
    ).toBeVisible();
    expect(screen.getByText(/Dasselbe Lesefenster wie die Ausführungen/)).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it('shows UNKNOWN and null position independently of historical evidence and a failed review read', async () => {
    override = (url) => {
      if (url.pathname.endsWith('/sources'))
        return response({ ...core(), state: 'UNKNOWN', open_quantity: null, timeline: [] });
      if (url.pathname.endsWith('/reviews')) return failure();
      if (url.pathname.endsWith('/evidence')) return response([evidence()]);
      return undefined;
    };
    mount();
    await screen.findByRole('link', { name: /Historische Interpretation.*CONTRADICTS/ });
    const position = screen.getByRole('region', { name: 'Position' });
    expect(within(position).getByText('UNKNOWN')).toBeVisible();
    expect(within(position).getByText('Nicht verfügbar')).toBeVisible();
    expect(within(position).queryByText('0 Stück')).toBeNull();
    expect(within(position).queryByRole('link')).toBeNull();
    expect(
      screen.getByText('Keine Ausführungs- oder Managementbelege dokumentiert.'),
    ).toBeVisible();
    const reviewRegion = screen.getByRole('region', { name: 'Dokumentierte Exit-Bewertung' });
    expect(within(reviewRegion).getByRole('alert')).toBeVisible();
    expect(within(reviewRegion).queryByText('Exit-Bewertung nicht dokumentiert.')).toBeNull();
    const evidenceRegion = screen.getByRole('region', { name: 'Evidence und Lesson-Versionen' });
    expect(
      within(evidenceRegion).getByText(/Alte Herkunft nicht vollständig auflösbar/),
    ).toBeVisible();
    expect(
      within(evidenceRegion).getByText(
        /Materialisierungsbereitschaft und der Lesson-Reviewstatus werden hier nicht geprüft/,
      ),
    ).toBeVisible();
    expect(screen.queryByText(/6\/6|100\s*%|Review abgeschlossen|Lesson freigegeben/)).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it('retains explicit zero quantity and keeps date-only execution separate from capture time', async () => {
    mount();
    await screen.findByText('Eine eigene Reflexion');
    const position = screen.getByRole('region', { name: 'Position' });
    expect(within(position).getByText('0 Stück')).toBeVisible();
    const execution = screen.getByRole('article', { name: 'Quelle buy' });
    expect(
      within(execution).getByText(/Ausführung: 2026-08-05 · Uhrzeit unbekannt · Europe\/Berlin/),
    ).toBeVisible();
    await userEvent.click(within(execution).getByText('Herkunftsdetails'));
    expect(within(execution).getByText(/Erfasst:.*16:00:00 UTC/)).toBeVisible();
    expect(within(execution).queryByText(/2026-08-04T22:00:00|2026-08-05T00:00:00/)).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it('does not turn a missing execution side, amount or price into a sale or zero', async () => {
    const data = core();
    override = (url) =>
      url.pathname.endsWith('/sources')
        ? response({
            ...data,
            timeline: [
              {
                ...data.timeline[0],
                execution_side: null,
                quantity: null,
                price_per_unit: null,
                execution_timezone: null,
              },
            ],
          })
        : undefined;
    mount();
    await screen.findByText('Eine eigene Reflexion');
    const execution = screen.getByRole('article', { name: 'Quelle buy' });
    expect(within(execution).getByRole('heading')).toHaveTextContent(
      'Ausführungsart nicht dokumentiert',
    );
    expect(
      within(execution).getByText(/Menge: Nicht verfügbar; Preis je Stück: Nicht verfügbar/),
    ).toBeVisible();
    expect(within(execution).getByText(/Zeitzone nicht dokumentiert/)).toBeVisible();
    expect(within(execution).queryByText('Verkauf')).toBeNull();
    expect(within(execution).queryByText(/0 Stück/)).toBeNull();
  });

  it('keeps a current draft and a finalized empty journal independent from older evidence', async () => {
    reviewValue = review(R2, null, 'DRAFT');
    journalValue = { ...journal('FINALIZED'), what_went_well: '' };
    override = (url) => {
      if (url.pathname.endsWith('/reviews'))
        return response({
          history: [reviewValue, review()],
          selected: reviewValue,
          source_currentness: 'CURRENT',
          checked_at: NOW,
        });
      if (url.pathname.endsWith('/evidence')) return response([evidence(true)]);
      return undefined;
    };
    mount(`trade_id=${A}&view=sources&review_version_id=${R2}&journal_version_id=${J1}`);
    await screen.findByRole('link', { name: /Historische Interpretation.*CONTRADICTS/ });
    const reviewRegion = screen.getByRole('region', { name: 'Dokumentierte Exit-Bewertung' });
    expect(within(reviewRegion).getByText(/Exakt angeforderte Version: 2 · DRAFT/)).toBeVisible();
    expect(within(reviewRegion).getByText(/Heutige Quellenprüfung: CURRENT/)).toBeVisible();
    const journalRegion = screen.getByRole('region', { name: 'Journal' });
    expect(within(journalRegion).getByText('Finales Journal ohne Reflexionstext.')).toBeVisible();
    expect(within(journalRegion).getByText(/Heutige Prüfung.*STALE/)).toBeVisible();
    expect(
      within(journalRegion).getByText(
        'Der gespeicherte Status bewertet nicht die Vollständigkeit der Reflexion.',
      ),
    ).toBeVisible();
    expect(
      screen.getByRole('link', { name: 'Exakte Evidence-Reviewquelle lesen' }).getAttribute('href'),
    ).toContain(`review_version_id=${R1}`);
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it.each([
    ['2026-07-01T09:00:00', /2026-07-01T09:00:00 \(Zeitbasis nicht belegt\)/],
    ['2026-07-01T09:00:00+02:00', /7:00:00 UTC/],
    ['invalidZ', /invalidZ \(Zeitangabe nicht lesbar\)/],
  ])('does not invent the timezone of historical timestamp %s', async (value, expected) => {
    const data = plan();
    override = (url) => {
      if (url.pathname.endsWith('/sources')) return response(plannedCore());
      if (url.pathname.endsWith('/plan'))
        return response({
          ...data,
          candidate_evaluation: { ...data.candidate_evaluation, evaluated_at: value },
        });
      return undefined;
    };
    mount();
    const analysis = await screen.findByRole('region', { name: 'Analyse / Kandidat' });
    await within(analysis).findByText('evaluation-3 · Version 3');
    const time = within(analysis).getByText('Bewertungszeit').nextElementSibling;
    expect(time).toHaveTextContent(expected);
    if (String(value) === '2026-07-01T09:00:00') expect(time).not.toHaveTextContent('UTC');
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it('keeps source details focusable and opens native details without new reads', async () => {
    mount();
    await screen.findByText('Eine eigene Reflexion');
    const position = screen.getByRole('region', { name: 'Position' });
    const summary = within(position).getByText('Herkunftsdetails');
    summary.focus();
    expect(summary).toHaveFocus();
    await userEvent.click(summary);
    expect(summary.closest('details')).toHaveAttribute('open');
    expect(within(position).getByText(/Projektion für Trade/)).toBeVisible();
    expect(
      within(position).getByText('Eine eigene Positions-ID wird in dieser Quelle nicht geliefert.'),
    ).toBeVisible();
    await userEvent.click(summary);
    expect(summary.closest('details')).not.toHaveAttribute('open');
    expect(summary).toHaveClass('focus-visible:outline-sky-300');
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });
});
