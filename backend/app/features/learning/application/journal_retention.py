"""Journal history retention contract shared with explicit destructive consumers."""


class JournalHistoryProtectedError(ValueError):
    code = "JOURNAL_HISTORY_PROTECTED"
