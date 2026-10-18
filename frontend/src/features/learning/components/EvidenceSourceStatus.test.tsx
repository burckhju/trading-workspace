import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { lessonReviewClient, type SourceInspection } from '../services/lessonReviewClient';
import { EvidenceSourceStatus } from './EvidenceSourceStatus';
vi.mock('../services/lessonReviewClient', () => ({ lessonReviewClient: { source: vi.fn() } }));
const source = (id: string): SourceInspection => ({
  evidence_id: id,
  source_type: 'TRADE_JOURNAL_VERSION',
  source_version_id: `v-${id}`,
  source_currentness: 'SUPERSEDED',
  review_currentness: 'STALE',
  superseded_by_version_id: 'successor',
  checked_at: 'now',
});
beforeEach(() => vi.resetAllMocks());
it('currentness, upstream review, exact version and read time remain distinct', async () => {
  vi.mocked(lessonReviewClient.source).mockResolvedValue(source('e1'));
  render(<EvidenceSourceStatus evidenceId="e1" />);
  await screen.findByText('Quellversion jetzt: SUPERSEDED');
  expect(screen.getByText('Review-Quelle jetzt: STALE')).toBeInTheDocument();
  expect(screen.getByText('Konkrete Quellversion: v-e1')).toBeInTheDocument();
  expect(screen.getByText(/successor \(nicht automatisch übernommen\)/)).toBeInTheDocument();
  expect(screen.getByText(/keine Aussage über damaliges Wissen/)).toBeInTheDocument();
});
it('read error remains unavailable; manual retry can expose unknown, not manufactured current', async () => {
  vi.mocked(lessonReviewClient.source)
    .mockRejectedValueOnce(new Error('unavailable'))
    .mockResolvedValueOnce({
      ...source('e1'),
      source_currentness: 'UNKNOWN',
      review_currentness: null,
      superseded_by_version_id: null,
    });
  render(<EvidenceSourceStatus evidenceId="e1" />);
  await screen.findByText(/Quellenprüfung nicht verfügbar/);
  expect(screen.queryByText(/Quellversion jetzt:/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Quellenprüfung erneut laden' }));
  await screen.findByText('Quellversion jetzt: UNKNOWN');
  expect(lessonReviewClient.source).toHaveBeenCalledTimes(2);
  expect(screen.queryByText(/Review-Quelle jetzt/)).not.toBeInTheDocument();
});
it('late old-source response cannot populate another evidence identity', async () => {
  let resolve!: (value: SourceInspection) => void;
  vi.mocked(lessonReviewClient.source)
    .mockImplementationOnce(
      () =>
        new Promise((r) => {
          resolve = r;
        }),
    )
    .mockResolvedValueOnce(source('e2'));
  const view = render(<EvidenceSourceStatus evidenceId="e1" />);
  view.rerender(<EvidenceSourceStatus evidenceId="e2" />);
  await screen.findByText('Konkrete Quellversion: v-e2');
  await act(async () => {
    resolve(source('e1'));
    await Promise.resolve();
  });
  expect(screen.queryByText('Konkrete Quellversion: v-e1')).not.toBeInTheDocument();
});
