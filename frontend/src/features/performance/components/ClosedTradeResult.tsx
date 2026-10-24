import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { performanceApiClient } from '../services/client';
import {
  CLOSED_REPORT_PATH,
  parseClosedContext,
  verifyClosedReport,
} from '../services/closedReportContext';
import { closedTradeGroupText, closedTradeReasonText } from '../services/closedTradesPresentation';
import type { ClosedTradeReport } from '../types/api';
import { ClosedTradeSources } from './ClosedTradeSources';

export function ClosedTradeResult({
  tradeId,
  productId,
  query,
}: {
  tradeId: string;
  productId: string;
  query: URLSearchParams;
}) {
  const parsed = parseClosedContext(query);
  if (parsed.error) return <p role="alert">{parsed.error}</p>;
  if (!parsed.context)
    return (
      <>
        <p>
          Kein Abschlussberichtskontext ausgewählt. Eine vollständige Geldqualifikation wird hier
          nicht durch einen Rohpositionswert ersetzt.
        </p>
        <Link className="text-sky-400 underline" to={CLOSED_REPORT_PATH}>
          Abschlussauswertung auswählen
        </Link>
      </>
    );
  const { context } = parsed;
  return (
    <ResultRead
      key={JSON.stringify([tradeId, productId, context])}
      tradeId={tradeId}
      productId={productId}
      context={context}
    />
  );
}

function ResultRead({
  tradeId,
  productId,
  context: initialContext,
}: {
  tradeId: string;
  productId: string;
  context: NonNullable<ReturnType<typeof parseClosedContext>['context']>;
}) {
  const [context] = useState(initialContext);
  const [attempt, setAttempt] = useState(0);
  const [report, setReport] = useState<ClosedTradeReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setReport(null);
    setError(null);
    performanceApiClient
      .closedTrades(context.filters, controller.signal)
      .then((value) => {
        if (!active || controller.signal.aborted) return;
        verifyClosedReport(value, context.filters);
        const items = value.items.filter((item) => item.trade_id.toLowerCase() === tradeId);
        if (items.length !== 1 || items[0].product_id !== productId)
          throw new Error(
            'Der eigene Trade fehlt in dieser Ergebnisgrundlage oder seine Identität ist unpassend. Kein Ersatztrade.',
          );
        setReport(value);
      })
      .catch((reason: unknown) => {
        if (active && !controller.signal.aborted)
          setError(reason instanceof Error ? reason.message : 'Ergebnisgrundlage nicht verfügbar.');
      });
    return () => {
      active = false;
      controller.abort();
    };
    // A visit is keyed above and by the owning TradeManagementPage. Historical
    // pin changes and A→B→A cannot reuse a prior request lifetime.
  }, [tradeId, productId, context.filters, attempt]);
  if (error)
    return (
      <>
        <p role="alert">
          Das wirtschaftliche Ergebnis konnte nicht gelesen werden. Dies ist weder Null noch
          fehlende Reflexion. {error}
        </p>
        <button
          type="button"
          className="text-sky-400 underline"
          onClick={() => setAttempt((v) => v + 1)}
        >
          Gesamtergebnis neu lesen
        </button>
      </>
    );
  if (!report) return <p role="status">Wirtschaftliches Gesamtergebnis wird gelesen.</p>;
  const item = report.items.find((entry) => entry.trade_id.toLowerCase() === tradeId)!;
  const state =
    item.group === 'CANCELLED'
      ? 'Storniert – kein Verkauf'
      : item.group === 'OPEN'
        ? 'Offen – kein vollständiger Abschluss'
        : item.group === 'HISTORY_UNRESOLVED'
          ? 'Abschluss nicht zuverlässig bestimmbar'
          : 'Abgeschlossen';
  return (
    <>
      <p>Zustand in dieser Ergebnisgrundlage: {state}.</p>
      <p>{closedTradeGroupText[item.group]}</p>
      {item.reasons.map((reason) => (
        <p key={reason}>{closedTradeReasonText(reason)}</p>
      ))}
      <p>
        Brutto vor Gebühren, Kommissionen und Steuern. Keine Bewertung der Entscheidungsqualität.
      </p>
      <p role="status">
        {context.basis === null
          ? 'Kein Listenfingerprint mitgegeben; ein Vergleich mit der vorherigen Auswahl ist nicht belegt.'
          : context.basis === report.basis.id
            ? 'Die Berichtsgrundlage stimmt mit dem mitgegebenen Listenfingerprint überein.'
            : 'Die Berichtsgrundlage hat sich seit der Listenauswahl geändert. Hier wird der neu gelesene Stand gezeigt; betroffen sein können auch andere Trades oder Referenzdaten.'}{' '}
        Ein Fingerprint stellt keinen früheren Bericht wieder her und beglaubigt keine URL-Eingabe.
      </p>
      <p className="text-sm text-slate-400">
        Ergebnis und monetäre Buchungsquellen unten stammen gemeinsam aus genau einer Antwort. Die
        weiteren Ausführungs-, Plan- und Lernabschnitte haben eigene Lesefenster; sie bestätigen
        nicht automatisch diese Ergebnisgrundlage.
      </p>
      <details className="text-sm [overflow-wrap:anywhere]">
        <summary>Finanzdefinition und Ergebnisgrundlage</summary>
        <p>
          Definition: {report.definition_version}; Zeitraum: {report.filters.from_date} bis{' '}
          {report.filters.to_date}; Währung: {report.currency.code}; Zeitzone:{' '}
          {report.filters.report_timezone}.
        </p>
        <p>Quellenstand: {report.basis.id}</p>
        <p>
          Gelesen: {report.basis.read_started_at} bis {report.basis.read_completed_at}; berechnet:{' '}
          {report.basis.calculated_at}. Keine Ausführungszeit.
        </p>
      </details>
      <ClosedTradeSources item={item} report={report} showEditorLink={false} />
      <button
        type="button"
        className="text-sky-400 underline"
        onClick={() => setAttempt((v) => v + 1)}
      >
        Gesamtergebnis neu lesen
      </button>
    </>
  );
}
