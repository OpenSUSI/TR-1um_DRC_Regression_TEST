#!/usr/bin/env bash
# =============================================================================
# regression.sh – TR-1um DRC Regression Test Runner
# =============================================================================
# Runs the KLayout DRC runset against every GDS file in tests/gds/ and
# reports pass/fail.
#
# Conventions
# -----------
#   tests/gds/pass/  → all layouts expected to produce ZERO violations
#   tests/gds/fail/  → all layouts expected to produce ≥ 1 violation
#
# Exit codes
#   0  all tests passed
#   1  one or more tests failed
#
# Dependencies
#   klayout  ≥ 0.28  (klayout -b mode)
#
# Usage
#   bash tests/regression.sh [--drc-script <path>] [--gds-dir <path>]
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults (can be overridden via flags)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DRC_SCRIPT="${REPO_ROOT}/drc/tr1um.drc"
GDS_DIR="${SCRIPT_DIR}/gds"
REPORT_DIR="${SCRIPT_DIR}/reports"

PASS=0
FAIL=0
ERRORS=()

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --drc-script)  DRC_SCRIPT="$2"; shift 2 ;;
        --gds-dir)     GDS_DIR="$2";    shift 2 ;;
        --report-dir)  REPORT_DIR="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
if ! command -v klayout &>/dev/null; then
    echo "ERROR: 'klayout' command not found.  Install KLayout >= 0.28." >&2
    exit 1
fi

if [[ ! -f "${DRC_SCRIPT}" ]]; then
    echo "ERROR: DRC script not found: ${DRC_SCRIPT}" >&2
    exit 1
fi

mkdir -p "${REPORT_DIR}/pass" "${REPORT_DIR}/fail"

# ---------------------------------------------------------------------------
# Helper: count violations in an lyrdb XML report file
# ---------------------------------------------------------------------------
count_violations() {
    local report_file="$1"
    # Each <item> element in the lyrdb file represents one DRC violation
    grep -c '<item>' "${report_file}" 2>/dev/null || echo 0
}

# ---------------------------------------------------------------------------
# Helper: run DRC on a single GDS file
# ---------------------------------------------------------------------------
run_drc() {
    local gds_file="$1"
    local report_file="$2"
    klayout -b \
        -r "${DRC_SCRIPT}" \
        -rd input="${gds_file}" \
        -rd report="${report_file}" \
        2>&1
}

# ---------------------------------------------------------------------------
# Run PASS cases  (expected: 0 violations)
# ---------------------------------------------------------------------------
echo "======================================================================"
echo "  TR-1um DRC Regression Test"
echo "  DRC script : ${DRC_SCRIPT}"
echo "  GDS dir    : ${GDS_DIR}"
echo "======================================================================"

echo ""
echo "--- PASS cases (expect 0 violations) ---"

for gds in "${GDS_DIR}/pass/"*.gds; do
    [[ -f "${gds}" ]] || { echo "  (no pass/*.gds files found, skipping)"; break; }
    base="$(basename "${gds}" .gds)"
    report="${REPORT_DIR}/pass/${base}.lyrdb"

    run_drc "${gds}" "${report}" > /dev/null 2>&1 || true
    viols=$(count_violations "${report}")

    if [[ "${viols}" -eq 0 ]]; then
        echo "  PASS  ${base}  (${viols} violations)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  ${base}  (${viols} violations – expected 0)"
        ERRORS+=("${base}: expected 0 violations, got ${viols}")
        FAIL=$((FAIL + 1))
    fi
done

# ---------------------------------------------------------------------------
# Run FAIL cases  (expected: ≥ 1 violation)
# ---------------------------------------------------------------------------
echo ""
echo "--- FAIL cases (expect ≥ 1 violation) ---"

for gds in "${GDS_DIR}/fail/"*.gds; do
    [[ -f "${gds}" ]] || { echo "  (no fail/*.gds files found, skipping)"; break; }
    base="$(basename "${gds}" .gds)"
    report="${REPORT_DIR}/fail/${base}.lyrdb"

    run_drc "${gds}" "${report}" > /dev/null 2>&1 || true
    viols=$(count_violations "${report}")

    if [[ "${viols}" -ge 1 ]]; then
        echo "  PASS  ${base}  (${viols} violation(s) detected as expected)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  ${base}  (0 violations – expected ≥ 1)"
        ERRORS+=("${base}: expected ≥ 1 violation, got 0")
        FAIL=$((FAIL + 1))
    fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL=$((PASS + FAIL))
echo ""
echo "======================================================================"
echo "  Results: ${PASS}/${TOTAL} passed,  ${FAIL} failed"
echo "======================================================================"

if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo ""
    echo "Failures:"
    for msg in "${ERRORS[@]}"; do
        echo "  - ${msg}"
    done
    exit 1
fi

exit 0
