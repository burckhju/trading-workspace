"""The read model is the complete response; FastAPI serializes dates/UUIDs only.

All financial raw/display fields are already exact decimal strings from the
backend. The response has no monetary JSON numbers and no date-only clock anchor.
"""

from app.features.performance.domain.closed_models import ClosedTradeReport
from app.features.performance.domain.models import RealizedGrossReport

RealizedGrossReportResponse = RealizedGrossReport
ClosedTradeReportResponse = ClosedTradeReport
