import { environment } from '../../../services/environment';
import { requestJson } from '../../market';
import type { LessonState } from './lessonReviewClient';

/** The existing paginated Lesson read model. It does not report source currentness. */
export interface LessonListItem {
  lesson_id: string;
  current_version_id: string;
  version: number;
  current_state: LessonState;
  title: string;
  main_category: string;
  content: string;
  created_at: string;
  created_by: string;
}

export interface LessonListPageResponse {
  items: LessonListItem[];
  next_cursor: string | null;
}

function readPage(value: LessonListPageResponse): LessonListPageResponse {
  if (
    !value ||
    !Array.isArray(value.items) ||
    !(value.next_cursor === null || (typeof value.next_cursor === 'string' && value.next_cursor)) ||
    new Set(value.items.map((item) => item?.lesson_id)).size !== value.items.length ||
    value.items.some(
      (item) =>
        !item ||
        typeof item.lesson_id !== 'string' ||
        !item.lesson_id ||
        typeof item.current_version_id !== 'string' ||
        !item.current_version_id ||
        !Number.isInteger(item.version) ||
        item.version < 1 ||
        !['CURRENT', 'REVIEW_RECOMMENDED', 'RETIRED'].includes(item.current_state) ||
        [item.title, item.main_category, item.content, item.created_at, item.created_by].some(
          (field) => typeof field !== 'string',
        ),
    )
  ) {
    throw new Error('Die Erkenntnisliste wurde unvollständig oder mehrdeutig geliefert.');
  }
  return value;
}

export const lessonListClient = {
  list: async (cursor: string | null, signal?: AbortSignal): Promise<LessonListPageResponse> => {
    const query = new URLSearchParams({ limit: '25' });
    if (cursor !== null) query.set('cursor', cursor);
    const result = await requestJson<LessonListPageResponse>(
      `${environment.apiBaseUrl}/api/v1/learning/lessons?${query}`,
      { signal },
    );
    return readPage(result);
  },
};
