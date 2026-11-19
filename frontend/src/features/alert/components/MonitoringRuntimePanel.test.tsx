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
    expect(
      screen.queryByRole('region', { name: 'Produkttermin-Erinnerungen' }),
    ).not.toBeInTheDocument();
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

  it('recognizes the separate V2 scope without presenting assumptions as B58 or complete monitoring', async () => {
    vi.mocked(alertApiClient.monitoringRuntime).mockResolvedValue({
      ...reviewValue,
      review_scope: 'INDICATIVE_ENTRY_V2',
      review_rule_version: 'indicative-entry-review-v2',
    });
    render(<MonitoringRuntimePanel />);
    expect(
      await screen.findByText('Letzter indikativer Prüfdurchlauf abgeschlossen'),
    ).toBeInTheDocument();
    const scope = within(screen.getByRole('region', { name: 'Indikative Einstandsbeobachtung' }));
    expect(scope.getByText('Regelumfang: INDICATIVE_ENTRY_V2')).toBeInTheDocument();
    expect(scope.getByText(/Erweiterter indikativer Teilumfang/)).toHaveTextContent(
      'Bekannte Widersprüche sperren den Vergleich',
    );
    expect(scope.getByText(/Erweiterter indikativer Teilumfang/)).toHaveTextContent(
      'Instrumentmarktstatus ist damit nicht bestätigt',
    );
    expect(
      scope.getByText('Positionen ausgewertet · letzter abgeschlossener Durchlauf'),
    ).toBeInTheDocument();
    expect(scope.queryByRole('button')).not.toBeInTheDocument();
    expect(alertApiClient.monitoringRuntime).toHaveBeenCalledOnce();
  });

  it('does not describe a mismatched V2 scope and V1 version as an assessed operating scope', async () => {
    vi.mocked(alertApiClient.monitoringRuntime).mockResolvedValue({
      ...reviewValue,
      review_scope: 'INDICATIVE_ENTRY_V2',
      review_rule_version: 'indicative-entry-review-v1',
    });
    render(<MonitoringRuntimePanel />);
    expect(
      await screen.findByText('Teilumfang gewählt · Regelversion nicht belegt'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Letzter indikativer Prüfdurchlauf abgeschlossen'),
    ).not.toBeInTheDocument();
  });

  it('keeps deadline coverage counters separate from entry comparisons and shows missing deadline evidence', async () => {
    vi.mocked(alertApiClient.monitoringRuntime).mockResolvedValue({
      ...reviewValue,
      review_scope: 'INDICATIVE_ENTRY_V2',
      review_rule_version: 'indicative-entry-review-v2',
      last_result: {
        ...reviewValue.last_result,
        deadline_positions_evaluated: 6,
        deadline_alerts_created: 3,
        deadline_data_problems: 3,
        deadline_position_errors: 0,
      },
    });
    render(<MonitoringRuntimePanel />);
    expect(
      await screen.findByText('Produkttermin-Prüfung mit Daten- oder Auswertungsproblemen'),
    ).toBeInTheDocument();
    const deadline = within(screen.getByRole('region', { name: 'Produkttermin-Erinnerungen' }));
    const entry = within(screen.getByRole('region', { name: 'Indikative Einstandsbeobachtung' }));
    expect(entry.getByText('2')).toBeInTheDocument();
    expect(deadline.getByText('6')).toBeInTheDocument();
    expect(entry.getByText('Letzter indikativer Prüfdurchlauf abgeschlossen')).toBeInTheDocument();
    expect(deadline.getByText(/vollständige B05-Qualifikation bleiben offen/)).toBeInTheDocument();
    expect(
      deadline.queryByText('Letzter Produkttermin-Prüfdurchlauf abgeschlossen'),
    ).not.toBeInTheDocument();
    expect(alertApiClient.monitoringRuntime).toHaveBeenCalledOnce();
  });
});
