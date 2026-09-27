"""Capture reproducible S4-B2/P1 worker, ACL, token, and lifecycle evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mke_product.protocol.schema import SCHEMA_VERSION
from mke_product.worker.appcontainer import get_appcontainer_manager
from mke_product.worker.controller import WorkerController


def file_manifest(root: Path) -> dict:
    entries = []
    aggregate = hashlib.sha256()
    total_bytes = 0
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda p: str(p).lower()):
        relative = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        size = path.stat().st_size
        entries.append({"path": relative, "bytes": size, "sha256": digest})
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(digest))
        total_bytes += size
    return {
        "root_components": ["runtime", "src/mke_product", "worker_bootstrap.py"],
        "runtime_policy": {
            "root_files": ["python.exe", "python*.dll", "vcruntime*.dll"],
            "included_directories": ["DLLs", "Lib"],
            "excluded_directories": [
                "site-packages", "__pycache__", "ensurepip", "idlelib", "test",
                "tests", "tkinter", "turtledemo", "venv",
            ],
            "source_policy": "Only src/mke_product/**/*.py",
            "python_flags": ["-I", "-S", "-B"],
            "appcontainer_access": "(OI)(CI)RX",
        },
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "aggregate_sha256": aggregate.hexdigest().upper(),
        "files": entries,
    }


def main() -> int:
    controller = WorkerController(timeout_sec=10.0)
    request = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
    response = controller.execute_request(request)
    manager = get_appcontainer_manager()
    if response.get("outcome") != "SUCCESS":
        raise RuntimeError(f"P1 worker evidence request failed: {response}")
    if not manager.stage_root:
        raise RuntimeError("AppContainer stage is unavailable after successful request")

    stage_root = manager.stage_root
    manifest = file_manifest(stage_root)
    acl = subprocess.run(
        ["icacls.exe", str(stage_root)], text=True, capture_output=True
    )
    active_after_request = manager.active_children
    lease = manager.acquire()
    try:
        refused_cleanup = manager.cleanup()
    finally:
        lease.release()
    completed_cleanup = manager.cleanup()

    evidence = {
        "milestone": "S4-B2/P1",
        "request": request,
        "response": response,
        "token_and_job": controller.get_last_appcontainer_evidence(),
        "profile": {
            "name": refused_cleanup["profile_name"],
            "active_children_after_request": active_after_request,
            "cleanup_with_active_lease": refused_cleanup,
            "cleanup_after_release": completed_cleanup,
        },
        "acl": {
            "command": subprocess.list2cmdline(["icacls.exe", "<staged-root>"]),
            "returncode": acl.returncode,
            "stdout": acl.stdout.replace(str(stage_root), "<staged-root>").strip(),
            "stderr": acl.stderr.strip(),
            "intended_sid_rights": "(OI)(CI)RX",
        },
        "manifest_summary": {key: value for key, value in manifest.items() if key != "files"},
        "scope_limitations": [
            "No claim of complete filesystem isolation.",
            "No claim of outbound network isolation.",
        ],
    }

    out_dir = ROOT / "evidence" / "s4b2_p1"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "appcontainer_worker_evidence.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    (out_dir / "minimal_runtime_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
