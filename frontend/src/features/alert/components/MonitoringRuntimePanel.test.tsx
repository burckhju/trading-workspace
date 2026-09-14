import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { alertApiClient } from '../services/client';
import type { MonitoringRuntimeStatusResponse } from '../types/api';
import { MonitoringRuntimePanel } from './MonitoringRuntimePanel';

vi.mock('../services/client', () => ({ alertApiClient: { monitoringRuntime: vi.fn() } }));

const value: MonitoringRuntimeStatusResponse = {
  enabled: true,
  running: true,
  cycle_running: false,
  interval_seconds: 900,
  scope: 'PROCESS_LOCAL_ALL_WORKSPACES',
  price_basis: 'COMPLETED_UNDERLYING_DAILY_LOW_HIGH',
  last_cycle_started_at: '2026-09-14T13:00:00Z',
  last_cycle_completed_at: '2026-09-14T13:00:10Z',
  next_run_at: '2026-09-14T13:15:10Z',
  last_error: null,
  last_error_at: null,
  last_result: {
    positions_seen: 52,
    positions_checked: 50,
    subject_errors: 2,
    rules_evaluated: 100,
  },
};

describe('MonitoringRuntimePanel', () => {
  it('makes incomplete coverage visible despite a running scheduler', async () => {
    vi.mocked(alertApiClient.monitoringRuntime).mockResolvedValue(value);
    render(<MonitoringRuntimePanel />);
    expect(
      await screen.findByText('Prüfung aktiv · Daten- oder Regelfehler im letzten Durchlauf'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/50 von 52 Positionen mit Kursdaten geprüft; 100 Regeln/),
    ).toBeInTheDocument();
  });

  it('does not show an earlier completed cycle as recovery from a current failure', async () => {
    vi.mocked(alertApiClient.monitoringRuntime).mockResolvedValue({
      ...value,
      last_error: 'MONITORING_CYCLE_FAILED',
      last_error_at: '2026-09-14T13:15:11Z',
    });
    render(<MonitoringRuntimePanel />);
    expect(await screen.findByText('Letzter Prüfdurchlauf fehlgeschlagen')).toBeInTheDocument();
    expect(
      screen.getByText(/Zähler zeigen, soweit vorhanden, den vorherigen abgeschlossenen/),
    ).toBeInTheDocument();
  });

  it('does not interpret enabled configuration as a started runner', async () => {
    vi.mocked(alertApiClient.monitoringRuntime).mockResolvedValue({
      ...value,
      running: false,
      last_result: null,
    });
    render(<MonitoringRuntimePanel />);
    expect(
      await screen.findByText('Automatische Prüfung nicht gestartet oder beendet'),
    ).toBeInTheDocument();
    expect(screen.queryByText('Automatische Prüfung aktiv')).not.toBeInTheDocument();
  });
});
