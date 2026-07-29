const DEFAULT_API_BASE_URL = 'http://localhost:8000';

function parseAbsoluteHttpUrl(value: string): string {
  const url = new URL(value);

  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('VITE_API_BASE_URL must use HTTP or HTTPS.');
  }

  return url.toString().replace(/\/$/, '');
}

export const environment = Object.freeze({
  apiBaseUrl: parseAbsoluteHttpUrl(import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL),
});
