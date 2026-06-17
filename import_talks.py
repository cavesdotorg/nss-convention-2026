#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "python-dotenv",
# ]
# ///
"""
Import individual speaker talks into Pretalx.

These are the presentations within each session block, extracted from
2026-06-15/PrintCopy - 2026_NSSProgram_FINALv2.pdf (pages 45-59).

Each talk becomes a separate confirmed+scheduled submission, placed in the
same room as its parent session. Speaker names go in the abstract since we
don't have email addresses for profile creation.

Usage:
    uv run import_talks.py --dry-run
    uv run import_talks.py
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

API_BASE = "https://talks.caving.dev/api/events/nss-convention-2026"
STATE_FILE = os.path.join(os.path.dirname(__file__), "import_state.json")
TZ = timezone(timedelta(hours=-4))

# ---------------------------------------------------------------------------
# Talk data extracted from program guide (PDF pp. 45-59)
# Each entry: (date, start_hhmm, end_hhmm_or_None, room_name, title, speakers)
# end=None → duration inferred from next talk or DEFAULT_DURATION_MINUTES
# ---------------------------------------------------------------------------

DEFAULT_DURATION = 20  # minutes

TALKS = [
    # ===== MONDAY JULY 6 =====
    # Cave Exploration of the Ohio Valley Region — morning (Auditorium)
    ("2026-07-06","09:05","09:15","Auditorium","Regional Geology and GIS Overview","Rai Bosch"),
    ("2026-07-06","09:15","09:25","Auditorium","Ohio Cave Survey—State Overview","Frank Vlchek"),
    ("2026-07-06","09:25","09:35","Auditorium","Indiana Cave Survey—State Overview","Dave Everton"),
    ("2026-07-06","09:35","09:45","Auditorium","Kentucky Speleological Survey","Stephanie Suen"),
    ("2026-07-06","09:45","10:05","Auditorium","Exploring Courtey Cave and the Cave Systems of Central Ohio's Scioto River Corridor","Ryan Braggs"),
    ("2026-07-06","10:05","10:45","Auditorium","Caves of Edwards Mountain & Wayne County (incl Spelunger Cave)","Lee Florea & Chris Bauer"),
    ("2026-07-06","10:55","11:15","Auditorium","Modern Exploration in Big Bat Cave","Adam Hjermenrud"),
    ("2026-07-06","11:15","11:35","Auditorium","Pless Cave—Exploration & Mapping","Dave Everton"),
    ("2026-07-06","11:35","12:00","Auditorium","James Cave, The Cave, The Exploration","Charlie Bishop"),
    # Cave Exploration — afternoon (Auditorium)
    ("2026-07-06","13:00","13:20","Auditorium","Big Bat Cave—A Brief History of Exploration","Ken Bailey"),
    ("2026-07-06","13:20","13:40","Auditorium","Sandstone Caves in Northeast Ohio","Frank Vlchek"),
    ("2026-07-06","13:40","14:00","Auditorium","Great Caves, Great Survey Projects in Rockcastle County, Kentucky","Mary Gratsch"),
    ("2026-07-06","14:10","14:50","Auditorium","Twenty Kentucky Caves that Might be Bigger than Mammoth","Catherine Bishop"),
    ("2026-07-06","14:50","15:10","Auditorium","Fisher Ridge Cave System Project 2023-2026 Update","Sean Lewis & Ben Tobin"),
    ("2026-07-06","15:10","15:30","Auditorium","Roppel Cave","Jim Borden, Holly McClintock & Matt Medzydlo"),
    ("2026-07-06","15:30","15:50","Auditorium","History of Cave Exploration in Wayne County, Kentucky","Janeen Sharpshair & Harry Goepel"),
    ("2026-07-06","15:50","16:10","Auditorium","Cedar Grove Cave—Discovery of a Virgin Cave","Gary O'Dell"),
    ("2026-07-06","16:10","16:30","Auditorium","Whigpistle Cave Project Update","Joel Despain, Niles Lathrop & Pat Kambesis"),
    ("2026-07-06","16:30","16:50","Auditorium","Cave Mapping and Inventory of a Significant Kentucky National Forest","Stephanie Suen"),
    # Communications & Electronics — afternoon (112)
    ("2026-07-06","14:15","14:45","112","UC Bat Edition for Bioacoustic Monitoring (virtual)","Tim Clark"),
    ("2026-07-06","14:45","15:15","112","Flamingo Cave Radios","Jamie Moon & Bob Reese, Huntsville Cave Rescue"),
    ("2026-07-06","15:15","15:45","112","Tuned Loop Antenna Matching Made Easy","Brian Pease"),
    ("2026-07-06","15:45","16:15","112","Analysis of a Network Outage in BuecherNet in Fort Stanton Cave, NM","Fort Stanton Study Project"),
    ("2026-07-06","16:15","16:45","112","Audio in Cave Projects","Steve Reames"),

    # ===== TUESDAY JULY 7 =====
    # US Exploration — morning (Auditorium)
    ("2026-07-07","09:00","09:20","Auditorium","Modern Exploration of Warren Cave in Florida","Maggie Brosky"),
    ("2026-07-07","09:20","09:40","Auditorium","Lee County Blowing – A Speleo Who Dun It","Mike Ficco, Katarina Kosič Ficco"),
    ("2026-07-07","09:40","10:00","Auditorium","Binkley Cave Project","Rand Heazlitt, Marion Ziemons"),
    ("2026-07-07","10:00","10:20","Auditorium","Recent Discoveries in Shoveleater Cave","Mark Minton"),
    ("2026-07-07","10:20","10:45","Auditorium","Fern Cave Project","Rand Heazlitt, Marion Ziemons"),
    ("2026-07-07","10:45","11:05","Auditorium","Warm River Cave Update","Mark Minton and Yvonne Droms"),
    ("2026-07-07","11:05","11:25","Auditorium","Cave Mapping and Inventory of a Significant KY National Forest","Stephanie Suen"),
    ("2026-07-07","11:25","11:45","Auditorium","Recent Discoveries in Hidden River Cave, Kentucky","Liam Tobin"),
    ("2026-07-07","11:45","12:15","Auditorium","Whigpistle Cave Project Update: 2026","Joel Despain and Niles Lathrop"),
    # Cave Conservation & Management — morning (205)
    ("2026-07-07","09:00","09:20","205","The Powell Mountain Karst Preserve: A Management Plan Analysis","Penelope Vorster"),
    ("2026-07-07","09:20","09:40","205","Conservation and Management of the Paul Wightman Subterranean Nature Preserve","Robert Weck"),
    ("2026-07-07","09:40","10:00","205","The Effects of Excavation on Cave Ecosystems (Two Years Later)","Drew Rollin Thompson"),
    ("2026-07-07","10:00","10:30","205","Are There Renewable Resources in Caves? Do Drip Hole Rings Count? And What Can Cavers Ethically Do in Exploring and Studying Caves?","Roy A. Jameson"),
    ("2026-07-07","10:30","11:00","205","Protecting Caves and Karst – A Holistic Approach","Geary Schindel"),
    ("2026-07-07","11:00","11:20","205","Cavers, State Agencies, and the United States Forest Service Working Together to Protect Caves and Karst in Virginia","Katarina Kosič Ficco, Chad Harrold, Wil Orndorff"),
    ("2026-07-07","11:20","12:00","205","Celebrate the UNESCO International Day of Caves and Karst, September 13th","Val Hildreth-Werker"),
    # US Exploration — afternoon (Auditorium)
    ("2026-07-07","14:00","14:30","Auditorium","Progress in Fort Stanton Cave, New Mexico","Riley Drake, Riannon Colton and John T. M. Lyles"),
    ("2026-07-07","14:30","14:50","Auditorium","Gem Cave: A New Discovery Under South Dakota's Black Hills","Rene Ohms and Adam Weaver"),
    ("2026-07-07","14:50","15:20","Auditorium","Walking into Mordor: The Mount Baker Glaciovolcanic Cave Expedition","Christian Stenner, Lee Florea"),
    ("2026-07-07","15:20","15:40","Auditorium","2025 Silvertip Expedition: Bobsled Cave Exploration","Chelsea Dau"),
    ("2026-07-07","15:40","16:10","Auditorium","Klamath Mountains Project, Cave Research Foundation","Joel Despain, Niles Lathrop, Heather Veerkamp"),
    ("2026-07-07","16:10","16:30","Auditorium","Report-Walking: Using Search and Rescue Reports to Find Unmapped Caves","Angelica Mucciarone Brewer, Tyler Nash, Elby Jones, and Ben Heely"),
    ("2026-07-07","16:30","17:00","Auditorium","Geology, Mineralogy, Archeology and Exploration History of Hualalai Ranch Cave, Hawaii","John Rosenfeld"),
    # Cave Conservation & Management — afternoon (205)
    ("2026-07-07","14:00","14:20","205","The Restoration of Pleasant Valley Cave","Tony Schmitt"),
    ("2026-07-07","14:20","14:40","205","Bigger, Better Mobile Caves for STEM Education Outreach","Dave Jackson"),
    ("2026-07-07","14:40","15:00","205","2026 U.S. Cave Animal of the Year – The Slimy Salamander","Cave Animal of the Year Team, NSS Cave Conservation and Science Division"),
    ("2026-07-07","15:00","15:30","205","Documenting and Describing Two Species of Cave-Adapted Blind Fish in the Tiger Cave System, Phong Nha-Kẻ Bàng National Park, Việt Nam","Dean A. Wiseman"),
    ("2026-07-07","15:30","16:00","205","Phong Nha-Kẻ Bàng: Cave Ecotourism for Sustainable Development in Việt Nam","Lê Lưu Dũng, Founder & CEO of Jungle Boss Tours"),
    ("2026-07-07","16:00","17:00","205","Celebrate the Conservation Legacy of Rob Stitt — Stories, Song, Snacks","Aslan Rife"),

    # ===== WEDNESDAY JULY 8 =====
    # International Exploration — morning (Auditorium)
    ("2026-07-08","09:00","09:30","Auditorium","PESH 2026","Bill Steele"),
    ("2026-07-08","09:30","10:00","Auditorium","Cueva Sin Fin","Megan Necessary & Peter Sprouse"),
    ("2026-07-08","10:00","10:30","Auditorium","40 Years of Exploration at Cueva Cheve, Oaxaca, Mexico","Matt Covington & Aidan Ward"),
    ("2026-07-08","10:30","11:00","Auditorium","Roaming North-Eastern Mexico Surveying Unexplored Caves","Carl Haken"),
    ("2026-07-08","11:00","11:30","Auditorium","New Zealand Expedition, 2026","Joel Despain, Nic Barth, Carol Vesely"),
    ("2026-07-08","11:30","12:00","Auditorium","Exploration in Montenegro","Mátyás Gyimesi"),
    # Biospeleology (205, 8:00-12:30)
    ("2026-07-08","08:10","08:30","205","Examining Genetic Diversity and Potential Cryptic Diversity within the Georgia Blind Salamander (Eurycea wallacei) and the Dougherty Plain Cave Crayfish (Cambarus cryptodytes) of the Upper Floridan Aquifer","Jacob Schaefer"),
    ("2026-07-08","08:30","08:50","205","New Surveys of Cave and Groundwater Fauna in the Upper Floridan Aquifer","Eric Maxwell"),
    ("2026-07-08","08:50","09:10","205","Mapping Cave Vulnerability and Priority Areas for Biospeleological Conservation","Lael Anderson"),
    ("2026-07-08","09:10","09:30","205","Directed Phytokarst: Red-Shifted Phototrophy and Limestone Dissolution in Cave Twilight Zones","Isuru Ethige"),
    ("2026-07-08","09:30","09:50","205","Examining Phylogenetic Relationships and Cryptic Diversity in the Genus Scoterpes (Chordeumatida: Trichopetalidae), a Wide-Ranging Genus of North American Cave-Obligate Millipedes","Coral Quering"),
    ("2026-07-08","09:50","10:10","205","Evaluating the Biogenicity of Biovermiculations in Mammoth Cave, KY, USA","Amelia Freeland"),
    ("2026-07-08","10:30","10:50","205","Population Monitoring of the Enigmatic Cave Snail, Fontigens antroecetes, in Stemler Cave","Bob Weck"),
    ("2026-07-08","10:50","11:10","205","A Creature from the 'Upside Down': Cryptic Cavefish Diversity in a Long-Studied Karst Cave Ecosystem","Matt Niemiller"),
    ("2026-07-08","11:10","11:30","205","Sediment Geochemistry, Manganese Oxidation, Human Traffic, and Microbial Community Structure across Three Southern Appalachian Caves","Suzanna Brauer"),
    ("2026-07-08","11:30","11:50","205","Subterranean Isopod Diversity in Caves of the Northern Interior Low Plateaus","Jerry Lewis"),
    # Caving & Culture (102, 9:00-Noon)
    ("2026-07-08","09:00","09:30","102","Cavers: Who, Why, So What?","Catherine Bishop"),
    ("2026-07-08","09:30","10:00","102","Creating a Legacy at UA","Jacqueline F. Heggen, J. Max Koether, and Anna Drabik, University of Alabama"),
    ("2026-07-08","10:00","10:30","102","Expressing Culture Piece by Piece","Catherine Bishop"),
    ("2026-07-08","10:30","12:00","102","Discussion of 'Empowering Women Through Cave Exploration and Conservation' (Article by Ellen Trautner)",""),
    # International Exploration — afternoon (Auditorium)
    ("2026-07-08","14:00","14:30","Auditorium","Sternes Cave Project, Crete, Greece","Dustin Kisner"),
    ("2026-07-08","14:30","15:00","Auditorium","Beneath the Thunder Dragon: Cave Exploration in Bhutan","Pat Kambesis"),
    ("2026-07-08","15:00","15:30","Auditorium","Mulu Cave Project 2026","Christine Saw and Kevin Liow"),
    ("2026-07-08","15:30","16:00","Auditorium","Mapping the Extensive Caves of the Newly Accessible Lạng Sơn Geopark, Vietnam",""),
    ("2026-07-08","16:00","16:30","Auditorium","Archaeology to Advocacy: Southeast Sulawesi 2025","Cydney Sea"),
    ("2026-07-08","16:30","17:00","Auditorium","Continued Exploration in Mindanao, Philippines","Thomas Hawkins"),

    # ===== THURSDAY JULY 9 =====
    # Spelean History (205, 9:00-Noon)
    ("2026-07-09","09:00","09:15","205",'"Camp Rock," aka "The Black Mountain Hotel": Mount Mitchell\'s Historic Rock Shelter',"Cato Holler and Nancy Holler Aulenbach"),
    ("2026-07-09","09:15","09:40","205","A Brief Overview of the Significant Hoosier Cavers 1850-2025","Gary Roberson"),
    ("2026-07-09","09:40","10:00","205","The 130-Year History of the Ohio Cave Survey","Curt Harler and Frank Vlchek"),
    ("2026-07-09","10:10","10:30","205","Historic Cave Slides of Lewis David Lamon, NSS2188FE, Taken 1952-1990","John M. Benton"),
    ("2026-07-09","10:30","10:50","205","Josiah Mosher Jr. and the Mammoth Cave Hotel","Joseph C. Douglas"),
    ("2026-07-09","10:50","11:05","205","When Martel was Banished from Mammoth Cave, or On Discovering a Rare Version of Hovey's 1912 Guidebook","Katie Algeo"),
    ("2026-07-09","11:15","11:35","205","Cooper's Cave, New York: A Notable Bicentennial, 1826-2026","Ernst H. Kastning"),
    ("2026-07-09","11:35","11:55","205","Charles Waldack and Mammoth Cave","Michael McEachern"),
    ("2026-07-09","11:55","12:15","205","Pennsylvania's Show Caves","Jack Speece"),
    # Vertical Section (254, 9:00-2:00)
    ("2026-07-09","09:00","09:45","254","An Investigation of Permanently Rigged Ropes","Philip Rykwalder"),
    ("2026-07-09","09:45","10:10","254","NSS Vertical Training Commission: July 2026 Progress Update","Ron Miller"),
    ("2026-07-09","10:10","10:35","254","Vertical Caving: Some of My Heretical Opinions","Gary Storrick"),
    ("2026-07-09","10:35","11:00","254","Fundamentals of Rigging","Rachel Saker"),
    ("2026-07-09","11:00","11:25","254","The Gauntlet","Kevin Mulligan"),
    ("2026-07-09","11:25","11:50","254","History of Kernmantle Rope","Tim White"),
    ("2026-07-09","11:50","12:15","254","From Incident to Insight: A College Grotto's Perspective on a Vertical Rescue in Wind-Hicks Cave","Jenna Crabtree"),
    ("2026-07-09","12:15","12:40","254","Bolting Considerations for High Traffic Caves and/or Bad Rock Quality: A Brief Introduction to Glue-In's","Rachel Saker"),
    ("2026-07-09","12:40","14:00","254","Fun and Sketchy Things to Do with Rappel Devices","Jerin Manalel"),
    # Paleontology (102, 9:00-Noon)
    ("2026-07-09","09:05","09:25","102","The Discovery and Recovery of the Shenandoah Caverns Peccaries and Reincarnation of PRIOVAC","David A. Hubbard, Jr., Blaine W. Schubert, and Carol Tiderman"),
    ("2026-07-09","09:25","09:45","102","Extinct Long-Nosed Peccary Remains from Shenandoah Wild Cave, Virginia: An Update","Blaine W. Schubert, David A. Hubbard, Jr., Davis Gunnin, Shay Maden, and Laura Emmert"),
    ("2026-07-09","09:45","10:05","102","The Importance of Small Mammals in Cave Paleontology","Olivia Williams, Blaine W. Schubert, Shay Maden, and Davis Gunnin"),
    ("2026-07-09","10:25","10:45","102","Advances in Discovering and Managing Paleontological Resources in Tennessee Caves","Davis Gunnin, Blaine W. Schubert, and Shay Maden"),
    ("2026-07-09","10:45","11:05","102","New Interpretation of Sediments and Fossils from a Cave in Sullivan County, Tennessee","Shay Maden, Blaine W. Schubert, Davis Gunnin, and Keila Bredehoeft"),
    ("2026-07-09","11:05","12:00","102","An Ancient Short-Faced Bear Skeleton and Other Fauna from Cebada, Chiquibul Cave System, Belize","Blaine W. Schubert and Alson Ovando"),
    # Cave Photography Session (154, 2:00-5:00)
    ("2026-07-09","14:15","14:45","154","Can AI Image Editing Tools Understand a Cave?","Dan Legnini"),
    ("2026-07-09","14:45","15:15","154","Why and When to Choose a Cell Phone Over a Conventional Digital Camera for Cave Photography","Dave Bunnell"),
    ("2026-07-09","15:15","15:45","154","Diffraction Limited Optics and the New Galaxy S25 Ultra 200Mp Lens","Edward Schultz"),
    # Archaeology (102, 2:00-5:00)
    ("2026-07-09","14:05","14:25","102","Cataloging the National Cave Museum","Bert Ashbrook"),
    ("2026-07-09","14:25","14:45","102","Early Woodland Gypsum Mining at Bluff Cave, Mammoth Cave National Park, Kentucky","Joseph C. Douglas, Jim Honaker, and Larry W. Johnson"),
    ("2026-07-09","14:45","15:05","102","The Salts Cave/Unknown Cave Footprint Project, Mammoth Cave National Park, Kentucky","George Crothers, Sam Koontz, Rick Toomey"),

    # ===== FRIDAY JULY 10 =====
    # Geology & Geography — morning (Auditorium)
    ("2026-07-10","09:00","09:20","Auditorium","Geologic Characterization of the Glaciovolcanic Caves of Mount Baker, Washington","Lee Florea"),
    ("2026-07-10","09:20","09:40","Auditorium","New Paradigms of Speleogenesis in the Ohio River Valley","Lee Florea"),
    ("2026-07-10","09:40","10:00","Auditorium","Utilizing Structural Lineament Mapping with Digital Elevation Models for Understanding Speleogeneic Patterns in the Mammoth Cave Plateau","Ljubomir Risteski"),
    ("2026-07-10","10:20","10:40","Auditorium","Applied Geophysics and LiDAR in Karst: From Environmental Consulting to Cave Discovery","Michael Jones"),
    ("2026-07-10","10:40","11:00","Auditorium","Quantifying and Comparing Sinkhole Morphometry across Different Geospatial Datasets","Perla Romero"),
    ("2026-07-10","11:00","11:20","Auditorium","Understanding the Variability in Gas Concentrations of Carlsbad Cavern","Riannon Colton"),
    # Geology & Geography — afternoon (Auditorium)
    ("2026-07-10","13:30","13:50","Auditorium","Evaluating Speleothem Samples as a Geological Archive for Paleomagnetic Records and Environmental Interpretation","Maggie Brosky"),
    ("2026-07-10","13:50","14:10","Auditorium","The Importance of Caves in the History of Geology","Greg Brick"),
    ("2026-07-10","14:10","14:30","Auditorium","The Consequences of the Self-Modification of Island Karst Aquifers",""),
    ("2026-07-10","14:50","15:10","Auditorium","Exploring the Stratigraphic and Structural Context of the Cheve Karst System, Oaxaca, Mexico","Matt Covington"),
    ("2026-07-10","15:10","15:30","Auditorium","Talus Caves of Franconia Notch, New Hampshire","Anatoliy Bulychov"),
    ("2026-07-10","15:30","16:00","Auditorium","The Influence of Magnitude and Frequency on the Relative Importance of Chemical and Mechanical Erosion: Examples from J2 and Slot Canyons in the Ozarks","Matt Covington"),
    # Survey & Cartography Section (SACS, 205, 1:00-5:00)
    ("2026-07-10","13:00","13:15","205","Software Defined Cave Symbology","Michael A. Raymond"),
    ("2026-07-10","13:15","13:40","205","How Do I Know Where This Drone Image Is?","Philip Balister"),
    ("2026-07-10","13:40","14:05","205","Photogrammetry for Fun and Prospecting","Philip Balister"),
    ("2026-07-10","14:05","14:25","205","Testing and Reviewing the New 3DMakerpro Raven Handheld LiDAR Scanner","Dean Wiseman"),
    ("2026-07-10","14:25","14:50","205","Speleological Model in ArcGIS","Garry Petrie"),
    ("2026-07-10","15:00","15:20","205","Developing New Surveyors, Sketchers and Cartographers through Beginner Focused Projects","Kyle Kreutz"),
    ("2026-07-10","15:20","15:45","205","Techniques for Generating High-Definition Karst-Focused Terrain Imagery from LiDAR Surface Data","Joe Walko"),
    ("2026-07-10","15:45","16:10","205","0Bar Maps: Interactive Maps for Your Cave Phone","Dwight Livingston"),
    ("2026-07-10","16:10","16:35","205","Select Methods Using Adobe Illustrator","Dwight Livingston"),
    ("2026-07-10","16:35","17:00","205","Automated Cave Detection from LiDAR: Improved Methods and Broader Access","Zach Englebert"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'rooms': {}, 'submissions': {}}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def make_session(token):
    s = requests.Session()
    s.headers.update({'Authorization': f'Token {token}', 'Content-Type': 'application/json'})
    return s


def api_get_all(session, path):
    results, url = [], f"{API_BASE}/{path.lstrip('/')}"
    while url:
        resp = session.get(url, timeout=30)
        if not resp.ok:
            print(f"  GET {url} → {resp.status_code}: {resp.text[:200]}")
            break
        data = resp.json()
        if isinstance(data, list):
            results.extend(data); break
        results.extend(data.get('results', []))
        url = (data.get('next') or '').replace('http://', 'https://') or None
    return results


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


def parse_dt(date_str, time_str):
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=TZ)


def fmt_dt(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + dt.strftime('%z')[:6]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Import individual speaker talks into Pretalx')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    token = os.environ.get('PRETALX_TOKEN')
    if not token and not args.dry_run:
        print("ERROR: PRETALX_TOKEN not set"); sys.exit(1)

    if args.dry_run:
        print("=== DRY RUN ===\n")

    state = load_state()
    room_map = state.get('rooms', {})  # name → id

    print(f"Loaded {len(room_map)} rooms from state")
    print(f"Importing {len(TALKS)} individual talks\n")

    if args.dry_run:
        for date, start, end, room, title, speakers in TALKS:
            start_dt = parse_dt(date, start)
            end_dt = parse_dt(date, end)
            dur = int((end_dt - start_dt).total_seconds() / 60)
            room_id = room_map.get(room, '???')
            spk = f" [{speakers}]" if speakers else ""
            print(f"  [{date} {start}] {title[:60]:<60} | {dur:3}m | {room} (id={room_id}){spk}")
        return

    session = make_session(token)

    # Get submission type
    types = api_get_all(session, 'submission-types/')
    if not types:
        print("ERROR: no submission types"); sys.exit(1)
    type_id = types[0]['id']

    stats = {'created': 0, 'skipped': 0, 'errors': 0}

    for date, start, end, room, title, speakers in TALKS:
        key = f"talk|{date}|{start}|{room}|{title[:40]}"
        if key in state['submissions'] and state['submissions'][key].get('scheduled'):
            print(f"  [skip] {title[:60]}")
            stats['skipped'] += 1
            continue

        start_dt = parse_dt(date, start)
        end_dt = parse_dt(date, end)
        dur = int((end_dt - start_dt).total_seconds() / 60)
        room_id = room_map.get(room)
        if not room_id:
            print(f"  WARNING: room '{room}' not in state, skipping '{title[:50]}'")
            stats['errors'] += 1
            continue

        # Pretalx enforces a 200-char title limit; if over, keep full title in abstract
        api_title = title if len(title) <= 200 else title[:197] + '...'
        abstract_parts = []
        if len(title) > 200:
            abstract_parts.append(title)
        if speakers:
            abstract_parts.append(f"Presenter(s): {speakers}")
        abstract = '\n\n'.join(abstract_parts)

        print(f"\n  [{date} {start}] {title[:65]}")
        if speakers:
            print(f"    {speakers}")

        sub_resp = api_post(session, 'submissions/', {
            'title': api_title,
            'abstract': abstract,
            'submission_type': type_id,
            'duration': dur,
            'content_locale': 'en',
        })
        if not sub_resp.ok:
            stats['errors'] += 1
            continue

        code = sub_resp.json()['code']
        api_post(session, f'submissions/{code}/accept/', {})
        api_post(session, f'submissions/{code}/confirm/', {})

        slots = api_get_all(session, f'slots/?submission={code}')
        if not slots:
            print(f"    WARNING: no slot for {code}")
            state['submissions'][key] = {'code': code, 'slot': None, 'scheduled': False}
            save_state(state)
            stats['errors'] += 1
            stats['created'] += 1
            continue

        slot_id = slots[0]['id']
        patch_resp = api_patch(session, f'slots/{slot_id}/', {
            'room': room_id,
            'start': fmt_dt(start_dt),
        })
        scheduled = patch_resp.ok
        if scheduled:
            print(f"    code={code} slot={slot_id} → {fmt_dt(start_dt)} {room} ({dur}m)")
        else:
            stats['errors'] += 1

        state['submissions'][key] = {'code': code, 'slot': slot_id, 'scheduled': scheduled, 'title': title}
        save_state(state)
        stats['created'] += 1

    print(f"""
=== Summary ===
  Talks imported:   {stats['created']}
  Skipped:          {stats['skipped']}
  Errors:           {stats['errors']}
""")
    if not args.dry_run and stats['created'] > 0:
        print("Run: uv run reimport_schedule.py  (with --skip-rooms, no --delete-all)")
        print("then release a new schedule version to publish the updated slots.")


if __name__ == '__main__':
    main()
