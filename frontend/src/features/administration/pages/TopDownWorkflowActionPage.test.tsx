import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { topDownAdminClient } from '../services/topDownAdminClient';
import { TopDownWorkflowActionPage } from './TopDownWorkflowActionPage';

vi.mock('../services/topDownAdminClient', () => ({
  topDownAdminClient: {
    references: vi.fn(),
    sectors: vi.fn(),
    mappings: vi.fn(),
    assignBenchmark: vi.fn(),
    assignSector: vi.fn(),
    assignSectorReference: vi.fn(),
    assignReferenceListing: vi.fn(),
    createMapping: vi.fn(),
    validateMapping: vi.fn(),
    activateReference: vi.fn(),
    activateSector: vi.fn(),
    importHistory: vi.fn(),
    createAnalysis: vi.fn(),
    runAnalysis: vi.fn(),
  },
}));

const client = vi.mocked(topDownAdminClient);

function renderPage(search: string) {
  render(
    <MemoryRouter initialEntries={[`/admin/top-down${search}`]}>
      <Routes>
        <Route path="/admin/top-down" element={<TopDownWorkflowActionPage />} />
        <Route path="/candidates" element={<div>Candidate destination</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('TopDownWorkflowActionPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    client.references.mockResolvedValue([
      { id: 'r1', code: 'SPX', name: 'S&P 500', reference_type: 'INDEX', active: true },
    ]);
    client.sectors.mockResolvedValue([
      { id: 's1', code: 'TECH', name: 'Technology', active: true },
    ]);
    client.mappings.mockResolvedValue([]);
    client.assignBenchmark.mockResolvedValue({} as never);
    client.createMapping.mockResolvedValue({} as never);
    client.createAnalysis.mockResolvedValue({ id: 'a1', underlying_id: 'u1', listing_id: 'l1' });
    client.runAnalysis.mockResolvedValue({} as never);
  });

  it('assigns benchmark', async () => {
    renderPage('?action=ASSIGN_BROAD_MARKET_BENCHMARK&candidate_id=c1&underlying_id=u1');
    fireEvent.change(await screen.findByRole('combobox'), { target: { value: 'r1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Aktion ausführen' }));
    await waitFor(() => expect(client.assignBenchmark).toHaveBeenCalledWith('u1', 'r1'));
  });

  it('creates mapping', async () => {
    renderPage('?action=CREATE_EODHD_MAPPING&candidate_id=c1&underlying_id=u1&listing_id=l1');
    const inputs = await screen.findAllByRole('textbox');
    fireEvent.change(inputs[0], { target: { value: 'SAP' } });
    fireEvent.change(inputs[1], { target: { value: 'XETRA' } });
    fireEvent.click(screen.getByRole('button', { name: 'Aktion ausführen' }));
    await waitFor(() => expect(client.createMapping).toHaveBeenCalledWith('l1', 'SAP', 'XETRA'));
  });

  it('runs market analysis', async () => {
    renderPage('?action=RUN_MARKET_ANALYSIS&candidate_id=c1&underlying_id=u1&listing_id=l1');
    await screen.findByText('RUN_MARKET_ANALYSIS');
    fireEvent.click(screen.getByRole('button', { name: 'Aktion ausführen' }));
    await waitFor(() => expect(client.createAnalysis).toHaveBeenCalledWith('u1', 'l1'));
    expect(client.runAnalysis).toHaveBeenCalled();
  });
});
