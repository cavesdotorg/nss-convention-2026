#!/usr/bin/env python3
"""
Import NSS 2026 schedule from Google Sheet into Pretalx.

Usage:
    PRETALX_TOKEN=<token> python import_schedule.py [--dry-run] [--skip-rooms] [--skip-submissions]
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library not found. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1nv4gmPcHrfDJp62hioi666MGbg9Hz_-b"
    "/export?format=csv&gid=779280412"
)
API_BASE = "https://talks.caving.dev/api/events/nss-convention-2026"
STATE_FILE = os.path.join(os.path.dirname(__file__), "import_state.json")

# US Eastern in July = UTC-4
TZ_OFFSET = timezone(timedelta(hours=-4))

# Day column groups: (day_date, event_col, time_col, where_col)
# Columns are 0-indexed after csv.reader
DAY_COLUMNS = [
    (datetime(2026, 7, 6, tzinfo=TZ_OFFSET), 2, 3, 4),   # Monday Jul 6
    (datetime(2026, 7, 7, tzinfo=TZ_OFFSET), 6, 7, 8),   # Tuesday Jul 7
    (datetime(2026, 7, 8, tzinfo=TZ_OFFSET), 10, 11, 12), # Wednesday Jul 8
    (datetime(2026, 7, 9, tzinfo=TZ_OFFSET), 14, 15, 16), # Thursday Jul 9
    (datetime(2026, 7, 10, tzinfo=TZ_OFFSET), 18, 19, 20), # Friday Jul 10
]

DEFAULT_DURATION_MINUTES = 60

# Canonical room name normalization
ROOM_NAME_MAP = {
    'jr. high gym': 'Junior High Gym',
    'campground': 'Campground',
}


# ---------------------------------------------------------------------------
# State persistence (for idempotent re-runs)
# ---------------------------------------------------------------------------

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"rooms": {}, "submissions": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

def normalize_room_name(name):
    """Normalize variant room names to a canonical form."""
    return ROOM_NAME_MAP.get(name.strip().lower(), name.strip())


def normalize_time_str(s):
    """Normalize a time string like '8:30 -9:00' → '8:30-9:00'."""
    s = s.strip()
    # collapse spaces around dashes
    s = re.sub(r'\s*-\s*', '-', s)
    return s


def parse_single_time(t, day_date, assume_pm=False):
    """
    Parse a single time token (e.g. '9:00', 'Noon', 'Midnight', '8:30am', '6pm')
    and return a datetime on day_date in TZ_OFFSET.
    assume_pm: if True and no am/pm given, treat ambiguous hours (1-11) as PM.
    Returns None on failure.
    """
    t = t.strip()
    if not t:
        return None

    # Named times
    if t.lower() == 'noon':
        return day_date.replace(hour=12, minute=0, second=0, microsecond=0)
    if t.lower() == 'midnight':
        # midnight = start of next day
        next_day = day_date + timedelta(days=1)
        return next_day.replace(hour=0, minute=0, second=0, microsecond=0)

    # Strip trailing non-time words like "start"
    t = re.sub(r'\s+start\s*$', '', t, flags=re.IGNORECASE).strip()

    # Parse am/pm suffix
    am_pm = None
    m = re.match(r'^(\d{1,2}(?::\d{2})?)\s*(am|pm)$', t, re.IGNORECASE)
    if m:
        t = m.group(1)
        am_pm = m.group(2).lower()

    # Parse HH:MM or HH
    if ':' in t:
        parts = t.split(':')
        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except (ValueError, IndexError):
            return None
    else:
        try:
            hour = int(t)
            minute = 0
        except ValueError:
            return None

    # Apply am/pm
    if am_pm == 'pm' and hour != 12:
        hour += 12
    elif am_pm == 'am' and hour == 12:
        hour = 0
    elif am_pm is None:
        if assume_pm and 1 <= hour <= 11:
            hour += 12
        elif hour < 8:
            # Heuristic: hour < 8 with no am/pm → PM (e.g. "6" → 18:00)
            hour += 12

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    return day_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def parse_time_range(time_str, day_date, assume_pm=False):
    """
    Parse a time range string like '9:00-Noon', '8:30-9:00', '12:30 start'.
    assume_pm: if True, treat ambiguous start/end hours as PM.
    Returns (start_dt, end_dt) or (start_dt, None) if no end.
    Returns (None, None) on failure.
    """
    time_str = normalize_time_str(time_str)
    if not time_str:
        return None, None

    parts = time_str.split('-', 1)

    # If end is 'Midnight', the start must be PM
    end_token = parts[1].strip() if len(parts) == 2 else ''
    if end_token.lower() == 'midnight':
        assume_pm = True

    start_dt = parse_single_time(parts[0], day_date, assume_pm=assume_pm)
    if start_dt is None:
        return None, None

    if end_token:
        end_dt = parse_single_time(end_token, day_date)
        # If start is evening (≥18:00) and end is ambiguous AM (1-11), try PM for end
        if end_dt is not None and start_dt.hour >= 18 and 1 <= end_dt.hour <= 11:
            end_pm = end_dt.replace(hour=end_dt.hour + 12)
            if end_pm > start_dt:
                end_dt = end_pm
        # Handle wrap: end <= start means end is next day
        if end_dt is not None and end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)
        # Cap at midnight of the start day — events don't run overnight
        if end_dt is not None and end_dt.date() != start_dt.date():
            end_dt = (start_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        end_dt = None

    return start_dt, end_dt


def duration_minutes(start_dt, end_dt):
    if start_dt and end_dt:
        delta = end_dt - start_dt
        return max(int(delta.total_seconds() / 60), 1)
    return DEFAULT_DURATION_MINUTES


# ---------------------------------------------------------------------------
# CSV fetching and parsing
# ---------------------------------------------------------------------------

def fetch_csv():
    print(f"Fetching schedule CSV from Google Sheets...")
    resp = requests.get(SHEET_URL, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_events(csv_text):
    """
    Parse the wide-format CSV and return a list of event dicts:
      {title, location, day_date, start_dt, end_dt, duration_minutes}
    """
    reader = list(csv.reader(io.StringIO(csv_text)))

    events = []
    # Find the header row (contains 'Event' or 'Time' in the day-column positions)
    header_row_idx = None
    for i, row in enumerate(reader):
        # Check if the day columns look like headers
        if len(row) > 4 and row[2].strip().lower() in ('event', 'title', 'session'):
            header_row_idx = i
            break
        # Also check for the word "Event" anywhere in likely positions
        for col in [2, 6, 10, 14, 18]:
            if len(row) > col and row[col].strip().lower() == 'event':
                header_row_idx = i
                break
        if header_row_idx is not None:
            break

    if header_row_idx is None:
        # Fall back: assume row 6 (0-indexed) per plan
        header_row_idx = 6
        print(f"  Warning: could not detect header row, assuming row index {header_row_idx}")
    else:
        print(f"  Found header row at index {header_row_idx}")

    data_rows = reader[header_row_idx + 1:]

    in_evening = False
    for row in data_rows:
        # Detect "Evening" section marker in col 1
        if len(row) > 1 and row[1].strip().lower() == 'evening':
            in_evening = True

        for day_date, ev_col, time_col, where_col in DAY_COLUMNS:
            # Safely get cell values
            def cell(col):
                return row[col].strip() if len(row) > col else ''

            title = cell(ev_col)
            time_str = cell(time_col)
            location = cell(where_col)

            if not title:
                continue

            # Skip obviously meta rows
            if title.lower() in ('event', 'title', 'session', 'activity'):
                continue

            start_dt, end_dt = parse_time_range(time_str, day_date, assume_pm=in_evening)
            dur = duration_minutes(start_dt, end_dt)

            events.append({
                'title': title,
                'location': normalize_room_name(location) if location else 'TBD',
                'day_date': day_date,
                'start_dt': start_dt,
                'end_dt': end_dt,
                'duration_minutes': dur,
                'time_str': time_str,
            })

    return events


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def make_session(token):
    s = requests.Session()
    s.headers.update({
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json',
    })
    return s


def api_get(session, path, params=None):
    url = f"{API_BASE}/{path.lstrip('/')}"
    resp = session.get(url, params=params, timeout=30)
    if not resp.ok:
        print(f"  GET {url} → {resp.status_code}: {resp.text[:200]}")
    return resp


def api_post(session, path, data):
    url = f"{API_BASE}/{path.lstrip('/')}"
    resp = session.post(url, json=data, timeout=30)
    if not resp.ok:
        print(f"  POST {url} → {resp.status_code}: {resp.text[:500]}")
    return resp


def api_patch(session, path, data):
    url = f"{API_BASE}/{path.lstrip('/')}"
    resp = session.patch(url, json=data, timeout=30)
    if not resp.ok:
        print(f"  PATCH {url} → {resp.status_code}: {resp.text[:500]}")
    return resp


def get_all_pages(session, path, params=None):
    """Fetch all pages of a paginated list endpoint."""
    results = []
    url = f"{API_BASE}/{path.lstrip('/')}"
    while url:
        resp = session.get(url, params=params, timeout=30)
        if not resp.ok:
            print(f"  GET {url} → {resp.status_code}: {resp.text[:200]}")
            break
        data = resp.json()
        if isinstance(data, list):
            results.extend(data)
            break
        results.extend(data.get('results', []))
        url = data.get('next')
        params = None  # next URL already has params
    return results


# ---------------------------------------------------------------------------
# Import steps
# ---------------------------------------------------------------------------

def get_submission_type_id(session):
    print("Fetching submission types...")
    types = get_all_pages(session, 'submission-types/')
    if not types:
        print("  ERROR: no submission types found")
        sys.exit(1)
    type_id = types[0]['id']
    print(f"  Using submission type id={type_id} ({types[0].get('name', {}).get('en', '?')})")
    return type_id


def create_rooms(session, locations, state, dry_run):
    """Create rooms for each unique location. Returns dict location→room_id."""
    print(f"\nCreating {len(locations)} room(s)...")
    room_map = {}

    for loc in sorted(locations):
        if loc in state['rooms']:
            room_id = state['rooms'][loc]
            print(f"  [skip] Room '{loc}' already in state (id={room_id})")
            room_map[loc] = room_id
            continue

        if dry_run:
            print(f"  [dry-run] Would create room: '{loc}'")
            room_map[loc] = f"dry-run-room-{loc}"
            continue

        resp = api_post(session, 'rooms/', {'name': {'en': loc}})
        if resp.ok:
            room_id = resp.json()['id']
            state['rooms'][loc] = room_id
            save_state(state)
            print(f"  Created room '{loc}' → id={room_id}")
            room_map[loc] = room_id
        else:
            print(f"  ERROR creating room '{loc}', skipping")

    return room_map


def fmt_dt(dt):
    """Format datetime as ISO 8601 with offset."""
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + dt.strftime('%z')[:6] or '+00:00'


def import_events(session, events, room_map, submission_type_id, state, dry_run):
    """Create submissions, accept, confirm, and schedule them."""
    stats = {'created': 0, 'skipped': 0, 'slot_ok': 0, 'errors': 0}

    for ev in events:
        title = ev['title']
        location = ev['location']
        start_dt = ev['start_dt']
        end_dt = ev['end_dt']
        dur = ev['duration_minutes']

        # Build a stable key for dedup
        key = f"{ev['day_date'].date()}|{title}|{ev['time_str']}"

        if key in state['submissions']:
            info = state['submissions'][key]
            if info.get('scheduled'):
                print(f"  [skip] '{title}' already imported and scheduled (code={info.get('code')})")
                stats['skipped'] += 1
                continue
            # Submission exists but slot not yet scheduled — fall through to patch slot
            code = info.get('code')
            slot_id = info.get('slot')
            if not code or not slot_id:
                stats['skipped'] += 1
                continue
            print(f"\n  Event: '{title}' (retry slot patch, code={code}, slot={slot_id})")
            patch_data = {}
            room_id = room_map.get(location)
            if room_id:
                patch_data['room'] = room_id
            if ev['start_dt']:
                patch_data['start'] = fmt_dt(ev['start_dt'])
            if patch_data:
                patch_resp = api_patch(session, f'slots/{slot_id}/', patch_data)
                if patch_resp.ok:
                    print(f"    Slot scheduled: {patch_data.get('start')}")
                    stats['slot_ok'] += 1
                    info['scheduled'] = True
                    save_state(state)
                else:
                    stats['errors'] += 1
            stats['skipped'] += 1
            continue

        print(f"\n  Event: '{title}'")
        print(f"    Date: {ev['day_date'].date()}  Time: {ev['time_str']}  Location: {location}")
        print(f"    Duration: {dur} min")

        if dry_run:
            print(f"    [dry-run] Would create submission + schedule in room '{location}'")
            stats['created'] += 1
            continue

        # Step 3: create submission
        sub_resp = api_post(session, 'submissions/', {
            'title': title,
            'abstract': '',
            'submission_type': submission_type_id,
            'duration': dur,
            'content_locale': 'en',
        })
        if not sub_resp.ok:
            stats['errors'] += 1
            continue

        sub = sub_resp.json()
        code = sub['code']
        print(f"    Submission created: code={code}")

        # Step 4a: accept
        acc_resp = api_post(session, f'submissions/{code}/accept/', {})
        if not acc_resp.ok:
            print(f"    WARNING: accept failed for {code}")
            stats['errors'] += 1

        # Step 4b: confirm
        conf_resp = api_post(session, f'submissions/{code}/confirm/', {})
        if not conf_resp.ok:
            print(f"    WARNING: confirm failed for {code}")
            # Don't abort; try to schedule anyway

        # Step 5: find WIP slot
        slots = get_all_pages(session, 'slots/', {'submission': code})
        if not slots:
            print(f"    WARNING: no slots found for {code}")
            stats['errors'] += 1
            state['submissions'][key] = {'code': code, 'slot': None}
            save_state(state)
            stats['created'] += 1
            continue

        slot_id = slots[0]['id']
        print(f"    Slot id={slot_id}")

        # Build patch payload — end is derived from start + duration, don't set it
        patch_data = {}
        room_id = room_map.get(location)
        if room_id:
            patch_data['room'] = room_id
        if start_dt:
            patch_data['start'] = fmt_dt(start_dt)

        if patch_data:
            patch_resp = api_patch(session, f'slots/{slot_id}/', patch_data)
            if patch_resp.ok:
                print(f"    Slot scheduled: {patch_data.get('start')} (duration {dur} min)")
                stats['slot_ok'] += 1
            else:
                print(f"    WARNING: slot patch failed for slot {slot_id}")
                stats['errors'] += 1

        state['submissions'][key] = {'code': code, 'slot': slot_id, 'scheduled': patch_data.get('start') is not None and patch_resp.ok if patch_data else False}
        save_state(state)
        stats['created'] += 1

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Import NSS 2026 schedule into Pretalx')
    parser.add_argument('--dry-run', action='store_true', help='Print plan without hitting API')
    parser.add_argument('--skip-rooms', action='store_true', help='Skip room creation')
    parser.add_argument('--skip-submissions', action='store_true', help='Skip submission creation')
    args = parser.parse_args()

    token = os.environ.get('PRETALX_TOKEN')
    if not token and not args.dry_run:
        print("ERROR: PRETALX_TOKEN environment variable not set")
        sys.exit(1)

    if args.dry_run:
        print("=== DRY RUN MODE — no API calls will be made ===\n")

    # Fetch and parse CSV
    csv_text = fetch_csv()
    events = parse_events(csv_text)
    print(f"\nParsed {len(events)} event(s) from schedule")

    if not events:
        print("No events found, exiting.")
        sys.exit(0)

    # Print summary of what was parsed
    locations = sorted(set(ev['location'] for ev in events))
    print(f"Unique locations ({len(locations)}): {', '.join(locations)}")

    if args.dry_run:
        print("\n--- Events that would be imported ---")
        for ev in events:
            start = fmt_dt(ev['start_dt']) if ev['start_dt'] else 'NO TIME'
            end = fmt_dt(ev['end_dt']) if ev['end_dt'] else '?'
            print(f"  [{ev['day_date'].date()}] {ev['title'][:60]:<60} | {start} - {end} | {ev['location']}")
        print("\n--- Rooms that would be created ---")
        for loc in locations:
            print(f"  {loc}")
        print("\n[dry-run complete]")
        return

    # Live run
    state = load_state()
    session = make_session(token)

    # Step 1: get submission type
    submission_type_id = get_submission_type_id(session)

    # Step 2: create rooms
    room_map = {}
    if not args.skip_rooms:
        room_map = create_rooms(session, locations, state, dry_run=False)
    else:
        print("\nSkipping room creation (--skip-rooms)")
        # Try to load existing room map from state
        for loc in locations:
            if loc in state['rooms']:
                room_map[loc] = state['rooms'][loc]

    # Step 3-5: create and schedule submissions
    stats = {'created': 0, 'skipped': 0, 'slot_ok': 0, 'errors': 0}
    if not args.skip_submissions:
        print(f"\nImporting {len(events)} events...")
        stats = import_events(session, events, room_map, submission_type_id, state, dry_run=False)
    else:
        print("\nSkipping submission creation (--skip-submissions)")

    # Summary
    print(f"""
=== Import Summary ===
  Rooms created:       {len(state['rooms'])}
  Submissions created: {stats['created']}
  Submissions skipped: {stats['skipped']}
  Slots scheduled:     {stats['slot_ok']}
  Errors:              {stats['errors']}
""")


if __name__ == '__main__':
    main()
