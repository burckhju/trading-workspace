import { MarketApiError, requestJson } from '../../market/services/http';
import { lossAssessment, lossEpisode, lossReport } from '../test/hebeltraderLossFixture';
import { readHebeltraderLoss, verifyHebeltraderLoss } from './hebeltraderLoss';

vi.mock('../../market/services/http', async (original) => ({
  ...(await original<typeof import('../../market/services/http')>()),
  requestJson: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(requestJson).mockReset();
});

it('reads only the exact position-scoped GET with cancellation and no user inputs', async () => {
  const report = lossReport({ trade_id: 'trade/a', position_id: 'position/b' });
  vi.mocked(requestJson).mockResolvedValueOnce(report);
  const signal = new AbortController().signal;
  expect(await readHebeltraderLoss('trade/a', 'position/b', signal)).toBe(report);
  expect(requestJson).toHaveBeenCalledExactlyOnceWith(
    expect.stringMatching(/trades\/trade%2Fa\/hebeltrader-loss\?position_id=position%2Fb$/),
    { signal },
  );
});

it('accepts an existing episode alongside a data gap without inferring recovery', () => {
  const active = lossEpisode();
  const report = lossReport({
    latest_assessment: lossAssessment(),
    assessment_count: 2,
    active_episode: active,
    recent_episodes: [active],
    episode_count: 1,
  });
  expect(verifyHebeltraderLoss(report, 'trade-1', 'position-1')).toBe(report);
  expect(report.latest_assessment?.outcome).toBe('NOT_ASSESSABLE');
  expect(report.active_episode?.closed_at).toBeNull();
});

it.each(['LOSS', 'RECOVERED', 'NOT_ASSESSABLE', 'NOT_REACHED', 'CLOSED'] as const)(
  'preserves owner outcome %s without calculating losses in the browser',
  (outcome) => {
    const report = lossReport({
      assessment_count: 1,
      latest_assessment: lossAssessment({
        outcome,
        gross_entry: outcome === 'CLOSED' ? '0E-10' : '0.55',
      }),
    });
    expect(verifyHebeltraderLoss(report, 'trade-1', 'position-1')).toBe(report);
  },
);

it('keeps a qualified enabled scope distinct from its disabled runner', () => {
  const report = lossReport({
    activation_status: 'SCOPE_ENABLED',
    source_qualification_references: ['synthetic-qualified-reference'],
  });
  expect(verifyHebeltraderLoss(report, 'trade-1', 'position-1').runner_enabled).toBe(false);
});

it('rejects foreign scope, invented activation and inconsistent episode copies', () => {
  const original = lossReport();
  const active = lossEpisode();
  const cases: unknown[] = [
    null,
    [],
    { ...original, trade_id: 'foreign' },
    { ...original, position_id: 'foreign' },
    { ...original, definition_version: 'future' },
    { ...original, rule_scope: 'FULL_BASELINE' },
    { ...original, baseline_id: 'other' },
    { ...original, baseline_version: 'future' },
    { ...original, full_baseline_activated: true },
    { ...original, remaining_scope: [] },
    { ...original, read_status: 'WRITE' },
    { ...original, runner_enabled: 'true' },
    { ...original, activation_status: 'SCOPE_ENABLED' },
    {
      ...original,
      activation_status: 'BLOCKED_SOURCE',
      source_qualification_references: ['invented'],
    },
    { ...original, read_at: '2026-11-17' },
    { ...original, read_at: '2026-02-30T12:00:00Z' },
    { ...original, read_at: '2026-11-17T24:00:00Z' },
    { ...original, read_at: '2026-11-17T12:00:00-00:00' },
    { ...original, assessment_count: 1 },
    { ...original, latest_assessment: lossAssessment() },
    { ...original, episode_count: 1 },
    { ...original, active_episode: active },
    { ...original, episode_count: 1, recent_episodes: [active] },
    {
      ...original,
      episode_count: 1,
      active_episode: { ...active, alert_id: 'different' },
      recent_episodes: [active],
    },
    { ...original, episode_count: 2, active_episode: active, recent_episodes: [active, active] },
    {
      ...original,
      episode_count: 2,
      active_episode: active,
      recent_episodes: [active, { ...active, id: 'another' }],
    },
    { ...original, assessment_count: 1, latest_assessment: lossAssessment({ bid: 'NaN' }) },
    {
      ...original,
      assessment_count: 1,
      latest_assessment: lossAssessment({ outcome: 'LOSS', bid_at: null }),
    },
    { ...original, assessment_count: -1 },
  ];
  for (const value of cases)
    expect(() => verifyHebeltraderLoss(value, 'trade-1', 'position-1')).toThrow(
      /B04\/B57-Regelstand/,
    );
});

it('accepts closed episode history without inventing an active episode', () => {
  const closed = lossEpisode({
    closed_at: '2026-11-17T12:00:00Z',
    close_reason: 'RECOVERED',
    closing_assessment_id: 'assessment-1',
  });
  const report = lossReport({
    recent_episodes: [closed],
    episode_count: 1,
    latest_assessment: lossAssessment({ outcome: 'RECOVERED' }),
    assessment_count: 2,
  });
  expect(verifyHebeltraderLoss(report, 'trade-1', 'position-1')).toBe(report);
});

it('reports read failures without asserting missing business evidence and preserves abort', async () => {
  vi.mocked(requestJson).mockRejectedValueOnce(new Error('unavailable'));
  await expect(readHebeltraderLoss('trade-1', 'position-1')).rejects.toThrow(
    /Zustand einer Verlustepisode ist damit nicht geklärt/,
  );
  vi.mocked(requestJson).mockRejectedValueOnce(
    new MarketApiError(403, {
      code: 'DENIED',
      message: 'No',
      details: [],
      timestamp: '2026-11-17T12:00:00Z',
    }),
  );
  await expect(readHebeltraderLoss('trade-1', 'position-1')).rejects.toThrow(/Keine Berechtigung/);
  const abort = new DOMException('Aborted', 'AbortError');
  vi.mocked(requestJson).mockRejectedValueOnce(abort);
  await expect(readHebeltraderLoss('trade-1', 'position-1')).rejects.toBe(abort);
});
