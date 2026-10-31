/** Documentation type tests. Synthetic identities only; never execute commands. */
import type { ExecutionCurrencyResolution } from '../../../frontend/src/features/trade/types/api';
import type { RealizedGrossReport } from '../../../frontend/src/features/performance/types/api';
import type {
  AuthorityRef,
  AutomaticResolution,
  CurrencyNotice,
  ExistingDestination,
  GovernanceEvidence,
  NoticeAction,
  NoticeCause,
  NoticeContext,
  NoticeLifecycle,
  NoticePresentation,
  OwnerEvidence,
  UserNeed,
} from './contracts';

export const context = {
  workspaceKey: 'synthetic-workspace',
  subject: {
    kind: 'execution',
    id: '00000000-0000-4000-8000-000000000001',
    label: 'Synthetische Kaufbuchung',
    versionId: null,
  },
  purpose: 'execution-currency-evidence',
  relatedSubjects: [
    {
      kind: 'trade',
      id: '00000000-0000-4000-8000-000000000002',
      label: 'Synthetischer Trade',
      versionId: null,
    },
  ],
  versionPins: {},
  report: null,
  sourceIdentity: null,
  requestGeneration: 1,
  snapshotToken: 'synthetic-read-1',
} as const satisfies NoticeContext;

export const authority = {
  owner: 'trade_position',
  contract: 'execution-currency-v3',
  snapshotToken: context.snapshotToken,
  references: ['currency_resolution.source', 'currency_resolution.reason'],
} as const satisfies AuthorityRef;

export const currencyFacts = {
  currency_code: null,
  source: 'UNKNOWN',
  source_execution_ids: [],
  confirmation_ids: [],
  evidence_ids: [],
  evidence: [],
  reason: 'NO_HISTORICAL_EVIDENCE',
  resolver_version: 'execution-currency-v3',
} satisfies ExecutionCurrencyResolution;

export const destination = {
  availability: 'verified-existing',
  href: '/trade-management?trade_id=00000000-0000-4000-8000-000000000002#execution-dates',
  builder: 'existing trade booking section',
  subject: {
    kind: 'trade',
    id: '00000000-0000-4000-8000-000000000002',
    label: 'Synthetischer Trade',
    versionId: null,
  },
  granularity: 'section',
  context,
  relationshipProof: {
    owner: 'trade_position',
    contract: 'ExecutionResponse',
    snapshotToken: context.snapshotToken,
    references: [
      'execution.id=00000000-0000-4000-8000-000000000001',
      'execution.trade_id=00000000-0000-4000-8000-000000000002',
    ],
  },
} as const satisfies ExistingDestination;

export const readAction = {
  kind: 'read',
  label: 'Vorhandene Kaufbelege prüfen',
  destination,
} as const satisfies NoticeAction;

export const decisionAction = {
  kind: 'open-decision',
  label: 'Währungsbestätigung vorbereiten',
  destination,
  decision: 'confirm',
  confirmation: 'explicit-in-owner',
} as const satisfies NoticeAction;

export const currencyNotice = {
  id: 'trade_position:currency-unresolved:synthetic-execution',
  catalogRule: 'execution-currency.unresolved',
  context,
  evidence: {
    authority,
    snapshot: currencyFacts,
    conditionFields: ['source', 'reason'],
  },
  presentation: { kind: 'warning', priority: 'relevant-problem' },
  title: 'Ausführungswährung noch nicht belegt',
  cause: {
    known: true,
    explanation: 'Für diese Buchung liegt kein ausreichender historischer Nachweis vor.',
    proof: authority,
  },
  impact: 'Eine währungsabhängige Qualifikation benötigt einen gültigen Nachweis.',
  automatic: {
    kind: 'none-evidenced',
    explanation: 'Der vorhandene Resolver hat keinen ausreichenden Nachweis gefunden.',
  },
  userNeed: {
    kind: 'optional-inspection',
    explanation: 'Vorhandene Quellen können geprüft werden.',
  },
  lifecycle: {
    kind: 'active',
    change: 'uncompared',
    comparisonSnapshotToken: null,
  },
  time: {
    observedAt: null,
    checkedAt: null,
    validFrom: null,
    validTo: null,
    explanation: 'Fehlende Zeiten bleiben unbekannt.',
  },
  details: [],
  actions: [readAction],
  missingDestination: null,
} as const satisfies CurrencyNotice;

export const receiptAuthority = {
  owner: 'trade_position',
  contract: 'ExecutionCurrencyConfirmation',
  snapshotToken: 'synthetic-confirmation-receipt-2',
  references: ['confirmation.id=synthetic-confirmation-2', 'request_id=synthetic-request-2'],
} as const satisfies AuthorityRef;

export const resolvedCurrencyFacts = {
  currency_code: 'EUR',
  source: 'EXECUTION_DOCUMENT',
  source_execution_ids: [context.subject.id],
  confirmation_ids: [],
  evidence_ids: ['synthetic-document-3'],
  resolver_version: 'execution-currency-v3',
} satisfies ExecutionCurrencyResolution;

export const recoveryAuthority = {
  owner: 'trade_position',
  contract: 'execution-currency-v3',
  snapshotToken: 'synthetic-qualified-read-3',
  references: [
    'currency_resolution.source=EXECUTION_DOCUMENT',
    'evidence_ids=synthetic-document-3',
  ],
} as const satisfies AuthorityRef;

export const successWithReceipt = {
  kind: 'success',
  priority: 'normal',
  completedOperation: 'Explizite Bestätigung gespeichert',
  proof: receiptAuthority,
} as const satisfies NoticePresentation;

export const resolvedWithEvidence = {
  kind: 'resolved',
  proof: {
    authority: recoveryAuthority,
    sameConditionId: currencyNotice.id,
    checkedAt: '2026-10-30T12:00:00Z',
    resolvedImpact: 'Owner bestätigt die nun ausreichende historische Evidenz.',
  },
} as const satisfies NoticeLifecycle;

export const partialSummary = {
  status: 'PARTIAL',
  total: null,
  total_display: null,
  subtotal: '12.50',
  subtotal_display: '12.50',
  rounding_difference: '0.00',
  rounding_difference_display: '0.00',
} satisfies RealizedGrossReport['summary'];

export const emptySummary = {
  status: 'EMPTY',
  total: '0',
  total_display: '0.00',
  subtotal: null,
  subtotal_display: null,
  rounding_difference: null,
  rounding_difference_display: null,
} satisfies RealizedGrossReport['summary'];

export const separateGovernance: GovernanceEvidence = {
  approval: null,
  activation: null,
};

// Negative contracts: removing an expected error must fail the typecheck.
// @ts-expect-error A severity word is not an execution currency source.
export const domainSeverityMixup: ExecutionCurrencyResolution['source'] = 'WARNING';

// @ts-expect-error Success needs the completed operation and its evidence.
export const unprovedSuccess: NoticePresentation = {
  kind: 'success',
  priority: 'normal',
};

// @ts-expect-error A blocker must identify the operation and owner proof.
export const unprovedBlocker: NoticePresentation = {
  kind: 'blocker',
  priority: 'blocked-operation',
};

// @ts-expect-error A recovery cannot be inferred from an empty list or timestamp alone.
export const unprovedRecovery: NoticeLifecycle = { kind: 'resolved' };

// @ts-expect-error Information cannot demand a user decision.
export const urgentInformation: NoticePresentation = {
  kind: 'information',
  priority: 'decision-required',
};

export const unprovedDeterioration: NoticeLifecycle = {
  kind: 'active',
  change: 'worsened',
  // @ts-expect-error A first unqualified comparison cannot claim deterioration.
  comparisonSnapshotToken: null,
};

// @ts-expect-error Required user decisions need an operation and owner proof.
export const unprovedNeed: UserNeed = {
  kind: 'required-for-operation',
  explanation: 'Please act',
};

// @ts-expect-error A retry must be backed by a real schedule and owner proof.
export const inventedRetry: AutomaticResolution = {
  kind: 'owner-retry-scheduled',
  explanation: 'Soon',
};

// @ts-expect-error A known cause cannot omit its supporting owner evidence.
export const guessedCause: NoticeCause = {
  known: true,
  explanation: 'Probably an old listing',
};

// @ts-expect-error Decision navigation must state explicit confirmation in the owner.
export const silentDecision: NoticeAction = {
  kind: 'open-decision',
  label: 'Confirm',
  destination,
  decision: 'confirm',
};

export const hiddenPost: NoticeAction = {
  kind: 'read',
  label: 'Open',
  destination,
  // @ts-expect-error Notice actions do not accept write methods or request payloads.
  method: 'POST',
};

export const mutationCallback: NoticeAction = {
  kind: 'read',
  label: 'Open',
  destination,
  // @ts-expect-error Notice actions cannot execute mutations.
  onExecute: () => undefined,
};

export const unavailableTarget = {
  availability: 'integration-required',
  explanation: 'Exact source-check route missing',
  owner: 'UX-2',
} as const;
export const speculativeAction: NoticeAction = {
  kind: 'read',
  label: 'Open source',
  // @ts-expect-error An integration request is not a usable navigation destination.
  destination: unavailableTarget,
};

// @ts-expect-error A response must be tied to a generation and snapshot, not only an ID.
export const incompleteContext: NoticeContext = {
  workspaceKey: 'synthetic',
  subject: context.subject,
};

export const invalidCurrencyFields: OwnerEvidence<ExecutionCurrencyResolution> = {
  authority,
  snapshot: currencyFacts,
  // @ts-expect-error No copied/imagined domain field may replace real DTO keys.
  conditionFields: ['risk_approval_status'],
};

export function approvalIsNotActivation(
  approval: NonNullable<GovernanceEvidence['approval']>,
): void {
  // @ts-expect-error Approval is not a RuntimeActivation result.
  const activation: GovernanceEvidence['activation'] = approval;
  void activation;
}

export function immutableEvidence(value: CurrencyNotice): void {
  // @ts-expect-error Presentation may not turn a read into user confirmation.
  value.evidence.snapshot.source = 'USER_CONFIRMED';
}

export function immutableSources(value: CurrencyNotice): void {
  // @ts-expect-error Presentation must not add source evidence to its input.
  value.evidence.snapshot.evidence_ids?.push('invented-evidence');
}

// @ts-expect-error Money remains a domain decimal string or null, not a JS number fallback.
export const unknownTotalAsNumber: RealizedGrossReport['summary']['total'] = 0;
