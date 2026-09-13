/** Calendar dates stay calendar dates. UTC conversion is only for a known time. */
export function localToday(now = new Date()): string {
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
  ].join('-');
}

export function executionTime(date: string, time = '') {
  if (!date || date > localToday())
    throw new Error('Bitte ein gültiges Kauf-/Verkaufsdatum bis heute wählen.');
  if (time) {
    const at = new Date(`${date}T${time}`);
    if (
      Number.isNaN(at.getTime()) ||
      localToday(at) !== date ||
      `${String(at.getHours()).padStart(2, '0')}:${String(at.getMinutes()).padStart(2, '0')}` !==
        time
    ) {
      throw new Error('Die Uhrzeit ist in der lokalen Zeitzone nicht gültig.');
    }
    // Date silently chooses one offset for a repeated local clock time. Check
    // offsets on both sides of the transition, including non-hour clock changes.
    const offset = at.getTimezoneOffset();
    const ambiguous = [-36, 36].some((hours) => {
      const otherOffset = new Date(at.getTime() + hours * 3600000).getTimezoneOffset();
      if (otherOffset === offset) return false;
      const other = new Date(at.getTime() + (otherOffset - offset) * 60000);
      return (
        localToday(other) === date &&
        other.getHours() === at.getHours() &&
        other.getMinutes() === at.getMinutes()
      );
    });
    if (ambiguous) {
      throw new Error(
        'Die Uhrzeit ist wegen der Zeitumstellung nicht eindeutig. ' +
          'Bitte die tatsächliche Ausführung prüfen; keine Uhrzeit schätzen. ' +
          'Ohne eindeutig bekannte Uhrzeit nur das bestätigte Datum erfassen.',
      );
    }
    if (at.getTime() > Date.now())
      throw new Error('Die Ausführung darf nicht in der Zukunft liegen.');
    return { executed_at: at.toISOString() };
  }
  return {
    executed_on: date,
    execution_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}

const pending = new Map<string, { fingerprint: string; id: string }>();

/** Same payload retries (including a page reload in this tab) retain the same key. */
export function captureRequest(scope: string, payload: object): string {
  const storageKey = `trade-capture:${scope}`;
  const fingerprint = JSON.stringify(payload);
  try {
    const previous = JSON.parse(sessionStorage.getItem(storageKey) ?? 'null') as {
      fingerprint?: string;
      id?: string;
    } | null;
    if (previous?.fingerprint === fingerprint && previous.id) {
      pending.set(storageKey, { fingerprint, id: previous.id });
      return previous.id;
    }
  } catch {
    /* Corrupt / unavailable local storage is not transaction truth. */
  }
  const cached = pending.get(storageKey);
  if (cached?.fingerprint === fingerprint) return cached.id;
  const id = crypto.randomUUID();
  pending.set(storageKey, { fingerprint, id });
  try {
    sessionStorage.setItem(storageKey, JSON.stringify({ fingerprint, id }));
  } catch {
    /* Backend still enforces the supplied key. */
  }
  return id;
}

export function finishCapture(scope: string) {
  pending.delete(`trade-capture:${scope}`);
  try {
    sessionStorage.removeItem(`trade-capture:${scope}`);
  } catch {
    /* No database effect. */
  }
}
