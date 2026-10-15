"""Only synthetic prices for an explicitly allowed, fresh CI journal browser stack."""

import asyncio
import os
import sys
from uuid import UUID
from sqlalchemy.engine import make_url
from tests.integration.backend.learning.test_journal_write_postgres import seed_prices

if __name__ == "__main__":
    assert os.environ.get("CI") == "true"
    assert os.environ.get("JOURNAL_E2E_WRITES_ALLOWED") == "1"
    url = os.environ["TRADING_WORKSPACE_TEST_DATABASE_URL"]
    target = make_url(url)
    assert target.database == "trading_workspace_test"
    assert target.host in ("127.0.0.1", "localhost") and target.port == 25432
    listing = UUID(sys.argv[1])
    asyncio.run(seed_prices(url, listing))
