import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';

const bulkImportUrl = `${environment.apiBaseUrl}/api/v1/learning/bulk-imports`;

export type BulkImportFile = {
  id: string;
  filename: string;
  status: string;
  duplicate_of_file_id: string | null;
  failure_code: string | null;
  failure_detail: string | null;
};

export type BulkImportJob = {
  job_id: string;
  status: string;
  files_total: number;
  files_by_status: Record<string, number>;
  files: BulkImportFile[];
};

export type BulkImportReviewRow = {
  id: string;
  batch_id: string;
  validation_status: string;
  disposition: string;
  underlying_id: string | null;
  product_id: string | null;
  payload: Record<string, unknown>;
};

export type BulkImportConfirmResult = {
  job_id: string;
  status: string;
  accepted_observation_version_ids: string[];
};

function errorMessage(payload: unknown, status: number): string {
  if (typeof payload === 'object' && payload !== null) {
    if ('message' in payload && typeof payload.message === 'string') return payload.message;
    if ('detail' in payload && typeof payload.detail === 'string') return payload.detail;
  }
  return `Upload fehlgeschlagen (HTTP ${status}).`;
}

async function uploadFiles(files: File[]): Promise<BulkImportJob> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const response = await fetch(`${bulkImportUrl}/hebeltrader`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
    body: formData,
  });
  const payload = (await response.json()) as unknown;
  if (!response.ok) {
    throw new Error(errorMessage(payload, response.status));
  }
  return payload as BulkImportJob;
}

export const bulkImportClient = {
  upload: uploadFiles,
  getJob: (jobId: string) => requestJson<BulkImportJob>(`${bulkImportUrl}/${jobId}`),
  reviewRows: (jobId: string) =>
    requestJson<BulkImportReviewRow[]>(`${bulkImportUrl}/${jobId}/review`),
  resolve: (jobId: string, rowId: string, underlyingId: string, productId: string) =>
    requestJson<BulkImportReviewRow>(`${bulkImportUrl}/${jobId}/review/${rowId}/resolve`, {
      method: 'POST',
      body: { underlying_id: underlyingId, product_id: productId },
    }),
  discard: (jobId: string, rowId: string) =>
    requestJson<BulkImportReviewRow>(`${bulkImportUrl}/${jobId}/review/${rowId}/discard`, {
      method: 'POST',
    }),
  confirm: (jobId: string) =>
    requestJson<BulkImportConfirmResult>(`${bulkImportUrl}/${jobId}/confirm`, { method: 'POST' }),
};
