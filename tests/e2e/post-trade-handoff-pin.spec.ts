import { expect, test, type Page } from '@playwright/test';
import type { JournalHistory } from '../../frontend/src/features/learning/services/journalClient';

// Browser/HTTP boundary tests with intercepted synthetic API data, not database E2E.
const tradeId = '11111111-1111-4111-8111-111111111111';
const version1 = '22222222-2222-4222-8222-222222222222';
const version2 = '33333333-3333-4333-8333-333333333333';
const evidenceId = '44444444-4444-4444-8444-444444444444';
const lessonId = '55555555-5555-4555-8555-555555555555';
const lessonVersionId = '66666666-6666-4666-8666-666666666666';
const journalId = '88888888-8888-4888-8888-888888888888';
const journalDraftId = '99999999-9999-4999-8999-999999999999';
const journalFinalId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const at = '2026-08-18T12:00:00Z';
const createdLessonHref = `/lessons/${lessonId}?trade_id=${tradeId}&trade_return_view=journal#lesson-history`;
const referencedLessonHref = `/lessons/${lessonId}?trade_id=${tradeId}&trade_return_view=journal&lesson_version_id=${lessonVersionId}#lesson-history`;
const journalLessonHref = `/lessons/${lessonId}?trade_id=${tradeId}&journal_version_id=${journalFinalId}&trade_return_view=journal#lesson-history`;

async function setup(
  page: Page,
  mode: 'draft' | 'ready' | 'changed' | 'stale-replay' | 'journal-navigation',
  failLessonReadback = false,
) {
  let finalized = mode !== 'draft';
  let currentVersion = version1;
  let ready = finalized;
  let materialized = false;
  let interpreted = false;
  let lessonContent = '';
  let reason = finalized ? 'READY' : 'EXIT_REVIEW_NOT_FINALIZED';
  let rationale = '';
  const writes: {
    path: string;
    method: string;
    body: unknown;
    key?: string;
  }[] = [];
  const statusReads: { ready: boolean; version: string }[] = [];
  const review = () => ({
    exit_review_id: 'review-1',
    current_version_id: currentVersion,
    version: currentVersion === version1 ? 1 : 2,
    status: finalized ? 'FINALIZED' : 'DRAFT',
    currentness: reason === 'EXIT_REVIEW_STALE' ? 'STALE' : 'CURRENT',
    timing: 'GOOD',
    process_adherence: 'GOOD',
    risk_decision: 'GOOD',
    overall_exit_decision: 'NOT_ASSESSABLE',
    rationale,
    created_at: at,
    created_by: 'actor-1',
    finalized_at: finalized ? at : null,
    finalized_by: finalized ? 'actor-1' : null,
    supersedes_version_id: currentVersion === version1 ? null : version1,
    stale_at: reason === 'EXIT_REVIEW_STALE' ? at : null,
    stale_reason: reason === 'EXIT_REVIEW_STALE' ? 'INPUT_CHANGED' : null,
  });
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname.split('/api/v1')[1];
    const body = req.postData() ? req.postDataJSON() : null;
    if (req.method() !== 'GET') {
      writes.push({
        path,
        method: req.method(),
        body,
        key: req.headers()['idempotency-key'],
      });
    }
    const json = (value: unknown, status = 200) => route.fulfill({ status, json: value });
    if (mode === 'journal-navigation' && path.endsWith('/journal') && req.method() === 'GET') {
      const history: JournalHistory = {
        trade_id: tradeId,
        journal_id: journalId,
        handoff: { ready: true, reason: 'READY', exit_review_version_id: version1 },
        versions: [2, 1].map((version) => ({
          version: {
            id: version === 2 ? journalDraftId : journalFinalId,
            trade_journal_id: journalId,
            version,
            edit_revision: 1,
            status: version === 2 ? 'DRAFT' : 'FINALIZED',
            source_exit_review_version_id: version1,
            supersedes_version_id: version === 2 ? journalFinalId : null,
            created_at: at,
            created_by: 'synthetic-actor',
            updated_at: at,
            updated_by: 'synthetic-actor',
            finalized_at: version === 2 ? null : at,
            finalized_by: version === 2 ? null : 'synthetic-actor',
            what_went_well: version === 2 ? 'Gespeicherter Journalentwurf.' : 'Frühere Reflexion.',
            would_do_differently: '',
            additional_notes: '',
          },
          is_latest: version === 2,
          source_currentness: 'CURRENT',
          source_checked_at: at,
          learning_evidence_id: null,
        })),
      };
      return json(history);
    }
    if (path.endsWith('/materialization-status')) {
      statusReads.push({ ready, version: currentVersion });
      return json({
        ready,
        reason,
        materialized: ready && materialized,
        learning_evidence_id: ready && materialized ? evidenceId : null,
        exit_review_version_id: ready ? currentVersion : null,
      });
    }
    if (path.endsWith('/ft011-evidence/materialize')) {
      if (mode === 'changed' && currentVersion === version1) {
        currentVersion = version2;
        return json(
          {
            code: 'SOURCE_VERSION_MISMATCH',
            message: 'Changed source',
            details: [],
            timestamp: at,
          },
          409,
        );
      }
      if (mode === 'stale-replay') {
        ready = false;
        reason = 'EXIT_REVIEW_STALE';
        return json({
          learning_evidence_id: evidenceId,
          exit_review_version_id: version1,
          created: false,
          replayed: true,
        });
      }
      materialized = true;
      return json({
        learning_evidence_id: evidenceId,
        exit_review_version_id: currentVersion,
        created: true,
        replayed: false,
      });
    }
    if (path.endsWith('/observation'))
      return json({
        id: 'observation-1',
        trade_id: tradeId,
        status: 'COMPLETED',
        underlying_listing_id: 'listing-1',
        target_observation_count: 20,
        available_observation_count: 20,
        missing_observation_count: 0,
        is_complete: true,
        started_at: at,
        completed_at: at,
        created_at: at,
      });
    if (path.endsWith('/observation/evidence'))
      return json({
        observation_id: 'observation-1',
        trade_id: tradeId,
        product_context: null,
        planning_context: {
          trade_plan_id: null,
          trade_plan_version_id: null,
          original_stop: null,
          original_targets: [],
        },
        management_levels: [],
        actual_exit: {
          full_exit_at: at,
          realized_gross_pnl: null,
          executions: [],
        },
        counterfactual: null,
      });
    if (path.endsWith('/handoff'))
      return json({
        ready,
        reason,
        post_trade_observation_id: 'observation-1',
        exit_review_id: 'review-1',
        exit_review_version_id: currentVersion,
      });
    if (path.endsWith('/exit-review/history')) return json([]);
    if (path.endsWith('/exit-review/draft')) {
      rationale = body.rationale;
      return json(review());
    }
    if (path.endsWith('/exit-review/finalize')) {
      finalized = ready = true;
      reason = 'READY';
      return json(review());
    }
    if (path.endsWith('/exit-review')) return json(review());
    if (path === '/learning/lessons' && req.method() === 'POST') {
      interpreted = true;
      lessonContent = body.content;
      return json(
        {
          lesson_id: lessonId,
          current_version_id: lessonVersionId,
          current_state: 'CURRENT',
        },
        201,
      );
    }
    if (path === `/learning/lessons/${lessonId}/review-context`)
      return json({
        lesson: {
          id: lessonId,
          title: 'Bewusste Interpretation',
          current_version_id: lessonVersionId,
          current_state: 'CURRENT',
        },
        history: [
          {
            version: {
              id: lessonVersionId,
              lesson_id: lessonId,
              version: 1,
              main_category: 'Prozess',
              content: lessonContent,
              created_at: at,
              created_by: 'synthetic-actor',
              supersedes_version_id: null,
            },
            evidence_links: [
              {
                id: '77777777-7777-4777-8777-777777777777',
                lesson_version_id: lessonVersionId,
                learning_evidence_id: evidenceId,
                relation: 'SUPPORTS',
              },
            ],
          },
        ],
        signals: [],
        transitions: [],
        read_at: at,
      });
    if (
      path === '/learning/learning-evidence' ||
      path === `/model-governance/lesson-versions/${lessonVersionId}/hypotheses`
    )
      return json([]);
    if (path.includes(`/learning/learning-evidence/${evidenceId}/lessons`)) {
      if (interpreted && failLessonReadback)
        return json(
          {
            code: 'READBACK_UNAVAILABLE',
            message: 'Synthetic readback failure',
            details: [],
            timestamp: at,
          },
          503,
        );
      return json(
        interpreted
          ? [
              {
                lesson_id: lessonId,
                current_version_id: lessonVersionId,
                current_state: 'CURRENT',
                title: 'Bewusste Interpretation',
              },
            ]
          : [],
      );
    }
    return json(
      {
        code: 'NOT_FOUND',
        message: 'No optional synthetic context',
        details: [],
        timestamp: at,
      },
      404,
    );
  });
  await page.goto(`/post-trade?trade_id=${tradeId}`);
  return { writes, statusReads };
}

test('review finalization, explicit pinned handoff and explicit interpretation stay separate', async ({
  page,
}) => {
  const { writes } = await setup(page, 'draft');
  await expect(page.getByLabel('Review-Begründung')).toBeEnabled();
  await page.getByLabel('Review-Begründung').fill('Eine bewusst begründete Ausstiegsentscheidung.');
  await page.getByRole('button', { name: 'Review finalisieren', exact: true }).click();
  const handoff = page.getByRole('button', {
    name: 'An Lessons Learned übergeben',
    exact: true,
  });
  await expect(handoff).toBeEnabled();
  expect(writes.map((w) => w.path)).toEqual([
    `/post-trade/trades/${tradeId}/exit-review/draft`,
    `/post-trade/trades/${tradeId}/exit-review/finalize`,
  ]);
  await expect(
    page.getByRole('button', {
      name: 'Als LearningEvidence materialisieren',
      exact: true,
    }),
  ).toHaveCount(0);
  await handoff.click();
  await expect(page.getByLabel('Lesson-Titel')).toBeVisible();
  const materialization = writes.filter((w) => w.path.endsWith('/materialize'));
  expect(materialization).toEqual([
    {
      path: `/learning/trades/${tradeId}/ft011-evidence/materialize`,
      method: 'POST',
      body: { expected_exit_review_version_id: version1 },
      key: `ft011-to-ft012:v2:${tradeId}:${version1}`,
    },
  ]);
  await expect(page.getByRole('button', { name: 'Lesson anlegen', exact: true })).toBeDisabled();
  expect(writes).toHaveLength(3);
  await page.getByLabel('Lesson-Titel').fill('Bewusste Interpretation');
  await page.getByLabel('Lesson-Kategorie').fill('Prozess');
  await page
    .getByLabel('Lesson-Inhalt')
    .fill(
      'Diese konkrete Evidenz ist Kontext, kein Beweis für einen handelbaren Optionsscheinkurs.',
    );
  await page.getByRole('button', { name: 'Lesson anlegen', exact: true }).click();
  await expect(page.getByRole('link', { name: /Bewusste Interpretation/ })).toHaveAttribute(
    'href',
    referencedLessonHref,
  );
  expect(writes).toHaveLength(4);
  expect(writes[3].body).toMatchObject({
    evidence_links: [{ learning_evidence_id: evidenceId, relation: 'SUPPORTS' }],
  });
  const open = page.getByRole('link', { name: 'Lesson öffnen', exact: true });
  await expect(open).toHaveCount(1);
  await expect(open).toHaveAttribute('href', createdLessonHref);
  await expect(page.getByText('Lesson angelegt: LS-55555555', { exact: true })).toBeVisible();
  await open.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(new URL(createdLessonHref, page.url()).href);
  await expect(
    page.getByText(
      'Diese konkrete Evidenz ist Kontext, kein Beweis für einen handelbaren Optionsscheinkurs.',
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.getByText(`SUPPORTS · Evidence ${evidenceId}`, { exact: true })).toBeVisible();
  expect(writes).toHaveLength(4);
});

test('a confirmed Lesson remains directly accessible when its reference readback fails', async ({
  page,
}) => {
  const { writes } = await setup(page, 'ready', true);
  await page.getByRole('button', { name: 'An Lessons Learned übergeben', exact: true }).click();
  await page.getByLabel('Lesson-Titel').fill('Bewusste Interpretation');
  await page.getByLabel('Lesson-Kategorie').fill('Prozess');
  await page
    .getByLabel('Lesson-Inhalt')
    .fill('Eine bereits bestätigte Interpretation bleibt erreichbar.');
  await page.getByRole('button', { name: 'Lesson anlegen', exact: true }).click();
  await expect(
    page.getByText('Lesson-Verweise konnten nicht geladen werden.', {
      exact: true,
    }),
  ).toBeVisible();
  const open = page.getByRole('link', { name: 'Lesson öffnen', exact: true });
  await expect(open).toHaveCount(1);
  await expect(open).toHaveAttribute('href', createdLessonHref);
  await expect(page.getByRole('button', { name: 'Lesson anlegen', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Lesson-Verweise erneut laden', exact: true }).click();
  await expect(
    page.getByText('Lesson-Verweise konnten nicht geladen werden.', {
      exact: true,
    }),
  ).toBeVisible();
  await open.click();
  await expect(page).toHaveURL(new URL(createdLessonHref, page.url()).href);
  await expect(
    page.getByText('Eine bereits bestätigte Interpretation bleibt erreichbar.', { exact: true }),
  ).toBeVisible();
  expect(writes.filter((write) => write.path === '/learning/lessons')).toHaveLength(1);
  expect(writes).toHaveLength(2);
});

test('discarding journal edits for a same-trade version change preserves the confirmed Lesson', async ({
  page,
}) => {
  const { writes } = await setup(page, 'journal-navigation');
  const journal = page.getByRole('region', { name: 'Trade-Journal', exact: true });
  const directLesson = page.locator('section').filter({
    has: page.getByRole('heading', { name: 'FT-012 Learning', exact: true }),
  });
  await page.getByRole('button', { name: 'An Lessons Learned übergeben', exact: true }).click();
  await directLesson.getByLabel('Lesson-Titel').fill('Bewusste Interpretation');
  await directLesson.getByLabel('Lesson-Kategorie').fill('Prozess');
  await directLesson
    .getByLabel('Lesson-Inhalt')
    .fill('Die bestätigte Interpretation bleibt trotz verworfener Journaländerung erhalten.');
  await directLesson.getByRole('button', { name: 'Lesson anlegen', exact: true }).click();
  await expect(directLesson.getByText('Bereits interpretiert', { exact: true })).toBeVisible();
  const open = directLesson.getByRole('link', { name: 'Lesson öffnen', exact: true });
  await expect(open).toHaveAttribute('href', createdLessonHref);

  await journal.getByRole('button', { name: 'Journal bearbeiten', exact: true }).click();
  await journal.getByLabel('Was lief gut?').fill('Diese ungespeicherte Journaländerung verwerfen.');
  const selection = journal.getByLabel('Journalversion ansehen');
  await expect(selection).toHaveValue(journalDraftId);
  await selection.selectOption(journalFinalId);
  const guard = page.getByRole('alertdialog');
  await expect(guard.getByRole('button', { name: 'Hier bleiben', exact: true })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(journal.getByLabel('Was lief gut?')).toHaveValue(
    'Diese ungespeicherte Journaländerung verwerfen.',
  );
  await expect(open).toBeVisible();

  await selection.selectOption(journalFinalId);
  await guard.getByRole('button', { name: 'Eingaben verwerfen und wechseln', exact: true }).click();
  await expect(selection).toHaveValue(journalFinalId);
  expect(new URL(page.url()).searchParams.get('trade_id')).toBe(tradeId);
  expect(new URL(page.url()).searchParams.get('journal_version_id')).toBe(journalFinalId);
  await expect(journal.getByText('Frühere Reflexion.', { exact: true })).toBeVisible();
  await expect(journal.getByLabel('Was lief gut?')).toHaveCount(0);
  await expect(
    directLesson.getByText('Lesson angelegt: LS-55555555', { exact: true }),
  ).toBeVisible();
  await expect(open).toHaveCount(1);
  await expect(open).toHaveAttribute('href', journalLessonHref);
  await expect(directLesson.getByLabel('Lesson-Titel')).toHaveCount(0);
  await expect(
    directLesson.getByRole('button', { name: 'Lesson anlegen', exact: true }),
  ).toHaveCount(0);

  await open.click();
  await expect(page).toHaveURL(new URL(journalLessonHref, page.url()).href);
  await expect(
    page.getByText(
      'Die bestätigte Interpretation bleibt trotz verworfener Journaländerung erhalten.',
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.getByText(`SUPPORTS · Evidence ${evidenceId}`, { exact: true })).toBeVisible();
  expect(writes.map((write) => write.path)).toEqual([
    `/learning/trades/${tradeId}/ft011-evidence/materialize`,
    '/learning/lessons',
  ]);
  expect(writes[1].body).toMatchObject({
    evidence_links: [{ learning_evidence_id: evidenceId, relation: 'SUPPORTS' }],
  });
});

test('changed review requires a fresh explicit confirmation without an automatic retry', async ({
  page,
}) => {
  const { writes, statusReads } = await setup(page, 'changed');
  const handoff = page.getByRole('button', {
    name: 'An Lessons Learned übergeben',
    exact: true,
  });
  await handoff.click();
  await expect(page.getByText(/Die Review-Version hat sich geändert/)).toBeVisible();
  await expect.poll(() => statusReads.some((r) => r.version === version2)).toBe(true);
  await expect(page.getByText(`ExitReviewVersion: ${version2}`, { exact: true })).toBeVisible();
  expect(writes).toHaveLength(1);
  expect(writes[0].body).toEqual({ expected_exit_review_version_id: version1 });
  await handoff.click();
  await expect(page.getByLabel('Lesson-Titel')).toBeVisible();
  expect(writes).toHaveLength(2);
  expect(writes[1].body).toEqual({ expected_exit_review_version_id: version2 });
  expect(writes[1].key).toBe(`ft011-to-ft012:v2:${tradeId}:${version2}`);
});

test('historical replay cannot manufacture current learning eligibility', async ({ page }) => {
  const { writes, statusReads } = await setup(page, 'stale-replay');
  await page.getByRole('button', { name: 'An Lessons Learned übergeben', exact: true }).click();
  await expect.poll(() => statusReads.some((r) => !r.ready)).toBe(true);
  await expect(page.getByText(/Noch nicht bereit: EXIT_REVIEW_STALE/)).toBeVisible();
  await expect(page.getByLabel('Lesson-Titel')).toHaveCount(0);
  await expect(
    page.getByRole('button', {
      name: 'An Lessons Learned übergeben',
      exact: true,
    }),
  ).toHaveCount(0);
  expect(writes).toHaveLength(1);
  expect(writes[0].body).toEqual({ expected_exit_review_version_id: version1 });
});
