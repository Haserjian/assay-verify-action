#!/usr/bin/env python3
"""Accumulate a trust record into a JSON array file.

Usage: accumulate-trust.py <records_file> <verify_json> <pack_name>

Reads the verify-pack JSON, extracts the trust block if present,
appends {pack_name, trust} to the records array, and writes back.
"""
import json
import sys


def main() -> int:
    if len(sys.argv) < 4:
        return 0

    records_file = sys.argv[1]
    verify_json_str = sys.argv[2]
    pack_name = sys.argv[3]

    try:
        with open(records_file) as f:
            records = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        records = []

    try:
        pack_data = json.loads(verify_json_str)
    except (json.JSONDecodeError, TypeError):
        return 0

    trust = pack_data.get("trust")
    if trust:
        records.append({"pack_name": pack_name, "trust": trust})
        with open(records_file, "w") as f:
            json.dump(records, f)

    return 0


if __name__ == "__main__":
    sys.exit(main())
