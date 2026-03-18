#!/usr/bin/env python3
"""Render trust evaluation sections from assay verify-pack output.

Accepts JSON from stdin or first positional arg.

Input formats:
  1. Single verify-pack JSON: {"trust": {...}, ...}
  2. List of pack trust records: [{"pack_name": "...", "trust": {...}}, ...]

Outputs markdown trust summary to stdout. Empty output if no trust data.
"""
import json
import sys


def _render_one_trust(trust: dict, pack_name: str = "") -> list[str]:
    """Render a single trust block into markdown lines."""
    target = trust.get("acceptance", {}).get("target", "?")
    auth_st = trust.get("authorization", {}).get("status", "?")
    acc_dec = trust.get("acceptance", {}).get("decision", "?")
    auth_rc = trust.get("authorization", {}).get("reason_codes", [])
    acc_rc = trust.get("acceptance", {}).get("reason_codes", [])
    errs = trust.get("load_errors", [])

    header = "### Trust Evaluation"
    if pack_name:
        header = "### Trust: `%s`" % pack_name

    out = ["", header, ""]
    out.append("| Field | Value |")
    out.append("|-------|-------|")
    out.append("| Target | `%s` |" % target)
    out.append("| Authorization | %s |" % auth_st)
    out.append("| Acceptance | %s |" % acc_dec)
    if auth_rc:
        out.append("| Auth reasons | %s |" % ", ".join(auth_rc))
    if acc_rc:
        out.append("| Accept reasons | %s |" % ", ".join(acc_rc))
    out.append("")

    if errs:
        out.append("> **Trust policy load errors:**")
        for e in errs:
            out.append("> - %s" % e)
        out.append("")

    return out


def render_trust_summary(json_str: str) -> str:
    """Parse trust data and render markdown summary."""
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return ""

    sections: list[str] = []

    if isinstance(data, list):
        # List of pack trust records: [{"pack_name": ..., "trust": ...}, ...]
        for record in data:
            trust = record.get("trust")
            if trust:
                pack_name = record.get("pack_name", "")
                sections.extend(_render_one_trust(trust, pack_name))
    elif isinstance(data, dict):
        # Single verify-pack JSON: {"trust": {...}, ...}
        trust = data.get("trust")
        if trust:
            sections.extend(_render_one_trust(trust))

    if not sections:
        return ""

    sections.append("> Trust evaluation is advisory only and does not affect the exit code.")
    sections.append("")
    return "\n".join(sections)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        json_str = sys.argv[1]
    elif not sys.stdin.isatty():
        json_str = sys.stdin.read()
    else:
        sys.exit(0)
    result = render_trust_summary(json_str)
    if result:
        print(result)
