import { afterEach, describe, expect, it, vi } from 'vitest';

import { bulkImportClient } from './bulkImportClient';

const parsedJob = {
  job_id: 'job-1',
  status: 'READY',
  files_total: 1,
  files_by_status: { PARSED: 1 },
  files: [
    {
      id: 'file-1',
      filename: 'issue.pdf',
      status: 'PARSED',
      duplicate_of_file_id: null,
      failure_code: null,
      failure_detail: null,
    },
  ],
};

function mockResponse(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('bulkImportClient.upload', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('posts PDFs as multipart form data', async () => {
    const fetchMock = mockResponse(
      new Response(JSON.stringify(parsedJob), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const file = new File(['pdf'], 'issue.pdf', { type: 'application/pdf' });

    const result = await bulkImportClient.upload([file]);

    expect(result).toEqual(parsedJob);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).getAll('files')).toHaveLength(1);
  });

  it('keeps 103 PDFs in one multipart request without replay or confirmation', async () => {
    const files = Array.from(
      { length: 103 },
      (_, index) => new File(['synthetic pdf'], `issue-${index}.pdf`, { type: 'application/pdf' }),
    );
    const job = {
      ...parsedJob,
      files_total: files.length,
      files_by_status: { PARSED: files.length },
      files: files.map((file, index) => ({
        ...parsedJob.files[0],
        id: `file-${index}`,
        filename: file.name,
      })),
    };
    const response = new Response(JSON.stringify(job), { status: 201 });
    const fetchMock = mockResponse(response);

    await expect(bulkImportClient.upload(files)).resolves.toEqual(job);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/bulk-imports\/hebeltrader$/);
    expect(init.method).toBe('POST');
    expect(new Headers(init.headers).get('Accept')).toBe('application/json');
    expect(new Headers(init.headers).has('Content-Type')).toBe(false);
    expect((init.body as FormData).getAll('files')).toEqual(files);
    expect(response.bodyUsed).toBe(true);
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

  it('preserves an existing JSON detail error', async () => {
    const fetchMock = mockResponse(
      new Response(JSON.stringify({ detail: 'file must not be empty' }), { status: 400 }),
    );

    await expect(bulkImportClient.upload([])).rejects.toThrow('file must not be empty');
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it('explains an HTML 413 with the upload size limit and a smaller explicit selection', async () => {
    const fetchMock = mockResponse(
      new Response('<html><h1>Request Entity Too Large</h1></html>', {
        status: 413,
        headers: { 'Content-Type': 'text/html' },
      }),
    );

    const upload = bulkImportClient.upload([]);

    await expect(upload).rejects.toThrow(/HTTP 413/);
    await expect(upload).rejects.toThrow(/Größenlimit/);
    await expect(upload).rejects.toThrow(/kleinere PDF-Auswahl/);
    await expect(upload).rejects.not.toThrow(/<html>|Unexpected token|not valid JSON/);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it.each([502, 503, 504])('reports an unknown import outcome for HTML HTTP %i', async (status) => {
    const fetchMock = mockResponse(
      new Response('<html><h1>internal gateway information</h1></html>', {
        status,
        headers: { 'Content-Type': 'text/html' },
      }),
    );

    const upload = bulkImportClient.upload([]);

    await expect(upload).rejects.toThrow(`HTTP ${status}`);
    await expect(upload).rejects.toThrow(/Importstand ist unklar/);
    await expect(upload).rejects.not.toThrow(/<html>|internal gateway|Unexpected token/);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it.each(['message', 'detail'])(
    'keeps the API %s alongside an unknown server outcome',
    async (key) => {
      mockResponse(
        new Response(JSON.stringify({ [key]: 'Service is unavailable.' }), { status: 503 }),
      );

      const upload = bulkImportClient.upload([]);

      await expect(upload).rejects.toThrow('Service is unavailable.');
      await expect(upload).rejects.toThrow(/HTTP 503/);
      await expect(upload).rejects.toThrow(/Importstand ist unklar/);
    },
  );

  it('retains the HTTP status for a non-JSON client error', async () => {
    const fetchMock = mockResponse(new Response('plain-text error', { status: 400 }));

    await expect(bulkImportClient.upload([])).rejects.toThrow('Upload fehlgeschlagen (HTTP 400).');
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it.each([
    ['HTML', '<html><h1>unexpected page</h1></html>'],
    ['broken JSON', '{"job_id":'],
    ['an empty body', ''],
  ])('reports an unknown import outcome for HTTP 201 with %s', async (_, body) => {
    const fetchMock = mockResponse(new Response(body, { status: 201 }));

    await expect(bulkImportClient.upload([])).rejects.toThrow(/Importstand ist unklar/);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it.each([
    ['null', null],
    ['an array', []],
    ['an unrelated object', { message: 'accepted' }],
    ['a missing job ID', { ...parsedJob, job_id: undefined }],
    ['an empty job ID', { ...parsedJob, job_id: '' }],
    ['an invalid job status', { ...parsedJob, status: null }],
    ['an invalid total', { ...parsedJob, files_total: '1' }],
    ['invalid status counts', { ...parsedJob, files_by_status: { PARSED: '1' } }],
    ['an array of status counts', { ...parsedJob, files_by_status: [] }],
    ['a missing file list', { ...parsedJob, files: undefined }],
    ['a null file', { ...parsedJob, files: [null] }],
    [
      'an invalid file field',
      { ...parsedJob, files: [{ ...parsedJob.files[0], failure_detail: { message: 'bad' } }] },
    ],
  ])('rejects %s as an unconfirmed upload response', async (_, payload) => {
    const fetchMock = mockResponse(new Response(JSON.stringify(payload), { status: 201 }));

    await expect(bulkImportClient.upload([])).rejects.toThrow(/Importstand ist unklar/);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it('accepts additive fields and status strings without inventing domain validation', async () => {
    const job = {
      ...parsedJob,
      status: 'ADDITIONAL_STATUS',
      files_by_status: { ADDITIONAL_FILE_STATUS: 1 },
      files: [{ ...parsedJob.files[0], status: 'ADDITIONAL_FILE_STATUS' }],
      additional_field: true,
    };
    mockResponse(new Response(JSON.stringify(job), { status: 201 }));

    await expect(bulkImportClient.upload([])).resolves.toEqual(job);
  });

  it.each([
    new TypeError('internal network failure'),
    new DOMException('internal request aborted', 'AbortError'),
  ])('reports an unknown outcome after a rejected request without replay', async (failure) => {
    const fetchMock = vi.fn().mockRejectedValue(failure);
    vi.stubGlobal('fetch', fetchMock);

    const upload = bulkImportClient.upload([]);

    await expect(upload).rejects.toThrow(/Importstand ist unklar/);
    await expect(upload).rejects.not.toThrow(/internal/);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it.each([201, 504])(
    'reports an unknown outcome after a body read fails with HTTP %i',
    async (status) => {
      const body = new ReadableStream({
        start(controller) {
          controller.error(new Error('internal response stream failure'));
        },
      });
      const fetchMock = mockResponse(new Response(body, { status }));

      const upload = bulkImportClient.upload([]);

      await expect(upload).rejects.toThrow(/Importstand ist unklar/);
      await expect(upload).rejects.not.toThrow(/internal response/);
      expect(fetchMock).toHaveBeenCalledOnce();
    },
  );

  it('preserves an HTTP 413 size rejection when its response body cannot be read', async () => {
    const body = new ReadableStream({
      start(controller) {
        controller.error(new Error('internal response stream failure'));
      },
    });
    const fetchMock = mockResponse(new Response(body, { status: 413 }));

    const upload = bulkImportClient.upload([]);

    await expect(upload).rejects.toThrow(/HTTP 413/);
    await expect(upload).rejects.toThrow(/Größenlimit/);
    await expect(upload).rejects.toThrow(/kleinere PDF-Auswahl/);
    await expect(upload).rejects.not.toThrow(/Importstand ist unklar|internal response/);
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
