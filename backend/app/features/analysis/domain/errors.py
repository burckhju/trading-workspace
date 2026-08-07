"""Domain and application errors for market analysis."""


class AnalysisError(Exception):
    """Base error with stable machine-readable code."""

    code = "analysis_error"


class InvalidAnalysisParameters(AnalysisError):
    code = "invalid_analysis_parameters"


class AnalysisNotFound(AnalysisError):
    code = "analysis_not_found"


class AnalysisDataUnavailable(AnalysisError):
    code = "analysis_data_unavailable"


class AnalysisConflict(AnalysisError):
    code = "analysis_conflict"


class AnalysisExecutionFailed(AnalysisError):
    code = "analysis_execution_failed"
