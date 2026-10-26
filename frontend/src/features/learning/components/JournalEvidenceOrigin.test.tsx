import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { requestJson } from '../../market/services/http';
import { journalClient, type JournalHistory } from '../services/journalClient';
import { lessonReviewClient, type EvidenceSummary } from '../services/lessonReviewClient';
import { JournalEvidenceOrigin } from './JournalEvidenceOrigin';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
vi.mock('../services/journalClient', () => ({ journalClient: { version: vi.fn() } }));
vi.mock('../services/lessonReviewClient', () => ({ lessonReviewClient: { source: vi.fn() } }));
const at = '2026-10-14T12:00:00Z';
const source: EvidenceSummary = {
  evidence_id: 'evidence',
  source_type: 'TRADE_JOURNAL_VERSION',
  source: { type: 'TRADE_JOURNAL_VERSION', trade_journal_version_id: 'j1' },
  created_at: at,
};
function history(): JournalHistory {
  return {
    trade_id: 'trade',
    journal_id: 'journal',
    handoff: { ready: false, reason: 'EXIT_REVIEW_STALE', exit_review_version_id: 'r2' },
    versions: [
      {
        version: {
          id: 'j1',
          trade_journal_id: 'journal',
          version: 1,
          edit_revision: 3,
          status: 'FINALIZED',
          source_exit_review_version_id: 'r1',
          supersedes_version_id: null,
          what_went_well: 'Originale persönliche Reflexion',
          would_do_differently: 'Originale Verbesserung',
          additional_notes: 'Originale Notizen',
          created_at: at,
          created_by: 'actor',
          updated_at: at,
          updated_by: 'actor',
          finalized_at: at,
          finalized_by: 'actor',
        },
        is_latest: false,
        source_currentness: 'STALE',
        source_checked_at: '2026-10-14T13:00:00Z',
        learning_evidence_id: 'evidence',
      },
    ],
  };
}
function mount(evidenceId = 'evidence') {
  return render(
    <MemoryRouter>
      <JournalEvidenceOrigin evidenceId={evidenceId} />
    </MemoryRouter>,
  );
}
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(requestJson).mockResolvedValue(source);
  vi.mocked(journalClient.version).mockResolvedValue(history());
  vi.mocked(lessonReviewClient.source).mockResolvedValue({
    evidence_id: 'evidence',
    source_type: 'TRADE_JOURNAL_VERSION',
    source_version_id: 'j1',
    source_currentness: 'SUPERSEDED',
    review_currentness: 'STALE',
    superseded_by_version_id: 'j2',
    checked_at: '2026-10-14T13:01:00Z',
  });
});
it('shows exact compact historical provenance once and separates lineage from review, without copying texts', async () => {
  mount();
  await screen.findByText('Quellversion jetzt: SUPERSEDED');
  expect(journalClient.version).toHaveBeenCalledWith('j1', expect.any(AbortSignal));
  expect(requestJson).toHaveBeenCalledWith(expect.stringContaining('/learning-evidence/evidence'), {
    signal: expect.any(AbortSignal),
  });
  expect(screen.getByText('Review-Quelle jetzt: STALE')).toBeVisible();
  expect(screen.getByText(/2026-10-14T13:01:00Z/)).toBeVisible();
  expect(screen.getAllByText('Quellentyp: TRADE_JOURNAL_VERSION')).toHaveLength(1);
  expect(screen.getAllByText('Konkrete Quellversion: j1')).toHaveLength(1);
  expect(screen.getAllByText(`Materialisiert: ${at}`)).toHaveLength(1);
  expect(screen.getByText(/Persönliches Trade-Journal · Version 1/)).toBeVisible();
  for (const text of [
    'Originale persönliche Reflexion',
    'Originale Verbesserung',
    'Originale Notizen',
    'Was lief gut?',
    'Was würde ich anders machen?',
    'Weitere Notizen',
  ]) {
    expect(screen.queryByText(text)).not.toBeInTheDocument();
  }
  expect(screen.getByRole('link', { name: 'Genau diese Journalversion öffnen' })).toHaveAttribute(
    'href',
    '/post-trade?trade_id=trade&journal_version_id=j1',
  );
  expect(screen.getByText(/Die heutige Quellenprüfung ändert/)).toBeVisible();
  expect(requestJson).toHaveBeenCalledTimes(1);
  expect(lessonReviewClient.source).toHaveBeenCalledTimes(1);
});
it('does not substitute a different returned version and requires a deliberate read retry', async () => {
  const wrong = history();
  wrong.versions[0].version.id = 'j2';
  vi.mocked(journalClient.version).mockResolvedValue(wrong);
  mount();
  await screen.findByRole('alert');
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(lessonReviewClient.source).not.toHaveBeenCalled();
  vi.mocked(journalClient.version).mockResolvedValue(history());
  fireEvent.click(screen.getByRole('button', { name: 'Quellenherkunft erneut laden' }));
  await screen.findByRole('link', { name: 'Genau diese Journalversion öffnen' });
  expect(journalClient.version).toHaveBeenCalledTimes(2);
});
it.each([
  ['EXTERNAL_OBSERVATION', 'external_observation_version_id'],
  ['EXTERNAL_OBSERVATION_JOURNAL_VERSION', 'external_observation_journal_version_id'],
  ['FT011', 'exit_review_version_id'],
])('does not treat %s evidence as a personal real-trade journal', async (type, field) => {
  vi.mocked(requestJson).mockResolvedValue({
    evidence_id: 'evidence',
    source_type: type,
    source: { type, [field]: 'external-v1' },
    created_at: at,
  });
  vi.mocked(lessonReviewClient.source).mockResolvedValue({
    evidence_id: 'evidence',
    source_type: type,
    source_version_id: 'external-v1',
    source_currentness: 'UNKNOWN',
    review_currentness: null,
    superseded_by_version_id: null,
    checked_at: at,
  });
  mount();
  await screen.findByText(`Quellentyp: ${type}`);
  await screen.findByText('Quellversion jetzt: UNKNOWN');
  expect(journalClient.version).not.toHaveBeenCalled();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.queryByText(/Persönliches Trade-Journal/)).not.toBeInTheDocument();
});
it.each([
  { ...source, source: { type: 'TRADE_JOURNAL_VERSION' } },
  { ...source, evidence_id: 'foreign-evidence' },
  { ...source, source_type: 'EXTERNAL_OBSERVATION' },
  { ...source, source_type: 'UNRECOGNIZED', source: { type: 'UNRECOGNIZED' } },
])(
  'rejects missing or inconsistent evidence identity without requesting latest',
  async (invalid) => {
    vi.mocked(requestJson).mockResolvedValue(invalid);
    mount();
    await screen.findByRole('alert');
    expect(journalClient.version).not.toHaveBeenCalled();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  },
);
it.each(['journal', 'evidence', 'draft', 'trade', 'duplicate'])(
  'rejects a mismatched %s in the exact journal origin',
  async (mismatch) => {
    const wrong = history();
    if (mismatch === 'journal') wrong.versions[0].version.trade_journal_id = 'foreign-journal';
    if (mismatch === 'evidence') wrong.versions[0].learning_evidence_id = 'foreign-evidence';
    if (mismatch === 'draft') wrong.versions[0].version.status = 'DRAFT';
    if (mismatch === 'trade') wrong.trade_id = '';
    if (mismatch === 'duplicate') wrong.versions.push(wrong.versions[0]);
    vi.mocked(journalClient.version).mockResolvedValue(wrong);
    mount();
    await screen.findByRole('alert');
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  },
);
it('keeps a failed currentness read separate from a valid exact historical link', async () => {
  vi.mocked(lessonReviewClient.source).mockRejectedValue(new Error('unavailable'));
  mount();
  await screen.findByText(/Quellenprüfung nicht verfügbar/);
  expect(screen.getByRole('link', { name: 'Genau diese Journalversion öffnen' })).toHaveAttribute(
    'href',
    '/post-trade?trade_id=trade&journal_version_id=j1',
  );
  expect(screen.queryByText(/Quellversion jetzt:/)).not.toBeInTheDocument();
});
it('ignores a late source response after evidence navigation', async () => {
  let resolve!: (value: unknown) => void;
  vi.mocked(requestJson).mockReturnValueOnce(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const view = mount();
  vi.mocked(requestJson).mockResolvedValue({
    evidence_id: 'other',
    source_type: 'FT011',
    source: { type: 'FT011', exit_review_version_id: 'r-other' },
    created_at: at,
  });
  view.rerender(
    <MemoryRouter>
      <JournalEvidenceOrigin evidenceId="other" />
    </MemoryRouter>,
  );
  await screen.findByText('Quellentyp: FT011');
  await act(() => Promise.resolve(resolve(source)));
  await waitFor(() => expect(screen.getByText('Quellentyp: FT011')).toBeVisible());
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(journalClient.version).not.toHaveBeenCalled();
});
it('keeps A→B→A lifetimes isolated under StrictMode', async () => {
  let resolveOld!: (value: unknown) => void;
  vi.mocked(requestJson).mockReturnValueOnce(
    new Promise((r) => {
      resolveOld = r;
    }),
  );
  const renderSource = (id: string) => (
    <StrictMode>
      <MemoryRouter>
        <JournalEvidenceOrigin evidenceId={id} />
      </MemoryRouter>
    </StrictMode>
  );
  const view = render(renderSource('evidence'));
  await screen.findByRole('link', { name: 'Genau diese Journalversion öffnen' });
  view.rerender(renderSource('other'));
  await screen.findByRole('alert');
  view.rerender(renderSource('evidence'));
  await screen.findByRole('link', { name: 'Genau diese Journalversion öffnen' });
  await act(async () => {
    resolveOld({
      ...source,
      source: { type: 'TRADE_JOURNAL_VERSION', trade_journal_version_id: 'old' },
    });
    await Promise.resolve();
  });
  expect(screen.getByRole('link', { name: 'Genau diese Journalversion öffnen' })).toHaveAttribute(
    'href',
    '/post-trade?trade_id=trade&journal_version_id=j1',
  );
  expect(journalClient.version).not.toHaveBeenCalledWith('old', expect.anything());
});
