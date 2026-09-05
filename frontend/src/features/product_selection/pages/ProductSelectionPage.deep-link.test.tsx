import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ProductSelectionPage } from './ProductSelectionPage';

const runDetail = {
  run: {
    id: '00000000-0000-4000-8000-000000000101',
    trade_plan_id: '00000000-0000-4000-8000-000000000201',
    trade_plan_version_id: '00000000-0000-4000-8000-000000000202',
    trade_plan_version_status: 'APPROVED',
    underlying_id: '00000000-0000-4000-8000-000000000301',
    evaluated_at: '2026-08-16T10:00:00Z',
    universe_model: { model_id: 'universe', model_version: '1' },
    eligibility_model: { model_id: 'eligibility', model_version: '1' },
    evaluation_model: { model_id: 'evaluation', model_version: '1' },
    created_at: '2026-08-16T10:00:00Z',
    created_by: '00000000-0000-4000-8000-000000000002',
  },
  evaluations: [
    {
      id: '00000000-0000-4000-8000-000000000401',
      run_id: '00000000-0000-4000-8000-000000000101',
      warrant_id: '00000000-0000-4000-8000-000000000501',
      warrant_terms_version_id: '00000000-0000-4000-8000-000000000502',
      warrant_listing_id: '00000000-0000-4000-8000-000000000503',
      evaluated_at: '2026-08-16T10:00:00Z',
      eligibility_model: { model_id: 'eligibility', model_version: '1' },
      evaluation_model: { model_id: 'evaluation', model_version: '1' },
      inputs: [],
      criteria: [],
      metrics: [],
      eligibility_status: 'ELIGIBLE',
      reasons: [],
    },
  ],
  universe_omissions: [],
  selection: null,
};

function requestUrl(value: RequestInfo | URL | undefined): string {
  if (typeof value === 'string') return value;
  if (value instanceof URL) return value.href;
  return value?.url ?? '';
}

describe('ProductSelectionPage run deep link', () => {
  afterEach(() => vi.restoreAllMocks());

  it('loads the exact run and hydrates its plan context from run_id', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(runDetail), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            {
              id: runDetail.run.id,
              trade_plan_id: runDetail.run.trade_plan_id,
              trade_plan_version_id: runDetail.run.trade_plan_version_id,
              evaluated_at: runDetail.run.evaluated_at,
              created_at: runDetail.run.created_at,
            },
          ]),
          { status: 200 },
        ),
      );

    render(
      <MemoryRouter initialEntries={[`/product-selection?run_id=${runDetail.run.id}`]}>
        <ProductSelectionPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Produktvergleich')).toBeInTheDocument();
    expect(screen.getByLabelText('TradePlan-ID')).toHaveValue(runDetail.run.trade_plan_id);
    expect(screen.getByLabelText('TradePlanVersion-ID')).toHaveValue(
      runDetail.run.trade_plan_version_id,
    );
    expect(screen.getAllByText(runDetail.run.id).length).toBeGreaterThan(0);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const firstUrl = requestUrl(fetchMock.mock.calls[0]?.[0]);
    const secondUrl = requestUrl(fetchMock.mock.calls[1]?.[0]);
    expect(firstUrl).toContain(`/product-selection-runs/${runDetail.run.id}`);
    expect(secondUrl).toContain(
      `trade_plan_version_id=${encodeURIComponent(runDetail.run.trade_plan_version_id)}`,
    );
  });
});
