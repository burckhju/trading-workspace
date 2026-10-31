/** Local documentation checks; no application, network, database or provider access. */
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
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

test('all six deliverable documents are valid UTF-8 with complete code fences', () => {
  assert.equal(markdownFiles.length, 6);
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
  console.log(`Verified ${count} local file links (URL reachability and line anchors not tested).`);
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
