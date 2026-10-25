import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { marketApiClient } from '../../market/services/client';
import { MarketApiError, MarketTransportError } from '../../market/services/http';
import { warrantApiClient } from '../services/client';
import type { WarrantResponse, WarrantTermsResponse } from '../types/api';
import { WarrantAdminPage } from './WarrantAdminPage';

vi.mock('../../market/services/client', () => ({
  marketApiClient: {
    listIssuers: vi.fn(),
    searchUnderlyings: vi.fn(),
    listTradingVenues: vi.fn(),
    listCurrencies: vi.fn(),
  },
}));
vi.mock('../services/client', () => ({
  warrantApiClient: {
    list: vi.fn(),
    get: vi.fn(),
    terms: vi.fn(),
    listings: vi.fn(),
    create: vi.fn(),
    addTerms: vi.fn(),
    addListing: vi.fn(),
    correctIdentifiers: vi.fn(),
    deactivate: vi.fn(),
    reactivate: vi.fn(),
    delete: vi.fn(),
  },
}));

const market = vi.mocked(marketApiClient);
const warrants = vi.mocked(warrantApiClient);
const warrantA: WarrantResponse = {
  id: '00000000-0000-4000-8001-000000000401',
  workspace_id: '00000000-0000-4000-8000-000000000001',
  issuer_id: '00000000-0000-4000-8001-000000000301',
  underlying_id: '00000000-0000-4000-8001-000000000201',
  product_family: 'WARRANT',
  display_name: 'Alpha PUT',
  isin: 'DE000AAAA001',
  wkn: 'AAAA01',
  lifecycle_status: 'ACTIVE',
  version: 7,
  created_at: '2026-08-15T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};
const warrantB: WarrantResponse = {
  ...warrantA,
  id: '00000000-0000-4000-8001-000000000402',
  display_name: 'Beta CALL',
  isin: 'DE000BBBB002',
  wkn: 'BBBB02',
  version: 11,
};
const termsA: WarrantTermsResponse = {
  id: 'terms-a-3',
  warrant_id: warrantA.id,
  version_no: 3,
  effective_from: warrantA.updated_at,
  effective_to: null,
  option_direction: 'PUT',
  strike: '123.45',
  strike_currency_code: 'USD',
  maturity_date: '2027-12-17',
  ratio: '0.1',
  created_at: warrantA.updated_at,
};
const historicalTerms: WarrantTermsResponse = {
  ...termsA,
  id: 'terms-a-2',
  version_no: 2,
  effective_from: warrantA.created_at,
  effective_to: termsA.effective_from,
  strike: '98',
  strike_currency_code: null,
};
const termsB: WarrantTermsResponse = {
  ...termsA,
  id: 'terms-b-1',
  warrant_id: warrantB.id,
  version_no: 1,
  option_direction: 'CALL',
  strike: '222.20',
  strike_currency_code: 'CHF',
  ratio: '0.02',
};
let products: Map<string, WarrantResponse>;
let histories: Map<string, WarrantTermsResponse[]>;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((accept, fail) => {
    resolve = accept;
    reject = fail;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  products = new Map([
    [warrantA.id, { ...warrantA }],
    [warrantB.id, { ...warrantB }],
  ]);
  histories = new Map([
    [warrantA.id, [{ ...historicalTerms }, { ...termsA }]],
    [warrantB.id, [{ ...termsB }]],
  ]);
  market.listIssuers.mockResolvedValue({
    items: [
      {
        id: warrantA.issuer_id,
        legal_name: 'Synthetic Issuer AG',
        display_name: 'Synthetic Issuer',
        country_code: 'DE',
        lei: null,
      },
    ],
  });
  market.searchUnderlyings.mockResolvedValue({
    items: [
      {
        id: warrantA.underlying_id,
        type: 'STOCK',
        name: 'Synthetic Underlying',
        isin: null,
        wkn: null,
        lifecycle_status: 'ACTIVE',
        quality_status: 'COMPLETE',
        version: 1,
        created_at: warrantA.created_at,
        updated_at: warrantA.updated_at,
        primary_listing: null,
      },
    ],
    total: 1,
    offset: 0,
    limit: 100,
  });
  market.listTradingVenues.mockResolvedValue({
    items: [
      {
        id: 'venue-1',
        mic: 'XSTU',
        name: 'Synthetic Venue',
        country_code: 'DE',
        timezone: 'Europe/Berlin',
        reference_version: 'test',
      },
    ],
  });
  market.listCurrencies.mockResolvedValue({
    items: ['EUR', 'USD', 'CHF'].map((code) => ({
      code,
      name: code,
      minor_unit: 2,
      reference_version: 'test',
    })),
  });
  warrants.list.mockImplementation(() => Promise.resolve([...products.values()]));
  warrants.get.mockImplementation((id) => Promise.resolve({ ...products.get(id)! }));
  warrants.terms.mockImplementation((id) =>
    Promise.resolve(histories.get(id)!.map((terms) => ({ ...terms }))),
  );
  warrants.listings.mockResolvedValue([]);
  warrants.addTerms.mockImplementation((id, request) => {
    const previous = histories.get(id)!;
    const current = previous.find((terms) => terms.effective_to === null)!;
    const product = products.get(id)!;
    const changedAt = '2026-10-25T16:00:00Z';
    const next: WarrantTermsResponse = {
      id: `${current.id}-next`,
      warrant_id: id,
      version_no: current.version_no + 1,
      option_direction: request.option_direction,
      strike: request.strike,
      strike_currency_code: request.strike_currency_code ?? null,
      maturity_date: request.maturity_date,
      ratio: request.ratio,
      effective_from: changedAt,
      effective_to: null,
      created_at: changedAt,
    };
    histories.set(id, [
      ...previous.map((terms) =>
        terms.effective_to === null ? { ...terms, effective_to: changedAt } : terms,
      ),
      next,
    ]);
    products.set(id, { ...product, version: product.version + 1, updated_at: changedAt });
    return Promise.resolve(next);
  });
});

async function readyForTerms(name = warrantA.display_name) {
  await screen.findByRole('heading', { name });
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Produktbedingungen ändern' })).toBeEnabled(),
  );
}

async function editLoadedTerms() {
  fireEvent.click(screen.getByRole('button', { name: 'Produktbedingungen ändern' }));
  await waitFor(() =>
    expect(screen.getByLabelText('Neue Strike-Währung')).toHaveAttribute('aria-busy', 'false'),
  );
}

async function openTerms() {
  const view = render(<WarrantAdminPage />);
  await readyForTerms();
  await editLoadedTerms();
  return view;
}

function changeMaturity(value = '2030-11-15') {
  fireEvent.change(screen.getByLabelText('Neue Fälligkeit'), { target: { value } });
}

function saveTerms() {
  fireEvent.click(screen.getByRole('button', { name: 'Neue Terms-Version' }));
}

describe('current terms and immutable editor basis', () => {
  it('shows current terms once and opens historical values only after a deliberate selection', async () => {
    render(<WarrantAdminPage />);
    await readyForTerms();
    expect(screen.queryByLabelText('Anzeigename *')).not.toBeInTheDocument();
    expect(screen.getAllByText(/123[.,]45 USD/)).toHaveLength(1);
    expect(screen.queryByText(/98 \(Währung ungeklärt\)/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Änderungshistorie'));
    const history = screen.getByLabelText('Historische Bedingungsversion');
    expect(history).toHaveValue('');
    fireEvent.change(history, { target: { value: historicalTerms.id } });
    expect(screen.getByText(/98 \(Währung ungeklärt\)/)).toBeVisible();
    expect(screen.getByText(/\bHistorisch\b/)).toBeVisible();
    expect(screen.getAllByText(/123[.,]45 USD/)).toHaveLength(1);
  });

  it('prefills PUT and sends one complete version when only maturity changes', async () => {
    await openTerms();
    expect(screen.getByLabelText('Neue Richtung')).toHaveValue('PUT');
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue('123.45');
    expect(screen.getByLabelText('Neue Strike-Währung')).toHaveValue('USD');
    expect(screen.getByLabelText('Neues Bezugsverhältnis')).toHaveValue('0.1');
    expect(screen.queryByText(/123[.,]45 USD/)).not.toBeInTheDocument();
    changeMaturity();
    saveTerms();

    await waitFor(() => expect(warrants.addTerms).toHaveBeenCalledTimes(1));
    expect(warrants.addTerms).toHaveBeenCalledWith(warrantA.id, {
      expected_version: 7,
      option_direction: 'PUT',
      strike: '123.45',
      strike_currency_code: 'USD',
      maturity_date: '2030-11-15',
      ratio: '0.1',
    });
    await waitFor(() => expect(screen.queryByLabelText('Neuer Strike')).not.toBeInTheDocument());
    expect(histories.get(warrantA.id)![1]).toMatchObject({
      id: termsA.id,
      strike: termsA.strike,
      maturity_date: termsA.maturity_date,
    });
    expect(warrants.create).not.toHaveBeenCalled();
  });

  it.each([null, undefined])(
    'preserves zero and unresolved strike currency %s',
    async (currency) => {
      histories.set(warrantA.id, [{ ...termsA, strike: '0', strike_currency_code: currency }]);
      warrants.listings.mockResolvedValue([
        {
          id: 'listing-a',
          warrant_id: warrantA.id,
          workspace_id: warrantA.workspace_id,
          trading_venue_id: 'venue-1',
          symbol: null,
          quotation_currency_code: 'EUR',
          lifecycle_status: 'ACTIVE',
          version: 1,
          created_at: warrantA.created_at,
          updated_at: warrantA.updated_at,
        },
      ]);
      await openTerms();
      expect(screen.getByLabelText('Neuer Strike')).toHaveValue('0');
      expect(screen.getByLabelText('Neue Strike-Währung')).toHaveValue('');
      changeMaturity();
      saveTerms();

      await waitFor(() =>
        expect(warrants.addTerms).toHaveBeenCalledWith(
          warrantA.id,
          expect.objectContaining({ strike: '0', strike_currency_code: null, expected_version: 7 }),
        ),
      );
      expect(warrants.addTerms).toHaveBeenCalledTimes(1);
    },
  );

  it('keeps long decimal values as API strings without numeric rounding', async () => {
    const strike = '123.4500000000000000001';
    const ratio = '0.1000000000000000001';
    histories.set(warrantA.id, [{ ...termsA, strike, ratio }]);
    await openTerms();
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue(strike);
    expect(screen.getByLabelText('Neues Bezugsverhältnis')).toHaveValue(ratio);
    changeMaturity();
    saveTerms();
    await waitFor(() =>
      expect(warrants.addTerms).toHaveBeenCalledWith(
        warrantA.id,
        expect.objectContaining({ strike, ratio, expected_version: 7 }),
      ),
    );
  });

  it('does not mutate when editing is opened, cancelled or the saved product is reloaded', async () => {
    await openTerms();
    changeMaturity();
    fireEvent.click(screen.getByRole('button', { name: 'Bedingungen abbrechen' }));
    expect(screen.queryByLabelText('Neue Fälligkeit')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Produkt neu laden' }));
    await readyForTerms();
    await editLoadedTerms();
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue(termsA.maturity_date);
    expect(screen.getByLabelText('Neue Richtung')).toHaveValue('PUT');
    expect(warrants.addTerms).not.toHaveBeenCalled();
    expect(warrants.addListing).not.toHaveBeenCalled();
    expect(warrants.create).not.toHaveBeenCalled();
  });

  it('preserves a draft when an object switch is declined and starts B from its own terms', async () => {
    await openTerms();
    changeMaturity();
    vi.mocked(window.confirm).mockReturnValueOnce(false);
    fireEvent.click(screen.getByRole('button', { name: /Beta CALL/ }));
    expect(screen.getByRole('heading', { name: warrantA.display_name })).toBeInTheDocument();
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue('2030-11-15');

    vi.mocked(window.confirm).mockReturnValueOnce(true);
    fireEvent.click(screen.getByRole('button', { name: /Beta CALL/ }));
    await readyForTerms(warrantB.display_name);
    await editLoadedTerms();
    expect(screen.getByLabelText('Neue Richtung')).toHaveValue('CALL');
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue(termsB.strike);
    expect(screen.getByLabelText('Neue Strike-Währung')).toHaveValue('CHF');
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue(termsB.maturity_date);
    expect(warrants.addTerms).not.toHaveBeenCalled();
  });

  it('keeps the draft and original expected version across a catalogue refresh', async () => {
    await openTerms();
    changeMaturity();
    products.set(warrantA.id, { ...warrantA, version: 8 });
    histories.set(warrantA.id, [{ ...termsA, id: 'external-change', strike: '456.78' }]);
    warrants.addTerms.mockRejectedValueOnce(
      new MarketApiError(409, {
        code: 'WARRANT_CONCURRENT_MODIFICATION',
        message: 'Produktversion wurde geändert.',
        details: [],
        timestamp: '2026-10-25T16:00:00Z',
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Katalog neu laden' }));
    await waitFor(() => expect(warrants.list).toHaveBeenCalledTimes(2));
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue('123.45');
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue('2030-11-15');
    saveTerms();
    expect(await screen.findByRole('alert')).toHaveTextContent('Versionskonflikt');
    expect(warrants.addTerms).toHaveBeenCalledWith(
      warrantA.id,
      expect.objectContaining({
        expected_version: 7,
        strike: '123.45',
        maturity_date: '2030-11-15',
      }),
    );
    expect(warrants.addTerms).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['missing', []],
    ['closed only', [historicalTerms]],
    ['two current versions', [termsA, { ...termsA, id: 'second-open' }]],
    ['foreign product terms', [{ ...termsA, warrant_id: warrantB.id }]],
  ] as const)('blocks invented defaults for %s current terms', async (_case, terms) => {
    histories.set(warrantA.id, [...terms]);
    render(<WarrantAdminPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/Bedingungen|Produkt/);
    const edit = screen.queryByRole('button', { name: 'Produktbedingungen ändern' });
    if (edit) expect(edit).toBeDisabled();
    expect(screen.queryByLabelText('Neue Richtung')).not.toBeInTheDocument();
    expect(warrants.addTerms).not.toHaveBeenCalled();
  });

  it('rejects a product returned for another identity', async () => {
    warrants.get.mockResolvedValue(warrantB);
    render(<WarrantAdminPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/Produkt|Kontext/);
    expect(screen.queryByLabelText('Neuer Strike')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: warrantB.display_name })).not.toBeInTheDocument();
    expect(warrants.addTerms).not.toHaveBeenCalled();
  });

  it('does not offer an editor for terms read across changing product versions', async () => {
    warrants.get
      .mockResolvedValueOnce(warrantA)
      .mockResolvedValueOnce({ ...warrantA, version: warrantA.version + 1 });
    render(<WarrantAdminPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/geändert|Version|konsistent/);
    const edit = screen.queryByRole('button', { name: 'Produktbedingungen ändern' });
    if (edit) expect(edit).toBeDisabled();
    expect(warrants.addTerms).not.toHaveBeenCalled();
  });
});

describe('isolated reads, writes and error recovery', () => {
  it('ignores a delayed read of A after B has been opened', async () => {
    const pending = deferred<WarrantTermsResponse[]>();
    warrants.terms.mockReturnValueOnce(pending.promise);
    render(<WarrantAdminPage />);
    await waitFor(() =>
      expect(warrants.terms).toHaveBeenCalledWith(warrantA.id, expect.any(AbortSignal)),
    );
    fireEvent.click(await screen.findByRole('button', { name: /Beta CALL/ }));
    await readyForTerms(warrantB.display_name);
    await act(async () => {
      pending.resolve([termsA]);
      await pending.promise;
    });
    expect(screen.getByRole('heading', { name: warrantB.display_name })).toBeInTheDocument();
    await editLoadedTerms();
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue(termsB.strike);
    expect(screen.getByLabelText('Neue Richtung')).toHaveValue('CALL');
  });

  it('does not show a late read error from A on B', async () => {
    const pending = deferred<WarrantTermsResponse[]>();
    warrants.terms.mockReturnValueOnce(pending.promise);
    render(<WarrantAdminPage />);
    await waitFor(() =>
      expect(warrants.terms).toHaveBeenCalledWith(warrantA.id, expect.any(AbortSignal)),
    );
    fireEvent.click(await screen.findByRole('button', { name: /Beta CALL/ }));
    await readyForTerms(warrantB.display_name);
    await act(async () => {
      pending.reject(new Error('Nur A konnte nicht gelesen werden'));
      await pending.promise.catch(() => undefined);
    });
    expect(screen.queryByText('Nur A konnte nicht gelesen werden')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: warrantB.display_name })).toBeInTheDocument();
  });

  it('locks inputs and product switching synchronously across a pending save', async () => {
    const pending = deferred<WarrantTermsResponse>();
    warrants.addTerms.mockReturnValueOnce(pending.promise);
    await openTerms();
    changeMaturity();
    const form = screen.getByRole('button', { name: 'Neue Terms-Version' }).closest('form')!;
    act(() => {
      fireEvent.submit(form);
      fireEvent.submit(form);
    });
    expect(warrants.addTerms).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Neuer Strike')).toBeDisabled();
    expect(screen.getByLabelText('Neue Fälligkeit')).toBeDisabled();
    expect(screen.getByLabelText('Neue Richtung')).toBeDisabled();
    expect(screen.getByRole('button', { name: /Beta CALL/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Produkt neu laden' })).toBeDisabled();
    await act(async () => {
      pending.resolve({ ...termsA, id: 'terms-a-4', version_no: 4, maturity_date: '2030-11-15' });
      await pending.promise;
    });
  });

  it('does not change B or its messages after an A save resolves following unmount', async () => {
    const pending = deferred<WarrantTermsResponse>();
    warrants.addTerms.mockReturnValueOnce(pending.promise);
    const view = await openTerms();
    changeMaturity();
    saveTerms();
    view.unmount();
    warrants.list.mockResolvedValue([warrantB]);
    render(<WarrantAdminPage />);
    await readyForTerms(warrantB.display_name);
    await act(async () => {
      pending.resolve({ ...termsA, id: 'terms-a-4', version_no: 4, maturity_date: '2030-11-15' });
      await pending.promise;
    });
    expect(screen.getByRole('heading', { name: warrantB.display_name })).toBeInTheDocument();
    expect(screen.queryByText(/Bedingungen.*gespeichert/)).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await editLoadedTerms();
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue(termsB.strike);
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue(termsB.maturity_date);
    expect(warrants.addTerms).toHaveBeenCalledTimes(1);
  });

  it('keeps a conflicted draft until current data is deliberately compared and adopted', async () => {
    warrants.addTerms.mockRejectedValueOnce(
      new MarketApiError(409, {
        code: 'WARRANT_CONCURRENT_MODIFICATION',
        message: 'Produkt wurde zwischenzeitlich geändert.',
        details: [],
        timestamp: '2026-10-25T16:00:00Z',
      }),
    );
    await openTerms();
    changeMaturity();
    saveTerms();
    expect(await screen.findByRole('alert')).toHaveTextContent(/geändert|Versionskonflikt/);
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue('2030-11-15');
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue('123.45');
    products.set(warrantA.id, { ...warrantA, version: 8 });
    histories.set(warrantA.id, [
      { ...termsA, id: 'external-terms', strike: '150.25', version_no: 4 },
    ]);
    fireEvent.click(screen.getByRole('button', { name: 'Aktuellen Stand zum Vergleich laden' }));
    const adopt = await screen.findByRole('button', {
      name: 'Aktuellen Stand als Ausgangsbasis übernehmen',
    });
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue('2030-11-15');
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue('123.45');
    expect(warrants.addTerms).toHaveBeenCalledTimes(1);
    expect(warrants.addTerms.mock.calls[0][1].expected_version).toBe(7);

    vi.mocked(window.confirm).mockReturnValueOnce(false);
    fireEvent.click(adopt);
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue('2030-11-15');
    vi.mocked(window.confirm).mockReturnValueOnce(true);
    fireEvent.click(adopt);
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue('150.25');
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue(termsA.maturity_date);
    changeMaturity('2031-11-14');
    saveTerms();
    await waitFor(() => expect(warrants.addTerms).toHaveBeenCalledTimes(2));
    expect(warrants.addTerms.mock.calls[1]).toEqual([
      warrantA.id,
      {
        expected_version: 8,
        option_direction: 'PUT',
        strike: '150.25',
        strike_currency_code: 'USD',
        maturity_date: '2031-11-14',
        ratio: '0.1',
      },
    ]);
  });

  it('retains inputs after an uncertain transport failure without automatically retrying the write', async () => {
    warrants.addTerms.mockRejectedValueOnce(new MarketTransportError('Verbindung unterbrochen.'));
    await openTerms();
    changeMaturity();
    saveTerms();
    expect(await screen.findByRole('alert')).toHaveTextContent(/Verbindung|Abschluss|unklar/);
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue('2030-11-15');
    expect(screen.getByLabelText('Neuer Strike')).toHaveValue('123.45');
    await act(() => Promise.resolve());
    expect(warrants.addTerms).toHaveBeenCalledTimes(1);
  });

  it('keeps a confirmed terms save successful when refresh fails and only rereads on reload', async () => {
    await openTerms();
    changeMaturity();
    warrants.terms.mockRejectedValueOnce(new Error('Details vorübergehend nicht erreichbar'));
    saveTerms();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      /Anzeige konnte nicht aktualisiert werden/,
    );
    expect(
      await screen.findByText(/Produktbedingungen gespeichert.*Nicht erneut speichern/),
    ).toHaveAttribute('role', 'status');
    expect(screen.queryByRole('button', { name: 'Neue Terms-Version' })).not.toBeInTheDocument();
    expect(warrants.addTerms).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Produkt neu laden' }));
    await readyForTerms();
    await editLoadedTerms();
    expect(screen.getByLabelText('Neue Fälligkeit')).toHaveValue('2030-11-15');
    expect(warrants.addTerms).toHaveBeenCalledTimes(1);
  });

  it('does not display two mutation forms for the same product', async () => {
    await openTerms();
    expect(screen.queryByLabelText('Verifizierte ISIN')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Handelsplatz')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Notierung hinzufügen' }));
    expect(screen.queryByLabelText('Handelsplatz')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Bedingungen abbrechen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Notierung hinzufügen' }));
    expect(screen.getByLabelText('Handelsplatz')).toBeInTheDocument();
    expect(screen.queryByLabelText('Neuer Strike')).not.toBeInTheDocument();
  });

  it('guards a dirty listing on object switch and never transfers its input to B', async () => {
    render(<WarrantAdminPage />);
    await readyForTerms();
    fireEvent.click(screen.getByRole('button', { name: 'Notierung hinzufügen' }));
    fireEvent.change(screen.getByLabelText('Symbol'), { target: { value: 'ONLY-A' } });
    fireEvent.change(screen.getByLabelText('Handelswährung'), { target: { value: 'USD' } });
    vi.mocked(window.confirm).mockReturnValueOnce(false);
    fireEvent.click(screen.getByRole('button', { name: /Beta CALL/ }));
    expect(screen.getByLabelText('Symbol')).toHaveValue('ONLY-A');
    vi.mocked(window.confirm).mockReturnValueOnce(true);
    fireEvent.click(screen.getByRole('button', { name: /Beta CALL/ }));
    await readyForTerms(warrantB.display_name);
    fireEvent.click(screen.getByRole('button', { name: 'Notierung hinzufügen' }));
    expect(screen.getByLabelText('Symbol')).toHaveValue('');
    expect(screen.getByLabelText('Handelswährung')).toHaveValue('');
    expect(warrants.addListing).not.toHaveBeenCalled();
  });
});
