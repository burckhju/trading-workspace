import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router-dom';

import {
  resolveReferenceDataContext,
  type ReferenceDataContext,
  type ResolvedReferenceDataContext,
} from '../services/referenceDataContext';
import { topDownAdminClient } from '../services/topDownAdminClient';
import { TopDownWorkflowActionPage } from './TopDownWorkflowActionPage';

vi.mock('../services/referenceDataContext', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../services/referenceDataContext')>()),
  resolveReferenceDataContext: vi.fn(),
}));
vi.mock('../services/topDownAdminClient', () => ({
  topDownAdminClient: {
    assignBenchmark: vi.fn(),
    assignSector: vi.fn(),
    assignSectorReference: vi.fn(),
    assignReferenceListing: vi.fn(),
    createMapping: vi.fn(),
    validateMapping: vi.fn(),
    importHistory: vi.fn(),
    activateReference: vi.fn(),
    activateSector: vi.fn(),
    createAnalysis: vi.fn(),
    runAnalysis: vi.fn(),
  },
}));
const client = vi.mocked(topDownAdminClient);
const resolve = vi.mocked(resolveReferenceDataContext);
function resolved(context: ReferenceDataContext): ResolvedReferenceDataContext {
  return {
    ...context,
    underlying: null,
    listing: null,
    reference: null,
    sector: null,
    mapping: null,
    workflow: null,
    workflowStep: null,
  };
}
function Destination() {
  const location = useLocation();
  return (
    <p>
      {location.pathname}
      {location.search}
    </p>
  );
}
function renderPage(search: string) {
  const router = createMemoryRouter(
    [
      { path: '/top-down-admin', element: <TopDownWorkflowActionPage /> },
      { path: '/chart-setup', element: <Destination /> },
      { path: '/candidates', element: <Destination /> },
      { path: '/underlyings/:id', element: <Destination /> },
    ],
    { initialEntries: [`/top-down-admin${search}`] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

beforeEach(() => {
  vi.clearAllMocks();
  resolve.mockImplementation((context) => Promise.resolve(resolved(context)));
  client.createAnalysis.mockResolvedValue({ id: 'a1', underlying_id: 'u1', listing_id: 'l1' });
  client.runAnalysis.mockResolvedValue({});
  client.activateReference.mockResolvedValue({
    id: 'r1',
    code: 'SPX',
    name: 'S&P 500',
    reference_type: 'INDEX',
    active: true,
  });
  client.activateSector.mockResolvedValue({
    id: 's1',
    code: 'TECH',
    name: 'Technology',
    active: true,
  });
});

describe('TopDownWorkflowActionPage canonical forwarding', () => {
  it.each([
    ['ASSIGN_BROAD_MARKET_BENCHMARK', 'underlying_id=u1'],
    ['ASSIGN_SECTOR', 'underlying_id=u1'],
    ['ASSIGN_SECTOR_REFERENCE', 'sector_id=s1'],
    ['ASSIGN_REFERENCE_LISTING', 'market_reference_id=r1'],
    ['CREATE_EODHD_MAPPING', 'listing_id=l1&underlying_id=u1'],
    ['VALIDATE_EODHD_MAPPING', 'mapping_id=m1&listing_id=l1&underlying_id=u1'],
    ['IMPORT_DAILY_PRICE_HISTORY', 'listing_id=l1&mapping_id=m1&underlying_id=u1'],
  ])(
    'forwards %s only after checked reads and renders no second form',
    async (action, identities) => {
      const router = renderPage(`?action=${action}&candidate_id=c1&${identities}`);
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
      await waitFor(() => expect(router.state.location.pathname).toBe('/chart-setup'));
      const params = new URLSearchParams(router.state.location.search);
      expect(params.get('action')).toBe(action);
      expect(params.get('candidate_id')).toBe('c1');
      expect(resolve).toHaveBeenCalledWith(
        expect.objectContaining({ workflowAction: action, candidateId: 'c1' }),
        expect.any(AbortSignal),
      );
      for (const method of Object.values(client)) expect(method).not.toHaveBeenCalled();
      expect(router.state.historyAction).toBe('REPLACE');
    },
  );

  it('translates market_reference_id to canonical reference_id and carries resolved owner', async () => {
    const router = renderPage(
      '?action=ASSIGN_REFERENCE_LISTING&candidate_id=c1&resource_id=r1&market_reference_id=r1',
    );
    await waitFor(() => expect(router.state.location.pathname).toBe('/chart-setup'));
    const params = new URLSearchParams(router.state.location.search);
    expect(params.get('reference_id')).toBe('r1');
    expect(params.has('market_reference_id')).toBe(false);
    expect(params.has('underlying_id')).toBe(false);
  });

  it('blocks unknown, incomplete and conflicting input without an editor or writes', async () => {
    renderPage('?action=VALIDATE_EODHD_MAPPING&candidate_id=c1&resource_id=m1&mapping_id=m2');
    expect(await screen.findByRole('alert')).toHaveTextContent('Widersprüchliche');
    expect(resolve).not.toHaveBeenCalled();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zurück zum Kandidaten' })).toHaveAttribute(
      'href',
      '/candidates?candidate=c1',
    );
  });

  it('shows failed freshness/identity reads as blocked, retaining the exact return', async () => {
    resolve.mockRejectedValue(new Error('Dieser konkrete Schritt hat sich geändert.'));
    const router = renderPage('?action=ASSIGN_SECTOR&candidate_id=c1&underlying_id=u1');
    expect(await screen.findByRole('alert')).toHaveTextContent('konkrete Schritt');
    expect(router.state.location.pathname).toBe('/top-down-admin');
    expect(client.assignSector).not.toHaveBeenCalled();
  });

  it('rejects an unknown workflow action instead of offering a generic submit', () => {
    renderPage('?action=UNKNOWN&candidate_id=c1');
    expect(screen.getByRole('alert')).toHaveTextContent('Unbekannte Aktion');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('ignores the first A response after A→B→A, including its late failure', async () => {
    const pending: Array<{
      context: ReferenceDataContext;
      signal?: AbortSignal;
      complete: (value: ResolvedReferenceDataContext) => void;
      fail: (reason: Error) => void;
    }> = [];
    resolve.mockImplementation(
      (context, signal) =>
        new Promise((complete, fail) => {
          pending.push({ context, signal, complete, fail });
        }),
    );
    const query = (underlyingId: string) =>
      `/top-down-admin?action=ASSIGN_SECTOR&candidate_id=c1&underlying_id=${underlyingId}`;
    const router = renderPage(query('a').slice('/top-down-admin'.length));
    await waitFor(() => expect(pending).toHaveLength(1));
    await act(() => router.navigate(query('b')));
    await waitFor(() => expect(pending).toHaveLength(2));
    await act(() => router.navigate(query('a')));
    await waitFor(() => expect(pending).toHaveLength(3));
    expect(pending[0].signal?.aborted).toBe(true);
    await act(async () => {
      pending[0].fail(new Error('Stale A failure'));
      pending[1].complete(resolved(pending[1].context));
      await Promise.resolve();
    });
    expect(router.state.location.pathname).toBe('/top-down-admin');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await act(async () => {
      pending[2].complete(resolved(pending[2].context));
      await Promise.resolve();
    });
    expect(router.state.location.pathname).toBe('/chart-setup');
    expect(new URLSearchParams(router.state.location.search).get('underlying_id')).toBe('a');
  });
});

describe('remaining unique workflow actions', () => {
  it('runs the existing explicit market analysis with exact identities once on double submit', async () => {
    const router = renderPage(
      '?action=RUN_MARKET_ANALYSIS&candidate_id=c1&underlying_id=u1&listing_id=l1',
    );
    fireEvent.change(screen.getByLabelText('Von'), { target: { value: '2026-01-01' } });
    fireEvent.change(screen.getByLabelText('Bis'), { target: { value: '2026-10-26' } });
    const button = screen.getByRole('button', { name: 'Aktion ausführen' });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(client.createAnalysis).toHaveBeenCalledWith('u1', 'l1'));
    expect(client.createAnalysis).toHaveBeenCalledTimes(1);
    expect(client.runAnalysis).toHaveBeenCalledWith('a1', '2026-01-01', '2026-10-26');
    await waitFor(() => expect(router.state.location.search).toBe('?candidate=c1'));
  });

  it.each([
    ['ACTIVATE_OR_REASSIGN_BENCHMARK', 'market_reference_id=r1', 'activateReference'],
    ['ACTIVATE_OR_REASSIGN_SECTOR_REFERENCE', 'resource_id=r1', 'activateReference'],
    ['ACTIVATE_OR_REASSIGN_SECTOR', 'sector_id=s1', 'activateSector'],
  ] as const)('preserves %s', async (action, query, method) => {
    renderPage(`?action=${action}&candidate_id=c1&${query}`);
    fireEvent.click(screen.getByRole('button', { name: 'Aktion ausführen' }));
    await waitFor(() =>
      expect(client[method]).toHaveBeenCalledWith(method === 'activateSector' ? 's1' : 'r1'),
    );
    expect(resolve).not.toHaveBeenCalled();
  });

  it('keeps primary listing maintenance in the existing underlying screen', () => {
    renderPage('?action=CREATE_OR_SELECT_PRIMARY_LISTING&candidate_id=c1&underlying_id=u1');
    expect(screen.getByRole('link', { name: 'Basiswert öffnen' })).toHaveAttribute(
      'href',
      '/underlyings/u1',
    );
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('uses the real route guard for a dirty analysis period, with focused stay and explicit discard', async () => {
    const router = renderPage(
      '?action=RUN_MARKET_ANALYSIS&candidate_id=c1&underlying_id=u1&listing_id=l1',
    );
    fireEvent.change(screen.getByLabelText('Von'), { target: { value: '2026-01-01' } });
    fireEvent.click(screen.getByRole('link', { name: 'Abbrechen' }));
    await screen.findByRole('alertdialog');
    expect(screen.getByRole('button', { name: 'Hier bleiben' })).toHaveFocus();
    expect(router.state.location.pathname).toBe('/top-down-admin');
    fireEvent.click(screen.getByRole('button', { name: 'Eingaben verwerfen und wechseln' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/candidates'));
  });

  it('does not offer discard or a second mutation while the existing write is pending', async () => {
    let finish!: (value: { id: string; underlying_id: string; listing_id: string }) => void;
    client.createAnalysis.mockReturnValue(
      new Promise((done) => {
        finish = done;
      }),
    );
    const router = renderPage(
      '?action=RUN_MARKET_ANALYSIS&candidate_id=c1&underlying_id=u1&listing_id=l1',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Aktion ausführen' }));
    fireEvent.click(screen.getByRole('link', { name: 'Abbrechen' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Speicherung läuft');
    expect(
      screen.queryByRole('button', { name: 'Eingaben verwerfen und wechseln' }),
    ).not.toBeInTheDocument();
    expect(client.createAnalysis).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Hier bleiben' }));
    await act(async () => {
      finish({ id: 'a1', underlying_id: 'u1', listing_id: 'l1' });
      await Promise.resolve();
    });
    await waitFor(() => expect(router.state.location.pathname).toBe('/candidates'));
  });
});
