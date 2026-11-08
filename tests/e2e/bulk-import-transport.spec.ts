import { randomUUID } from 'node:crypto';
import { expect, test, type APIResponse } from '@playwright/test';

const bulkImportPath = '/api/api/v1/learning/bulk-imports';
const fileCount = 103;
const fileSize = 16 * 1024;
const missingJobMessage = 'import job does not exist in workspace';

// These requests traverse the real frontend proxy. They deliberately fail before
// any import job/file is created; they do not qualify successful PDF parsing.
// No browser route interception, external provider or import confirmation is used.
test.beforeEach(({ baseURL }) => {
  if (!baseURL) throw new Error('The disposable local proxy base URL is required.');
  const target = new URL(baseURL);
  expect(['localhost', '127.0.0.1', '[::1]']).toContain(target.hostname);
  expect(target.protocol).toBe('http:');
  expect(target.username).toBe('');
  expect(target.password).toBe('');
});

function syntheticFiles(field: 'proxy_probe' | 'files'): FormData {
  const body = new FormData();
  for (let index = 0; index < fileCount; index += 1) {
    body.append(
      field,
      new File([new Uint8Array(fileSize)], `transport-probe-${index}.pdf`, {
        type: 'application/pdf',
      }),
    );
  }
  // The file bytes alone exceed the old limit, before multipart overhead.
  expect(fileCount * fileSize).toBeGreaterThan(1024 * 1024);
  return body;
}

async function jsonResponse(response: APIResponse, status: number): Promise<unknown> {
  expect(response.status(), await response.text()).toBe(status);
  expect(response.headers()['content-type']).toMatch(/^application\/json\b/);
  return response.json();
}

test('passes 103 multipart files above 1 MiB to initial-upload validation without creating a job', async ({
  request,
}) => {
  // A wrong file field reaches FastAPI's required-field validation, without
  // invoking create_job. These remain file parts, not one oversized text field.
  const response = await request.post(`${bulkImportPath}/hebeltrader`, {
    multipart: syntheticFiles('proxy_probe'),
    maxRedirects: 0,
  });

  expect(await jsonResponse(response, 422)).toMatchObject({
    code: 'REQUEST_VALIDATION_ERROR',
    details: expect.arrayContaining([expect.objectContaining({ field: 'body.files' })]),
  });
});

test('passes 103 multipart files above 1 MiB to append validation for a nonexistent job', async ({
  request,
}) => {
  const jobPath = `${bulkImportPath}/${randomUUID()}`;
  const missingJob = { code: 'HTTP_404', message: missingJobMessage };
  expect(await jsonResponse(await request.get(jobPath, { maxRedirects: 0 }), 404)).toMatchObject(
    missingJob,
  );

  // ingest_pdf checks this absent job before creating or updating any file.
  const response = await request.post(`${jobPath}/files`, {
    multipart: syntheticFiles('files'),
    maxRedirects: 0,
  });
  expect(await jsonResponse(response, 400)).toMatchObject({
    code: 'HTTP_400',
    message: missingJobMessage,
  });

  expect(await jsonResponse(await request.get(jobPath, { maxRedirects: 0 }), 404)).toMatchObject(
    missingJob,
  );
});

test('keeps the existing 1 MiB proxy limit on other API routes', async ({ request }) => {
  // Health has no POST write handler even if a misplaced global limit were to
  // forward this request. Its proxy limit must remain outside the import budget.
  const response = await request.post('/api/health', {
    multipart: syntheticFiles('proxy_probe'),
    maxRedirects: 0,
  });

  expect(response.status(), await response.text()).toBe(413);
  expect(response.headers()['content-type']).toMatch(/^text\/html\b/);
  expect(await response.text()).toContain('413 Request Entity Too Large');
});
