"""One complete snapshot produces one complete report response."""

from uuid import UUID

from app.features.performance.domain.models import RealizedGrossReport, ReportFilters
from app.features.performance.domain.periods import report_interval
from app.features.performance.domain.report import build_report
from app.features.performance.service.reader import RealizedGrossSnapshotReader


class RealizedGrossReportService:
    def __init__(self, reader: RealizedGrossSnapshotReader) -> None:
        self._reader = reader

    async def report(self, workspace_id: UUID, filters: ReportFilters) -> RealizedGrossReport:
        report_interval(filters)
        snapshot = await self._reader.read(workspace_id, filters.report_currency)
        return build_report(snapshot, filters)
