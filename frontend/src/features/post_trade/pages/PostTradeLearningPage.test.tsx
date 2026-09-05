import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { lessonReadbackClient } from '../../learning/services/lessonReadbackClient';
import { ft011MaterializationClient } from '../../learning/services/materializationClient';
import { warrantApiClient } from '../../product/services/client';
import { tradeManagementApiClient } from '../../trade/services/client';
import { PostTradeLearningPage } from './PostTradeLearningPage';

vi.mock('./PostTradeReviewPage', () => ({
  PostTradeReviewPage: () => <div>review</div>,
}));

vi.mock('../../learning/components/LessonDraftFromEvidence', () => ({
  LessonDraftFromEvidence: () => <div>lesson-form</div>,
}));

vi.mock('../../learning/services/materializationClient', () => ({
  ft011MaterializationClient: { status: vi.fn(), materialize: vi.fn() },
}));

vi.mock('../../learning/services/lessonReadbackClient', () => ({
  lessonReadbackClient: {
    listForEvidence: vi.fn(),
    getLesson: vi.fn(),
  },
}));

vi.mock('../../product/services/client', () => ({
  warrantApiClient: { get: vi.fn() },
}));

vi.mock('../../trade/services/client', () => ({
  tradeManagementApiClient: { trade: vi.fn() },
}));

const status = vi.mocked(ft011MaterializationClient.status);
const materialize = vi.mocked(ft011MaterializationClient.materialize);
const listForEvidence = vi.mocked(lessonReadbackClient.listForEvidence);
const warrantGet = vi.mocked(warrantApiClient.get);
const tradeGet = vi.mocked(tradeManagementApiClient.trade);

const trade = {
  id: 'trade-1',
  product_id: 'product-1',
  origin: 'WORKSPACE_SELECTION' as const,
  trade_plan_id: 'plan-12345678',
  trade_plan_version_id: 'plan-version-1',
  product_selection_id: 'selection-1',
  product_evaluation_id: 'evaluation-1',
  created_at: '2026-08-18T10:00:00Z',
};

const warrant = {
  id: 'product-1',
  workspace_id: 'workspace-1',
  issuer_id: 'issuer-1',
  underlying_id: 'underlying-1',
  product_family: 'WARRANT' as const,
  display_name: 'DAX Call 19000',
  isin: 'DE000TEST123',
  wkn: 'TEST12',
  lifecycle_status: 'ACTIVE' as const,
  version: 1,
  created_at: '2026-08-18T09:00:00Z',
  updated_at: '2026-08-18T09:00:00Z',
};

describe('PostTradeLearningPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    tradeGet.mockResolvedValue(trade);
    warrantGet.mockResolvedValue(warrant);
    status.mockResolvedValue({
      ready: true,
      reason: 'READY',
      materialized: true,
      learning_evidence_id: 'evidence-1',
      exit_review_version_id: 'version-1',
    });
    materialize.mockResolvedValue({
      learning_evidence_id: 'evidence-1',
      exit_review_version_id: 'version-1',
      created: true,
      replayed: false,
    });
  });

  it('keeps visible Trade, product and TradePlan context above the review', async () => {
    listForEvidence.mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeLearningPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole('heading', { name: /TR-TRADE-1 · DAX Call 19000/ }),
    ).toBeInTheDocument();
    expect(screen.getByText(/ISIN DE000TEST123 · WKN TEST12/)).toBeInTheDocument();
    expect(screen.getByText('Workspace-Produktauswahl')).toBeInTheDocument();
    expect(screen.getByText('TP-PLAN-123')).toBeInTheDocument();
    expect(screen.getByText('LearningEvidence materialisiert')).toBeInTheDocument();
    expect(screen.getByText('review')).toBeInTheDocument();
    expect(tradeGet).toHaveBeenCalledWith('trade-1', expect.any(AbortSignal));
    expect(warrantGet).toHaveBeenCalledWith('product-1', expect.any(AbortSignal));
  });

  it('hands a ready finalized review to FT-012 before showing the Lesson form', async () => {
    status.mockResolvedValue({
      ready: true,
      reason: 'READY',
      materialized: false,
      learning_evidence_id: null,
      exit_review_version_id: 'version-1',
    });
    listForEvidence.mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeLearningPage />
      </MemoryRouter>,
    );

    const handoff = await screen.findByRole('button', { name: 'An Lessons Learned übergeben' });
    expect(screen.queryByText('lesson-form')).not.toBeInTheDocument();

    fireEvent.click(handoff);

    await waitFor(() =>
      expect(materialize).toHaveBeenCalledWith(
        'trade-1',
        'ft011-to-ft012:trade-1:version-1',
      ),
    );
    expect(await screen.findByText('lesson-form')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'An Lessons Learned übergeben' })).not.toBeInTheDocument();
  });

  it('shows existing Lessons and suppresses duplicate creation form', async () => {
    listForEvidence.mockResolvedValue([
      {
        lesson_id: 'lesson-1',
        current_version_id: 'lesson-version-1',
        current_state: 'CURRENT',
        title: 'Exit discipline',
      },
    ]);

    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeLearningPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Bereits interpretiert')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Exit discipline/ })).toHaveAttribute(
      'href',
      '/lessons/lesson-1',
    );
    expect(screen.queryByText('lesson-form')).not.toBeInTheDocument();
  });

  it('shows the create form when no Lesson references the Evidence', async () => {
    listForEvidence.mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeLearningPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(listForEvidence).toHaveBeenCalledWith('evidence-1', expect.anything()),
    );
    expect(screen.getByText('lesson-form')).toBeInTheDocument();
  });

  it('does not block review or learning when optional visible context cannot be loaded', async () => {
    tradeGet.mockRejectedValue(new Error('trade context unavailable'));
    listForEvidence.mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/post-trade?trade_id=trade-1']}>
        <PostTradeLearningPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(tradeGet).toHaveBeenCalled());
    expect(screen.getByText('review')).toBeInTheDocument();
    expect(await screen.findByText('lesson-form')).toBeInTheDocument();
    expect(screen.queryByText('Post-Trade-Kontext')).not.toBeInTheDocument();
  });
});
