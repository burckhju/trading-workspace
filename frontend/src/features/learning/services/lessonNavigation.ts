export type LessonListPurpose = 'lessons' | 'models';

export const lessonListPath = (purpose: LessonListPurpose) =>
  purpose === 'models' ? '/model-improvements' : '/lessons';

type CursorStep = { cursor: string; previous: string | null };
const cursorHistoryLimit = 100;
const cursorHistoryKey = (purpose: LessonListPurpose) =>
  `trading-workspace.lesson-list-navigation.v1.${purpose}`;

function readCursorHistory(purpose: LessonListPurpose): CursorStep[] {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem(cursorHistoryKey(purpose)) ?? '[]');
    if (!Array.isArray(value)) return [];
    return value.slice(-cursorHistoryLimit).filter((step: unknown): step is CursorStep => {
      if (!step || typeof step !== 'object' || !('cursor' in step) || !('previous' in step)) {
        return false;
      }
      return (
        typeof step.cursor === 'string' &&
        step.cursor.length > 0 &&
        (step.previous === null ||
          (typeof step.previous === 'string' && step.previous.length > 0)) &&
        step.cursor !== step.previous
      );
    });
  } catch {
    return [];
  }
}

/** Remember only followed page links, never lesson data or inferred backend cursors. */
export function rememberLessonListCursor(
  purpose: LessonListPurpose,
  cursor: string,
  previous: string | null,
): void {
  if (!cursor || previous === '' || cursor === previous) return;
  const history = readCursorHistory(purpose).filter((step) => step.cursor !== cursor);
  history.push({ cursor, previous });
  try {
    sessionStorage.setItem(
      cursorHistoryKey(purpose),
      JSON.stringify(history.slice(-cursorHistoryLimit)),
    );
  } catch {
    // Browser history state still supports the immediate return when storage is unavailable.
  }
}

export function previousLessonListCursor(
  purpose: LessonListPurpose,
  cursor: string | null,
): string | null | undefined {
  if (cursor === null) return undefined;
  return readCursorHistory(purpose)
    .reverse()
    .find((step) => step.cursor === cursor)?.previous;
}

/** Only the two owned list routes can be used as return destinations. */
export function lessonListReturnLink(params: URLSearchParams): string | null {
  const values = params.getAll('lesson_list');
  if (values.length !== 1 || !['lessons', 'models'].includes(values[0])) return null;
  const cursors = params.getAll('lesson_cursor');
  if (cursors.length > 1 || (cursors.length === 1 && !cursors[0])) return null;
  const query = new URLSearchParams();
  if (cursors.length === 1) query.set('cursor', cursors[0]);
  return `${lessonListPath(values[0] as LessonListPurpose)}${query.size ? `?${query}` : ''}`;
}

export function lessonListDetailLink(
  lessonId: string,
  versionId: string,
  purpose: LessonListPurpose,
  cursor: string | null,
): string {
  const params = new URLSearchParams({ lesson_version_id: versionId, lesson_list: purpose });
  if (cursor !== null) params.set('lesson_cursor', cursor);
  return `/lessons/${encodeURIComponent(lessonId)}?${params}#${purpose === 'models' ? 'model-improvement' : 'lesson-history'}`;
}

export const lessonStateLabel = {
  CURRENT: 'Aktuelle Interpretation',
  REVIEW_RECOMMENDED: 'Prüfung empfohlen',
  RETIRED: 'Außer Gebrauch',
} as const;
