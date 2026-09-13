import type { OperationalPosition } from '../types';

export function statusLabel(status: string): string {
  if (status === 'OK' || status === 'AVAILABLE') return 'Aktuell';
  if (status === 'LAST_AVAILABLE') return 'Letzter verfügbarer Kurs';
  if (status === 'INDICATIVE') return 'Indikativer Referenzkurs';
  if (status === 'STALE') return 'Veraltet';
  if (status === 'MISSING') return 'Fehlt';
  if (status === 'INSUFFICIENT') return 'Noch nicht ausreichend';
  if (status === 'UNAVAILABLE') return 'Nicht verfügbar';
  return 'Prüfen';
}
export function signalLabel(p: OperationalPosition): string {
  const signal = p.position_signal;
  if (!signal) return 'Positionssignal: nicht verfügbar';
  if (signal.quality_status !== 'AVAILABLE')
    return `Positionssignal: ${signal.quality_status === 'STALE' ? 'Daten veraltet' : signal.quality_status === 'MISSING' ? 'Daten fehlen' : signal.quality_status === 'INSUFFICIENT' ? 'noch nicht ausreichend Daten' : 'Prüfung erforderlich'}`;
  if (signal.alert_level === 'CRITICAL') return 'Positionssignal: dynamischer Stop erreicht';
  if (signal.alert_level === 'ATTENTION') return 'Positionssignal: Gewinnschutz aktiv';
  return 'Positionssignal: keine besondere Aufmerksamkeit nötig';
}
