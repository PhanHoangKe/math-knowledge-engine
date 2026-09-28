"""
MKE PRODUCT-03B-R2-HF1: Regression Runner & Strict Evidence Integrity Generator.

Guarantees:
1. Enforces tracked working-tree cleanliness before running tests (aborts if dirty).
2. Executes full test suite across all units, multi-engine CAS operations, HTTP endpoints,
   Windows containment/worker isolation, and browser tests.
3. Records precise source commit SHA, environmental metadata, and test metrics.
4. Generates structured JSON evidence and raw console log in evidence/p03b_r2_hf1/.
"""

import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO_ROOT / "evidence" / "p03b_r2_hf1"


def check_working_tree_cleanliness() -> tuple[bool, str]:
    """Check if tracked source/test/script files contain uncommitted changes."""
    res = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        return False, f"git status failed: {res.stderr}"

    # Ignore evidence/ directory changes if any
    dirty_lines = [
        line for line in res.stdout.splitlines()
        if line.strip() and not ("evidence/" in line or "evidence\\" in line)
    ]
    if dirty_lines:
        return False, "Uncommitted changes in tracked files:\n" + "\n".join(dirty_lines)
    return True, "Clean working tree"


def run_tests() -> int:
    is_clean, clean_msg = check_working_tree_cleanliness()
    if not is_clean:
        print(f"[!] EVIDENCE INTEGRITY ERROR: Cannot run evidence suite on dirty working tree.")
        print(f"[!] {clean_msg}")
        print(f"[!] Please commit all source and test changes before generating evidence.")
        return 1

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    raw_log_path = EVIDENCE_DIR / "p03b_r2_hf1_test_suite_raw.log"
    results_json_path = EVIDENCE_DIR / "p03b_r2_hf1_test_results.json"

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

    import sympy
    import pytest

    env_metadata = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "sympy_version": sympy.__version__,
        "pytest_version": pytest.__version__,
    }

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        "tests",
    ]

    print(f"[*] Running MKE PRODUCT-03B-R2-HF1 full regression suite on clean commit: {commit_hash} (branch: {git_branch})")
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
        f.write(f"# MKE PRODUCT-03B-R2-HF1 FULL REGRESSION TEST SUITE LOG\n")
        f.write(f"# Commit: {commit_hash}\n")
        f.write(f"# Branch: {git_branch}\n")
        f.write(f"# Environment: Python {sys.version.split()[0]} on {platform.system()} {platform.release()}\n")
        f.write(f"# SymPy: {sympy.__version__}, Pytest: {pytest.__version__}\n")
        f.write(f"# Duration: {duration_sec:.2f}s\n")
        f.write(f"# Exit Code: {returncode}\n\n")
        f.write(output_text)

    print(f"\n[*] Raw log saved to: {raw_log_path}")

    # Parse passed/failed counts
    passed_count = 0
    failed_count = 0
    for line in output_text.splitlines():
        if "passed" in line and "=" in line:
            m_pass = re.search(r"(\d+)\s+passed", line)
            m_fail = re.search(r"(\d+)\s+failed", line)
            if m_pass:
                passed_count = int(m_pass.group(1))
            if m_fail:
                failed_count = int(m_fail.group(1))

    results = {
        "milestone": "PRODUCT-03B-R2-HF1",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "commit_hash": commit_hash,
        "git_branch": git_branch,
        "environment": env_metadata,
        "source_cleanliness": clean_msg,
        "exit_code": returncode,
        "duration_seconds": round(duration_sec, 2),
        "total_passed": passed_count,
        "total_failed": failed_count,
        "success": (returncode == 0 and failed_count == 0),
    }

    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"[*] Results JSON saved to: {results_json_path}")
    print(f"[*] Summary: {passed_count} passed, {failed_count} failed in {duration_sec:.2f}s")

    return returncode


if __name__ == "__main__":
    sys.exit(run_tests())
