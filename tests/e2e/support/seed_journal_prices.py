"""Only synthetic prices for an explicitly allowed, fresh CI journal browser stack."""

import asyncio
import os
import sys
from uuid import UUID

from journal_database_guard import verify

from tests.integration.backend.learning.test_journal_write_postgres import seed_prices

if __name__ == "__main__":
    # Independent host read verifies this run's exact database before fixture writes.
    asyncio.run(verify())
    url = os.environ["TRADING_WORKSPACE_TEST_DATABASE_URL"]
    listing = UUID(sys.argv[1])
    start, stop = (int(value) for value in sys.argv[2:]) if len(sys.argv) == 4 else (0, 20)
    if not 0 <= start < stop <= 20:
        raise ValueError("Synthetic fixture range must remain within its 20 defined observations")
    asyncio.run(seed_prices(url, listing, start=start, stop=stop))
