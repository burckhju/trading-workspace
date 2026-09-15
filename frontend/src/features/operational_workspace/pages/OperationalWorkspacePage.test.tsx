import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { operationalWorkspaceApiClient } from '../services/client';
import type { OperationalAction } from '../types';
import { OperationalWorkspacePage } from './OperationalWorkspacePage';

vi.mock('../services/client', () => ({
  operationalWorkspaceApiClient: { getActions: vi.fn(), getPositions: vi.fn() },
}));

function action(id: string, changes: Partial<OperationalAction> = {}): OperationalAction {
  return {
    id,
    source_feature: 'SYNTHETIC',
    action_type: 'POSITION_DATA_HEALTH',
    priority: 'ACTION',
    state: 'ACTIONABLE',
    title: 'Produktkurs fehlt',
    detail: 'Kein Kurs. Keine Orderfreigabe.',
    resource_type: 'trade',
    resource_id: id,
    next_action: 'Prüfen',
    target: `/trade-management?trade_id=${id}`,
    occurred_at: null,
    ...changes,
  };
}

function show(actions: OperationalAction[]) {
  vi.mocked(operationalWorkspaceApiClient.getActions).mockResolvedValue({
    generated_at: '2026-09-14T12:00:00Z',
    actions,
  });
  vi.mocked(operationalWorkspaceApiClient.getPositions).mockResolvedValue({
    generated_at: '2026-09-14T12:00:00Z',
    positions: [],
  });
  render(
    <MemoryRouter>
      <OperationalWorkspacePage />
    </MemoryRouter>,
  );
}

describe('workspace action product identity', () => {
  it.each([
    'POSITION_ALERT',
    'POSITION_DATA_HEALTH',
    'NOTIFICATION_DELIVERY_FAILURE',
    'INITIAL_PURCHASE',
    'OPEN_POSITION_MANAGEMENT',
    'POST_TRADE_OBSERVATION',
    'EXIT_REVIEW',
  ])('shows the exact product on %s even without open positions', async (action_type) => {
    show([
      action('alpha', {
        action_type,
        product_id: 'warrant-a',
        product_name: 'SYNTHETIC Alpha Call',
        product_isin: 'DE000SYN0010',
        product_wkn: 'SYN001',
      }),
      action('beta', {
        action_type,
        product_id: 'warrant-b',
        product_name: 'SYNTHETIC Beta Call',
        product_isin: 'DE000SYN0020',
        product_wkn: 'SYN002',
      }),
    ]);
    const alpha = (await screen.findByText('Optionsschein: SYNTHETIC Alpha Call')).closest('li')!;
    expect(within(alpha).getByText('WKN: SYN001 · ISIN: DE000SYN0010')).toBeInTheDocument();
    expect(within(alpha).queryByText(/Beta/)).not.toBeInTheDocument();
    expect(within(alpha).getByRole('link', { name: 'Öffnen' })).toHaveAttribute(
      'href',
      '/trade-management?trade_id=alpha',
    );
    expect(await screen.findByText('Optionsschein: SYNTHETIC Beta Call')).toBeInTheDocument();
    expect(operationalWorkspaceApiClient.getPositions).toHaveBeenCalledTimes(1);
    expect(operationalWorkspaceApiClient.getActions).toHaveBeenCalledTimes(1);
  });

  it('keeps missing product identity explicit and does not infer from the target', async () => {
    show([action('old-backend')]);
    expect(await screen.findByText('Optionsschein: Name nicht verfügbar')).toBeInTheDocument();
    expect(screen.getByText('WKN: — · ISIN: —')).toBeInTheDocument();
  });

  it('does not invent a warrant before product selection', async () => {
    show([
      action('unselected', {
        action_type: 'PRODUCT_SELECTION_CHOICE',
        resource_type: 'product_selection_run',
        title: 'Produkt auswählen',
      }),
    ]);
    await screen.findByText('Produkt auswählen');
    expect(screen.queryByText(/Optionsschein:/)).not.toBeInTheDocument();
  });

  it('renders special characters as text and normalizes blank names', async () => {
    show([
      action('markup', { product_id: 'a', product_name: 'SYNTHETIC <img src=x> & Call' }),
      action('blank', { product_id: 'b', product_name: '  \n  ' }),
    ]);
    expect(
      await screen.findByText('Optionsschein: SYNTHETIC <img src=x> & Call'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByText('Optionsschein: Name nicht verfügbar')).toBeInTheDocument();
  });
});
