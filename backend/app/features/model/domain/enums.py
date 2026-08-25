"""Lifecycle enums for FT-013 controlled model governance."""

from enum import StrEnum


class ModelVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class HypothesisStatus(StrEnum):
    OPEN = "OPEN"
    PROPOSED = "PROPOSED"
    CLOSED = "CLOSED"


class ProposalStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"


class ValidationMethod(StrEnum):
    RETROSPECTIVE = "RETROSPECTIVE"


class ValidationConclusion(StrEnum):
    SUPPORTS = "SUPPORTS"
    INCONCLUSIVE = "INCONCLUSIVE"
    CONTRADICTS = "CONTRADICTS"
