import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { requestJson } from '../../market/services/http';
import { journalClient, type JournalHistory } from '../services/journalClient';
import { JournalEvidenceOrigin } from './JournalEvidenceOrigin';

vi.mock('../../market/services/http', () => ({ requestJson: vi.fn() }));
vi.mock('../services/journalClient', () => ({ journalClient: { version: vi.fn() } }));
const at = '2026-10-14T12:00:00Z';
const source = {
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
          would_do_differently: null,
          additional_notes: '  ',
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
});
it('reads the exact historical source with its original text and present stale check, not latest', async () => {
  mount();
  await screen.findByText('Originale persönliche Reflexion');
  expect(journalClient.version).toHaveBeenCalledWith('j1', expect.any(AbortSignal));
  expect(requestJson).toHaveBeenCalledWith(expect.stringContaining('/learning-evidence/evidence'), {
    signal: expect.any(AbortSignal),
  });
  expect(screen.getByText(/Quellenprüfung jetzt: STALE/)).toBeVisible();
  expect(screen.getByText(/2026-10-14T13:00:00Z/)).toBeVisible();
  expect(screen.getAllByText('Nicht ausgefüllt')).toHaveLength(2);
  expect(screen.getByRole('link', { name: 'Genau diese Journalversion öffnen' })).toHaveAttribute(
    'href',
    '/post-trade?trade_id=trade&journal_version_id=j1',
  );
  expect(requestJson).toHaveBeenCalledTimes(1);
});
it('does not substitute a different returned version and requires a deliberate read retry', async () => {
  const wrong = history();
  wrong.versions[0].version.id = 'j2';
  vi.mocked(journalClient.version).mockResolvedValue(wrong);
  mount();
  await screen.findByRole('alert');
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.queryByText('Originale persönliche Reflexion')).not.toBeInTheDocument();
  vi.mocked(journalClient.version).mockResolvedValue(history());
  fireEvent.click(screen.getByRole('button', { name: 'Quellenherkunft erneut laden' }));
  await screen.findByText('Originale persönliche Reflexion');
  expect(journalClient.version).toHaveBeenCalledTimes(2);
});
it('does not treat external evidence as a personal real-trade journal', async () => {
  vi.mocked(requestJson).mockResolvedValue({
    source: { type: 'EXTERNAL_OBSERVATION' },
    created_at: at,
  });
  mount();
  await screen.findByText(/Quellentyp: EXTERNAL_OBSERVATION/);
  expect(journalClient.version).not.toHaveBeenCalled();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});
it('keeps missing journal source identity explicit rather than requesting latest', async () => {
  vi.mocked(requestJson).mockResolvedValue({
    source: { type: 'TRADE_JOURNAL_VERSION' },
    created_at: at,
  });
  mount();
  await screen.findByRole('alert');
  expect(journalClient.version).not.toHaveBeenCalled();
});
it('ignores a late source response after evidence navigation', async () => {
  let resolve!: (value: unknown) => void;
  vi.mocked(requestJson).mockReturnValueOnce(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const view = mount();
  vi.mocked(requestJson).mockResolvedValue({ source: { type: 'FT011' }, created_at: at });
  view.rerender(
    <MemoryRouter>
      <JournalEvidenceOrigin evidenceId="other" />
    </MemoryRouter>,
  );
  await screen.findByText(/Quellentyp: FT011/);
  await act(async () => resolve(source));
  await waitFor(() => expect(screen.getByText(/Quellentyp: FT011/)).toBeVisible());
  expect(screen.queryByText('Originale persönliche Reflexion')).not.toBeInTheDocument();
});
