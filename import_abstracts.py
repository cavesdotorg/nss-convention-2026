#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "python-dotenv",
#   "pypdf",
# ]
# ///
"""
Extract abstracts from the program guide PDF (pages 60-112) and patch
them onto the corresponding talk submissions in Pretalx.

Usage:
    uv run import_abstracts.py --dry-run
    uv run import_abstracts.py
"""

import argparse
import json
import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pypdf
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

API_BASE = "https://talks.caving.dev/api/events/nss-convention-2026"
PDF_PATH = Path(__file__).parent / "2026-06-15" / "PrintCopy - 2026_NSSProgram_FINALv2.pdf"
STATE_FILE = os.path.join(os.path.dirname(__file__), "import_state.json")

# ---------------------------------------------------------------------------
# Talk titles (must match import_talks.py exactly for state-key lookup)
# ---------------------------------------------------------------------------

TALKS = [
    ("2026-07-06","09:05","Auditorium","Regional Geology and GIS Overview"),
    ("2026-07-06","09:15","Auditorium","Ohio Cave Survey—State Overview"),
    ("2026-07-06","09:25","Auditorium","Indiana Cave Survey—State Overview"),
    ("2026-07-06","09:35","Auditorium","Kentucky Speleological Survey"),
    ("2026-07-06","09:45","Auditorium","Exploring Courtey Cave and the Cave Systems of Central Ohio's Scioto River Corridor"),
    ("2026-07-06","10:05","Auditorium","Caves of Edwards Mountain & Wayne County (incl Spelunger Cave)"),
    ("2026-07-06","10:55","Auditorium","Modern Exploration in Big Bat Cave"),
    ("2026-07-06","11:15","Auditorium","Pless Cave—Exploration & Mapping"),
    ("2026-07-06","11:35","Auditorium","James Cave, The Cave, The Exploration"),
    ("2026-07-06","13:00","Auditorium","Big Bat Cave—A Brief History of Exploration"),
    ("2026-07-06","13:20","Auditorium","Sandstone Caves in Northeast Ohio"),
    ("2026-07-06","13:40","Auditorium","Great Caves, Great Survey Projects in Rockcastle County, Kentucky"),
    ("2026-07-06","14:10","Auditorium","Twenty Kentucky Caves that Might be Bigger than Mammoth"),
    ("2026-07-06","14:50","Auditorium","Fisher Ridge Cave System Project 2023-2026 Update"),
    ("2026-07-06","15:10","Auditorium","Roppel Cave"),
    ("2026-07-06","15:30","Auditorium","History of Cave Exploration in Wayne County, Kentucky"),
    ("2026-07-06","15:50","Auditorium","Cedar Grove Cave—Discovery of a Virgin Cave"),
    ("2026-07-06","16:10","Auditorium","Whigpistle Cave Project Update"),
    ("2026-07-06","16:30","Auditorium","Cave Mapping and Inventory of a Significant Kentucky National Forest"),
    ("2026-07-06","14:15","112","UC Bat Edition for Bioacoustic Monitoring (virtual)"),
    ("2026-07-06","14:45","112","Flamingo Cave Radios"),
    ("2026-07-06","15:15","112","Tuned Loop Antenna Matching Made Easy"),
    ("2026-07-06","15:45","112","Analysis of a Network Outage in BuecherNet in Fort Stanton Cave, NM"),
    ("2026-07-06","16:15","112","Audio in Cave Projects"),
    ("2026-07-07","09:00","Auditorium","Modern Exploration of Warren Cave in Florida"),
    ("2026-07-07","09:20","Auditorium","Lee County Blowing – A Speleo Who Dun It"),
    ("2026-07-07","09:40","Auditorium","Binkley Cave Project"),
    ("2026-07-07","10:00","Auditorium","Recent Discoveries in Shoveleater Cave"),
    ("2026-07-07","10:20","Auditorium","Fern Cave Project"),
    ("2026-07-07","10:45","Auditorium","Warm River Cave Update"),
    ("2026-07-07","11:05","Auditorium","Cave Mapping and Inventory of a Significant KY National Forest"),
    ("2026-07-07","11:25","Auditorium","Recent Discoveries in Hidden River Cave, Kentucky"),
    ("2026-07-07","11:45","Auditorium","Whigpistle Cave Project Update: 2026"),
    ("2026-07-07","09:00","205","The Powell Mountain Karst Preserve: A Management Plan Analysis"),
    ("2026-07-07","09:20","205","Conservation and Management of the Paul Wightman Subterranean Nature Preserve"),
    ("2026-07-07","09:40","205","The Effects of Excavation on Cave Ecosystems (Two Years Later)"),
    ("2026-07-07","10:00","205","Are There Renewable Resources in Caves? Do Drip Hole Rings Count? And What Can Cavers Ethically Do in Exploring and Studying Caves?"),
    ("2026-07-07","10:30","205","Protecting Caves and Karst – A Holistic Approach"),
    ("2026-07-07","11:00","205","Cavers, State Agencies, and the United States Forest Service Working Together to Protect Caves and Karst in Virginia"),
    ("2026-07-07","11:20","205","Celebrate the UNESCO International Day of Caves and Karst, September 13th"),
    ("2026-07-07","14:00","Auditorium","Progress in Fort Stanton Cave, New Mexico"),
    ("2026-07-07","14:30","Auditorium","Gem Cave: A New Discovery Under South Dakota's Black Hills"),
    ("2026-07-07","14:50","Auditorium","Walking into Mordor: The Mount Baker Glaciovolcanic Cave Expedition"),
    ("2026-07-07","15:20","Auditorium","2025 Silvertip Expedition: Bobsled Cave Exploration"),
    ("2026-07-07","15:40","Auditorium","Klamath Mountains Project, Cave Research Foundation"),
    ("2026-07-07","16:10","Auditorium","Report-Walking: Using Search and Rescue Reports to Find Unmapped Caves"),
    ("2026-07-07","16:30","Auditorium","Geology, Mineralogy, Archeology and Exploration History of Hualalai Ranch Cave, Hawaii"),
    ("2026-07-07","14:00","205","The Restoration of Pleasant Valley Cave"),
    ("2026-07-07","14:20","205","Bigger, Better Mobile Caves for STEM Education Outreach"),
    ("2026-07-07","14:40","205","2026 U.S. Cave Animal of the Year – The Slimy Salamander"),
    ("2026-07-07","15:00","205","Documenting and Describing Two Species of Cave-Adapted Blind Fish in the Tiger Cave System, Phong Nha-Kẻ Bàng National Park, Việt Nam"),
    ("2026-07-07","15:30","205","Phong Nha-Kẻ Bàng: Cave Ecotourism for Sustainable Development in Việt Nam"),
    ("2026-07-07","16:00","205","Celebrate the Conservation Legacy of Rob Stitt — Stories, Song, Snacks"),
    ("2026-07-08","09:00","Auditorium","PESH 2026"),
    ("2026-07-08","09:30","Auditorium","Cueva Sin Fin"),
    ("2026-07-08","10:00","Auditorium","40 Years of Exploration at Cueva Cheve, Oaxaca, Mexico"),
    ("2026-07-08","10:30","Auditorium","Roaming North-Eastern Mexico Surveying Unexplored Caves"),
    ("2026-07-08","11:00","Auditorium","New Zealand Expedition, 2026"),
    ("2026-07-08","11:30","Auditorium","Exploration in Montenegro"),
    ("2026-07-08","08:10","205","Examining Genetic Diversity and Potential Cryptic Diversity within the Georgia Blind Salamander (Eurycea wallacei) and the Dougherty Plain Cave Crayfish (Cambarus cryptodytes) of the Upper Floridan Aquifer"),
    ("2026-07-08","08:30","205","New Surveys of Cave and Groundwater Fauna in the Upper Floridan Aquifer"),
    ("2026-07-08","08:50","205","Mapping Cave Vulnerability and Priority Areas for Biospeleological Conservation"),
    ("2026-07-08","09:10","205","Directed Phytokarst: Red-Shifted Phototrophy and Limestone Dissolution in Cave Twilight Zones"),
    ("2026-07-08","09:30","205","Examining Phylogenetic Relationships and Cryptic Diversity in the Genus Scoterpes (Chordeumatida: Trichopetalidae), a Wide-Ranging Genus of North American Cave-Obligate Millipedes"),
    ("2026-07-08","09:50","205","Evaluating the Biogenicity of Biovermiculations in Mammoth Cave, KY, USA"),
    ("2026-07-08","10:30","205","Population Monitoring of the Enigmatic Cave Snail, Fontigens antroecetes, in Stemler Cave"),
    ("2026-07-08","10:50","205","A Creature from the 'Upside Down': Cryptic Cavefish Diversity in a Long-Studied Karst Cave Ecosystem"),
    ("2026-07-08","11:10","205","Sediment Geochemistry, Manganese Oxidation, Human Traffic, and Microbial Community Structure across Three Southern Appalachian Caves"),
    ("2026-07-08","11:30","205","Subterranean Isopod Diversity in Caves of the Northern Interior Low Plateaus"),
    ("2026-07-08","09:00","102","Cavers: Who, Why, So What?"),
    ("2026-07-08","09:30","102","Creating a Legacy at UA"),
    ("2026-07-08","10:00","102","Expressing Culture Piece by Piece"),
    ("2026-07-08","10:30","102","Discussion of 'Empowering Women Through Cave Exploration and Conservation' (Article by Ellen Trautner)"),
    ("2026-07-08","14:00","Auditorium","Sternes Cave Project, Crete, Greece"),
    ("2026-07-08","14:30","Auditorium","Beneath the Thunder Dragon: Cave Exploration in Bhutan"),
    ("2026-07-08","15:00","Auditorium","Mulu Cave Project 2026"),
    ("2026-07-08","15:30","Auditorium","Mapping the Extensive Caves of the Newly Accessible Lạng Sơn Geopark, Vietnam"),
    ("2026-07-08","16:00","Auditorium","Archaeology to Advocacy: Southeast Sulawesi 2025"),
    ("2026-07-08","16:30","Auditorium","Continued Exploration in Mindanao, Philippines"),
    ("2026-07-09","09:00","205",'"Camp Rock," aka "The Black Mountain Hotel": Mount Mitchell\'s Historic Rock Shelter'),
    ("2026-07-09","09:15","205","A Brief Overview of the Significant Hoosier Cavers 1850-2025"),
    ("2026-07-09","09:40","205","The 130-Year History of the Ohio Cave Survey"),
    ("2026-07-09","10:10","205","Historic Cave Slides of Lewis David Lamon, NSS2188FE, Taken 1952-1990"),
    ("2026-07-09","10:30","205","Josiah Mosher Jr. and the Mammoth Cave Hotel"),
    ("2026-07-09","10:50","205","When Martel was Banished from Mammoth Cave, or On Discovering a Rare Version of Hovey's 1912 Guidebook"),
    ("2026-07-09","11:15","205","Cooper's Cave, New York: A Notable Bicentennial, 1826-2026"),
    ("2026-07-09","11:35","205","Charles Waldack and Mammoth Cave"),
    ("2026-07-09","11:55","205","Pennsylvania's Show Caves"),
    ("2026-07-09","09:00","254","An Investigation of Permanently Rigged Ropes"),
    ("2026-07-09","09:45","254","NSS Vertical Training Commission: July 2026 Progress Update"),
    ("2026-07-09","10:10","254","Vertical Caving: Some of My Heretical Opinions"),
    ("2026-07-09","10:35","254","Fundamentals of Rigging"),
    ("2026-07-09","11:00","254","The Gauntlet"),
    ("2026-07-09","11:25","254","History of Kernmantle Rope"),
    ("2026-07-09","11:50","254","From Incident to Insight: A College Grotto's Perspective on a Vertical Rescue in Wind-Hicks Cave"),
    ("2026-07-09","12:15","254","Bolting Considerations for High Traffic Caves and/or Bad Rock Quality: A Brief Introduction to Glue-In's"),
    ("2026-07-09","12:40","254","Fun and Sketchy Things to Do with Rappel Devices"),
    ("2026-07-09","09:05","102","The Discovery and Recovery of the Shenandoah Caverns Peccaries and Reincarnation of PRIOVAC"),
    ("2026-07-09","09:25","102","Extinct Long-Nosed Peccary Remains from Shenandoah Wild Cave, Virginia: An Update"),
    ("2026-07-09","09:45","102","The Importance of Small Mammals in Cave Paleontology"),
    ("2026-07-09","10:25","102","Advances in Discovering and Managing Paleontological Resources in Tennessee Caves"),
    ("2026-07-09","10:45","102","New Interpretation of Sediments and Fossils from a Cave in Sullivan County, Tennessee"),
    ("2026-07-09","11:05","102","An Ancient Short-Faced Bear Skeleton and Other Fauna from Cebada, Chiquibul Cave System, Belize"),
    ("2026-07-09","14:15","154","Can AI Image Editing Tools Understand a Cave?"),
    ("2026-07-09","14:45","154","Why and When to Choose a Cell Phone Over a Conventional Digital Camera for Cave Photography"),
    ("2026-07-09","15:15","154","Diffraction Limited Optics and the New Galaxy S25 Ultra 200Mp Lens"),
    ("2026-07-09","14:05","102","Cataloging the National Cave Museum"),
    ("2026-07-09","14:25","102","Early Woodland Gypsum Mining at Bluff Cave, Mammoth Cave National Park, Kentucky"),
    ("2026-07-09","14:45","102","The Salts Cave/Unknown Cave Footprint Project, Mammoth Cave National Park, Kentucky"),
    ("2026-07-10","09:00","Auditorium","Geologic Characterization of the Glaciovolcanic Caves of Mount Baker, Washington"),
    ("2026-07-10","09:20","Auditorium","New Paradigms of Speleogenesis in the Ohio River Valley"),
    ("2026-07-10","09:40","Auditorium","Utilizing Structural Lineament Mapping with Digital Elevation Models for Understanding Speleogeneic Patterns in the Mammoth Cave Plateau"),
    ("2026-07-10","10:20","Auditorium","Applied Geophysics and LiDAR in Karst: From Environmental Consulting to Cave Discovery"),
    ("2026-07-10","10:40","Auditorium","Quantifying and Comparing Sinkhole Morphometry across Different Geospatial Datasets"),
    ("2026-07-10","11:00","Auditorium","Understanding the Variability in Gas Concentrations of Carlsbad Cavern"),
    ("2026-07-10","13:30","Auditorium","Evaluating Speleothem Samples as a Geological Archive for Paleomagnetic Records and Environmental Interpretation"),
    ("2026-07-10","13:50","Auditorium","The Importance of Caves in the History of Geology"),
    ("2026-07-10","14:10","Auditorium","The Consequences of the Self-Modification of Island Karst Aquifers"),
    ("2026-07-10","14:50","Auditorium","Exploring the Stratigraphic and Structural Context of the Cheve Karst System, Oaxaca, Mexico"),
    ("2026-07-10","15:10","Auditorium","Talus Caves of Franconia Notch, New Hampshire"),
    ("2026-07-10","15:30","Auditorium","The Influence of Magnitude and Frequency on the Relative Importance of Chemical and Mechanical Erosion: Examples from J2 and Slot Canyons in the Ozarks"),
    ("2026-07-10","13:00","205","Software Defined Cave Symbology"),
    ("2026-07-10","13:15","205","How Do I Know Where This Drone Image Is?"),
    ("2026-07-10","13:40","205","Photogrammetry for Fun and Prospecting"),
    ("2026-07-10","14:05","205","Testing and Reviewing the New 3DMakerpro Raven Handheld LiDAR Scanner"),
    ("2026-07-10","14:25","205","Speleological Model in ArcGIS"),
    ("2026-07-10","15:00","205","Developing New Surveyors, Sketchers and Cartographers through Beginner Focused Projects"),
    ("2026-07-10","15:20","205","Techniques for Generating High-Definition Karst-Focused Terrain Imagery from LiDAR Surface Data"),
    ("2026-07-10","15:45","205","0Bar Maps: Interactive Maps for Your Cave Phone"),
    ("2026-07-10","16:10","205","Select Methods Using Adobe Illustrator"),
    ("2026-07-10","16:35","205","Automated Cave Detection from LiDAR: Improved Methods and Broader Access"),
]

# ---------------------------------------------------------------------------
# Text normalization for fuzzy matching
# ---------------------------------------------------------------------------

def norm(s):
    s = s.lower()
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def similarity(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()

# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_abstract_text():
    reader = pypdf.PdfReader(PDF_PATH)
    pages = []
    for i in range(59, len(reader.pages)):
        text = reader.pages[i].extract_text() or ''
        # Remove page header
        text = re.sub(r'NSS Convention 2026[—\-]Corydon, Indiana\s+\d+\s*\n?', '', text)
        pages.append(text)
    return '\n'.join(pages)

# ---------------------------------------------------------------------------
# Abstract section extraction
#
# Strategy: find candidate title positions using fuzzy matching against all
# known talk titles, then extract the text between consecutive matches.
# ---------------------------------------------------------------------------

def find_title_positions(full_text, titles):
    """
    For each title, find its best-matching position in full_text.
    Returns sorted list of (pos, title, score).
    """
    # Build a list of (line_start, line_end, line_text) for all non-empty lines
    lines = []
    pos = 0
    for line in full_text.split('\n'):
        end = pos + len(line)
        stripped = line.strip()
        if stripped:
            lines.append((pos, end, stripped))
        pos = end + 1  # +1 for the \n

    results = {}
    for title in titles:
        best_score = 0
        best_pos = -1
        title_words = set(norm(title).split())

        for lstart, lend, line in lines:
            # Quick pre-filter: at least 40% word overlap
            line_words = set(norm(line).split())
            if not title_words or not line_words:
                continue
            overlap = len(title_words & line_words) / len(title_words)
            if overlap < 0.3:
                continue

            # Also try merging with next 1-2 lines for multi-line titles
            line_idx = lines.index((lstart, lend, line))
            for window in range(1, 4):
                chunk_lines = [l for _, _, l in lines[line_idx:line_idx+window]]
                candidate = ' '.join(chunk_lines)
                score = similarity(title, candidate)
                if score > best_score:
                    best_score = score
                    best_pos = lstart

        if best_score >= 0.55:
            results[title] = (best_pos, best_score)

    return results

def extract_abstract_for_title(full_text, pos, next_pos):
    """
    Extract and clean abstract text between pos and next_pos.
    Strips the title line(s), author/affiliation lines, and cleans up hyphenation.
    """
    chunk = full_text[pos:next_pos] if next_pos else full_text[pos:]

    lines = chunk.split('\n')
    # Skip first 1-5 lines (title + authors/affiliations)
    # Heuristic: skip until we find a line that looks like prose (>40 chars, ends in letter)
    body_lines = []
    skipping = True
    skip_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not skipping:
                body_lines.append('')
            continue
        if skipping:
            skip_count += 1
            # Stop skipping when we hit a substantive prose line
            # (long line, not an email/URL/affiliation)
            is_email = '@' in stripped or 'http' in stripped.lower()
            is_affiliation = (
                len(stripped) < 60 and skip_count <= 8 and
                not stripped[0].isupper() or
                re.match(r'^[A-Z]\w+\s+(University|College|Department|Institute|Laboratory|Center|NSS|NPS)', stripped)
            )
            looks_like_prose = (
                len(stripped) > 50 and
                stripped[0].isupper() and
                stripped[-1] in 'abcdefghijklmnopqrstuvwxyz.,;:)' and
                not is_email
            )
            if looks_like_prose and skip_count >= 2:
                skipping = False
                body_lines.append(stripped)
        else:
            body_lines.append(stripped)

    # Rejoin, fixing hyphenation at line breaks (PDF artifact: "sub- \nterranean" → "subterranean")
    text = '\n'.join(body_lines)
    text = re.sub(r'-\s*\n\s*', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    token = os.environ.get('PRETALX_TOKEN')
    if not token and not args.dry_run:
        print("ERROR: PRETALX_TOKEN not set"); sys.exit(1)

    with open(STATE_FILE) as f:
        state = json.load(f)

    # Build lookup: title[:40] → submission code
    title_to_code = {}
    for key, info in state['submissions'].items():
        if key.startswith('talk|'):
            parts = key.split('|')
            if len(parts) >= 5:
                title_to_code[parts[4]] = info['code']

    print("Extracting abstract text from PDF...")
    full_text = extract_abstract_text()
    print(f"  Extracted {len(full_text):,} characters from pages 60-112")

    all_titles = [t for _, _, _, t in TALKS]
    print(f"\nMatching {len(all_titles)} talk titles...")
    title_positions = find_title_positions(full_text, all_titles)
    print(f"  Found matches for {len(title_positions)} titles")

    # Deduplicate: if two titles matched the same position, keep the higher score
    by_pos = {}
    for title, (pos, score) in title_positions.items():
        if pos not in by_pos or score > by_pos[pos][1]:
            by_pos[pos] = (title, score)
    title_positions = {title: (pos, score) for pos, (title, score) in by_pos.items()}
    print(f"  After dedup: {len(title_positions)} unique positions")

    # Sort by position to get ordered abstract boundaries
    sorted_matches = sorted(title_positions.items(), key=lambda x: x[1][0])

    h = {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}
    session = requests.Session()
    session.headers.update(h)

    updated = skipped = no_abstract = errors = 0

    for i, (title, (pos, score)) in enumerate(sorted_matches):
        next_pos = sorted_matches[i+1][1][0] if i+1 < len(sorted_matches) else None
        abstract = extract_abstract_for_title(full_text, pos, next_pos)

        code = title_to_code.get(title[:40])
        if not code:
            print(f"  WARN: no submission code for '{title[:60]}'")
            no_abstract += 1
            continue

        if args.dry_run:
            print(f"\n  [{score:.2f}] {title[:65]}")
            print(f"         code={code}  abstract_len={len(abstract)}")
            if abstract:
                print(f"         preview: {abstract[:120].replace(chr(10),' ')}")
            continue

        if not abstract:
            skipped += 1
            continue

        resp = session.patch(
            f"{API_BASE}/submissions/{code}/",
            json={'abstract': abstract},
            timeout=30,
        )
        if resp.ok:
            print(f"  [{score:.2f}] {title[:65]} → {len(abstract)}c")
            updated += 1
        else:
            print(f"  ERROR {code}: {resp.status_code} {resp.text[:200]}")
            errors += 1

    # Report titles with no match
    matched = set(t for t, _ in sorted_matches)
    unmatched = [t for t in all_titles if t not in matched]
    if unmatched:
        print(f"\nNo abstract found for {len(unmatched)} talks:")
        for t in unmatched:
            print(f"  - {t[:80]}")

    if not args.dry_run:
        print(f"\nUpdated: {updated}  Skipped (empty): {skipped}  Missing code: {no_abstract}  Errors: {errors}")


if __name__ == '__main__':
    main()
