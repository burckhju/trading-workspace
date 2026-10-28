/** The UI names the browser time zone before using these local calendar boundaries. */
function localMidnight(value: string): Date {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Bitte gültige Kalendertage angeben.');
  const [year, month, day] = value.split('-').map(Number);
  const at = new Date(0);
  at.setFullYear(year, month - 1, day);
  at.setHours(0, 0, 0, 0);
  if (
    at.getFullYear() !== year ||
    at.getMonth() !== month - 1 ||
    at.getDate() !== day ||
    at.getHours() !== 0 ||
    at.getMinutes() !== 0
  )
    throw new Error(
      'Dieser Tagesbeginn ist in der Browserzeitzone nicht eindeutig verwendbar. Bitte genaue Zeitpunkte mit Zeitzone angeben.',
    );
  return at;
}

/** Inclusive source days become [start, next local midnight); DST may make a day 23/25 hours. */
export function historicalCurrencyDayWindow(from: string, through: string) {
  const start = localMidnight(from);
  const lastDay = localMidnight(through);
  if (lastDay < start)
    throw new Error('Das letzte gültige Datum darf nicht vor dem ersten liegen.');
  const end = new Date(lastDay);
  end.setDate(end.getDate() + 1);
  if (end.getHours() !== 0 || end.getMinutes() !== 0)
    throw new Error('Der Tagesübergang benötigt einen genauen Zeitpunkt mit Zeitzone.');
  return { valid_from: start.toISOString(), valid_to: end.toISOString() };
}
