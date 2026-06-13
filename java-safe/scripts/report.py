#!/usr/bin/env python3
"""Render a java-safe scan result as a standalone HTML report.

Stdlib-only. Embeds the scan data into report-template.html by replacing the
`/*__SCAN_DATA__*/` placeholder, exactly like skill-creator's generate_review.py.
The output is a single self-contained file — no server, no assets to ship
alongside it.
"""

import datetime
import json
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "report-template.html"


def render_html(scan_data: dict) -> str:
    """Return a complete standalone HTML page for the given scan data."""
    payload = dict(scan_data)
    payload.setdefault(
        "generated_at",
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    data_js = f"const EMBEDDED_DATA = {json.dumps(payload)};"
    return template.replace("/*__SCAN_DATA__*/", data_js)


def write_report(scan_data: dict, out_path: Path) -> Path:
    """Write the HTML report to out_path and return it."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(scan_data), encoding="utf-8")
    return out_path
