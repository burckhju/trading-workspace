"""Domain/persistence mapping for FT-012 build slice 01."""

from app.features.learning.domain import (
    ExternalObservation,
    ExternalObservationRecordingMethod,
    ExternalObservationTradeLink,
    ExternalObservationTradeLinkVersion,
    ExternalObservationVersion,
    IdempotencyRecord,
    IdempotencyStatus,
    Lesson,
    LessonEvidenceLink,
    LessonEvidenceRelation,
    LessonReviewSignal,
    LessonReviewSignalEvidence,
    LessonState,
    LessonStateTransition,
    LessonSuggestion,
    LessonVersion,
    TradeJournal,
    TradeJournalVersion,
    TradeLinkChangeReason,
    TradeLinkStatus,
)
from app.features.learning.persistence.models import (
    ExternalObservationModel,
    ExternalObservationTradeLinkRecordModel,
    ExternalObservationTradeLinkVersionRecordModel,
    ExternalObservationVersionModel,
    IdempotencyRecordModel,
    LessonEvidenceLinkModel,
    LessonModel,
    LessonReviewSignalEvidenceRecordModel,
    LessonReviewSignalRecordModel,
    LessonStateTransitionRecordModel,
    LessonSuggestionRecordModel,
    LessonVersionModel,
    TradeJournalModel,
    TradeJournalVersionModel,
)


def trade_journal_to_model(value: TradeJournal) -> TradeJournalModel:
    return TradeJournalModel(
        id=value.id,
        workspace_id=value.workspace_id,
        trade_id=value.trade_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def trade_journal_version_to_model(value: TradeJournalVersion) -> TradeJournalVersionModel:
    return TradeJournalVersionModel(
        id=value.id,
        trade_journal_id=value.trade_journal_id,
        version=value.version,
        status=value.status.value,
        what_went_well=value.what_went_well,
        would_do_differently=value.would_do_differently,
        additional_notes=value.additional_notes,
        created_at=value.created_at,
        created_by=value.created_by,
        updated_at=value.updated_at,
        updated_by=value.updated_by,
        finalized_at=value.finalized_at,
        finalized_by=value.finalized_by,
        supersedes_version_id=value.supersedes_version_id,
    )


def lesson_to_model(value: Lesson) -> LessonModel:
    return LessonModel(
        id=value.id,
        workspace_id=value.workspace_id,
        title=value.title,
        current_version_id=value.current_version_id,
        current_state=value.current_state.value,
        created_at=value.created_at,
        created_by=value.created_by,
        updated_at=value.updated_at,
        updated_by=value.updated_by,
    )


def lesson_version_to_model(value: LessonVersion) -> LessonVersionModel:
    return LessonVersionModel(
        id=value.id,
        lesson_id=value.lesson_id,
        version=value.version,
        main_category=value.main_category,
        content=value.content,
        created_at=value.created_at,
        created_by=value.created_by,
        supersedes_version_id=value.supersedes_version_id,
    )


def lesson_evidence_link_to_model(value: LessonEvidenceLink) -> LessonEvidenceLinkModel:
    return LessonEvidenceLinkModel(
        id=value.id,
        lesson_version_id=value.lesson_version_id,
        learning_evidence_id=value.learning_evidence_id,
        relation=value.relation.value,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def lesson_state_transition_to_model(
    value: LessonStateTransition,
) -> LessonStateTransitionRecordModel:
    return LessonStateTransitionRecordModel(
        id=value.id,
        lesson_id=value.lesson_id,
        from_state=(value.from_state.value if value.from_state is not None else None),
        to_state=value.to_state.value,
        reason=value.reason,
        related_lesson_version_id=value.related_lesson_version_id,
        occurred_at=value.occurred_at,
        actor=value.occurred_by,
    )


def idempotency_to_model(value: IdempotencyRecord) -> IdempotencyRecordModel:
    return IdempotencyRecordModel(
        id=value.id,
        workspace_id=value.workspace_id,
        command_type=value.command_type,
        idempotency_key=value.idempotency_key,
        request_fingerprint=value.request_fingerprint,
        status=value.status.value,
        result_type=value.result_type,
        result_id=value.result_id,
        error_code=value.error_code,
        created_at=value.created_at,
        completed_at=value.completed_at,
    )


def lesson_from_model(value: LessonModel) -> Lesson:
    return Lesson(
        id=value.id,
        workspace_id=value.workspace_id,
        title=value.title,
        current_version_id=value.current_version_id,
        current_state=LessonState(value.current_state),
        created_at=value.created_at,
        created_by=value.created_by,
        updated_at=value.updated_at,
        updated_by=value.updated_by,
    )


def lesson_version_from_model(value: LessonVersionModel) -> LessonVersion:
    return LessonVersion(
        id=value.id,
        lesson_id=value.lesson_id,
        version=value.version,
        main_category=value.main_category,
        content=value.content,
        created_at=value.created_at,
        created_by=value.created_by,
        supersedes_version_id=value.supersedes_version_id,
    )


def lesson_evidence_link_from_model(value: LessonEvidenceLinkModel) -> LessonEvidenceLink:
    return LessonEvidenceLink(
        id=value.id,
        lesson_version_id=value.lesson_version_id,
        learning_evidence_id=value.learning_evidence_id,
        relation=LessonEvidenceRelation(value.relation),
        created_at=value.created_at,
        created_by=value.created_by,
    )


def idempotency_from_model(value: IdempotencyRecordModel) -> IdempotencyRecord:
    return IdempotencyRecord(
        id=value.id,
        workspace_id=value.workspace_id,
        command_type=value.command_type,
        idempotency_key=value.idempotency_key,
        request_fingerprint=value.request_fingerprint,
        status=IdempotencyStatus(value.status),
        result_type=value.result_type,
        result_id=value.result_id,
        error_code=value.error_code,
        created_at=value.created_at,
        completed_at=value.completed_at,
    )


def external_observation_from_model(
    value: ExternalObservationModel,
) -> ExternalObservation:
    return ExternalObservation(
        id=value.id,
        workspace_id=value.workspace_id,
        current_version_id=value.current_version_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def external_observation_version_from_model(
    value: ExternalObservationVersionModel,
) -> ExternalObservationVersion:
    return ExternalObservationVersion(
        id=value.id,
        external_observation_id=value.external_observation_id,
        version=value.version,
        underlying_id=value.underlying_id,
        product_id=value.product_id,
        source_type=value.source_type,
        source_name=value.source_name,
        external_reference=value.external_reference,
        observed_at=value.observed_at,
        recorded_at=value.recorded_at,
        imported_at=value.imported_at,
        recording_method=ExternalObservationRecordingMethod(value.recording_method),
        import_row_id=value.import_row_id,
        source_metadata=value.source_metadata,
        supersedes_version_id=value.supersedes_version_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def external_observation_trade_link_to_model(
    value: ExternalObservationTradeLink,
) -> ExternalObservationTradeLinkRecordModel:
    return ExternalObservationTradeLinkRecordModel(
        id=value.id,
        workspace_id=value.workspace_id,
        external_observation_id=value.external_observation_id,
        current_version_id=value.current_version_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def external_observation_trade_link_from_model(
    value: ExternalObservationTradeLinkRecordModel,
) -> ExternalObservationTradeLink:
    return ExternalObservationTradeLink(
        id=value.id,
        workspace_id=value.workspace_id,
        external_observation_id=value.external_observation_id,
        current_version_id=value.current_version_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def external_observation_trade_link_version_to_model(
    value: ExternalObservationTradeLinkVersion,
) -> ExternalObservationTradeLinkVersionRecordModel:
    return ExternalObservationTradeLinkVersionRecordModel(
        id=value.id,
        external_observation_trade_link_id=value.external_observation_trade_link_id,
        version=value.version,
        external_observation_version_id=value.external_observation_version_id,
        trade_id=value.trade_id,
        status=value.status.value,
        supersedes_version_id=value.supersedes_version_id,
        change_reason=value.change_reason.value,
        change_note=value.change_note,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def external_observation_trade_link_version_from_model(
    value: ExternalObservationTradeLinkVersionRecordModel,
) -> ExternalObservationTradeLinkVersion:
    return ExternalObservationTradeLinkVersion(
        id=value.id,
        external_observation_trade_link_id=value.external_observation_trade_link_id,
        version=value.version,
        external_observation_version_id=value.external_observation_version_id,
        trade_id=value.trade_id,
        status=TradeLinkStatus(value.status),
        change_reason=TradeLinkChangeReason(value.change_reason),
        created_at=value.created_at,
        created_by=value.created_by,
        supersedes_version_id=value.supersedes_version_id,
        change_note=value.change_note,
    )


def lesson_review_signal_to_model(
    value: LessonReviewSignal,
) -> LessonReviewSignalRecordModel:
    return LessonReviewSignalRecordModel(
        id=value.id,
        lesson_id=value.lesson_id,
        lesson_version_id=value.lesson_version_id,
        status=value.status.value,
        raised_at=value.raised_at,
        opened_by=value.opened_by,
        resolved_at=value.resolved_at,
        resolved_by=value.resolved_by,
        resolution=(value.resolution.value if value.resolution is not None else None),
        resulting_lesson_version_id=value.resulting_lesson_version_id,
    )


def lesson_review_signal_from_model(
    model: LessonReviewSignalRecordModel,
) -> LessonReviewSignal:
    from app.features.learning.domain import (
        LessonReviewResolution,
        LessonReviewSignalStatus,
    )

    if model.opened_by is None:
        raise ValueError("persisted lesson review signal requires opened_by")

    return LessonReviewSignal(
        id=model.id,
        lesson_id=model.lesson_id,
        lesson_version_id=model.lesson_version_id,
        status=LessonReviewSignalStatus(model.status),
        raised_at=model.raised_at,
        opened_by=model.opened_by,
        resolution=(
            LessonReviewResolution(model.resolution) if model.resolution is not None else None
        ),
        resolved_at=model.resolved_at,
        resolved_by=model.resolved_by,
        resulting_lesson_version_id=model.resulting_lesson_version_id,
    )


def lesson_review_signal_evidence_to_model(
    value: LessonReviewSignalEvidence,
) -> LessonReviewSignalEvidenceRecordModel:
    return LessonReviewSignalEvidenceRecordModel(
        lesson_review_signal_id=value.lesson_review_signal_id,
        lesson_evidence_link_id=value.lesson_evidence_link_id,
        lesson_version_id=value.lesson_version_id,
    )


def lesson_suggestion_from_model(
    model: LessonSuggestionRecordModel,
) -> LessonSuggestion:
    from app.features.learning.domain import LessonSuggestionStatus

    statement = model.suggested_statement

    return LessonSuggestion(
        id=model.id,
        workspace_id=model.workspace_id,
        status=LessonSuggestionStatus(model.status),
        proposed_title=statement,
        proposed_main_category=(model.suggested_main_category or "GENERAL"),
        proposed_content=statement,
        created_at=model.created_at,
        created_by=model.created_by,
        decided_at=model.decided_at,
        decided_by=model.decided_by,
        resulting_lesson_id=model.resulting_lesson_id,
    )
