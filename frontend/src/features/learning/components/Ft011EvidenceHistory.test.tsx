import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';

import { Ft011EvidenceHistory } from './Ft011EvidenceHistory';
import { ft011MaterializationClient } from '../services/materializationClient';
import type { Ft011EvidenceHistoryItem } from '../types/materialization';

vi.mock('../services/materializationClient', () => ({
  ft011MaterializationClient: { history: vi.fn(), materialize: vi.fn() },
}));
const item: Ft011EvidenceHistoryItem = {
  learning_evidence_id: 'evidence-old',
  evidence_type: 'FT011',
  materialized_at: '2026-09-01T12:00:00Z',
  trade_id: 'trade-A',
  post_trade_observation_id: 'observation-A',
  exit_review_id: 'review-A',
  exit_review_version_id: 'review-v1',
  review_version: 1,
  review_status: 'FINALIZED',
  stored_review_currentness: 'CURRENT',
  source_currentness: 'STALE',
  superseded_by_version_id: 'review-v2',
  checked_at: '2026-10-16T18:00:00Z',
  lesson_links: [
    {
      link_id: 'link1',
      lesson_id: 'lesson1',
      lesson_title: 'Old interpretation',
      lesson_version_id: 'lesson-v1',
      lesson_version: 1,
      relation: 'CONTRADICTS',
      is_current_version: false,
    },
  ],
};
const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
};
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(ft011MaterializationClient.history).mockResolvedValue([item]);
});
function content(tradeId = 'trade-A', refreshVersion = 0) {
  return (
    <MemoryRouter>
      <Ft011EvidenceHistory key={tradeId} tradeId={tradeId} refreshVersion={refreshVersion} />
    </MemoryRouter>
  );
}
it('reads exact historical IDs and relation without requiring ready or making a command', async () => {
  render(content());
  expect(await screen.findByText(/Quellenprüfung: STALE/)).toBeInTheDocument();
  expect(screen.getByText(/Gespeichert: FINALIZED · CURRENT/)).toBeInTheDocument();
  expect(screen.getByText(/Späterer Reviewstand: review-v2/)).toBeInTheDocument();
  expect(
    screen.getByRole('link', { name: /Old interpretation · Version 1 · CONTRADICTS · historisch/ }),
  ).toHaveAttribute('href', '/lessons/lesson1?lesson_version_id=lesson-v1#lesson-history');
  expect(screen.getByText('ExitReviewVersion: review-v1')).toBeInTheDocument();
  expect(ft011MaterializationClient.materialize).not.toHaveBeenCalled();
});
it('does not call loading or failure an empty inventory; explicit retry restores it', async () => {
  const pending = deferred<Ft011EvidenceHistoryItem[]>();
  vi.mocked(ft011MaterializationClient.history).mockReturnValueOnce(pending.promise);
  const mounted = render(content());
  expect(screen.getByRole('status')).toHaveTextContent('Evidence-Historie wird geladen');
  expect(screen.queryByText(/Noch keine Review-Evidence/)).not.toBeInTheDocument();
  await act(async () => {
    pending.resolve([]);
    await pending.promise;
  });
  expect(await screen.findByText(/Noch keine Review-Evidence/)).toBeInTheDocument();
  vi.mocked(ft011MaterializationClient.history).mockRejectedValueOnce(new Error('offline'));
  mounted.rerender(content('trade-A', 1));
  expect(await screen.findByRole('alert')).toHaveTextContent('bedeutet nicht');
  expect(screen.queryByText(/Noch keine Review-Evidence/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Evidence-Historie neu laden' }));
  expect(await screen.findByText(/Quellenprüfung: STALE/)).toBeInTheDocument();
});
it('ignores a late response from a different trade and aborts the old request', async () => {
  const pending = deferred<Ft011EvidenceHistoryItem[]>();
  vi.mocked(ft011MaterializationClient.history)
    .mockReturnValueOnce(pending.promise)
    .mockResolvedValueOnce([]);
  const mounted = render(content());
  const signal = vi.mocked(ft011MaterializationClient.history).mock.calls[0][1]!;
  mounted.rerender(content('trade-B'));
  expect(await screen.findByText(/Noch keine Review-Evidence/)).toBeInTheDocument();
  await act(async () => {
    pending.resolve([item]);
    await pending.promise;
  });
  expect(signal.aborted).toBe(true);
  expect(screen.queryByText(/Quellenprüfung: STALE/)).not.toBeInTheDocument();
  expect(ft011MaterializationClient.materialize).not.toHaveBeenCalled();
});
it('ignores a late same-trade refresh and keeps UNKNOWN distinct from CURRENT', async () => {
  const pending = deferred<Ft011EvidenceHistoryItem[]>();
  vi.mocked(ft011MaterializationClient.history)
    .mockReturnValueOnce(pending.promise)
    .mockResolvedValueOnce([{ ...item, source_currentness: 'UNKNOWN' }]);
  const mounted = render(content());
  mounted.rerender(content('trade-A', 1));
  await screen.findByText(/Quellenprüfung: UNKNOWN/);
  await act(async () => {
    pending.resolve([item]);
    await pending.promise;
  });
  await waitFor(() => expect(screen.queryByText(/Quellenprüfung: STALE/)).not.toBeInTheDocument());
});
