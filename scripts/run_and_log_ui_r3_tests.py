"""
MKE PRODUCT-03A-R3: Full Regression & Automated Browser Gate Test Suite Runner.

Executes:
1. Baseline unit tests (solver, parser, rational, protocol, evaluator)
2. CAS multi-engine tests (test_cas_product03a.py)
3. HTTP E2E integration tests (test_cas_http_integration.py)
4. Automated browser verification suite with Selenium (test_browser_canonical_ui.py)
5. Windows worker containment tests (test_worker_windows.py)

Captures stdout/stderr, execution timings, exit codes, and generates
structured JSON evidence in evidence/ui_r3/.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO_ROOT / "evidence" / "ui_r3"


def run_tests() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    raw_log_path = EVIDENCE_DIR / "ui_r3_test_suite_raw.log"
    results_json_path = EVIDENCE_DIR / "ui_r3_test_results.json"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    # Get Git commit hash and branch
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
        git_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception as exc:
        commit_hash = f"UNKNOWN ({exc})"
        git_branch = "UNKNOWN"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        "tests",
    ]

    print(f"[*] Running MKE PRODUCT-03A-R3 full regression suite on commit: {commit_hash} (branch: {git_branch})")
    start_time = time.monotonic()

    process = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    full_output = []
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            sys.stdout.write(line)
            full_output.append(line)

    returncode = process.poll() or 0
    duration_sec = time.monotonic() - start_time
    output_text = "".join(full_output)

    # Save raw console log
    with open(raw_log_path, "w", encoding="utf-8") as f:
        f.write(f"# MKE PRODUCT-03A-R3 FULL REGRESSION & BROWSER TEST SUITE LOG\n")
        f.write(f"# Commit: {commit_hash}\n")
        f.write(f"# Branch: {git_branch}\n")
        f.write(f"# Duration: {duration_sec:.2f}s\n")
        f.write(f"# Exit Code: {returncode}\n\n")
        f.write(output_text)

    print(f"\n[*] Raw log saved to: {raw_log_path}")

    # Parse passed/failed counts
    passed_count = 0
    failed_count = 0
    subtests_count = 0
    for line in output_text.splitlines():
        if "passed" in line and "=" in line:
            m_pass = re.search(r"(\d+)\s+passed", line)
            m_fail = re.search(r"(\d+)\s+failed", line)
            m_sub = re.search(r"(\d+)\s+subtests passed", line)
            if m_pass:
                passed_count = int(m_pass.group(1))
            if m_fail:
                failed_count = int(m_fail.group(1))
            if m_sub:
                subtests_count = int(m_sub.group(1))

    results = {
        "suite": "MKE_PRODUCT_03A_R3_FULL_REGRESSION",
        "commit": commit_hash,
        "branch": git_branch,
        "duration_sec": round(duration_sec, 2),
        "returncode": returncode,
        "passed": passed_count,
        "failed": failed_count,
        "subtests": subtests_count,
        "verdict": "PASS" if returncode == 0 and failed_count == 0 else "FAIL",
        "tested_files": [
            "tests/test_browser_canonical_ui.py",
            "tests/test_cas_http_integration.py",
            "tests/test_cas_product03a.py",
            "tests/test_evaluator.py",
            "tests/test_parser.py",
            "tests/test_protocol.py",
            "tests/test_rational.py",
            "tests/test_solver.py",
            "tests/test_worker_windows.py",
        ],
    }

    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"[*] Results JSON saved to: {results_json_path}")
    print(f"[*] Final Verdict: {results['verdict']} ({passed_count} passed, {failed_count} failed, {subtests_count} subtests)")

    return returncode


if __name__ == "__main__":
    sys.exit(run_tests())
