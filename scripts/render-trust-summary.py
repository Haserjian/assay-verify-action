#!/usr/bin/env python3
"""Render trust evaluation section from assay verify-pack --json output.

Usage: render-trust-summary.py <json_string>
Outputs markdown trust summary section to stdout. Empty output if no trust block.
"""
import json
import sys


def render_trust_summary(json_str: str) -> str:
    """Extract trust block from verify-pack JSON and render markdown summary."""
    try:
        d = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return ""

    t = d.get("trust")
    if not t:
        return ""

    target = t.get("acceptance", {}).get("target", "?")
    auth_st = t.get("authorization", {}).get("status", "?")
    acc_dec = t.get("acceptance", {}).get("decision", "?")
    auth_rc = t.get("authorization", {}).get("reason_codes", [])
    acc_rc = t.get("acceptance", {}).get("reason_codes", [])
    errs = t.get("load_errors", [])

    out = ["\n### Trust Evaluation\n"]
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

    out.append("> Trust evaluation is advisory only and does not affect the exit code.\n")
    return "\n".join(out)


if __name__ == "__main__":
    # Accept JSON from positional arg or stdin
    if len(sys.argv) >= 2:
        json_str = sys.argv[1]
    elif not sys.stdin.isatty():
        json_str = sys.stdin.read()
    else:
        sys.exit(0)
    result = render_trust_summary(json_str)
    if result:
        print(result)
