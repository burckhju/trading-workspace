/** Local documentation checks; no application, network, database or provider access. */
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, isAbsolute, relative, resolve } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const repository = resolve(directory, '../../..');
const markdownFiles = readdirSync(directory)
  .filter((name) => name.endsWith('.md'))
  .map((name) => resolve(directory, name));
const texts = new Map(
  markdownFiles.map((file) => [
    file,
    new TextDecoder('utf-8', { fatal: true }).decode(readFileSync(file)),
  ]),
);

function localLinks(file, text) {
  return [...text.matchAll(/\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g)]
    .map((match) => match[1])
    .filter((href) => !/^[a-z][a-z\d+.-]*:/i.test(href) && !href.startsWith('#'))
    .map((href) => resolve(dirname(file), decodeURIComponent(href.split('#')[0])));
}

test('all seven canonical documents are valid UTF-8 with complete code fences', () => {
  assert.equal(markdownFiles.length, 7);
  for (const [file, text] of texts) {
    assert.ok(text.endsWith('\n'), `${file}: missing final newline`);
    assert.ok(!text.startsWith('\uFEFF'), `${file}: unexpected byte order mark`);
    assert.ok(!/[\t ]+$/m.test(text), `${file}: trailing whitespace`);
    assert.equal([...text.matchAll(/^```/gm)].length % 2, 0, `${file}: unclosed fence`);
  }
});

test('all local documentation and source links resolve inside the repository', () => {
  let count = 0;
  for (const [file, text] of texts) {
    for (const target of localLinks(file, text)) {
      const path = relative(repository, target);
      assert.ok(!path.startsWith('..') && !isAbsolute(path), `${file}: escaped repository`);
      assert.ok(statSync(target).isFile(), `${file}: not a file: ${path}`);
      count += 1;
    }
  }
  assert.ok(count > 0, 'No source links were checked');
  console.log(`Verified ${count} local file links (external URL reachability not tested).`);
});

function markdownAnchors(text) {
  const anchors = new Set(
    [...text.matchAll(/<a\s+(?:id|name)=["']([^"']+)["']/g)].map((match) => match[1]),
  );
  const duplicates = new Map();
  let fenced = false;
  for (const line of text.split('\n')) {
    if (/^```/.test(line)) fenced = !fenced;
    if (fenced) continue;
    const heading = line.match(/^#{1,6}\s+(.+?)(?:\s+#+)?$/);
    if (!heading) continue;
    const slug = heading[1]
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/[`*_~]/g, '')
      .toLowerCase()
      .replace(/[^\p{L}\p{N}_\- ]/gu, '')
      .replace(/ /g, '-');
    const index = duplicates.get(slug) ?? 0;
    duplicates.set(slug, index + 1);
    anchors.add(index ? `${slug}-${index}` : slug);
  }
  return anchors;
}

test('canonical links preserve existing local Markdown heading and explicit anchors', () => {
  let count = 0;
  for (const [file, text] of texts) {
    for (const match of text.matchAll(/\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g)) {
      const href = match[1];
      if (/^[a-z][a-z\d+.-]*:/i.test(href) || !href.includes('#')) continue;
      const [path, fragment] = href.split('#');
      const target = path ? resolve(dirname(file), decodeURIComponent(path)) : file;
      if (!target.endsWith('.md')) continue;
      assert.ok(
        markdownAnchors(readFileSync(target, 'utf8')).has(decodeURIComponent(fragment)),
        `${relative(repository, file)}: missing anchor ${href}`,
      );
      count += 1;
    }
  }
  console.log(`Verified ${count} local Markdown anchors.`);
});

test('all Markdown tables keep a consistent column count', () => {
  let count = 0;
  for (const [file, text] of texts) {
    let columns = null;
    for (const [index, line] of text.split('\n').entries()) {
      if (!line.startsWith('|')) {
        columns = null;
        continue;
      }
      const current = [...line.matchAll(/(?<!\\)\|/g)].length - 1;
      if (columns === null) {
        columns = current;
        count += 1;
      }
      assert.equal(current, columns, `${relative(repository, file)}:${index + 1}`);
    }
  }
  console.log(`Verified ${count} Markdown tables.`);
});

test('every inventory row has a unique ID, seven columns and actual code evidence', () => {
  const file = resolve(directory, 'inventory.md');
  const rows = texts
    .get(file)
    .split('\n')
    .filter((line) => /^\| [ABCDE]\d{2} /.test(line));
  const expected = { A: 17, B: 14, C: 9, D: 24, E: 16 };
  const ids = new Set();
  for (const row of rows) {
    const cells = row.split(/(?<!\\)\|/).slice(1, -1);
    assert.equal(cells.length, 7, `Malformed table row: ${row.slice(0, 80)}`);
    const id = cells[0].trim().slice(0, 3);
    assert.ok(!ids.has(id), `Duplicate inventory ID ${id}`);
    ids.add(id);
    assert.ok(
      localLinks(file, cells[6]).some((target) => {
        const path = relative(repository, target);
        return path.startsWith('frontend/src/') || path.startsWith('backend/app/');
      }),
      `${id}: missing application source evidence`,
    );
  }
  for (const [area, count] of Object.entries(expected)) {
    for (let index = 1; index <= count; index += 1) {
      assert.ok(ids.has(`${area}${String(index).padStart(2, '0')}`), `Missing ${area}${index}`);
    }
  }
  assert.equal(
    ids.size,
    Object.values(expected).reduce((sum, count) => sum + count, 0),
  );
});

test('the 79 supplementary findings remain traceable in eight separate domains', () => {
  const detail = texts.get(resolve(directory, 'detail-inventory.md'));
  const rows = [...detail.matchAll(/^\|\s*(T|C|P|TP|Q|M|JL|MG)(\d{2})(?:\s|\|)/gm)];
  const expected = { T: 8, C: 8, P: 8, TP: 7, Q: 12, M: 11, JL: 14, MG: 11 };
  const ids = rows.map((match) => `${match[1]}${match[2]}`);
  assert.equal(new Set(ids).size, ids.length, 'Duplicate detail-inventory ID');
  for (const [area, count] of Object.entries(expected)) {
    for (let index = 1; index <= count; index += 1) {
      assert.ok(ids.includes(`${area}${String(index).padStart(2, '0')}`));
    }
  }
  assert.equal(ids.length, 79);
});

test('all 24 incoming acceptance cases map to the preserved and extended canonical catalog', () => {
  const text = texts.get(resolve(directory, 'test-and-acceptance.md'));
  const incoming = [...text.matchAll(/^\|\s*A(\d{2})\s*\|/gm)].map((match) => match[1]);
  assert.equal(incoming.length, 24);
  assert.equal(new Set(incoming).size, 24);
  for (let index = 1; index <= 24; index += 1) {
    assert.ok(incoming.includes(String(index).padStart(2, '0')), `Missing A${index}`);
  }
  const canonical = [...text.matchAll(/^\|\s*TC-(\d{2})(?=\s|\|)/gm)].map((match) => match[1]);
  assert.equal(canonical.length, 64);
  assert.equal(new Set(canonical).size, 64);
  for (let index = 1; index <= 64; index += 1) {
    assert.ok(canonical.includes(String(index).padStart(2, '0')), `Missing TC-${index}`);
  }
});

test('there is one normative contract and no parallel UX3-B/C/D plan file', () => {
  for (const path of ['docs/ui/ux3-notice-contract.md', 'docs/planning/UX3_FOLLOW_UP_ORDERS.md']) {
    assert.ok(!existsSync(resolve(repository, path)), `Competing normative file: ${path}`);
  }
  for (const path of ['README.md', 'notice-contract.md', 'contracts.ts']) {
    assert.ok(statSync(resolve(directory, path)).isFile());
  }
});

test('proposal references existing domain DTOs with type-only imports', () => {
  const file = resolve(directory, 'contracts.ts');
  const text = readFileSync(file, 'utf8');
  const imports = [...text.matchAll(/import\s+(type\s+)?[\s\S]*?from\s+['"]([^'"]+)['"]/g)];
  assert.ok(imports.length > 0);
  for (const match of imports) {
    assert.equal(match[1], 'type ', `Runtime import in documentation: ${match[2]}`);
    assert.ok(statSync(resolve(directory, `${match[2]}.ts`)).isFile(), match[2]);
  }
});

test('documentation contracts remain outside the application import graph', () => {
  function visit(path) {
    for (const entry of readdirSync(path, { withFileTypes: true })) {
      const file = resolve(path, entry.name);
      if (entry.isDirectory()) visit(file);
      else if (/\.(ts|tsx)$/.test(entry.name)) {
        assert.ok(
          !/from\s+['"][^'"]*docs\/ui\/ux-3\//.test(readFileSync(file, 'utf8')),
          `${relative(repository, file)} imports documentation as production code`,
        );
      }
    }
  }
  visit(resolve(repository, 'frontend/src'));
});
