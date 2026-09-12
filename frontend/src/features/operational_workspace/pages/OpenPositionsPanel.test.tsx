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
    position_signal: {
      trade_id: 'trade-1',
      position_id: 'position-1',
      alert_level: 'NORMAL',
      attention_required: false,
      quality_status: 'AVAILABLE',
      reason: 'NO_POSITION_ATTENTION_REQUIRED',
      candidate_stop: '1.80',
      latest_price: '2.50',
      phase: 'TREND',
      policy_version: 'POSITION_ALERT_V1',
      dynamic_stop_policy_version: 'DYNAMIC_STOP_V1',
      analysis_run_id: 'analysis-1',
    },
    ...overrides,
  };
}

describe('OpenPositionsPanel', () => {
  it('labels the previous-session valuation as outdated and indicative', () => {
    render(
      <MemoryRouter>
        <OpenPositionsPanel positions={[position({ valuation_status: 'LAST_AVAILABLE' })]} />
      </MemoryRouter>,
    );

    expect(screen.getByText('Produktkurs: Letzter verfügbarer Kurs')).toBeInTheDocument();
    expect(screen.getByText(/Kursdaten veraltet:/)).toHaveTextContent('Keine Orderfreigabe');
    expect(screen.getByText('25 EUR')).toBeInTheDocument();
  });

  it('shows direct sell capture and management links for an open position', () => {
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
    expect(
      screen.getByText('Positionssignal: keine besondere Aufmerksamkeit nötig'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Trade verwalten' })).toHaveAttribute(
      'href',
      '/trade-management?trade_id=trade-1',
    );
    expect(screen.getByRole('link', { name: 'Verkauf erfassen' })).toHaveAttribute(
      'href',
      '/trade-management?trade_id=trade-1',
    );
    expect(screen.queryByPlaceholderText('UUID des Trades')).not.toBeInTheDocument();
  });

  it('keeps sell capture available when product valuation is stale', () => {
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
    expect(screen.getByRole('link', { name: 'Verkauf erfassen' })).toHaveAttribute(
      'href',
      '/trade-management?trade_id=trade-1',
    );
  });

  it('surfaces an existing position alert without blocking sell capture', () => {
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

    expect(screen.getByText('1 offener Hinweis')).toBeInTheDocument();
    expect(screen.getByText('Stop erreicht')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Verkauf erfassen' })).toBeInTheDocument();
  });

  it('shows critical and stale position signals in German', () => {
    const critical = position({
      position_signal: {
        ...position().position_signal!,
        alert_level: 'CRITICAL',
        attention_required: true,
        reason: 'DYNAMIC_STOP_BREACHED',
      },
    });
    const stale = position({
      trade_id: 'trade-2',
      position_id: 'position-2',
      position_signal: {
        ...position().position_signal!,
        trade_id: 'trade-2',
        position_id: 'position-2',
        alert_level: null,
        attention_required: false,
        quality_status: 'STALE',
        reason: 'COMPLETED_DAILY_PRICE_STALE',
      },
    });

    render(
      <MemoryRouter>
        <OpenPositionsPanel positions={[critical, stale]} />
      </MemoryRouter>,
    );

    expect(screen.getByText('Positionssignal: dynamischer Stop erreicht')).toBeInTheDocument();
    expect(screen.getByText('Positionssignal: Daten veraltet')).toBeInTheDocument();
  });
});
