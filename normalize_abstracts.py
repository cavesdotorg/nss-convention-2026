#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "python-dotenv",
# ]
# ///
"""
Remove hard line-wraps from abstracts (PDF extraction artifact).
Single \\n → space; double \\n\\n (paragraph breaks) preserved.
"""

import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

import os
TOKEN = os.environ["PRETALX_TOKEN"]
API_BASE = "https://talks.caving.dev/api/events/nss-convention-2026"
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}


def unwrap(text: str) -> str:
    if not text:
        return text
    # Split on paragraph breaks, unwrap each paragraph, rejoin
    paragraphs = re.split(r'\n{2,}', text)
    paragraphs = [re.sub(r'\n', ' ', p).strip() for p in paragraphs]
    # Collapse multiple spaces
    paragraphs = [re.sub(r'  +', ' ', p) for p in paragraphs]
    return '\n\n'.join(p for p in paragraphs if p)


def get_all(url):
    results = []
    while url:
        url = url.replace('http://', 'https://', 1)
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        results.extend(data['results'])
        url = data.get('next')
    return results


def main():
    dry_run = '--dry-run' in sys.argv
    print("Fetching all submissions...")
    subs = get_all(f"{API_BASE}/submissions/?limit=100")
    print(f"  {len(subs)} submissions")

    updated = skipped = 0
    for s in subs:
        code = s['code']
        abstract = s.get('abstract') or ''
        new_abstract = unwrap(abstract)
        if new_abstract == abstract:
            skipped += 1
            continue
        if dry_run:
            print(f"\n[dry] {s['title'][:60]}")
            print(f"  before: {abstract[:80]!r}")
            print(f"  after:  {new_abstract[:80]!r}")
            updated += 1
        else:
            r = requests.patch(f"{API_BASE}/submissions/{code}/",
                               json={'abstract': new_abstract}, headers=HEADERS)
            if r.ok:
                updated += 1
                print(f"  patched {code}: {s['title'][:55]}")
            else:
                print(f"  ERROR {code}: {r.status_code} {r.text[:80]}")

    print(f"\nDone. {'Would update' if dry_run else 'Updated'} {updated}, unchanged {skipped}.")


if __name__ == '__main__':
    main()
