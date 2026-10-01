#!/usr/bin/env python3
"""MKE MVP V1 — OpenAPI Schema Exporter.

Deterministic repository tool to export the OpenAPI 3.1.0 schema directly
from the accepted FastAPI transport application (mke_product.transport.app:create_app)
without requiring a running server or network connection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mke_product.transport.app import create_app


def export_openapi(output_path: Path | None = None) -> str:
    """Generate deterministic JSON OpenAPI schema from create_app()."""
    app = create_app()
    schema = app.openapi()
    
    # Deterministic JSON representation (sorted keys, 2-space indent, trailing newline)
    json_text = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_text, encoding="utf-8")
        print(f"OpenAPI schema exported successfully to {output_path}")
    
    return json_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Export MKE OpenAPI Schema")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=REPO_ROOT / "src" / "frontend" / "openapi" / "mke.openapi.json",
        help="Path to output OpenAPI JSON file (default: src/frontend/openapi/mke.openapi.json)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout instead of writing to file",
    )
    args = parser.parse_args()

    if args.stdout:
        sys.stdout.write(export_openapi(None))
    else:
        export_openapi(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
