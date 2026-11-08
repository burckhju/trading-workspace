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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === 'string';
}

function isBulkImportFile(value: unknown): value is BulkImportFile {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.filename === 'string' &&
    typeof value.status === 'string' &&
    isNullableString(value.duplicate_of_file_id) &&
    isNullableString(value.failure_code) &&
    isNullableString(value.failure_detail)
  );
}

function isBulkImportJob(value: unknown): value is BulkImportJob {
  return (
    isRecord(value) &&
    typeof value.job_id === 'string' &&
    value.job_id.trim().length > 0 &&
    typeof value.status === 'string' &&
    typeof value.files_total === 'number' &&
    isRecord(value.files_by_status) &&
    Object.values(value.files_by_status).every((count) => typeof count === 'number') &&
    Array.isArray(value.files) &&
    value.files.every(isBulkImportFile)
  );
}

function unknownImportMessage(status?: number): string {
  const httpStatus = status === undefined ? '' : ` (HTTP ${status})`;
  return `Keine verlässliche Antwort auf den PDF-Import erhalten${httpStatus}. Der Importstand ist unklar. Bitte vor einem erneuten Upload den Importstand prüfen.`;
}

function errorMessage(payload: unknown, status: number): string {
  let apiMessage: string | undefined;
  if (isRecord(payload)) {
    if (typeof payload.message === 'string') apiMessage = payload.message;
    else if (typeof payload.detail === 'string') apiMessage = payload.detail;
  }
  if (status === 413) {
    const sizeMessage =
      'Die Upload-Anfrage überschreitet das Größenlimit (HTTP 413). Bitte eine kleinere PDF-Auswahl treffen und den Import erneut starten.';
    return apiMessage === undefined ? sizeMessage : `${apiMessage} ${sizeMessage}`;
  }
  if (status >= 500) {
    const unknownMessage = unknownImportMessage(status);
    return apiMessage === undefined ? unknownMessage : `${apiMessage} ${unknownMessage}`;
  }
  return apiMessage ?? `Upload fehlgeschlagen (HTTP ${status}).`;
}

async function uploadFiles(files: File[]): Promise<BulkImportJob> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  let response: Response;
  try {
    response = await fetch(`${bulkImportUrl}/hebeltrader`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
      body: formData,
    });
  } catch {
    throw new Error(unknownImportMessage());
  }

  let body: string;
  try {
    body = await response.text();
  } catch {
    throw new Error(
      response.ok
        ? unknownImportMessage(response.status)
        : errorMessage(undefined, response.status),
    );
  }
  let payload: unknown;
  try {
    payload = JSON.parse(body) as unknown;
  } catch {
    // Gateways can return HTML or an empty body; the HTTP status remains evidence.
    payload = undefined;
  }
  if (!response.ok) {
    throw new Error(errorMessage(payload, response.status));
  }
  if (!isBulkImportJob(payload)) {
    throw new Error(unknownImportMessage(response.status));
  }
  return payload;
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
