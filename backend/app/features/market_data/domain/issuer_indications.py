"""Shared selection and monitoring contracts for verified issuer indications.

The policy identifies the permitted use of a quote, not a claim about its freshness.
Date/time uncertainty and the monitoring receipt-age checks remain mandatory.
"""

ISSUER_INDICATIONS = {
    "JPMORGAN": (
        "OFFICIAL_ISSUER_INDICATION_TIME_ONLY",
        "DATE_AND_TIMEZONE_UNKNOWN",
        "JPMORGAN_ISSUER_INDICATION_V1",
        "QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
    ),
    "MORGAN_STANLEY": (
        "OFFICIAL_ISSUER_INDICATION_LOCAL_DATETIME",
        "LOCAL_DATETIME_TIMEZONE_UNKNOWN",
        "MORGAN_STANLEY_ISSUER_INDICATION_V1",
        "QUOTE_TIMEZONE_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
    ),
}
