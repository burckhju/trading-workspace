import { afterEach, describe, expect, it, vi } from 'vitest';

import { bulkImportClient } from './bulkImportClient';

describe('bulkImportClient.upload', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('posts PDFs as multipart form data', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          job_id: 'job-1',
          status: 'READY',
          files_total: 1,
          files_by_status: { PARSED: 1 },
          files: [],
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
    const file = new File(['pdf'], 'issue.pdf', { type: 'application/pdf' });

    const result = await bulkImportClient.upload([file]);

    expect(result.job_id).toBe('job-1');
    expect(fetchMock).toHaveBeenCalledOnce();
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).getAll('files')).toHaveLength(1);
  });

  it('surfaces the project API message contract', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: 'HTTP_400',
            message: 'at least one PDF is required',
            details: [],
          }),
          {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          },
        ),
      ),
    );

    await expect(bulkImportClient.upload([])).rejects.toThrow('at least one PDF is required');
  });
});
