"""Run full test suite and save complete raw unedited log."""

import os
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
output_log = repo_root / "evidence" / "s4b2_p1_r1" / "test_suite_raw.log"
output_log.parent.mkdir(parents=True, exist_ok=True)

cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]

print(f"Executing: {' '.join(cmd)}")
proc = subprocess.run(cmd, cwd=str(repo_root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

# Write complete raw output
output_log.write_text(proc.stdout, encoding="utf-8")
print(proc.stdout)
print(f"\nSaved raw test log to: {output_log}")
print(f"Exit code: {proc.returncode}")
sys.exit(proc.returncode)
