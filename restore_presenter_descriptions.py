#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "python-dotenv"]
# ///
"""
Restore correct presenter names in description fields.
import_talks.py had wrong presenter names for ~79 talks; the correct names
come from the PDF program guide (pages 45-59).
"""

import os, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

TOKEN = os.environ["PRETALX_TOKEN"]
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
API = "https://talks.caving.dev/api/events/nss-convention-2026"

# (code, correct_presenter) from PDF program guide pages 45-59
CORRECTIONS = [
    # Tuesday US Exploration morning
    ("JVQKJK", "Maggie Brosky"),
    ("LTXCKF", "Mike Ficco, Katarina Kosič Ficco"),
    ("RF77U7", "Rand Heazlitt, Marion Ziemons"),
    ("LLGEBQ", "Mark Minton"),
    ("9MC7D9", "Rand Heazlitt, Marion Ziemons"),
    ("3RJDA8", "Mark Minton and Yvonne Droms"),
    ("KCHZ3T", "Joel Despain and Niles Lathrop"),  # Whigpistle 2026

    # Tuesday Conservation morning
    ("KRBSFE", "Penelope Vorster"),
    ("DTEUHC", "Robert Weck"),
    ("CJS8EE", "Drew Rollin Thompson"),
    ("HPN9BW", "Roy A. Jameson"),
    ("XS9R3V", "Geary Schindel"),
    ("LCHTEY", "Katarina Kosič Ficco, Chad Harrold, Wil Orndorff"),
    ("CHXURT", "Val Hildreth-Werker"),

    # Tuesday US Exploration afternoon
    ("YUHZA9", "Riley Drake, Riannon Colton and John T. M. Lyles"),
    ("N8A8TW", "Christian Stenner, Lee Florea"),
    ("QDS9QS", "Chelsea Dau"),
    ("FGPGAK", "Joel Despain, Niles Lathrop, Heather Veerkamp"),
    ("X7VKPR", "John Rosenfeld"),

    # Tuesday Conservation afternoon
    ("TTEVRG", "Tony Schmitt"),
    ("TQRT7A", "Dave Jackson"),
    ("WDCKVJ", "Cave Animal of the Year Team, NSS Cave Conservation and Science Division"),
    ("YLPEW8", "Dean A. Wiseman"),
    ("LC7R8Z", "Lê Lưu Dũng, Founder & CEO of Jungle Boss Tours"),

    # Wednesday International morning
    ("QTQHNT", "Bill Steele"),
    ("9JABTJ", "Megan Necessary & Peter Sprouse"),
    ("WCXAVH", "Matt Covington & Aidan Ward"),
    ("KGNWYT", "Carl Haken"),
    ("7H3SUP", "Joel Despain, Nic Barth, Carol Vesely"),

    # Wednesday Biospeleology
    ("AFK7SD", "Jacob Schaefer"),
    ("JZHX3X", "Eric Maxwell"),
    ("XYX9JM", "Lael Anderson"),
    ("CEKDDL", "Isuru Ethige"),
    ("TSHFEJ", "Amelia Freeland"),
    ("3PLDSS", "Suzanna Brauer"),
    ("Z77NGM", "Jerry Lewis"),

    # Wednesday Culture and Caving
    ("FLEJH8", "Catherine Bishop"),
    ("JGGNBG", "Jacqueline F. Heggen, J. Max Koether, and Anna Drabik"),
    ("Z8MPPC", "Catherine Bishop"),

    # Wednesday International afternoon
    ("EKVJKX", "Dustin Kisner"),

    # Thursday Spelean History
    ("RGBHTD", "Cato Holler and Nancy Holler Aulenbach"),
    ("ZBB3WN", "Gary Roberson"),
    ("JAQCKG", "John M. Benton"),
    ("VMDCR8", "Joseph C. Douglas"),
    ("MZW3VT", "Katie Algeo"),
    ("DJWQWK", "Ernst H. Kastning"),
    ("WS79S9", "Michael McEachern"),
    ("PVB3PZ", "Jack Speece"),

    # Thursday Vertical
    ("QJHFPJ", "Philip Rykwalder"),
    ("YH8FSH", "Ron Miller"),
    ("K9799B", "Gary Storrick"),
    ("KDCE9D", "Rachel Saker"),
    ("LW7FXW", "Kevin Mulligan"),
    ("CLYYPW", "Tim White"),
    ("N3M8MN", "Jenna Crabtree"),
    ("SDPJVC", "Rachel Saker"),
    # E3FSMZ already fixed to Jerin Manalel

    # Thursday Paleontology
    ("E89WP9", "Davis Gunnin, Blaine W. Schubert, and Shay Maden"),
    ("JS3QPU", "Shay Maden, Blaine W. Schubert, Davis Gunnin, and Keila Bredehoeft"),

    # Thursday Cave Photography
    ("SG9HJD", "Dan Legnini"),
    ("VBCM7E", "Dave Bunnell"),

    # Thursday Archaeology afternoon
    ("UBNCKV", "Joseph C. Douglas, Jim Honaker, and Larry W. Johnson"),

    # Friday Geology & Geography
    ("TPMWZW", "Lee Florea"),
    ("CGDGZQ", "Lee Florea"),
    ("XFVBQL", "Ljubomir Risteski"),
    ("JSAP8C", "Perla Romero"),
    ("WBPC8W", "Riannon Colton"),
    ("JBE8TB", "Maggie Brosky"),
    ("XLNPL7", "Greg Brick"),
    ("KHWDRF", "Matt Covington"),
    ("NDJQPE", "Matt Covington"),

    # Friday Survey & Cartography
    ("YTQULA", "Michael A. Raymond"),
    ("E93EGS", "Philip Balister"),
    ("VVR8UK", "Philip Balister"),
    ("YGF9QE", "Dean Wiseman"),
    ("PAYC8F", "Garry Petrie"),
    ("8XYDFB", "Joe Walko"),
    ("ELKPFF", "Dwight Livingston"),
    ("FTD7RP", "Dwight Livingston"),
    ("9YBURH", "Zach Englebert"),
]


def main():
    dry_run = '--dry-run' in sys.argv
    patched = errors = 0

    for code, presenter in CORRECTIONS:
        if dry_run:
            print(f"  [dry] [{code}] → {presenter!r}")
            patched += 1
            continue

        r = requests.patch(f"{API}/submissions/{code}/",
                           json={'description': presenter}, headers=HEADERS)
        if r.ok:
            print(f"  patched [{code}] → {presenter}")
            patched += 1
        else:
            print(f"  ERROR [{code}]: {r.status_code} {r.text[:80]}")
            errors += 1

    print(f"\nDone. {'Would patch' if dry_run else 'Patched'} {patched}, errors {errors}.")


if __name__ == '__main__':
    main()
