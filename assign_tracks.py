#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "python-dotenv",
# ]
# ///
"""
Create tracks in Pretalx and assign sessions to them based on title keywords.

Usage:
    uv run assign_tracks.py [--dry-run]
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

API_BASE = "https://talks.caving.dev/api/events/nss-convention-2026"
STATE_FILE = os.path.join(os.path.dirname(__file__), "import_state.json")

# ---------------------------------------------------------------------------
# Track definitions: (track_name, color, [keyword_patterns])
# Patterns are matched case-insensitively against submission titles.
# Order matters — first match wins.
# ---------------------------------------------------------------------------

TRACKS = [
    ("Vertical & Technical", "#9C0000", [  # very dark red
        r"vertical climbing contest",
        r"climbing contest",
        r"discover vertical caving",
        r"vertical section",
        r"vertical training commission",
        r"contingency vertical workshop",
        r"derigging from vertical",
    ]),
    ("Exploration", "#BF360C", [  # dark vermilion/burnt orange
        r"cave exploration",
        r"us exploration",
        r"international exploration",
        r"explorers club",
        r"cave diving exploration",
    ]),
    ("Geology & Geography", "#7B1FA2", [  # deep purple
        r"geology\s+and\s+geography",
        r"geology and geography meeting",
    ]),
    ("Biology", "#1B5E20", [  # very dark green
        r"biospeleology",
    ]),
    ("Spelean History", "#5D3A1A", [  # dark brown
        r"paleontology",
        r"spelean history",
        r"archeology",
        r"speleophilatelic",
    ]),
    ("Survey & Cartography", "#0D47A1", [  # very dark blue
        r"survey\s*&\s*cartography",
        r"introduction to sketching",
        r"in-cave sketching",
        r"state cave surveys",
        r"cave digging section",
        r"cartographic salon",
        r"sketching contest",
    ]),
    ("Conservation", "#00695C", [  # dark teal
        r"cave conservation",
        r"speleothem repair",
        r"cave conservancy roundtable",
        r"ncrc annual meeting",
        r"carlsbad caverns listening",
        r"nss preserves",
    ]),
    ("Arts & Culture", "#880E4F", [  # dark magenta/rose
        r"fine arts? salon",
        r"photo salon",
        r"video salon",
        r"cave ballad salon",
        r"print salon",
        r"photo workshop",
        r"cave writers\s+workshop",
        r"photo.*session",
        r"cave photography",
    ]),
    ("Special Events", "#7A5800", [  # dark amber/gold (light colors fail contrast)
        r"10 years of the caving podcast",
        r"the caving podcast live",
        r"caver story telling",
    ]),
    ("Education & Community", "#004D40", [  # very dark teal (distinct from Conservation)
        r"speleology for cavers",
        r"speleology class lunch",
        r"caving\s*&\s*culture",
        r"cavers against sexual harassment",
        r"collegiate grotto",
        r"planned giving",
        r"nps cave managers",
        r"interagency meeting",
    ]),
    ("NSS Business", "#37474F", [  # dark blue-grey
        r"bog\s+(open\s+)?meeting",
        r"bog\s+lunch",
        r"nsf trustees",
        r"nss awards committee",
        r"nckms steering committee",
        r"congress of grottos",
        r"convention planning",
        r"convention debrief",
    ]),
    ("Social & Events", "#6A1B9A", [  # dark violet (distinct from red/blue/green tracks)
        r"opening ceremony",
        r"howdy party",
        r"fellows",
        r"nss auction",
        r"nss awards banquet",
        r"cave open house",
        r"open mic",
        r"campground party",
        r"yoga",
        r"coffee\s*&\s*karst",
        r"book signing",
        r"arts and letters lunch",
        r"communications\s*&?\s*elect",
    ]),
    ("Speakers", "#33691E", [  # dark olive green
        r"luminary speaker",
        r"featured speaker",
    ]),
]


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def api_post(token, path, payload, dry_run=False):
    url = f"{API_BASE}/{path}"
    if dry_run:
        print(f"  [DRY-RUN] POST {url} {json.dumps(payload)}")
        return None
    resp = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
    )
    if not resp.ok:
        print(f"  ERROR POST {url}: {resp.status_code} {resp.text[:200]}")
        return None
    return resp.json()


def api_patch(token, path, payload, dry_run=False):
    url = f"{API_BASE}/{path}"
    if dry_run:
        print(f"  [DRY-RUN] PATCH {url} {json.dumps(payload)}")
        return True
    resp = requests.patch(
        url,
        json=payload,
        headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
    )
    if not resp.ok:
        print(f"  ERROR PATCH {url}: {resp.status_code} {resp.text[:200]}")
        return False
    return True


def match_track(title):
    """Return the track name that first matches the title, or None."""
    title_lower = title.lower()
    for track_name, _color, patterns in TRACKS:
        for pat in patterns:
            if re.search(pat, title_lower):
                return track_name
    return None


def create_tracks(token, state, dry_run):
    """Create all tracks in Pretalx and return name→id mapping."""
    existing = state.get("tracks", {})
    tracks_map = dict(existing)

    for track_name, color, _ in TRACKS:
        if track_name in tracks_map:
            print(f"  Track already exists: {track_name} (id={tracks_map[track_name]})")
            continue
        print(f"  Creating track: {track_name}")
        result = api_post(token, "tracks/", {"name": {"en": track_name}, "color": color}, dry_run)
        if result:
            tracks_map[track_name] = result["id"]
            print(f"    → id={result['id']}")
        elif dry_run:
            tracks_map[track_name] = f"<dry-run-{track_name}>"

    return tracks_map


def assign_tracks(token, state, tracks_map, dry_run):
    """Iterate submissions, match to a track, and PATCH each one."""
    submissions = state.get("submissions", {})
    assigned = 0
    unmatched = []

    for key, info in submissions.items():
        # key format: "2026-07-06|Title|time"
        parts = key.split("|", 2)
        title = parts[1] if len(parts) >= 2 else key
        code = info["code"]

        track_name = match_track(title)
        if not track_name:
            unmatched.append((code, title))
            continue

        track_id = tracks_map.get(track_name)
        if not track_id:
            print(f"  WARN: no id for track '{track_name}' — skipping {code}")
            continue

        print(f"  {code} | {title[:60]!r} → {track_name}")
        ok = api_patch(token, f"submissions/{code}/", {"track": track_id}, dry_run)
        if ok:
            assigned += 1

    return assigned, unmatched


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Assign tracks to NSS 2026 sessions in Pretalx")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without calling the API")
    args = parser.parse_args()

    token = os.environ.get("PRETALX_TOKEN")
    if not token and not args.dry_run:
        print("ERROR: set PRETALX_TOKEN environment variable")
        sys.exit(1)

    state = load_state()

    print("=== Step 1: Create tracks ===")
    tracks_map = create_tracks(token, state, args.dry_run)

    if not args.dry_run:
        state["tracks"] = tracks_map
        save_state(state)

    print(f"\n=== Step 2: Assign tracks to {len(state.get('submissions', {}))} submissions ===")
    assigned, unmatched = assign_tracks(token, state, tracks_map, args.dry_run)

    print(f"\n=== Summary ===")
    print(f"  Tracks created/loaded: {len(tracks_map)}")
    print(f"  Submissions assigned:  {assigned}")
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}):")
        for code, title in unmatched:
            print(f"    {code} | {title}")


if __name__ == "__main__":
    main()
