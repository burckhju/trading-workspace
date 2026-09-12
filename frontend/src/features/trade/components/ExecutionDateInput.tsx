import { localToday } from '../services/capture';

export function ExecutionDateInput({
  label,
  date,
  time,
  onDate,
  onTime,
}: {
  label: string;
  date: string;
  time: string;
  onDate: (value: string) => void;
  onTime: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <label className="block text-sm">
        {label}
        <input
          aria-label={label}
          type="date"
          required
          max={localToday()}
          value={date}
          onChange={(event) => onDate(event.target.value)}
          className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
        />
      </label>
      <label className="block text-sm">
        Uhrzeit, falls bekannt
        <input
          aria-label={`${label} Uhrzeit`}
          type="time"
          value={time}
          onChange={(event) => onTime(event.target.value)}
          className="mt-1 block w-full rounded border border-slate-700 bg-slate-950 p-2"
        />
      </label>
      <p className="text-xs text-slate-400">
        Tatsächliche Ausführung, nicht Erfassung. Ohne Uhrzeit wird nur das Datum gespeichert.
        Zeitzone: {Intl.DateTimeFormat().resolvedOptions().timeZone}.
      </p>
    </div>
  );
}
