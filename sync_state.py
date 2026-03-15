#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "python-dotenv",
# ]
# ///
"""
Sync import_state.json with current Pretalx state.

Fetches all submissions and their slots from Pretalx and updates
import_state.json to reflect any manual edits made in Pretalx.

Usage:
    uv run sync_state.py
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

API_BASE = "https://talks.caving.dev/api/events/nss-convention-2026"
STATE_FILE = os.path.join(os.path.dirname(__file__), "import_state.json")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def api_get_all(token, path):
    """Fetch all pages from a paginated endpoint."""
    results = []
    url = f"{API_BASE}/{path}"
    while url:
        resp = requests.get(url, headers={"Authorization": f"Token {token}"})
        if not resp.ok:
            print(f"ERROR GET {url}: {resp.status_code} {resp.text[:200]}")
            break
        data = resp.json()
        results.extend(data.get("results", []))
        url = (data.get("next") or "").replace("http://", "https://") or None
    return results


def main():
    token = os.environ.get("PRETALX_TOKEN")
    if not token:
        print("ERROR: set PRETALX_TOKEN environment variable")
        sys.exit(1)

    state = load_state()

    # Build a code → state_key index for fast lookup
    code_to_key = {
        info["code"]: key
        for key, info in state.get("submissions", {}).items()
    }

    print("Fetching submissions from Pretalx...")
    submissions = api_get_all(token, "submissions/?limit=100&expand=slots")
    print(f"  Got {len(submissions)} submissions")

    updated = 0
    added = 0

    for sub in submissions:
        code = sub["code"]
        slots = sub.get("slots", [])
        slot = slots[0] if slots else None

        entry = {
            "code": code,
            "title": sub.get("title"),
            "track": sub.get("track"),
            "state": sub.get("state"),
            "slot": slot["id"] if slot else None,
            "scheduled": slot is not None,
            "room": slot.get("room") if slot else None,
            "start": slot.get("start") if slot else None,
            "end": slot.get("end") if slot else None,
        }

        if code in code_to_key:
            key = code_to_key[code]
            old = state["submissions"][key]
            if old != entry:
                state["submissions"][key] = entry
                updated += 1
        else:
            # New submission added directly in Pretalx — key by code
            state.setdefault("submissions", {})[code] = entry
            added += 1

    save_state(state)

    print(f"\n=== Summary ===")
    print(f"  Submissions updated: {updated}")
    print(f"  New submissions added: {added}")
    print(f"  Total in state: {len(state.get('submissions', {}))}")


if __name__ == "__main__":
    main()
