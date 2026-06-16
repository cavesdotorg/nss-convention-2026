#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "python-dotenv",
#   "openpyxl",
# ]
# ///
"""
Re-import NSS 2026 schedule from the June 2026 final XLSX into Pretalx.

Source: 2026-06-15/ForPrint NSS2026_Schedule_FINAL_6_14_26 LD.xlsx
Cross-referenced against: 2026-06-15/PrintCopy - 2026_NSSProgram_FINALv2.pdf

Where XLSX and PDF conflict, the PDF is authoritative. See README.md for
known discrepancies that remain unresolved.

Usage:
    uv run reimport_schedule.py --dry-run
    uv run reimport_schedule.py --delete-all --dry-run
    uv run reimport_schedule.py --delete-all
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openpyxl
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XLSX_PATH = (
    Path(__file__).parent
    / "2026-06-15"
    / "ForPrint NSS2026_Schedule_FINAL_6_14_26 LD.xlsx"
)
API_BASE = "https://talks.caving.dev/api/events/nss-convention-2026"
STATE_FILE = os.path.join(os.path.dirname(__file__), "import_state.json")

TZ_OFFSET = timezone(timedelta(hours=-4))  # US Eastern in July

# (day_date, event_col, time_col, where_col) — 0-indexed columns in the XLSX
DAY_COLUMNS = [
    (datetime(2026, 7, 6, tzinfo=TZ_OFFSET), 2, 3, 4),    # Monday
    (datetime(2026, 7, 7, tzinfo=TZ_OFFSET), 6, 7, 8),    # Tuesday
    (datetime(2026, 7, 8, tzinfo=TZ_OFFSET), 10, 11, 12), # Wednesday
    (datetime(2026, 7, 9, tzinfo=TZ_OFFSET), 14, 15, 16), # Thursday
    (datetime(2026, 7, 10, tzinfo=TZ_OFFSET), 18, 19, 20), # Friday
]

DEFAULT_DURATION_MINUTES = 60

# Room name normalization (keys are lowercased for lookup)
ROOM_NAME_MAP = {
    # Numeric rooms (openpyxl returns these as floats)
    '100': '100', '101': '101', '102': '102', '104': '104',
    '110': '110', '112': '112', '154': '154', '202': '202',
    '205': '205', '223': '223', '228': '228', '254': '254',
    '283': '283',
    # Variants with parenthetical suffixes
    'vendors area (aux. gym)': 'Vendors Area',
    'vendors area         (aux. gym)': 'Vendors Area',
    'vendors area catwalk (aux. gym)': 'Vendors area catwalk',
    'vendors area catwalk          (aux. gym)': 'Vendors area catwalk',
    # Whitespace / case variants
    'high school     main entrance': 'High School Main Entrance',
    'high school main entrance': 'High School Main Entrance',
    'main ent hs': 'High School Main Entrance',
    'in-cave': 'in-cave',
    'in cave': 'in-cave',
    'campground stage': 'Campground stage',
    'fairgrounds ': 'Fairgrounds',
    'windell  ag  building': 'Windell  Ag  Building',
    'windell ag building': 'Windell  Ag  Building',
    'jr. high gym': 'Junior High Gym',
}

# Titles to skip outright (header rows, day labels)
SKIP_TITLES = frozenset({
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
    'event', 'title', 'session',
})


def is_descriptive_note(title: str) -> bool:
    """Return True for long informational blurbs that are not schedule items."""
    if len(title) > 120:
        return True
    keywords = (
        'see program guide', 'mammoth cave floor map', 'wyandotte cave guided tours',
        'special event station', 'cavesim', 'biology field trip',
        'karst hydrology of the lost river', 'stargazer float trip',
        'departing  cave country canoes', 'departs at 9am',
    )
    return any(k in title.lower() for k in keywords)


# ---------------------------------------------------------------------------
# Known corrections (PDF overrides XLSX where they conflict)
# ---------------------------------------------------------------------------

def apply_corrections(events):
    """
    Apply corrections where the PDF is authoritative over the XLSX.
    See README.md for full discrepancy notes.
    """
    corrected = []
    for ev in events:
        # Collapse runs of whitespace in titles (XLSX has many multi-space artifacts)
        ev['title'] = re.sub(r'\s+', ' ', ev['title']).strip()

        # XLSX typos
        ev['title'] = ev['title'].replace('Contetsts', 'Contests')
        ev['title'] = ev['title'].replace('Awrds', 'Awards')

        # PDF override: Mon lunch vertical climbing starts at 12:30 not 1:00pm
        # (XLSX says "1:00pm start"; PDF schedule table says "12:30 start")
        if (
            ev['title'] == 'Vertical Climbing Contests'
            and ev['time_str'] == '1:00pm start'
            and ev['day_date'].day == 6
        ):
            ev['time_str'] = '12:30 start'
            start, end = parse_time_range('12:30 start', ev['day_date'])
            ev['start_dt'] = start
            ev['end_dt'] = end
            ev['duration_minutes'] = duration_minutes(start, end)

        # Farewell Party has room embedded in time string; extract it
        if (
            'at fairgrounds' in (ev['time_str'] or '').lower()
            and ev['location'] == 'TBD'
        ):
            ev['location'] = 'Fairgrounds'

        corrected.append(ev)
    return corrected


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'rooms': {}, 'submissions': {}}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

def normalize_room(raw) -> str:
    if raw is None:
        return 'TBD'
    if isinstance(raw, (int, float)):
        raw = str(int(raw))
    s = str(raw).strip()
    return ROOM_NAME_MAP.get(s.lower(), s) or 'TBD'


def normalize_time_str(s: str) -> str:
    s = s.strip()
    s = re.sub(r'\s*-\s*', '-', s)
    return s


def parse_single_time(t: str, day_date: datetime, assume_pm: bool = False):
    t = t.strip()
    if not t:
        return None
    if t.lower() == 'noon':
        return day_date.replace(hour=12, minute=0, second=0, microsecond=0)
    if t.lower() == 'midnight':
        next_day = day_date + timedelta(days=1)
        return next_day.replace(hour=0, minute=0, second=0, microsecond=0)

    t = re.sub(r'\s+start\s*$', '', t, flags=re.IGNORECASE).strip()
    t = re.sub(r'\s+at\s+fairgrounds\s*$', '', t, flags=re.IGNORECASE).strip()

    am_pm = None
    m = re.match(r'^(\d{1,2}(?::\d{2})?)\s*(am|pm)$', t, re.IGNORECASE)
    if m:
        t, am_pm = m.group(1), m.group(2).lower()

    if ':' in t:
        parts = t.split(':')
        try:
            hour, minute = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return None
    else:
        try:
            hour, minute = int(t), 0
        except ValueError:
            return None

    if am_pm == 'pm' and hour != 12:
        hour += 12
    elif am_pm == 'am' and hour == 12:
        hour = 0
    elif am_pm is None:
        if assume_pm and 1 <= hour <= 11:
            hour += 12
        elif hour < 8:
            hour += 12

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return day_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def parse_time_range(time_str: str, day_date: datetime, assume_pm: bool = False):
    if not time_str:
        return None, None
    time_str = normalize_time_str(str(time_str))
    # Multi-segment times like "2:00-4:00   4:00-5:00" — take first range only
    time_str = re.split(r'\s{3,}', time_str)[0].strip()

    parts = time_str.split('-', 1)
    end_token = parts[1].strip() if len(parts) == 2 else ''

    if end_token.lower() == 'midnight':
        assume_pm = True

    start_dt = parse_single_time(parts[0], day_date, assume_pm=assume_pm)
    if start_dt is None:
        return None, None

    if end_token:
        end_dt = parse_single_time(end_token, day_date)
        if end_dt is not None and start_dt.hour >= 18 and 1 <= end_dt.hour <= 11:
            end_pm = end_dt.replace(hour=end_dt.hour + 12)
            if end_pm > start_dt:
                end_dt = end_pm
        if end_dt is not None and end_dt <= start_dt:
            end_dt += timedelta(days=1)
        if end_dt is not None and end_dt.date() != start_dt.date():
            end_dt = (start_dt + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
    else:
        end_dt = None

    return start_dt, end_dt


def duration_minutes(start_dt, end_dt) -> int:
    if start_dt and end_dt:
        return max(int((end_dt - start_dt).total_seconds() / 60), 1)
    return DEFAULT_DURATION_MINUTES


# ---------------------------------------------------------------------------
# XLSX parsing
# ---------------------------------------------------------------------------

def parse_xlsx(path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['FINAL']
    rows = list(ws.iter_rows(values_only=True))

    events = []
    in_evening = False

    for row in rows:
        col1 = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ''
        if col1.lower() == 'evening':
            in_evening = True

        for day_date, ev_col, time_col, where_col in DAY_COLUMNS:
            def cell(col):
                v = row[col] if col < len(row) else None
                if v is None:
                    return ''
                s = str(v).strip()
                return '' if s in ('None', ' ') else s

            title = cell(ev_col)
            time_raw = row[time_col] if time_col < len(row) else None
            time_str = str(time_raw).strip() if time_raw is not None else ''
            where_raw = row[where_col] if where_col < len(row) else None
            location = normalize_room(where_raw)

            if not title:
                continue
            if title.lower() in SKIP_TITLES:
                continue
            if is_descriptive_note(title):
                continue
            if not time_str or time_str in ('None', ' '):
                continue

            start_dt, end_dt = parse_time_range(time_str, day_date, assume_pm=in_evening)
            dur = duration_minutes(start_dt, end_dt)

            events.append({
                'title': title,
                'location': location,
                'day_date': day_date,
                'start_dt': start_dt,
                'end_dt': end_dt,
                'duration_minutes': dur,
                'time_str': time_str,
            })

    return apply_corrections(events)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def make_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json',
    })
    return s


def api_get_all(session, path: str) -> list:
    results = []
    url = f"{API_BASE}/{path.lstrip('/')}"
    while url:
        resp = session.get(url, timeout=30)
        if not resp.ok:
            print(f"  GET {url} → {resp.status_code}: {resp.text[:200]}")
            break
        data = resp.json()
        if isinstance(data, list):
            results.extend(data)
            break
        results.extend(data.get('results', []))
        url = (data.get('next') or '').replace('http://', 'https://') or None
    return results


def api_post(session, path: str, data: dict):
    url = f"{API_BASE}/{path.lstrip('/')}"
    resp = session.post(url, json=data, timeout=30)
    if not resp.ok:
        print(f"  POST {url} → {resp.status_code}: {resp.text[:500]}")
    return resp


def api_patch(session, path: str, data: dict):
    url = f"{API_BASE}/{path.lstrip('/')}"
    resp = session.patch(url, json=data, timeout=30)
    if not resp.ok:
        print(f"  PATCH {url} → {resp.status_code}: {resp.text[:500]}")
    return resp


def api_delete(session, path: str):
    url = f"{API_BASE}/{path.lstrip('/')}"
    resp = session.delete(url, timeout=30)
    if not resp.ok and resp.status_code != 404:
        print(f"  DELETE {url} → {resp.status_code}: {resp.text[:200]}")
    return resp


def fmt_dt(dt) -> str | None:
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + dt.strftime('%z')[:6]


# ---------------------------------------------------------------------------
# Delete all existing submissions
# ---------------------------------------------------------------------------

def delete_all_submissions(session, state: dict, dry_run: bool):
    print("\nFetching all submissions from Pretalx...")
    subs = api_get_all(session, 'submissions/?limit=100')
    print(f"  Found {len(subs)} submission(s) to delete")

    for sub in subs:
        code = sub['code']
        title = sub.get('title', '?')
        if dry_run:
            print(f"  [dry-run] Would delete {code} — {title}")
        else:
            resp = api_delete(session, f'submissions/{code}/')
            status = 'ok' if resp.status_code in (200, 204, 404) else f'ERROR {resp.status_code}'
            print(f"  DELETE {code} ({title[:50]}) → {status}")

    if not dry_run:
        state['submissions'] = {}
        save_state(state)
        print("  Cleared submissions from state")


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def get_submission_type_id(session) -> int:
    print("Fetching submission types...")
    types = api_get_all(session, 'submission-types/')
    if not types:
        print("  ERROR: no submission types found")
        sys.exit(1)
    type_id = types[0]['id']
    print(f"  Using type id={type_id} ({types[0].get('name', {}).get('en', '?')})")
    return type_id


def ensure_rooms(session, locations: list[str], state: dict, dry_run: bool) -> dict:
    print(f"\nChecking {len(locations)} room(s)...")
    room_map = {}
    for loc in sorted(locations):
        if loc in state['rooms']:
            room_map[loc] = state['rooms'][loc]
            print(f"  [exists] '{loc}' (id={state['rooms'][loc]})")
            continue
        if dry_run:
            print(f"  [dry-run] Would create room: '{loc}'")
            room_map[loc] = f'dry-{loc}'
            continue
        resp = api_post(session, 'rooms/', {'name': {'en': loc}})
        if resp.ok:
            room_id = resp.json()['id']
            state['rooms'][loc] = room_id
            save_state(state)
            print(f"  Created '{loc}' → id={room_id}")
            room_map[loc] = room_id
        else:
            print(f"  ERROR creating room '{loc}'")
    return room_map


def import_events(session, events: list, room_map: dict, type_id: int,
                  state: dict, dry_run: bool) -> dict:
    stats = {'created': 0, 'skipped': 0, 'slot_ok': 0, 'errors': 0}

    for ev in events:
        title = ev['title']
        location = ev['location']
        start_dt = ev['start_dt']
        end_dt = ev['end_dt']
        dur = ev['duration_minutes']
        key = f"{ev['day_date'].date()}|{title}|{ev['time_str']}"

        if key in state['submissions'] and state['submissions'][key].get('scheduled'):
            print(f"  [skip] '{title}' already scheduled")
            stats['skipped'] += 1
            continue

        print(f"\n  [{ev['day_date'].date()}] {title}")
        print(f"    {ev['time_str']} → {location} ({dur} min)")

        if dry_run:
            print(f"    start={fmt_dt(start_dt) or 'NO TIME'}")
            stats['created'] += 1
            continue

        sub_resp = api_post(session, 'submissions/', {
            'title': title,
            'abstract': '',
            'submission_type': type_id,
            'duration': dur,
            'content_locale': 'en',
        })
        if not sub_resp.ok:
            stats['errors'] += 1
            continue

        code = sub_resp.json()['code']
        print(f"    code={code}")

        api_post(session, f'submissions/{code}/accept/', {})
        api_post(session, f'submissions/{code}/confirm/', {})

        slots = api_get_all(session, f'slots/?submission={code}')
        if not slots:
            print(f"    WARNING: no slots found for {code}")
            state['submissions'][key] = {'code': code, 'slot': None, 'scheduled': False, 'title': title}
            save_state(state)
            stats['errors'] += 1
            stats['created'] += 1
            continue

        slot_id = slots[0]['id']
        patch_data = {}
        room_id = room_map.get(location)
        if room_id:
            patch_data['room'] = room_id
        if start_dt:
            patch_data['start'] = fmt_dt(start_dt)

        scheduled = False
        if patch_data:
            patch_resp = api_patch(session, f'slots/{slot_id}/', patch_data)
            if patch_resp.ok:
                print(f"    slot={slot_id} start={patch_data.get('start')}")
                stats['slot_ok'] += 1
                scheduled = True
            else:
                stats['errors'] += 1

        state['submissions'][key] = {
            'code': code, 'slot': slot_id, 'scheduled': scheduled, 'title': title,
        }
        save_state(state)
        stats['created'] += 1

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Re-import NSS 2026 schedule from final XLSX (cross-checked against PDF)'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Print plan without making any API calls')
    parser.add_argument('--delete-all', action='store_true',
                        help='Delete all existing Pretalx submissions before importing')
    parser.add_argument('--skip-rooms', action='store_true',
                        help='Skip room creation (use existing rooms from state)')
    args = parser.parse_args()

    token = os.environ.get('PRETALX_TOKEN')
    if not token and not args.dry_run:
        print("ERROR: PRETALX_TOKEN not set in pretalx.env")
        sys.exit(1)

    if args.dry_run:
        print("=== DRY RUN — no API calls will be made ===\n")

    print(f"Parsing {XLSX_PATH.name}...")
    events = parse_xlsx(XLSX_PATH)
    print(f"Parsed {len(events)} events")

    locations = sorted(set(ev['location'] for ev in events))
    print(f"Locations ({len(locations)}): {', '.join(locations)}")

    if args.dry_run:
        print("\n--- Events ---")
        for ev in events:
            start = fmt_dt(ev['start_dt']) or 'NO TIME'
            end = fmt_dt(ev['end_dt']) or '?'
            flag = '' if ev['start_dt'] else '  *** NO TIME ***'
            print(f"  [{ev['day_date'].date()}] {ev['title'][:55]:<55} | {start} — {end} | {ev['location']}{flag}")
        if args.delete_all:
            print("\n[dry-run] Would delete all existing submissions first")
        state = load_state()
        new_rooms = [loc for loc in locations if loc not in state['rooms']]
        if new_rooms:
            print(f"\n--- New rooms to create ---")
            for loc in new_rooms:
                print(f"  '{loc}'")
        return

    state = load_state()
    session = make_session(token)

    if args.delete_all:
        delete_all_submissions(session, state, dry_run=False)

    type_id = get_submission_type_id(session)

    room_map = {}
    if not args.skip_rooms:
        room_map = ensure_rooms(session, locations, state, dry_run=False)
    else:
        for loc in locations:
            if loc in state['rooms']:
                room_map[loc] = state['rooms'][loc]

    print(f"\nImporting {len(events)} events...")
    stats = import_events(session, events, room_map, type_id, state, dry_run=False)

    print(f"""
=== Summary ===
  Events imported:   {stats['created']}
  Already scheduled: {stats['skipped']}
  Slots placed:      {stats['slot_ok']}
  Errors:            {stats['errors']}
""")


if __name__ == '__main__':
    main()
