import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import type { OperationalPosition } from '../types';
import { OpenPositionsPanel } from './OpenPositionsPanel';

function position(overrides: Partial<OperationalPosition> = {}): OperationalPosition {
  return {
    trade_id: 'trade-1',
    position_id: 'position-1',
    product_name: 'Test Warrant',
    opened_at: '2026-09-08T08:00:00Z',
    open_quantity: 10,
    average_entry_price: '2.00',
    cost_basis: '20.00',
    realized_gross_pnl: '1.50',
    stop_price: '19000.00',
    target_price: '20500.00',
    monitoring_status: 'OK',
    underlying_symbol: 'DAX.INDX',
    valuation_status: 'AVAILABLE',
    product_symbol: 'TEST12.STU',
    valuation_currency: 'EUR',
    market_value: '25.00',
    unrealized_gross_pnl: '5.00',
    open_alert_count: 0,
    open_alert_types: [],
    attention_state: 'OK',
    target: '/trade-management?trade_id=trade-1',
    ...overrides,
  };
}

describe('OpenPositionsPanel', () => {
  it('shows the compact healthy depot state and management link', () => {
    render(
      <MemoryRouter>
        <OpenPositionsPanel positions={[position()]} />
      </MemoryRouter>,
    );

    expect(screen.getByText('Test Warrant')).toBeInTheDocument();
    expect(screen.getByText('25 EUR')).toBeInTheDocument();
    expect(screen.getByText('5 EUR')).toBeInTheDocument();
    expect(screen.getByText('Monitoring: Aktuell')).toBeInTheDocument();
    expect(screen.getByText('Produktkurs: Aktuell')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Trade-Management' })).toHaveAttribute(
      'href',
      '/trade-management?trade_id=trade-1',
    );
  });

  it('does not present stale product valuation as a current market value', () => {
    render(
      <MemoryRouter>
        <OpenPositionsPanel
          positions={[
            position({
              valuation_status: 'STALE',
              market_value: null,
              unrealized_gross_pnl: null,
              attention_state: 'DATA_HEALTH',
            }),
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText('Daten prüfen')).toBeInTheDocument();
    expect(screen.getByText('Produktkurs: Veraltet')).toBeInTheDocument();
    expect(screen.getAllByText('—')).toHaveLength(2);
  });

  it('surfaces an existing position alert above normal health labels', () => {
    render(
      <MemoryRouter>
        <OpenPositionsPanel
          positions={[
            position({
              open_alert_count: 1,
              open_alert_types: ['STOP_REACHED'],
              attention_state: 'ALERT',
            }),
          ]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText('1 offener Alert')).toBeInTheDocument();
    expect(screen.getByText('Stop erreicht')).toBeInTheDocument();
  });
});
