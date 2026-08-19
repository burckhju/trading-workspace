#!/usr/bin/env bash

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

COMPOSE=(docker compose --env-file docker/.env -f docker/compose.yml)

PASS=0
FAIL=0
SKIP=0

section() {
    printf '\n============================================================\n'
    printf '%s\n' "$1"
    printf '============================================================\n'
}

ok() {
    printf 'PASS  %s\n' "$1"
    PASS=$((PASS + 1))
}

fail() {
    printf 'FAIL  %s\n' "$1"
    FAIL=$((FAIL + 1))
}

skip() {
    printf 'SKIP  %s\n' "$1"
    SKIP=$((SKIP + 1))
}

run_gate() {
    local name="$1"
    shift

    section "$name"

    if "$@"; then
        ok "$name"
        return 0
    fi

    fail "$name"
    return 1
}


section "SPRINT 11 – FT-011 QUALIFICATION"

printf 'Repository: %s\n' "$ROOT"
printf 'Zeit:       %s\n' "$(date -Is)"


# ------------------------------------------------------------
# 1. Alembic
# ------------------------------------------------------------

section "1. ALEMBIC HEAD"

if (
    cd backend &&
    .venv/bin/alembic heads
); then
    ok "Alembic heads"
else
    fail "Alembic heads"
fi


# ------------------------------------------------------------
# 2. Backend complete quality gate
# ------------------------------------------------------------

section "2. BACKEND GATE"

if bash scripts/check-backend.sh; then
    ok "Backend complete gate"
else
    fail "Backend complete gate"
fi


# ------------------------------------------------------------
# 3. FT-011 unit tests
# ------------------------------------------------------------

section "3. FT-011 UNIT TESTS"

if PYTHONPATH=backend \
    backend/.venv/bin/python -m pytest \
    tests/unit/backend/features/post_trade \
    -q
then
    ok "FT-011 unit tests"
else
    fail "FT-011 unit tests"
fi


# ------------------------------------------------------------
# 4. FT-011 PostgreSQL integration
# ------------------------------------------------------------

section "4. FT-011 POSTGRESQL INTEGRATION"

if PYTHONPATH=backend:tests/integration/backend/post_trade \
    backend/.venv/bin/python -m pytest \
    tests/integration/backend/post_trade \
    -q
then
    ok "FT-011 PostgreSQL integration"
else
    fail "FT-011 PostgreSQL integration"
fi


# ------------------------------------------------------------
# 5. Test database isolation
# ------------------------------------------------------------

section "5. TEST DATABASE ISOLATION"

if "${COMPOSE[@]}" ps database >/dev/null 2>&1; then

    COUNTS="$(
        "${COMPOSE[@]}" exec -T database sh -lc '
        psql \
          -v ON_ERROR_STOP=1 \
          -U "$POSTGRES_USER" \
          -d trading_workspace_test \
          -At \
          -c "
        SELECT count(*) FROM post_trade_observations
        UNION ALL
        SELECT count(*) FROM exit_reviews
        UNION ALL
        SELECT count(*) FROM exit_review_versions;
        "
        ' 2>/dev/null
    )"

    if [ "$COUNTS" = $'0\n0\n0' ]; then
        printf '%s\n' "$COUNTS" | nl -ba
        ok "FT-011 test tables empty"
    else
        printf 'Unexpected row counts:\n%s\n' "$COUNTS"
        fail "FT-011 test database isolation"
    fi

else
    skip "PostgreSQL isolation – Docker database unavailable"
fi


# ------------------------------------------------------------
# 6. Frontend gate
# ------------------------------------------------------------

section "6. FRONTEND GATE"

if [ -f scripts/check-frontend.sh ]; then
    if bash scripts/check-frontend.sh; then
        ok "Frontend complete gate"
    else
        fail "Frontend complete gate"
    fi
else
    skip "Frontend gate – scripts/check-frontend.sh missing"
fi


# ------------------------------------------------------------
# 7. S11 acceptance matrix
# ------------------------------------------------------------

section "7. ACCEPTANCE MATRIX"

MATRIX="docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md"

if [ -f "$MATRIX" ]; then
    RESULT="$(
        python3 - "$MATRIX" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

expected = {
    f"AT-S11-{number:03d}"
    for number in range(1, 36)
}

found = set(re.findall(r"AT-S11-\d{3}", text))

rows = [
    line
    for line in text.splitlines()
    if line.startswith("| AT-S11-")
]

valid = (
    found == expected
    and len(rows) == 35
    and all(row.rstrip().endswith("| PASS |") for row in rows)
)

print("PASS" if valid else "FAIL")
PY
    )"

    if [ "$RESULT" = "PASS" ]; then
        ok "35/35 backend acceptance matrix"
    else
        fail "Backend acceptance matrix"
    fi
else
    fail "Backend acceptance matrix missing"
fi


# ------------------------------------------------------------
# 8. Git status
# ------------------------------------------------------------

section "8. SPRINT-11 GIT STATUS"

git status --short -- \
    backend/app/main.py \
    backend/app/features/post_trade \
    backend/migrations/versions/20260818_0019_ft011_post_trade_persistence.py \
    frontend \
    tests/unit/backend/features/post_trade \
    tests/integration/backend/post_trade \
    docs/decisions/ADR-S11-* \
    docs/implementation/SPRINT_11_FT011_* \
    2>/dev/null || true


# ------------------------------------------------------------
# Result
# ------------------------------------------------------------

section "RESULT"

printf 'PASS: %d\n' "$PASS"
printf 'FAIL: %d\n' "$FAIL"
printf 'SKIP: %d\n' "$SKIP"

if [ "$FAIL" -eq 0 ]; then
    printf '\nSPRINT 11 QUALIFICATION: PASS\n'
    exit 0
fi

printf '\nSPRINT 11 QUALIFICATION: FAIL\n'
exit 1
