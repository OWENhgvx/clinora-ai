#!/usr/bin/env bash
# Clinora — one-shot test runner
# Usage (from clinora/): bash run_tests.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/clinora-backend"
FRONTEND="$ROOT/clinora-frontend"

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
pass() { echo -e "${GREEN}  PASS${NC}  $1"; }
fail() { echo -e "${RED}  FAIL${NC}  $1"; FAILED=1; }

FAILED=0

echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}   Clinora Test Suite${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"

# ── Backend ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Backend (pytest) ──────────────────────${NC}"

cd "$BACKEND"

# Create / reuse venv
if [ ! -d "venv" ]; then
  echo "  Creating Python venv..."
  python -m venv venv
fi

source venv/Scripts/activate 2>/dev/null || source venv/bin/activate

echo "  Installing dependencies..."
pip install -r requirements.txt -q

echo ""
echo "  Running pytest..."
if python -m pytest tests/ -q --tb=short --no-header 2>&1; then
  pass "pytest — all tests passed"
else
  fail "pytest — some tests failed (see output above)"
fi

echo ""
echo "  Running coverage report..."
python -m pytest tests/ --cov=. --cov-report=term-missing -q --no-header 2>&1 | tail -20

deactivate 2>/dev/null || true

# ── Frontend ───────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Frontend (Vitest + ESLint) ────────────${NC}"

cd "$FRONTEND"

echo "  Installing dependencies..."
npm install --silent

echo ""
echo "  Running ESLint..."
if npm run lint --silent 2>&1; then
  pass "ESLint — 0 errors"
else
  fail "ESLint — errors found"
fi

echo ""
echo "  Running Vitest unit tests..."
if npm run test:run 2>&1; then
  pass "Vitest — all tests passed"
else
  fail "Vitest — some tests failed (see output above)"
fi

# ── Summary ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}  All test suites passed.${NC}"
else
  echo -e "${RED}  One or more test suites failed.${NC}"
fi
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo ""

exit $FAILED
