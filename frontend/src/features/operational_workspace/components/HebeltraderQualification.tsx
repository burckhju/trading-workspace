import { useEffect, useRef, useState } from 'react';
import type { TargetQualificationPreview } from '../hebeltraderQualification';
import type {
  HebeltraderTargetAssessmentRequest,
  HebeltraderTargetsReport,
} from '../hebeltraderTargets';
import type {
  QualificationSession,
  QualificationSessions,
} from '../hooks/useHebeltraderQualificationSessions';
import { readQualificationPreview } from '../services/hebeltraderQualification';
import {
  HebeltraderComparisonEvidence,
  QualificationIssues,
} from './HebeltraderComparisonEvidence';

const control =
  'rounded border border-slate-600 px-3 py-2 focus-visible:outline-2 focus-visible:outline-sky-300 disabled:opacity-40';

export function HebeltraderQualification({
  tradeId,
  positionId,
  report,
  sessionKey,
  session,
  update,
  blocked,
  onReport,
  onSubmit,
}: {
  tradeId: string;
  positionId: string;
  report: HebeltraderTargetsReport;
  sessionKey: string;
  session: QualificationSession;
  update: QualificationSessions['update'];
  blocked: boolean;
  onReport: (value: HebeltraderTargetsReport) => void;
  onSubmit: (payload: HebeltraderTargetAssessmentRequest) => Promise<void>;
}) {
  const [preview, setPreview] = useState<TargetQualificationPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadedCommandEpoch, setLoadedCommandEpoch] = useState<number | null>(null);
  const generation = useRef(0);
  const sessionRef = useRef(session);
  sessionRef.current = session;

  useEffect(() => {
    if (!session.open) return;
    const controller = new AbortController();
    const currentGeneration = ++generation.current;
    const commandAtRead = sessionRef.current.commandEpoch;
    const current = () => currentGeneration === generation.current && !controller.signal.aborted;
    setLoading(true);
    setError(null);
    setPreview(null);
    readQualificationPreview(tradeId, positionId, controller.signal)
      .then((value) => {
        if (!current()) return;
        setPreview(value);
        setLoadedCommandEpoch(commandAtRead);
        setLoading(false);
        // A read begun before a new command cannot replace the command's newer report.
        if (sessionRef.current.commandEpoch === commandAtRead) onReport(value.report);
      })
      .catch((reason: unknown) => {
        if (!current()) return;
        setLoading(false);
        setError(
          reason instanceof Error
            ? reason.message
            : 'Vergleichsbelege konnten nicht gelesen werden.',
        );
      });
    return () => {
      generation.current += 1;
      controller.abort();
    };
  }, [tradeId, positionId, session.open, attempt, onReport]);

  const changed =
    preview !== null &&
    (preview.report.current_basis_id !== report.current_basis_id ||
      preview.report.latest_assessment?.id !== report.latest_assessment?.id ||
      loadedCommandEpoch !== session.commandEpoch);
  const referenceChanged =
    preview !== null &&
    session.reference.length > 0 &&
    session.referenceBasisId !== preview.report.current_basis_id;
  const validReference =
    session.reference.trim().length >= 3 && session.reference.trim().length <= 1000;
  const canConfirm =
    preview?.readiness.status === 'REVIEWABLE' &&
    preview.qualification_binding !== null &&
    preview.qualification.status !== 'REUSABLE' &&
    report.position_state === 'OPEN' &&
    session.command?.phase !== 'REJECTED' &&
    !blocked &&
    !loading &&
    !changed &&
    !referenceChanged &&
    validReference;

  function confirm() {
    if (!canConfirm || !preview?.qualification_binding) return;
    void onSubmit({
      position_id: preview.report.position_id,
      request_id: crypto.randomUUID(),
      expected_basis_id: preview.report.current_basis_id,
      expected_assessment_id: preview.report.latest_assessment?.id ?? null,
      confirmation: 'ASSESS_SAVED_HEBELTRADER_EVIDENCE',
      qualification: {
        ...preview.qualification_binding,
        evidence_reference: session.reference.trim(),
        confirmation: 'CONFIRM_HISTORICAL_LISTING_AND_UNCHANGED_ORIGINAL_SCALE',
      },
    });
  }

  return (
    <section
      aria-label="Historische Vergleichsqualifikation"
      className="min-w-0 space-y-3 rounded border border-slate-700 p-3"
    >
      <h4 className="font-semibold">Historische Kursbelege und Vergleichsbestätigung</h4>
      <button
        type="button"
        className={control}
        aria-expanded={session.open}
        disabled={blocked}
        onClick={() => update(sessionKey, (previous) => ({ ...previous, open: !previous.open }))}
      >
        {session.open ? 'Vergleichsbelege schließen' : 'Historische Vergleichsbelege ansehen'}
      </button>
      {session.open && (
        <>
          <p>
            Dieser Leseweg zeigt gespeicherte Quellen und Originalkurse. Er fragt keinen Provider ab
            und startet keine Prüfung.
          </p>
          {loading && <p role="status">Gespeicherte Vergleichsbelege werden gelesen …</p>}
          {error && <p role="alert">{error}</p>}
          <button
            type="button"
            className={control}
            disabled={blocked || loading}
            onClick={() => setAttempt((value) => value + 1)}
          >
            Vergleichsbelege erneut lesen
          </button>
          {changed && (
            <p className="text-amber-200">
              Der gelesene Vergleichsstand ist überholt. Vor einer neuen Bestätigung die
              Vergleichsbelege erneut lesen. Der Entwurf bleibt erhalten.
            </p>
          )}
          {preview && (
            <>
              <p
                className={
                  preview.readiness.status === 'REVIEWABLE' ? 'text-slate-200' : 'text-amber-200'
                }
              >
                {preview.readiness.status === 'REVIEWABLE'
                  ? 'Eine konkrete historische Vergleichsbestätigung ist für diesen Stand möglich.'
                  : preview.readiness.status === 'NOT_APPLICABLE'
                    ? 'Für diese Position ist keine neue Vergleichsbestätigung anwendbar.'
                    : 'Für diesen Stand ist die Vergleichsbestätigung gesperrt.'}
              </p>
              <QualificationIssues items={preview.readiness.issues} />
              <HebeltraderComparisonEvidence key={preview.history.fingerprint} preview={preview} />
              {preview.notices.length > 0 && (
                <ul className="list-disc space-y-1 pl-5">
                  {preview.notices.map((notice) => (
                    <li key={notice}>{notice}</li>
                  ))}
                </ul>
              )}
              <section aria-label="Gespeicherte Vergleichsbestätigung" className="space-y-2">
                <h4 className="font-semibold">Gespeicherte Nutzererklärung</h4>
                <p>
                  {preview.qualification.status === 'REUSABLE'
                    ? 'Die vorhandene Bestätigung passt zu diesem Stand und wird wiederverwendet. Keine erneute Eingabe erforderlich.'
                    : preview.qualification.status === 'STALE'
                      ? 'Die gespeicherte Erklärung gehört zu einem anderen Vergleichsstand und ist hier nicht wiederverwendbar.'
                      : 'Für diese Reihe liegt keine gespeicherte Vergleichsbestätigung vor.'}
                </p>
                <p>Eine Nutzererklärung ist keine unabhängige Verifikation durch das System.</p>
                {preview.qualification.value && (
                  <>
                    <p>
                      Gespeicherte Belegreferenz: {preview.qualification.value.evidence_reference}
                    </p>
                    <p className="text-xs text-slate-300">
                      Enthalten in Prüfstand {preview.qualification.contained_in_assessment_id},
                      gespeichert {preview.qualification.contained_in_recorded_at}. Dies bezeichnet
                      den enthaltenden Snapshot, nicht den ursprünglichen Bestätiger.
                    </p>
                    <details className="text-xs">
                      <summary>Gebundener Stand der Nutzererklärung</summary>
                      <p>
                        Quelle {preview.qualification.value.source_version_id} · Maßstabsreferenz{' '}
                        {preview.qualification.value.source_scale_reference} · Kursbestand{' '}
                        {preview.qualification.value.history_fingerprint} · Listing{' '}
                        {preview.qualification.value.listing_fingerprint}.
                      </p>
                    </details>
                  </>
                )}
              </section>
              {preview.qualification.status !== 'REUSABLE' && (
                <form
                  className="space-y-3"
                  onSubmit={(event) => {
                    event.preventDefault();
                    confirm();
                  }}
                >
                  <label className="block space-y-1">
                    <span>
                      Konkreter Nachweis für historische Listingzuordnung und gemeinsamen
                      Originalmaßstab
                    </span>
                    <textarea
                      rows={3}
                      value={session.reference}
                      maxLength={1000}
                      disabled={blocked}
                      onChange={(event) => {
                        const reference = event.target.value;
                        update(sessionKey, (previous) => ({
                          ...previous,
                          reference,
                          referenceBasisId: preview.report.current_basis_id,
                        }));
                      }}
                      className="block w-full rounded border border-slate-600 bg-slate-950 p-2 text-slate-100 focus-visible:outline-2 focus-visible:outline-sky-300"
                      aria-describedby="hebeltrader-reference-help"
                    />
                  </label>
                  <p id="hebeltrader-reference-help" className="text-xs text-slate-300">
                    Konkretes Dokument beziehungsweise nachvollziehbare Belegstelle mit
                    Datum/Version und geprüfter Zuordnung angeben (3–1.000 Zeichen). IDs, Währungen
                    und Fingerprints werden aus dem gelesenen Stand übernommen. Details schließen,
                    Bereichswechsel innerhalb dieser Position und erneutes Lesen erhalten den
                    Entwurf. Beim Verlassen dieser Position oder Neuladen im Browser endet dieser
                    lokale Speicher.
                  </p>
                  {!validReference && (
                    <p>
                      Eine konkrete Belegreferenz mit mindestens drei Zeichen ist erforderlich;
                      Leerzeichen allein genügen nicht.
                    </p>
                  )}
                  {preview.qualification.value && !session.reference && (
                    <button
                      type="button"
                      className={control}
                      disabled={blocked}
                      onClick={() =>
                        update(sessionKey, (previous) => ({
                          ...previous,
                          reference: preview.qualification.value!.evidence_reference,
                          referenceBasisId: preview.report.current_basis_id,
                        }))
                      }
                    >
                      Bisherige Belegreferenz als Entwurf übernehmen
                    </button>
                  )}
                  {referenceChanged && (
                    <div className="space-y-2 text-amber-200">
                      <p>
                        Der Text stammt aus einem älteren Belegstand. Er wurde nicht automatisch auf
                        die neue Basis übertragen.
                      </p>
                      <button
                        type="button"
                        className={control}
                        disabled={blocked || changed}
                        onClick={() =>
                          update(sessionKey, (previous) => ({
                            ...previous,
                            referenceBasisId: preview.report.current_basis_id,
                          }))
                        }
                      >
                        Entwurf nach Prüfung auf diesen Belegstand beziehen
                      </button>
                    </div>
                  )}
                  <p>
                    Mit der folgenden Handlung bestätige ich anhand der genannten Belegstelle die
                    historische Listing-, Zeit- und Währungszuordnung sowie den unveränderten
                    gemeinsamen Originalmaßstab der angezeigten Hebeltrader-Quelle und der gesamten
                    gespeicherten Kursreihe. Ungeeignete Belege und Anpassungsindizien bleiben
                    gesperrt.
                  </p>
                  <button type="submit" className={control} disabled={!canConfirm}>
                    Historische Zuordnung und Originalmaßstab bestätigen und prüfen
                  </button>
                  <p className="text-xs text-slate-300">
                    Die Handlung speichert eine konkrete Nutzererklärung und startet den bestehenden
                    Prüflauf. Sie aktiviert weder Provider noch Regeln, bucht keine Ausführung und
                    verschickt keine Nachricht. B04/B05/B06/B58 und die Kalenderintegration bleiben
                    davon unbestätigt.
                  </p>
                </form>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
