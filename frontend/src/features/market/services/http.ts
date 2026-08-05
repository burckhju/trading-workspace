import type { ApiErrorResponse, AuditActorHeaders } from '../types/api';

const JSON_CONTENT_TYPE = 'application/json';

export class MarketApiError extends Error {
  readonly status: number;
  readonly response: ApiErrorResponse;

  constructor(status: number, response: ApiErrorResponse) {
    super(response.message);
    this.name = 'MarketApiError';
    this.status = status;
    this.response = response;
  }
}

export class MarketTransportError extends Error {
  readonly cause: unknown;

  constructor(message: string, cause?: unknown) {
    super(message);
    this.name = 'MarketTransportError';
    this.cause = cause;
  }
}

export interface HttpRequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  actor?: AuditActorHeaders;
  signal?: AbortSignal;
}

function actorHeaders(actor: AuditActorHeaders | undefined): HeadersInit {
  if (actor === undefined) {
    return {};
  }

  const headers: Record<string, string> = {};
  if (actor.actorId !== undefined) {
    headers['X-Actor-ID'] = actor.actorId;
  }
  if (actor.actorName !== undefined) {
    headers['X-Actor-Name'] = actor.actorName;
  }
  return headers;
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const candidate = value as Partial<ApiErrorResponse>;
  return (
    typeof candidate.code === 'string' &&
    typeof candidate.message === 'string' &&
    Array.isArray(candidate.details) &&
    typeof candidate.timestamp === 'string'
  );
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text.length === 0) {
    return undefined;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch (error) {
    throw new MarketTransportError('The API returned invalid JSON.', error);
  }
}

export async function requestJson<T>(
  url: string,
  options: HttpRequestOptions = {},
): Promise<T> {
  const headers = new Headers(actorHeaders(options.actor));
  if (options.body !== undefined) {
    headers.set('Content-Type', JSON_CONTENT_TYPE);
  }
  headers.set('Accept', JSON_CONTENT_TYPE);

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    throw new MarketTransportError('The API could not be reached.', error);
  }

  const payload = await readJson(response);
  if (!response.ok) {
    if (isApiErrorResponse(payload)) {
      throw new MarketApiError(response.status, payload);
    }
    throw new MarketTransportError(`The API request failed with HTTP ${response.status}.`);
  }

  return payload as T;
}
