"""Run handle forensics suite and save complete raw unedited log."""

import os
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
output_log = repo_root / "evidence" / "s4b2_p1_r2" / "handle_forensics_raw.log"
output_json = repo_root / "evidence" / "s4b2_p1_r2" / "handle_forensics_results.json"
output_log.parent.mkdir(parents=True, exist_ok=True)

cmd = [sys.executable, "scripts/handle_forensics.py"]

print(f"Executing: {' '.join(cmd)}")
proc = subprocess.run(cmd, cwd=str(repo_root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

# Write complete raw output
output_log.write_text(proc.stdout, encoding="utf-8")
print(proc.stdout)

# Copy root handle_forensics_results.json to dedicated evidence directory
root_json = repo_root / "handle_forensics_results.json"
if root_json.exists():
    output_json.write_text(root_json.read_text(encoding="utf-8"), encoding="utf-8")

print(f"\nSaved raw forensics log to: {output_log}")
print(f"Saved structured forensics JSON to: {output_json}")
print(f"Exit code: {proc.returncode}")
sys.exit(proc.returncode)
