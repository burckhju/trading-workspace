/**
 * UX-3 proposal, documentation only. No runtime imports or implementation.
 * Domain owners keep authority; these types describe presentation inputs.
 * See notice-contract.md for runtime validation that types cannot prove.
 */
import type { ExecutionCurrencyResolution } from '../../../frontend/src/features/trade/types/api';
import type {
  ClosedTradeItem,
  ClosedTradeReport,
  ClosedTradeStatistics,
  RealizedGrossItem,
  RealizedGrossReport,
} from '../../../frontend/src/features/performance/types/api';
import type { ApiErrorResponse } from '../../../frontend/src/features/market/types/api';
import type { TradePlanVersionResponse } from '../../../frontend/src/features/trade_plan/types/api';
import type { ProductEvaluationResponse } from '../../../frontend/src/features/product_selection/types/api';
import type { Ft011MaterializationStatus } from '../../../frontend/src/features/learning/types/materialization';
import type { ProposalApprovalResult } from '../../../frontend/src/features/model/types/proposalApproval';
import type { RuntimeActivation } from '../../../frontend/src/features/model/types/runtimeActivation';

export type DeepReadonly<T> = T extends object
  ? { readonly [K in keyof T]: DeepReadonly<T[K]> }
  : T;

/** Only a context-validated existing object may be a navigation destination. */
export interface KnownSubjectRef {
  readonly identity: 'known-object';
  readonly kind: string;
  readonly id: string;
  readonly label: string;
  readonly versionId: string | null;
}

/** A form/attempt can be known before its prospective object has an identity. */
export interface OperationSubjectRef {
  readonly identity: 'operation-context';
  readonly operation: string;
  readonly label: string;
  readonly parent: KnownSubjectRef | null;
  readonly id?: never;
  readonly versionId?: never;
}

export type SubjectRef = KnownSubjectRef | OperationSubjectRef;

/** The existing report definitions identify different financial populations. */
export interface RealizedNoticeReportContext<BasisId extends string = string> {
  readonly kind: 'realized-gross';
  readonly definitionVersion: 'realized-gross-sell-v2';
  readonly filters: Readonly<RealizedGrossReport['filters']>;
  readonly basisId: BasisId;
  readonly validation: {
    readonly reportValidator: 'verifyRealizedReport';
    readonly proof: AuthorityRef;
  };
}

export interface ClosedNoticeReportContext<BasisId extends string = string> {
  readonly kind: 'closed-trades';
  readonly definitionVersion: 'closed-trade-gross-v1';
  readonly filters: Readonly<ClosedTradeReport['filters']>;
  readonly basisId: BasisId;
  readonly validation: {
    readonly reportValidator: 'verifyClosedReport';
    readonly proof: AuthorityRef;
  };
}

export type PerformanceNoticeReportContext<BasisId extends string = string> =
  | RealizedNoticeReportContext<BasisId>
  | ClosedNoticeReportContext<BasisId>;

/** Local validated read context, never an API/DB status or a trusted URL claim. */
export interface NoticeContext<
  ReportContext extends
    PerformanceNoticeReportContext | null = PerformanceNoticeReportContext | null,
> {
  readonly workspaceKey: string;
  readonly subject: SubjectRef;
  readonly relatedSubjects: readonly KnownSubjectRef[];
  readonly purpose: string;
  readonly versionPins: Readonly<Record<string, string>>;
  readonly report: ReportContext;
  readonly sourceIdentity: string | null;
  readonly requestGeneration: number;
  readonly snapshotToken: string;
}

export interface AuthorityRef {
  readonly owner: string;
  readonly contract: string;
  readonly snapshotToken: string;
  /** Original DTO field paths/IDs; no private raw payload or secret URL. */
  readonly references: readonly string[];
}

/** Original owner DTO and fields, rather than a cloned list of domain states. */
export interface OwnerEvidence<Facts extends object> {
  readonly authority: AuthorityRef;
  readonly snapshot: DeepReadonly<Facts>;
  readonly conditionFields: readonly (keyof Facts & string)[];
}

export type NoticeCause =
  | {
      readonly known: true;
      readonly explanation: string;
      readonly proof: AuthorityRef;
    }
  | { readonly known: false; readonly explanation: string };

export interface ExistingDestination {
  readonly availability: 'verified-existing';
  readonly href: string;
  readonly builder: string;
  readonly subject: KnownSubjectRef;
  readonly granularity: 'object' | 'section' | 'version';
  /** Source context; destination may be a proven parent (execution -> trade). */
  readonly context: NoticeContext;
  readonly relationshipProof: AuthorityRef;
}

export interface UnavailableDestination {
  readonly availability: 'integration-required';
  readonly explanation: string;
  readonly owner: 'UX-2';
}

/** Both variants only navigate. Writes remain in explicit owner workflows. */
export type NoticeAction =
  | {
      readonly kind: 'read';
      readonly label: string;
      readonly destination: ExistingDestination;
    }
  | {
      readonly kind: 'open-decision';
      readonly label: string;
      readonly destination: ExistingDestination;
      readonly decision: 'confirm' | 'correct' | 'review' | 'approve';
      readonly confirmation: 'explicit-in-owner';
    };

export type UserNeed =
  | { readonly kind: 'none'; readonly explanation: string }
  | { readonly kind: 'optional-inspection'; readonly explanation: string }
  | {
      readonly kind: 'required-for-operation';
      readonly operation: string;
      readonly explanation: string;
      readonly proof: AuthorityRef;
    };

export type AutomaticResolution =
  | { readonly kind: 'none-evidenced'; readonly explanation: string }
  | {
      readonly kind: 'owner-result-reused';
      readonly explanation: string;
      readonly proof: AuthorityRef;
    }
  | {
      readonly kind: 'owner-retry-scheduled';
      readonly explanation: string;
      readonly notBefore: string;
      readonly proof: AuthorityRef;
    };

/** A proof reference is necessary, not sufficient: owner validation is mandatory. */
export interface ResolutionProof {
  readonly authority: AuthorityRef;
  readonly sameConditionId: string;
  readonly checkedAt: string;
  readonly resolvedImpact: string;
}

export type NoticeLifecycle =
  | {
      readonly kind: 'active';
      readonly change: 'uncompared';
      readonly comparisonSnapshotToken: null;
    }
  | {
      readonly kind: 'active';
      readonly change: 'new-in-session' | 'unchanged' | 'worsened';
      readonly comparisonSnapshotToken: string;
      readonly comparisonProof: AuthorityRef;
    }
  | { readonly kind: 'resolved'; readonly proof: ResolutionProof }
  | {
      readonly kind: 'historical';
      readonly occurredAt: string | null;
      readonly historicalContext: string;
    };

export type NoticePresentation =
  | {
      readonly kind: 'information';
      readonly priority: 'data-quality-information' | 'normal';
    }
  | {
      readonly kind: 'warning';
      readonly priority: 'decision-required' | 'relevant-problem' | 'data-quality-information';
    }
  | {
      readonly kind: 'blocker';
      readonly priority: 'blocked-operation';
      readonly blockedOperation: string;
      readonly proof: AuthorityRef;
    }
  | {
      readonly kind: 'error';
      readonly priority: 'blocked-operation' | 'decision-required' | 'relevant-problem';
      readonly failedOperation: string;
      readonly proof: AuthorityRef;
    }
  | {
      readonly kind: 'success';
      readonly priority: 'normal';
      readonly completedOperation: string;
      readonly proof: AuthorityRef;
    };

export interface NoticeTimeContext {
  readonly observedAt: string | null;
  readonly checkedAt: string | null;
  readonly validFrom: string | null;
  readonly validTo: string | null;
  readonly explanation: string;
}

export interface DetailRow {
  readonly label: string;
  readonly value: string;
  readonly proof: AuthorityRef | null;
}

interface NoticeContent<Facts extends object, Context extends NoticeContext> {
  /** Also excludes a changed global report basis when this cause is unchanged. */
  readonly id: string;
  readonly catalogRule: string;
  readonly context: Context;
  readonly evidence: OwnerEvidence<Facts>;
  readonly title: string;
  readonly cause: NoticeCause;
  readonly impact: string;
  readonly automatic: AutomaticResolution;
  readonly lifecycle: NoticeLifecycle;
  readonly time: NoticeTimeContext;
  readonly details: readonly DetailRow[];
  readonly actions: readonly NoticeAction[];
  readonly missingDestination: UnavailableDestination | null;
}

/** Information/success alone cannot establish a mandatory user decision. */
export type Notice<
  Facts extends object,
  Context extends NoticeContext = NoticeContext,
> = NoticeContent<Facts, Context> &
  (
    | {
        readonly presentation: Extract<NoticePresentation, { kind: 'information' | 'success' }>;
        readonly userNeed: Exclude<UserNeed, { kind: 'required-for-operation' }>;
      }
    | {
        readonly presentation: Exclude<NoticePresentation, { kind: 'information' | 'success' }>;
        readonly userNeed: UserNeed;
      }
  );

export interface NoticeCardProps<Facts extends object> {
  readonly notice: Notice<Facts>;
  readonly headingLevel: 2 | 3 | 4;
  readonly detailsId: string;
  readonly onNavigate: (destination: ExistingDestination) => void;
}

export interface NoticeGroup {
  readonly id: string;
  readonly title: string;
  readonly noticeIds: readonly string[];
  readonly affectedSubjects: readonly SubjectRef[];
  readonly primaryNoticeId: string;
}

export interface NoticeSummaryProps {
  /** Host deduplicates, orders and counts distinct subjects before rendering. */
  readonly groups: readonly NoticeGroup[];
  readonly onOpenGroup: (groupId: string) => void;
}

export interface NoticeDetailsProps {
  readonly id: string;
  readonly rows: readonly DetailRow[];
  readonly time: NoticeTimeContext;
}

export interface ContextActionLinkProps {
  readonly action: NoticeAction;
  readonly onNavigate: (destination: ExistingDestination) => void;
}

export interface NoticeStatusProps {
  readonly presentation: NoticePresentation;
  readonly label: string;
  readonly time: NoticeTimeContext | null;
}

/** Examples bind to existing public types; they introduce no domain enums. */
export type CurrencyNotice = Notice<ExecutionCurrencyResolution>;
export type PlanNotice = Notice<TradePlanVersionResponse>;
export type ProductEvaluationNotice = Notice<ProductEvaluationResponse>;
export type MaterializationNotice = Notice<Ft011MaterializationStatus>;

/**
 * Read-only diagnostics from the existing HTTP/response-validation owner.
 * An API response, including a structured 503, does not classify a write outcome.
 * No raw Error.cause, secret request payload or retry callback is transported.
 */
export type OwnerFailureSource =
  | {
      readonly kind: 'api';
      readonly status: number;
      readonly response: DeepReadonly<ApiErrorResponse>;
    }
  | { readonly kind: 'transport'; readonly message: string }
  | { readonly kind: 'context-validation'; readonly message: string };

export interface OwnerOperationRef<Effect extends 'read' | 'write'> {
  readonly operation: string;
  readonly effect: Effect;
  readonly context: NoticeContext;
  /** Existing owner symbol/contract; never a new UX-3 classification function. */
  readonly classifier: string;
  readonly classificationProof: AuthorityRef;
}

/** These variants describe already-classified owner facts, not a state machine. */
export interface ReadFailureEvidence {
  readonly classification: 'read-failed';
  readonly operation: OwnerOperationRef<'read'>;
  readonly error: OwnerFailureSource;
  readonly receipt?: never;
  readonly retry?: never;
}

export interface WriteRejectionEvidence {
  readonly classification: 'write-rejected';
  readonly operation: OwnerOperationRef<'write'>;
  readonly error: OwnerFailureSource;
  readonly receipt?: never;
  readonly retry?: never;
}

export interface WriteUnknownEvidence {
  readonly classification: 'write-unknown';
  readonly operation: OwnerOperationRef<'write'>;
  readonly error: OwnerFailureSource;
  readonly receipt?: never;
  readonly retry?: never;
}

export interface ReceiptReadbackFailureEvidence<Receipt extends object> {
  readonly classification: 'receipt-confirmed-readback-failed';
  readonly operation: OwnerOperationRef<'write'>;
  /** The original receipt confirms the command, not a new/current read snapshot. */
  readonly receipt: OwnerEvidence<Receipt>;
  readonly readback: ReadFailureEvidence;
  readonly relationshipProof: AuthorityRef;
  readonly retry?: never;
}

type FailureNotice<Facts extends object> = Notice<Facts> & {
  /** A separate receipt notice may be successful; the read failure remains visible. */
  readonly presentation: Exclude<NoticePresentation, { kind: 'success' }>;
};

export type ApiFailureNotice<Receipt extends object = object> =
  | FailureNotice<ReadFailureEvidence>
  | FailureNotice<WriteRejectionEvidence>
  | FailureNotice<WriteUnknownEvidence>
  | FailureNotice<ReceiptReadbackFailureEvidence<Receipt>>;

/**
 * No variant grants a retry. Journal's explicit frozen-attempt retry, its unknown
 * outcome surviving GET/discard, and other owners' lack of that guarantee stay
 * in their existing workflows. The adapter must verify the named classification;
 * TypeScript cannot infer it from a numeric HTTP status or a message string.
 */

interface GovernanceReadContext<ModelId extends string> {
  readonly workspaceKey: string;
  readonly modelId: ModelId;
  readonly versionPins: Readonly<Record<string, string>>;
  readonly requestGeneration: number;
}

export interface ApprovalReadContext<ModelId extends string = string>
  extends GovernanceReadContext<ModelId> {
  readonly reader: 'proposalApprovalClient.getForProposal';
  readonly proposalId: string;
}

export interface ActivationReadContext<ModelId extends string = string>
  extends GovernanceReadContext<ModelId> {
  readonly reader: 'runtimeActivationClient.getCurrent';
  /** This selected approved target need not be the currently active version. */
  readonly approvedVersionId: string | null;
}

/** Each reader owns its own lifecycle, timestamps, generation and proof. */
export type GovernanceRead<Value extends object, Context extends object> =
  | {
      readonly state: 'not-read';
      readonly context: Context;
      readonly readStartedAt: null;
      readonly readCompletedAt: null;
      readonly snapshotToken: null;
      readonly value?: never;
    }
  | {
      readonly state: 'loading';
      readonly context: Context;
      readonly readStartedAt: string | null;
      readonly readCompletedAt: null;
      readonly snapshotToken: null;
      readonly value?: never;
    }
  | {
      readonly state: 'ready';
      readonly context: Context;
      readonly readStartedAt: string | null;
      readonly readCompletedAt: string | null;
      readonly snapshotToken: string;
      readonly authority: AuthorityRef;
      /** Only a successful, context-validated read can establish absence. */
      readonly value: DeepReadonly<Value> | null;
    }
  | {
      readonly state: 'error';
      readonly context: Context;
      readonly readStartedAt: string | null;
      readonly readCompletedAt: string | null;
      readonly snapshotToken: null;
      readonly authority: AuthorityRef;
      readonly error: OwnerFailureSource;
      readonly value?: never;
    };

type ApprovalForModel<ModelId extends string> = ProposalApprovalResult & {
  readonly model_version: ProposalApprovalResult['model_version'] & {
    readonly model_id: ModelId;
  };
};

type ActivationForModel<ModelId extends string> = RuntimeActivation & {
  readonly model_id: ModelId;
  readonly model_version: RuntimeActivation['model_version'] & {
    readonly model_id: ModelId;
  };
};

/**
 * Original results and independent read states; no atomic governance snapshot.
 * Runtime checks still verify proposal/model/version IDs and stale generations.
 * Missing read timestamps remain null; approval/activation event times stay in
 * their original DTOs and must not be substituted for read times.
 */
export interface GovernanceEvidence<ModelId extends string = string> {
  readonly modelId: ModelId;
  readonly approval: GovernanceRead<ApprovalForModel<ModelId>, ApprovalReadContext<ModelId>>;
  readonly activation: GovernanceRead<ActivationForModel<ModelId>, ActivationReadContext<ModelId>>;
}

export type GovernanceNotice<ModelId extends string = string> = Notice<GovernanceEvidence<ModelId>>;

/** Narrow existing DTO fields after the existing feature validators succeed. */
export type RealizedReportSnapshot<BasisId extends string = string> = RealizedGrossReport & {
  readonly definition_version: 'realized-gross-sell-v2';
  readonly basis: RealizedGrossReport['basis'] & { readonly id: BasisId };
};

export type ClosedStatisticsSnapshot<BasisId extends string = string> = ClosedTradeStatistics & {
  readonly definition_version: 'closed-trade-statistics-v1';
  readonly report_basis_id: BasisId;
};

export type ClosedReportSnapshot<BasisId extends string = string> = ClosedTradeReport & {
  readonly definition_version: 'closed-trade-gross-v1';
  readonly basis: ClosedTradeReport['basis'] & { readonly id: BasisId };
  readonly statistics: ClosedStatisticsSnapshot<BasisId>;
};

export type PerformanceReportNotice<BasisId extends string = string> =
  | Notice<RealizedReportSnapshot<BasisId>, NoticeContext<RealizedNoticeReportContext<BasisId>>>
  | Notice<ClosedReportSnapshot<BasisId>, NoticeContext<ClosedNoticeReportContext<BasisId>>>;

export interface RealizedItemEvidence<BasisId extends string = string> {
  readonly report: RealizedReportSnapshot<BasisId>;
  readonly item: RealizedGrossItem;
  /** Items have no own basis field: the owning response supplies this binding. */
  readonly itemBasisId: BasisId;
  readonly membershipProof: AuthorityRef;
}

export interface ClosedItemEvidence<BasisId extends string = string> {
  readonly report: ClosedReportSnapshot<BasisId>;
  readonly item: ClosedTradeItem;
  readonly itemBasisId: BasisId;
  readonly membershipProof: AuthorityRef;
}

export type PerformanceItemNotice<BasisId extends string = string> =
  | Notice<RealizedItemEvidence<BasisId>, NoticeContext<RealizedNoticeReportContext<BasisId>>>
  | Notice<ClosedItemEvidence<BasisId>, NoticeContext<ClosedNoticeReportContext<BasisId>>>;

export interface ClosedStatisticsEvidence<BasisId extends string = string> {
  readonly report: ClosedReportSnapshot<BasisId>;
  /** Must be this response's statistics, not a separately assembled calculation. */
  readonly statistics: ClosedStatisticsSnapshot<BasisId>;
  readonly validation: {
    readonly statisticsValidator: 'verifyClosedStatistics';
    readonly proof: AuthorityRef;
  };
}

export type ClosedTradeStatisticsNotice<BasisId extends string = string> = Notice<
  ClosedStatisticsEvidence<BasisId>,
  NoticeContext<ClosedNoticeReportContext<BasisId>>
>;

/**
 * Literal basis parameters expose mismatches in type examples. Arbitrary server
 * strings still require verifyRealizedReport / verifyClosedReport and, for
 * statistics, verifyClosedStatistics. The adapter also verifies item membership,
 * subject and current request generation; no new financial validator is defined
 * here. Basis is validity evidence, never the stable identity of a local cause.
 */

// RefreshCheck is private in MarketDataRefreshPanel.tsx at the audited commit.
// A follow-up must expose its existing owner read contract before a typed adapter.
// Do not copy its enums here or mistake qualified_success for HTTP reachability.
