#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "python-dotenv", "pypdf"]
# ///
"""
Find and patch descriptions for empty session blocks.
Only extracts prose paragraphs (not schedule-table rows).
"""

import os, re, sys
from pathlib import Path
import requests
import pypdf
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

TOKEN = os.environ["PRETALX_TOKEN"]
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
API = "https://talks.caving.dev/api/events/nss-convention-2026"
PDF_PATH = Path(__file__).parent / "2026-06-15" / "PrintCopy - 2026_NSSProgram_FINALv2.pdf"


def get_all(url):
    results = []
    while url:
        url = url.replace('http://', 'https://', 1)
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        d = r.json()
        results.extend(d['results'])
        url = d.get('next')
    return results


def extract_pages(start_page, end_page):
    reader = pypdf.PdfReader(PDF_PATH)
    texts = []
    for i in range(start_page - 1, end_page):
        text = reader.pages[i].extract_text() or ''
        text = re.sub(r'NSS Convention 2026[—\-]Corydon, Indiana\s+\d+\s*\n?', '', text)
        texts.append(text)
    return '\n'.join(texts)


def is_schedule_line(line):
    """True if line looks like a schedule table row (time + room)."""
    return bool(re.search(r'\b\d{1,2}:\d{2}|\bNoon\b', line) and re.search(r'\b\d{3}\b|\bAuditorium\b|\bFairgrounds\b', line))


def extract_prose_after(full_text, heading, max_chars=800):
    """
    Find heading in full_text, skip header lines (time/location/presenter),
    then grab prose sentences. Returns None if no prose found.
    """
    # Find the heading (case-insensitive, partial match)
    heading_norm = re.sub(r'\s+', ' ', heading).strip()
    pattern = re.compile(re.escape(heading_norm[:30]), re.IGNORECASE)
    m = pattern.search(full_text)
    if not m:
        # Try shorter prefix
        pattern = re.compile(re.escape(heading_norm[:20]), re.IGNORECASE)
        m = pattern.search(full_text)
    if not m:
        return None

    # Get text after the heading line
    rest = full_text[m.end():]
    lines = rest.split('\n')

    body_lines = []
    skip_budget = 6  # skip up to 6 non-prose lines for header/time/location
    skipped = 0
    found_prose = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if found_prose:
                body_lines.append('')
            continue

        # Stop at what looks like the next section heading:
        # short line that doesn't end with a period, followed by a time pattern
        if found_prose and len(stripped) < 50 and not stripped.endswith('.') and not stripped.endswith(','):
            # Check if it looks like a new section start
            if stripped[0].isupper() and not re.search(r'\d', stripped):
                break
        if found_prose and is_schedule_line(stripped):
            break

        is_prose = (
            len(stripped) > 50 and
            stripped[0].isupper() and
            not is_schedule_line(stripped) and
            not re.match(r'^\d{1,2}:\d{2}', stripped) and
            '@' not in stripped
        )

        if not found_prose:
            if is_prose and skipped >= 1:
                found_prose = True
                body_lines.append(stripped)
            else:
                skipped += 1
                if skipped > skip_budget:
                    break
        else:
            body_lines.append(stripped)

        if sum(len(l) for l in body_lines) > max_chars:
            break

    if not body_lines:
        return None

    text = ' '.join(l for l in body_lines if l).strip()
    text = re.sub(r'  +', ' ', text)

    # Must have at least one sentence (period in middle)
    if not re.search(r'\.\s', text) and not text.endswith('.'):
        return None

    return text if len(text) > 60 else None


def main():
    patch = '--patch' in sys.argv

    print("Fetching submissions with empty abstract and description...")
    subs = get_all(f"{API}/submissions/?limit=100")
    empty = {s['code']: s['title'] for s in subs
             if not (s.get('abstract') or '').strip()
             and not (s.get('description') or '').strip()}
    print(f"  {len(empty)} empty sessions\n")

    print("Extracting PDF program guide (pages 45-59)...")
    full_text = extract_pages(45, 59)

    found = {}
    not_found = []

    for code, title in sorted(empty.items(), key=lambda x: x[1]):
        prose = extract_prose_after(full_text, title)
        if prose:
            found[code] = (title, prose)
        else:
            not_found.append(title)

    print(f"=== Found prose descriptions ({len(found)}) ===")
    for code, (title, prose) in found.items():
        print(f"\n  [{code}] {title[:65]}")
        print(f"  {prose[:200]!r}")

    print(f"\n=== No prose description found ({len(not_found)}) ===")
    for t in not_found:
        print(f"  {t[:80]}")

    if patch and found:
        print(f"\nPatching {len(found)} submissions...")
        for code, (title, prose) in found.items():
            r = requests.patch(f"{API}/submissions/{code}/",
                               json={'abstract': prose}, headers=HEADERS)
            status = 'ok' if r.ok else f'ERROR {r.status_code}'
            print(f"  {status} [{code}] {title[:55]}")


if __name__ == '__main__':
    main()
