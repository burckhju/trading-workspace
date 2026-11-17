import { act, render, screen, within } from '@testing-library/react';
import type { HebeltraderLossReport } from '../hebeltraderLoss';
import { readHebeltraderLoss } from '../services/hebeltraderLoss';
import { lossAssessment, lossEpisode, lossReport } from '../test/hebeltraderLossFixture';
import { HebeltraderLoss } from './HebeltraderLoss';

vi.mock('../services/hebeltraderLoss', () => ({ readHebeltraderLoss: vi.fn() }));

beforeEach(() => {
  vi.mocked(readHebeltraderLoss).mockReset().mockResolvedValue(lossReport());
});

it('separates partial activation, runner configuration and full baseline without commands', async () => {
  render(<HebeltraderLoss tradeId="trade-1" positionId="position-1" />);
  expect(await screen.findByText('Nicht aktiviert')).toBeInTheDocument();
  expect(screen.getByText('Deaktiviert')).toBeInTheDocument();
  expect(screen.getByText('Nicht vollständig aktiviert')).toBeInTheDocument();
  expect(
    screen.getByText(/B04\/B57 mit B58-Eingängen · hebeltrader-b04-b57-v1/),
  ).toBeInTheDocument();
  expect(screen.getByText(/Noch außerhalb dieses Teilumfangs:/)).toHaveTextContent(
    'B05 · Produktfristen',
  );
  expect(screen.getByText(/Noch keine B04\/B57-Bewertung gespeichert/)).toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(readHebeltraderLoss).toHaveBeenCalledOnce();
});

it('preserves an open loss episode beside unsuitable data and source blockage', async () => {
  const active = lossEpisode();
  vi.mocked(readHebeltraderLoss).mockResolvedValue(
    lossReport({
      activation_status: 'BLOCKED_SOURCE',
      runner_enabled: true,
      assessment_count: 2,
      latest_assessment: lossAssessment(),
      active_episode: active,
      recent_episodes: [active],
      episode_count: 1,
    }),
  );
  render(<HebeltraderLoss tradeId="trade-1" positionId="position-1" />);
  expect(
    await screen.findByText('Durch fehlende Quellenqualifikation blockiert'),
  ).toBeInTheDocument();
  expect(screen.getByText('Aktiviert; laufender Betrieb separat nachzuweisen')).toBeInTheDocument();
  expect(screen.getByText(/Verlustepisode 1 bleibt offen/)).toBeInTheDocument();
  expect(
    screen.getByText('Die Datenlücke beendet diese Verlustepisode nicht.'),
  ).toBeInTheDocument();
  expect(screen.getByText('Eingangsdaten nicht ausreichend qualifiziert')).toBeInTheDocument();
  expect(
    screen.getByText(/tatsächliche Anbieter-\/Instrument-\/Handelsplatzpfad/),
  ).toBeInTheDocument();
  const assessment = within(
    screen.getByRole('region', { name: 'Letzte gespeicherte B04-Bewertung' }),
  );
  expect(assessment.getByText('0.48')).toBeInTheDocument();
  expect(assessment.getByText('0.55')).toBeInTheDocument();
  expect(assessment.getByText('EUR')).toBeInTheDocument();
  expect(assessment.getByText('2300')).toBeInTheDocument();
  expect(assessment.getByText('20')).toBeInTheDocument();
});

it('shows a qualified partial scope without claiming that the runner is operating', async () => {
  vi.mocked(readHebeltraderLoss).mockResolvedValue(
    lossReport({
      activation_status: 'SCOPE_ENABLED',
      source_qualification_references: ['synthetic'],
      latest_assessment: lossAssessment({
        outcome: 'RECOVERED',
        reasons: ['B57_QUALIFIED_BID_AT_OR_ABOVE_ENTRY'],
      }),
      assessment_count: 1,
    }),
  );
  render(<HebeltraderLoss tradeId="trade-1" positionId="position-1" />);
  expect(await screen.findByText('Teilumfang zentral freigegeben')).toBeInTheDocument();
  expect(screen.getByText('Deaktiviert')).toBeInTheDocument();
  expect(screen.getByText('Qualifizierter Geldkurs mindestens auf Einstand')).toBeInTheDocument();
  expect(screen.queryByText(/bleibt offen/)).not.toBeInTheDocument();
});

it('does not turn a transport failure into recovery or no active episode', async () => {
  vi.mocked(readHebeltraderLoss).mockRejectedValue(
    new Error('Gespeicherter Prüfstand nicht lesbar.'),
  );
  render(<HebeltraderLoss tradeId="trade-1" positionId="position-1" />);
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Gespeicherter Prüfstand nicht lesbar.',
  );
  expect(screen.queryByText(/Keine offene Verlustepisode/)).not.toBeInTheDocument();
  expect(screen.queryByText(/auf Einstand/)).not.toBeInTheDocument();
});

function deferred() {
  let resolve!: (report: HebeltraderLossReport) => void;
  const promise = new Promise<HebeltraderLossReport>((yes) => {
    resolve = yes;
  });
  return { promise, resolve };
}

it('rejects stale responses across A to B to A and aborts on unmount', async () => {
  const first = deferred(),
    second = deferred(),
    third = deferred();
  vi.mocked(readHebeltraderLoss)
    .mockReturnValueOnce(first.promise)
    .mockReturnValueOnce(second.promise)
    .mockReturnValueOnce(third.promise);
  const view = render(<HebeltraderLoss tradeId="trade-A" positionId="position-A" />);
  const firstSignal = vi.mocked(readHebeltraderLoss).mock.calls[0][2];
  view.rerender(<HebeltraderLoss tradeId="trade-B" positionId="position-B" />);
  expect(firstSignal?.aborted).toBe(true);
  view.rerender(<HebeltraderLoss tradeId="trade-A" positionId="position-A" />);
  await act(async () => {
    third.resolve(lossReport({ trade_id: 'trade-A', position_id: 'position-A' }));
    await third.promise;
  });
  const active = lossEpisode();
  await act(async () => {
    first.resolve(
      lossReport({ active_episode: active, recent_episodes: [active], episode_count: 1 }),
    );
    second.resolve(lossReport({ activation_status: 'BLOCKED_SOURCE' }));
    await Promise.all([first.promise, second.promise]);
  });
  expect(screen.getByText('Nicht aktiviert')).toBeInTheDocument();
  expect(screen.queryByText(/Verlustepisode 1 bleibt offen/)).not.toBeInTheDocument();
  expect(
    screen.queryByText('Durch fehlende Quellenqualifikation blockiert'),
  ).not.toBeInTheDocument();
  const lastSignal = vi.mocked(readHebeltraderLoss).mock.calls[2][2];
  view.unmount();
  expect(lastSignal?.aborted).toBe(true);
});

it('rereads after an owner-basis change without requiring a user confirmation', async () => {
  const view = render(
    <HebeltraderLoss tradeId="trade-1" positionId="position-1" reloadToken="owner-before" />,
  );
  await screen.findByText('Nicht aktiviert');
  const firstSignal = vi.mocked(readHebeltraderLoss).mock.calls[0][2];
  view.rerender(
    <HebeltraderLoss tradeId="trade-1" positionId="position-1" reloadToken="owner-corrected" />,
  );
  await screen.findByText('Nicht aktiviert');
  expect(firstSignal?.aborted).toBe(true);
  expect(readHebeltraderLoss).toHaveBeenCalledTimes(2);
});
