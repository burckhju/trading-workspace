"""The read model is the complete response; FastAPI serializes dates/UUIDs only.

All financial raw/display fields are already exact decimal strings from the
backend. The response has no monetary JSON numbers and no date-only clock anchor.
Closed-trade statistics are an additive nested model with their own definition
and an explicit reference to the unchanged report basis.
"""

from app.features.performance.domain.closed_models import ClosedTradeReport
from app.features.performance.domain.models import RealizedGrossReport

RealizedGrossReportResponse = RealizedGrossReport
ClosedTradeReportResponse = ClosedTradeReport
