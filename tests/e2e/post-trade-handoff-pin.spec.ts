import { expect, test, type Page } from '@playwright/test';

// Browser/HTTP boundary tests with intercepted synthetic API data, not database E2E.
const tradeId = '11111111-1111-4111-8111-111111111111';
const version1 = '22222222-2222-4222-8222-222222222222';
const version2 = '33333333-3333-4333-8333-333333333333';
const evidenceId = '44444444-4444-4444-8444-444444444444';
const lessonId = '55555555-5555-4555-8555-555555555555';
const at = '2026-08-18T12:00:00Z';

async function setup(page: Page, mode: 'draft' | 'changed' | 'stale-replay') {
  let finalized = mode !== 'draft';
  let currentVersion = version1;
  let ready = finalized;
  let materialized = false;
  let interpreted = false;
  let reason = finalized ? 'READY' : 'EXIT_REVIEW_NOT_FINALIZED';
  let rationale = '';
  const writes: { path: string; method: string; body: unknown; key?: string }[] = [];
  const statusReads: { ready: boolean; version: string }[] = [];
  const review = () => ({
    exit_review_id: 'review-1', current_version_id: currentVersion,
    version: currentVersion === version1 ? 1 : 2,
    status: finalized ? 'FINALIZED' : 'DRAFT',
    currentness: reason === 'EXIT_REVIEW_STALE' ? 'STALE' : 'CURRENT',
    timing: 'GOOD', process_adherence: 'GOOD', risk_decision: 'GOOD',
    overall_exit_decision: 'NOT_ASSESSABLE', rationale,
    created_at: at, created_by: 'actor-1',
    finalized_at: finalized ? at : null, finalized_by: finalized ? 'actor-1' : null,
    supersedes_version_id: currentVersion === version1 ? null : version1,
    stale_at: reason === 'EXIT_REVIEW_STALE' ? at : null,
    stale_reason: reason === 'EXIT_REVIEW_STALE' ? 'INPUT_CHANGED' : null,
  });
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname.split('/api/v1')[1];
    const body = req.postData() ? req.postDataJSON() : null;
    if (req.method() !== 'GET') {
      writes.push({ path, method: req.method(), body, key: req.headers()['idempotency-key'] });
    }
    const json = (value: unknown, status = 200) => route.fulfill({ status, json: value });
    if (path.endsWith('/materialization-status')) {
      statusReads.push({ ready, version: currentVersion });
      return json({ ready, reason, materialized: ready && materialized,
        learning_evidence_id: ready && materialized ? evidenceId : null,
        exit_review_version_id: ready ? currentVersion : null });
    }
    if (path.endsWith('/ft011-evidence/materialize')) {
      if (mode === 'changed' && currentVersion === version1) {
        currentVersion = version2;
        return json({ code: 'SOURCE_VERSION_MISMATCH', message: 'Changed source', details: [], timestamp: at }, 409);
      }
      if (mode === 'stale-replay') {
        ready = false;
        reason = 'EXIT_REVIEW_STALE';
        return json({ learning_evidence_id: evidenceId, exit_review_version_id: version1, created: false, replayed: true });
      }
      materialized = true;
      return json({ learning_evidence_id: evidenceId, exit_review_version_id: currentVersion, created: true, replayed: false });
    }
    if (path.endsWith('/observation')) return json({ id: 'observation-1', trade_id: tradeId,
      status: 'COMPLETED', underlying_listing_id: 'listing-1', target_observation_count: 20,
      available_observation_count: 20, missing_observation_count: 0, is_complete: true,
      started_at: at, completed_at: at, created_at: at });
    if (path.endsWith('/observation/evidence')) return json({
      observation_id: 'observation-1', trade_id: tradeId, product_context: null,
      planning_context: { trade_plan_id: null, trade_plan_version_id: null, original_stop: null, original_targets: [] },
      management_levels: [], actual_exit: { full_exit_at: at, realized_gross_pnl: null, executions: [] },
      counterfactual: null,
    });
    if (path.endsWith('/handoff')) return json({ ready, reason,
      post_trade_observation_id: 'observation-1', exit_review_id: 'review-1', exit_review_version_id: currentVersion });
    if (path.endsWith('/exit-review/history')) return json([]);
    if (path.endsWith('/exit-review/draft')) { rationale = body.rationale; return json(review()); }
    if (path.endsWith('/exit-review/finalize')) {
      finalized = ready = true; reason = 'READY'; return json(review());
    }
    if (path.endsWith('/exit-review')) return json(review());
    if (path === '/learning/lessons' && req.method() === 'POST') {
      interpreted = true;
      return json({ lesson_id: lessonId, current_version_id: 'lesson-version-1', current_state: 'CURRENT' }, 201);
    }
    if (path.includes(`/learning/learning-evidence/${evidenceId}/lessons`)) return json(interpreted ? [{
      lesson_id: lessonId, current_version_id: 'lesson-version-1', current_state: 'CURRENT', title: 'Bewusste Interpretation',
    }] : []);
    return json({ code: 'NOT_FOUND', message: 'No optional synthetic context', details: [], timestamp: at }, 404);
  });
  await page.goto(`/post-trade?trade_id=${tradeId}`);
  return { writes, statusReads };
}

test('review finalization, explicit pinned handoff and explicit interpretation stay separate', async ({ page }) => {
  const { writes } = await setup(page, 'draft');
  await expect(page.getByLabel('Review-Begründung')).toBeEnabled();
  await page.getByLabel('Review-Begründung').fill('Eine bewusst begründete Ausstiegsentscheidung.');
  await page.getByRole('button', { name: 'Review finalisieren', exact: true }).click();
  const handoff = page.getByRole('button', { name: 'An Lessons Learned übergeben', exact: true });
  await expect(handoff).toBeEnabled();
  expect(writes.map(w => w.path)).toEqual([
    `/post-trade/trades/${tradeId}/exit-review/draft`,
    `/post-trade/trades/${tradeId}/exit-review/finalize`,
  ]);
  await expect(page.getByRole('button', { name: 'Als LearningEvidence materialisieren', exact: true })).toHaveCount(0);
  await handoff.click();
  await expect(page.getByLabel('Lesson-Titel')).toBeVisible();
  const materialization = writes.filter(w => w.path.endsWith('/materialize'));
  expect(materialization).toEqual([{ path: `/learning/trades/${tradeId}/ft011-evidence/materialize`, method: 'POST',
    body: { expected_exit_review_version_id: version1 }, key: `ft011-to-ft012:v2:${tradeId}:${version1}` }]);
  await expect(page.getByRole('button', { name: 'Lesson anlegen', exact: true })).toBeDisabled();
  expect(writes).toHaveLength(3);
  await page.getByLabel('Lesson-Titel').fill('Bewusste Interpretation');
  await page.getByLabel('Lesson-Kategorie').fill('Prozess');
  await page.getByLabel('Lesson-Inhalt').fill('Diese konkrete Evidenz ist Kontext, kein Beweis für einen handelbaren Optionsscheinkurs.');
  await page.getByRole('button', { name: 'Lesson anlegen', exact: true }).click();
  await expect(page.getByRole('link', { name: /Bewusste Interpretation/ })).toHaveAttribute('href', `/lessons/${lessonId}`);
  expect(writes).toHaveLength(4);
  expect(writes[3].body).toMatchObject({ evidence_links: [{ learning_evidence_id: evidenceId, relation: 'SUPPORTS' }] });
});

test('changed review requires a fresh explicit confirmation without an automatic retry', async ({ page }) => {
  const { writes, statusReads } = await setup(page, 'changed');
  const handoff = page.getByRole('button', { name: 'An Lessons Learned übergeben', exact: true });
  await handoff.click();
  await expect(page.getByText(/Die Review-Version hat sich geändert/)).toBeVisible();
  await expect.poll(() => statusReads.some(r => r.version === version2)).toBe(true);
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
  await expect.poll(() => statusReads.some(r => !r.ready)).toBe(true);
  await expect(page.getByText(/Noch nicht bereit: EXIT_REVIEW_STALE/)).toBeVisible();
  await expect(page.getByLabel('Lesson-Titel')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'An Lessons Learned übergeben', exact: true })).toHaveCount(0);
  expect(writes).toHaveLength(1);
  expect(writes[0].body).toEqual({ expected_exit_review_version_id: version1 });
});
