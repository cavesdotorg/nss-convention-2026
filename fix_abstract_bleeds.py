#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "python-dotenv"]
# ///
"""
Fix abstracts where PDF boundary detection grabbed the next talk's content.
Each entry specifies the submission code and the string to truncate at.
"""

import os, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

TOKEN = os.environ["PRETALX_TOKEN"]
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
API = "https://talks.caving.dev/api/events/nss-convention-2026"

# (code, truncate_at_string) — abstract is cut at the first occurrence of this string
TRUNCATIONS = [
    ("9YBURH",  "\n\nVertical Session"),
    ("AQH39E",  "\n\nExploration: USA Session"),
    ("E3FSMZ",  "\n\nAbout the Presenter"),
    ("EKVJKX",  "\n\nGeology and Geography Session"),
    ("FGPGAK",  "\n\nWhigpistle Cave Project Update"),
    ("JBE8TB",  "\n\nMineralogical and Genetic Controls"),
    ("JGHNBQ",  "\n\nSediment geochemistry"),
    ("KHWDRF",  "\n\nPaleontology Session"),
    ("LAMKYY",  "\n\nBiospeleology Session Chair"),
    ("LC7R8Z",  "\n\nCommunications and Electronics Session Chair"),
    ("N8A8TW",  "\n\nCave Mapping and Inventory of a Significant Kentucky"),
    ("PVB3PZ",  "\n\nSurvey and Cartography Session"),
    ("WBPC8W",  "\n\nInvestigating Harlansburg Cave"),
    ("XFVBQL",  "\n\nQuantifying and Comparing Sinkhole Morphometry"),
    ("Z77NGM",  "\n\nCave Conservation and Management Session Chair"),
    ("Z8MPPC",  "\n\nExploration: Regional"),
]


def get_sub(code):
    r = requests.get(f"{API}/submissions/{code}/", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def main():
    dry_run = '--dry-run' in sys.argv
    patched = skipped = errors = 0

    for code, cut_at in TRUNCATIONS:
        sub = get_sub(code)
        abstract = sub.get('abstract') or ''
        idx = abstract.find(cut_at)
        if idx == -1:
            print(f"  [{code}] cut string not found: {cut_at[:40]!r} — skipping")
            skipped += 1
            continue

        new_abstract = abstract[:idx].strip()
        if dry_run:
            print(f"  [dry] [{code}] {sub['title'][:55]}")
            print(f"    cut at pos {idx}, was {len(abstract)}c → now {len(new_abstract)}c")
            print(f"    ends with: ...{new_abstract[-80:]!r}")
            patched += 1
        else:
            r = requests.patch(f"{API}/submissions/{code}/",
                               json={'abstract': new_abstract}, headers=HEADERS)
            if r.ok:
                print(f"  patched [{code}] {sub['title'][:55]} ({len(abstract)}c → {len(new_abstract)}c)")
                patched += 1
            else:
                print(f"  ERROR [{code}]: {r.status_code} {r.text[:80]}")
                errors += 1

    print(f"\nDone. {'Would patch' if dry_run else 'Patched'} {patched}, skipped {skipped}, errors {errors}.")


if __name__ == '__main__':
    main()
