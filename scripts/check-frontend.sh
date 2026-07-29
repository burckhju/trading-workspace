#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repository_root}/frontend"

npm run typecheck
npm run lint
npm run format
npm run test:coverage -- \
  --coverage.thresholds.lines=80 \
  --coverage.thresholds.functions=80 \
  --coverage.thresholds.statements=80 \
  --coverage.thresholds.branches=70
npm run build
