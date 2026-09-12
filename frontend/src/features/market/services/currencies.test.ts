import { beforeEach, expect, it, vi } from 'vitest';
import { currencyAdminClient } from './currencies';
import { requestJson } from './http';

vi.mock('./http', () => ({ requestJson: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
it('uses existing JSON transport for reads, review-bound import and status commands', () => {
  const signal = new AbortController().signal;
  void currencyAdminClient.list(signal);
  expect(requestJson).toHaveBeenLastCalledWith(expect.stringContaining('/currencies/admin'), {
    signal,
  });
  void currencyAdminClient.history(signal);
  expect(requestJson).toHaveBeenLastCalledWith(expect.stringContaining('/admin/history'), {
    signal,
  });
  void currencyAdminClient.preview('{}');
  expect(requestJson).toHaveBeenLastCalledWith(expect.stringContaining('/catalog/preview'), {
    method: 'POST',
    body: { catalog_json: '{}' },
  });
  void currencyAdminClient.import('{}', 'token');
  expect(requestJson).toHaveBeenLastCalledWith(expect.stringContaining('/catalog/import'), {
    method: 'POST',
    body: { catalog_json: '{}', expected_preview_token: 'token', reviewed: true },
  });
  void currencyAdminClient.changeStatus('JPY', true, 'current');
  expect(requestJson).toHaveBeenLastCalledWith(expect.stringContaining('/JPY/activate'), {
    method: 'POST',
    body: { expected_token: 'current' },
  });
  void currencyAdminClient.changeStatus('JPY', false, 'new');
  expect(requestJson).toHaveBeenLastCalledWith(expect.stringContaining('/JPY/deactivate'), {
    method: 'POST',
    body: { expected_token: 'new' },
  });
});
