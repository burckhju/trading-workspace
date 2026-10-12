import { environment } from '../../../services/environment';
import { requestJson } from '../../market/services/http';
import type { IvModelForm, IvModelResult } from '../types/iv';

export const ivApi = {
  preview: (form: IvModelForm, signal?: AbortSignal) =>
    requestJson<IvModelResult>(
      `${environment.apiBaseUrl}/api/v1/position-monitoring/risk/iv/model-preview`,
      {
        method: 'POST',
        signal,
        body: {
          basis: 'HYPOTHETICAL_ASSUMPTIONS',
          product_type: 'VANILLA_WARRANT',
          exercise_style: form.scope,
          direction: form.direction,
          currency: form.currency,
          underlying_currency: form.currency,
          strike_currency: form.currency,
          quanto: false,
          dividend_model: 'CONTINUOUS_YIELD',
          ratio_convention: 'UNDERLYING_UNITS_PER_WARRANT',
          spot: form.spot,
          strike: form.strike,
          ratio: form.ratio,
          remaining_days: form.remaining_days,
          iv_percent: form.mode === 'iv' ? form.iv_percent : null,
          calibration_price: form.mode === 'price' ? form.calibration_price : null,
          rate_percent: form.rate_percent,
          dividend_yield_percent: form.dividend_yield_percent,
          scenario: {
            quantity: form.quantity,
            underlying_change_percent: form.underlying_change_percent,
            iv_change_pp: form.iv_change_pp,
            elapsed_days: form.elapsed_days,
          },
        },
      },
    ),
};

const labels: Record<string, string> = {
  PROVIDER_IV_AND_GREEKS_NOT_INGESTED:
    'Die angebundenen Datenverträge liefern keine IV oder Greeks.',
  SYNCHRONIZED_UNDERLYING_QUOTE_MISSING:
    'Ein Basiswertkurs mit passendem Originalzeitpunkt fehlt. Tageskurse ersetzen ihn nicht.',
  RATE_AND_DIVIDEND_ASSUMPTIONS_MISSING: 'Zins- und Dividendenannahmen sind nicht hinterlegt.',
  SESSION_CALENDAR_UNVERIFIED_NO_AGE_EXTENSION:
    'Handelssitzung und Feiertagskalender sind nicht verifiziert. Bestehende Altersgrenzen gelten auch nach Marktschluss; keine automatische Verlängerung.',
  VANILLA_PRODUCT_TYPE_UNVERIFIED: 'Klassischer Vanilla-Produkttyp ist nicht bestätigt.',
  EXERCISE_STYLE_UNKNOWN: 'Europäische oder amerikanische Ausübung ist unbekannt.',
  QUANTO_STATUS_UNKNOWN: 'FX-/Quanto-Eigenschaften sind nicht bestätigt.',
  RATIO_CONVENTION_UNVERIFIED: 'Die Bezugsverhältnis-Konvention ist nicht bestätigt.',
  MATURITY_MISSING: 'Fälligkeit fehlt.',
  MATURITY_REACHED_OR_TODAY: 'Fälligkeit erreicht oder heute; Bewertungszeitpunkt nicht gesichert.',
  EXACT_EXPIRY_TIME_UNVERIFIED:
    'Der genaue Ausübungs-/Bewertungszeitpunkt am Fälligkeitstag fehlt.',
  WARRANT_QUOTE_MISSING: 'Kein qualifizierter gespeicherter Optionsscheinkurs.',
  QUOTE_PROVENANCE_INCOMPLETE: 'Quelle oder bestätigte Kursroute fehlt.',
  REFERENCE_PRICE_NOT_CURRENT_IV_BASIS: 'Ein Referenzkurs belegt keine aktuelle handelbare Quote.',
  MID_REQUIRES_TWO_SIDED_QUOTE: 'Ein Mittelkurs erfordert ein gültiges Geld-/Briefpaar.',
  QUOTE_RECEIPT_UNKNOWN: 'Abrufzeitpunkt fehlt.',
  QUOTE_RECEIPT_INVALID: 'Abrufzeitpunkt ist unplausibel oder ohne Zeitzone.',
  QUOTE_AGE_POLICY_UNKNOWN: 'Zulässiges Alter dieser Kursroute ist unbekannt.',
  QUOTE_TIME_IN_FUTURE: 'Originalkurszeit liegt in der Zukunft.',
  VALUATION_CURRENCY_UNKNOWN: 'Produkt-, Basiswert- oder Basispreiswährung fehlt.',
  FX_OR_QUANTO_UNSUPPORTED: 'Währungsumrechnung und Quanto werden noch nicht modelliert.',
  UNSUPPORTED_PRODUCT_OR_EXERCISE: 'Nur europäische Vanilla-Calls und -Puts werden unterstützt.',
  MODEL_INPUT_OUT_OF_RANGE: 'Eingaben außerhalb des dokumentierten Modellbereichs.',
  SCENARIO_INPUT_OUT_OF_RANGE: 'Szenario außerhalb des dokumentierten Eingabebereichs.',
  SCENARIO_HORIZON_INVALID: 'Der Horizont muss zwischen heute und der Fälligkeit liegen.',
  CHOOSE_IV_OR_HYPOTHETICAL_PRICE: 'Genau eine IV- oder Preisannahme ist erforderlich.',
  IV_PRICE_OR_MATURITY_INVALID: 'Preis und Restlaufzeit müssen für eine IV-Lösung positiv sein.',
  PRICE_OUTSIDE_MODEL_BOUNDS: 'Die Preisannahme verletzt die Preisgrenzen dieses Modells.',
  TIME_VALUE_TOO_SMALL: 'Zu wenig Zeitwert für eine belastbare IV-Schätzung.',
  IV_NOT_BRACKETED: 'Keine IV-Lösung im numerischen Bereich 0,0001 % bis 500 %.',
  VEGA_TOO_SMALL: 'Vega fehlt oder ist zu klein für eine belastbare Sensitivität/IV-Schätzung.',
  SHORT_MATURITY_MODEL_SENSITIVE: 'Unter sieben Tagen Restlaufzeit: besonders modellabhängig.',
  LARGE_IV_CHANGE_FULL_REVALUATION_ONLY:
    'IV-Änderung über fünf Prozentpunkte oder über 25 % der Ausgangs-IV: lineare Näherung ausgesetzt, vollständig neu bewertet.',
  NO_QUALIFIED_IV_HISTORY:
    'Keine qualifizierte IV-Historie; Veränderung, Perzentil und Rank fehlen.',
  NO_VERIFIED_EVENT_SOURCE:
    'Keine verifizierte Ereignisquelle angebunden; kein Ereignis nachgewiesen.',
};

export const ivLabel = (code: string) => labels[code];
