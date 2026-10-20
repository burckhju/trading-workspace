import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { productSelectionApiClient } from '../services/client';
import type { ProductSelectionRunDetailResponse } from '../types/api';
import { ProductSelectionPage } from './ProductSelectionPage';

vi.mock('../services/client', () => ({
  productSelectionApiClient: {
    get: vi.fn(),
    listForTradePlanVersion: vi.fn(),
    start: vi.fn(),
    select: vi.fn(),
  },
}));
vi.mock('../services/useSelectionReferenceData', () => ({
  useSelectionReferenceData: () => ({
    products: {},
    plans: {},
    loading: false,
    errors: [],
    reload: vi.fn(),
  }),
}));
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
let detail: ProductSelectionRunDetailResponse;
beforeEach(() => {
  vi.resetAllMocks();
  detail = {
    run: {
      id: id(101),
      trade_plan_id: id(201),
      trade_plan_version_id: id(202),
      trade_plan_version_status: 'APPROVED',
      underlying_id: id(301),
      created_at: '2026-09-01T12:00:00Z',
      evaluated_at: '2026-09-01T12:00:00Z',
      created_by: id(2),
      universe_model: { model_id: 'u', model_version: '1' },
      eligibility_model: { model_id: 'e', model_version: '1' },
      evaluation_model: { model_id: 'm', model_version: '1' },
    },
    evaluations: [],
    universe_omissions: [],
    selection: null,
  };
  vi.mocked(productSelectionApiClient.get).mockImplementation(() => Promise.resolve(detail));
  vi.mocked(productSelectionApiClient.listForTradePlanVersion).mockResolvedValue([]);
});
function renderRun() {
  render(
    <MemoryRouter initialEntries={[`/product-selection?run_id=${id(101)}`]}>
      <ProductSelectionPage />
    </MemoryRouter>,
  );
}
describe('existing selection page has a way out of reference-data omissions', () => {
  it.each([
    ['NO_LISTING', 'Notierung fehlt', 'Notierung ergänzen'],
    ['NO_EFFECTIVE_TERMS', 'Gültige Produktbedingungen fehlen', 'Produktstammdaten prüfen'],
    ['FUTURE_REASON', 'FUTURE_REASON', 'Produktstammdaten prüfen'],
  ])(
    'links %s to the exact saved product and run without creating anything',
    async (reason, label, action) => {
      detail.universe_omissions = [{ warrant_id: id(401), reason, explanation: 'Saved reason' }];
      renderRun();
      expect(await screen.findByText(label)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: action })).toHaveAttribute(
        'href',
        `/warrants-admin?selection_run_id=${id(101)}&warrant_id=${id(401)}`,
      );
      expect(screen.getByText('Saved reason')).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: 'Dieses Produkt auswählen' }),
      ).not.toBeInTheDocument();
      expect(productSelectionApiClient.start).not.toHaveBeenCalled();
      expect(productSelectionApiClient.select).not.toHaveBeenCalled();
    },
  );
  it('offers the existing administration for a completely empty historical run, without guessing an instrument', async () => {
    renderRun();
    expect(
      await screen.findByText(/In diesem Bewertungslauf ist kein Optionsschein enthalten/),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Optionsscheinstammdaten prüfen' })).toHaveAttribute(
      'href',
      `/warrants-admin?selection_run_id=${id(101)}`,
    );
    expect(screen.getByText(/Dieser historische Lauf bleibt unverändert/)).toBeInTheDocument();
    expect(productSelectionApiClient.start).not.toHaveBeenCalled();
  });
});
