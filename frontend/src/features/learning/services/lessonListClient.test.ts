import { beforeEach, describe, expect, it, vi } from 'vitest';
import { requestJson } from '../../market';
import { lessonListClient } from './lessonListClient';
import { lessonListReturnLink } from './lessonNavigation';

vi.mock('../../market', () => ({ requestJson: vi.fn() }));
describe('existing paginated Lesson read contract', () => {
  beforeEach(() => vi.resetAllMocks());
  it('encodes the opaque cursor and keeps the abort signal on a bounded GET', async () => {
    vi.mocked(requestJson).mockResolvedValue({ items: [], next_cursor: null });
    const controller = new AbortController();
    await expect(lessonListClient.list('opaque+/ cursor', controller.signal)).resolves.toEqual({
      items: [],
      next_cursor: null,
    });
    const [url, options] = vi.mocked(requestJson).mock.calls[0];
    expect(String(url)).toContain('/api/v1/learning/lessons?');
    const query = new URL(String(url), 'http://workspace.test').searchParams;
    expect(query.get('limit')).toBe('25');
    expect(query.get('cursor')).toBe('opaque+/ cursor');
    expect(options).toEqual({ signal: controller.signal });
  });
  it.each([
    { items: [], next_cursor: '' },
    { items: [{ lesson_id: 'x' }], next_cursor: null },
    { items: 'not a page', next_cursor: null },
  ])('rejects incomplete page data without presenting an empty success', async (value) => {
    vi.mocked(requestJson).mockResolvedValue(value);
    await expect(lessonListClient.list(null)).rejects.toThrow('unvollständig oder mehrdeutig');
  });
  it.each([
    'lesson_list=https%3A%2F%2Fevil.test',
    'lesson_list=lessons&lesson_list=models',
    'lesson_list=lessons&lesson_cursor=',
    'lesson_list=models&lesson_cursor=a&lesson_cursor=b',
  ])('does not adopt an unowned or ambiguous return context: %s', (query) => {
    expect(lessonListReturnLink(new URLSearchParams(query))).toBeNull();
  });
});
