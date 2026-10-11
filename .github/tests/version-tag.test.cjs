const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const { join } = require('node:path');

// Execute the exact embedded workflow script against a fake GitHub API.
const workflow = readFileSync(join(__dirname, '../workflows/version-tag.yml'), 'utf8');
const script = workflow.split('          script: |\n')[1]
  .split('\n').map(line => line.slice(12)).join('\n');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const publish = new AsyncFunction('github', 'context', 'core', script);

function scenario({ main = 'release-sha', version = '1.4.0', existing = false, runs } = {}) {
  const writes = [];
  const complete = ['backend.yml', 'frontend.yml', 'e2e.yml'].map((name, id) => ({
    id, path: `.github/workflows/${name}`, status: 'completed', conclusion: 'success',
  }));
  const github = {
    paginate: async (_fn, params) => {
      assert.equal(params.head_sha, 'release-sha');
      assert.equal(params.event, 'push');
      assert.equal(params.branch, 'main');
      return runs ?? complete;
    },
    rest: {
      actions: { listWorkflowRunsForRepo() {} },
      repos: { getContent: async params => {
        assert.equal(params.ref, 'release-sha');
        return { data: { content: Buffer.from(version).toString('base64') } };
      } },
      git: {
        getRef: async ({ ref }) => {
          if (ref === 'heads/main') return { data: { object: { sha: main } } };
          if (existing) return { data: { object: { sha: 'previous-release' } } };
          throw Object.assign(new Error('missing'), { status: 404 });
        },
        createRef: async value => writes.push(value),
      },
    },
  };
  return {
    writes, complete,
    run: () => publish(github, {
      repo: { owner: 'test-owner', repo: 'test-repo' },
      payload: { workflow_run: { head_sha: 'release-sha' } },
    }, { info() {} }),
  };
}

test('only publishes the version at the tested main commit', async () => {
  const s = scenario(); await s.run();
  assert.deepEqual(s.writes, [{
    owner: 'test-owner', repo: 'test-repo', ref: 'refs/tags/v1.4.0', sha: 'release-sha',
  }]);
});

test('does not publish an older main or move a published version', async () => {
  for (const input of [{ main: 'newer-sha' }, { existing: true }]) {
    const s = scenario(input); await s.run(); assert.deepEqual(s.writes, []);
  }
});

test('requires all three successful workflows and ignores older successful attempts', async () => {
  const complete = scenario().complete;
  for (const runs of [[], complete.slice(1), [
    ...complete, { ...complete[0], id: 99, conclusion: 'failure' },
  ], [
    ...complete, { ...complete[0], id: 99, status: 'in_progress', conclusion: null },
  ]]) {
    const s = scenario({ runs }); await s.run(); assert.deepEqual(s.writes, []);
  }
});

test('refuses malformed versions', async () => {
  for (const version of ['1.4', '01.4.0', '../main', '1.4.0-beta']) {
    const s = scenario({ version });
    await assert.rejects(s.run(), /VERSION must contain/);
    assert.deepEqual(s.writes, []);
  }
});

test('write job is limited to successful main push events from this repository', () => {
  for (const guard of [
    "github.event.workflow_run.event == 'push'",
    "github.event.workflow_run.head_branch == 'main'",
    "github.event.workflow_run.conclusion == 'success'",
    'github.event.workflow_run.head_repository.full_name == github.repository',
  ]) assert.ok(workflow.includes(guard));
  assert.ok(workflow.includes('needs: validate'));
});

// A version-only release must schedule the same main-push workflows that the
// publisher requires. PR or manual runs cannot satisfy that publication gate.
for (const filename of ['backend.yml', 'frontend.yml', 'e2e.yml']) {
  test(`${filename} runs for VERSION changes on main`, () => {
    const source = readFileSync(join(__dirname, '../workflows', filename), 'utf8');
    const triggers = source.match(/^on:\n((?:[ \t].*\n|\n)*)/m)?.[1];
    assert.ok(triggers, `${filename}: on block missing`);
    const push = triggers.match(/^  push:\n((?: {4,}.*\n|\n)*)/m)?.[1];
    assert.ok(push, `${filename}: push trigger missing`);
    assert.match(push, /^    branches: \[main\]$/m);
    const paths = push.match(/^    paths:\n((?: {6}- .*\n)*)/m)?.[1];
    assert.ok(paths, `${filename}: push paths missing`);
    assert.match(paths, /^      - ['"]VERSION['"]$/m);
    assert.doesNotMatch(paths, /^      - ['"]!/m,
      `${filename}: review exclusions before changing release triggers`);
  });
}

test('all application package versions match VERSION', () => {
  const root = join(__dirname, '../..');
  const version = readFileSync(join(root, 'VERSION'), 'utf8').trim();
  const manifest = JSON.parse(readFileSync(join(root, 'frontend/package.json'), 'utf8'));
  const lock = JSON.parse(readFileSync(join(root, 'frontend/package-lock.json'), 'utf8'));
  const backend = readFileSync(join(root, 'backend/pyproject.toml'), 'utf8');
  const project = backend.split('[project]\n')[1]?.split('\n[')[0];
  assert.match(version, /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/);
  assert.equal(manifest.version, version);
  assert.equal(lock.version, version);
  assert.equal(lock.packages[''].version, version);
  assert.equal(project?.match(/^version = "([^"]+)"$/m)?.[1], version);
});
