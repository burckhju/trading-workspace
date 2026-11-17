import { render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
  beforeEach(() => {
    vi.clearAllMocks();
  });

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

  const reviewValue: MonitoringRuntimeStatusResponse = {
    ...value,
    review_scope: 'INDICATIVE_ENTRY_V1',
    review_rule_version: 'indicative-entry-review-v1',
    review_notifications_enabled: false,
    last_result: {
      ...value.last_result,
      review_positions_evaluated: 2,
      review_alerts_created: 1,
      review_data_problems: 0,
      review_position_errors: 0,
    },
  };

  it.each<[string, Partial<MonitoringRuntimeStatusResponse>, string]>([
    ['missing scope', { review_scope: undefined }, 'Aktivierung dieses Teilumfangs nicht belegt'],
    ['disabled', { review_scope: 'DISABLED' }, 'Indikative Beobachtung deaktiviert'],
    [
      'unknown version',
      { review_rule_version: undefined },
      'Teilumfang gewählt · Regelversion nicht belegt',
    ],
    [
      'disabled runner',
      { enabled: false, running: false },
      'Teilumfang gewählt · Hintergrundprüfung deaktiviert',
    ],
    ['not started', { running: false }, 'Teilumfang gewählt · Hintergrundprüfung nicht gestartet'],
    [
      'no completion',
      { last_cycle_completed_at: null },
      'Teilumfang eingeschaltet · erster Abschluss noch nicht belegt',
    ],
    [
      'missing results',
      { last_result: value.last_result },
      'Teilumfang eingeschaltet · Prüfergebnis nicht verfügbar',
    ],
    [
      'failed cycle',
      { last_error: 'MONITORING_CYCLE_FAILED' },
      'Teilumfang eingeschaltet · letzter Prüfdurchlauf fehlgeschlagen',
    ],
    [
      'data problem',
      { last_result: { ...reviewValue.last_result, review_data_problems: 1 } },
      'Teilumfang eingeschaltet · Daten- oder Auswertungsprobleme',
    ],
    [
      'position error',
      { last_result: { ...reviewValue.last_result, review_position_errors: 1 } },
      'Teilumfang eingeschaltet · Daten- oder Auswertungsprobleme',
    ],
    [
      'no positions',
      { last_result: { ...reviewValue.last_result, review_positions_evaluated: 0 } },
      'Teilumfang eingeschaltet · keine Position ausgewertet',
    ],
  ])(
    'keeps indicative configuration and actual progress separate: %s',
    async (_name, overrides, label) => {
      vi.mocked(alertApiClient.monitoringRuntime).mockResolvedValue({
        ...reviewValue,
        ...overrides,
      });
      render(<MonitoringRuntimePanel />);

      expect(await screen.findByText(label)).toBeInTheDocument();
      expect(
        screen.queryByText('Letzter indikativer Prüfdurchlauf abgeschlossen'),
      ).not.toBeInTheDocument();
      expect(
        screen.getByText(/Dieser Teilumfang aktiviert keine qualifizierte B04\/B57/),
      ).toHaveTextContent('keine vollständige Hebeltrader-Baseline');
    },
  );

  it('shows a completed indicative cycle and disabled external delivery without another request or activation form', async () => {
    vi.mocked(alertApiClient.monitoringRuntime).mockResolvedValue(reviewValue);
    render(<MonitoringRuntimePanel />);

    expect(
      await screen.findByText('Letzter indikativer Prüfdurchlauf abgeschlossen'),
    ).toBeInTheDocument();
    const scope = within(screen.getByRole('region', { name: 'Indikative Einstandsbeobachtung' }));
    expect(scope.getByText('Regelversion: indicative-entry-review-v1')).toBeInTheDocument();
    expect(
      scope.getByText(/externe Zustellung dieses Teilumfangs ausgeschaltet/),
    ).toBeInTheDocument();
    expect(
      scope.getByText('Positionen ausgewertet · letzter abgeschlossener Durchlauf'),
    ).toBeInTheDocument();
    expect(scope.getByText('2')).toBeInTheDocument();
    expect(scope.queryByRole('button')).not.toBeInTheDocument();
    expect(vi.mocked(alertApiClient.monitoringRuntime)).toHaveBeenCalledExactlyOnceWith(
      expect.any(AbortSignal),
    );
  });

  it('does not turn enabled external delivery into an actual delivered notification', async () => {
    vi.mocked(alertApiClient.monitoringRuntime).mockResolvedValue({
      ...reviewValue,
      review_notifications_enabled: true,
    });
    render(<MonitoringRuntimePanel />);

    expect(
      await screen.findByText(/Externe Zustellung dieses Teilumfangs konfiguriert/),
    ).toHaveTextContent('tatsächlichen Versand am jeweiligen Hinweis prüfen');
    expect(screen.queryByText(/zugestellt/)).not.toBeInTheDocument();
  });
});
