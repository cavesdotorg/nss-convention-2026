#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "python-dotenv"]
# ///
"""
Patch the description field on all individual talks to contain the correct
presenter name(s) from import_talks.py. Matches by title[:40] (state key logic).
"""

import os, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

TOKEN = os.environ["PRETALX_TOKEN"]
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
API = "https://talks.caving.dev/api/events/nss-convention-2026"

TALKS = [
    ("2026-07-06","09:05","09:15","Auditorium","Regional Geology and GIS Overview","Rai Bosch"),
    ("2026-07-06","09:15","09:25","Auditorium","Ohio Cave Survey—State Overview","Frank Vlchek"),
    ("2026-07-06","09:25","09:35","Auditorium","Indiana Cave Survey—State Overview","Dave Everton"),
    ("2026-07-06","09:35","09:45","Auditorium","Kentucky Speleological Survey","Stephanie Suen"),
    ("2026-07-06","09:45","10:05","Auditorium","Exploring Courtey Cave and the Cave Systems of Central Ohio's Scioto River Corridor","Ryan Braggs"),
    ("2026-07-06","10:05","10:45","Auditorium","Caves of Edwards Mountain & Wayne County (incl Spelunger Cave)","Lee Florea & Chris Bauer"),
    ("2026-07-06","10:55","11:15","Auditorium","Modern Exploration in Big Bat Cave","Adam Hjermenrud"),
    ("2026-07-06","11:15","11:35","Auditorium","Pless Cave—Exploration & Mapping","Dave Everton"),
    ("2026-07-06","11:35","12:00","Auditorium","James Cave, The Cave, The Exploration","Charlie Bishop"),
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
    ("2026-07-06","14:15","14:45","112","UC Bat Edition for Bioacoustic Monitoring (virtual)","Tim Clark"),
    ("2026-07-06","14:45","15:15","112","Flamingo Cave Radios","Jamie Moon & Bob Reese, Huntsville Cave Rescue"),
    ("2026-07-06","15:15","15:45","112","Tuned Loop Antenna Matching Made Easy","Brian Pease"),
    ("2026-07-06","15:45","16:15","112","Analysis of a Network Outage in BuecherNet in Fort Stanton Cave, NM","Fort Stanton Study Project"),
    ("2026-07-06","16:15","16:45","112","Audio in Cave Projects","Steve Reames"),
    ("2026-07-07","09:00","09:20","Auditorium","Modern Exploration of Warren Cave in Florida","Bill Gee"),
    ("2026-07-07","09:20","09:40","Auditorium","Lee County Blowing – A Speleo Who Dun It","Rick Toomey"),
    ("2026-07-07","09:40","10:00","Auditorium","Binkley Cave Project","Rick Toomey"),
    ("2026-07-07","10:00","10:20","Auditorium","Recent Discoveries in Shoveleater Cave","Phil Swart"),
    ("2026-07-07","10:20","10:45","Auditorium","Fern Cave Project","Billy Gee"),
    ("2026-07-07","10:45","11:05","Auditorium","Warm River Cave Update","Pete Lindsley"),
    ("2026-07-07","11:05","11:25","Auditorium","Cave Mapping and Inventory of a Significant KY National Forest","Stephanie Suen"),
    ("2026-07-07","11:25","11:45","Auditorium","Recent Discoveries in Hidden River Cave, Kentucky","Liam Tobin"),
    ("2026-07-07","11:45","12:00","Auditorium","Whigpistle Cave Project Update: 2026","Joel Despain"),
    ("2026-07-07","09:00","09:20","205","The Powell Mountain Karst Preserve: A Management Plan Analysis","Wil Orndorff"),
    ("2026-07-07","09:20","09:40","205","Conservation and Management of the Paul Wightman Subterranean Nature Preserve","Mark Olalde"),
    ("2026-07-07","09:40","10:00","205","The Effects of Excavation on Cave Ecosystems (Two Years Later)","Rod Horrocks"),
    ("2026-07-07","10:00","10:30","205","Are There Renewable Resources in Caves? Do Drip Hole Rings Count? And What Can Cavers Ethically Do in Exploring and Studying Caves?","Clint Frobose"),
    ("2026-07-07","10:30","11:00","205","Protecting Caves and Karst – A Holistic Approach","The Cave Conservancy of the Virginias"),
    ("2026-07-07","11:00","11:20","205","Cavers, State Agencies, and the United States Forest Service Working Together to Protect Caves and Karst in Virginia","Matt Huffman"),
    ("2026-07-07","11:20","11:40","205","Celebrate the UNESCO International Day of Caves and Karst, September 13th","The Cave Conservancy of the Virginias"),
    ("2026-07-07","14:00","14:30","Auditorium","Progress in Fort Stanton Cave, New Mexico","Bill Gee"),
    ("2026-07-07","14:30","14:50","Auditorium","Gem Cave: A New Discovery Under South Dakota's Black Hills","Rene Ohms and Adam Weaver"),
    ("2026-07-07","14:50","15:20","Auditorium","Walking into Mordor: The Mount Baker Glaciovolcanic Cave Expedition","Peter Sprouse"),
    ("2026-07-07","15:20","15:40","Auditorium","2025 Silvertip Expedition: Bobsled Cave Exploration","Geo Kourounis"),
    ("2026-07-07","15:40","16:10","Auditorium","Klamath Mountains Project, Cave Research Foundation","Wil Orndorff"),
    ("2026-07-07","16:10","16:30","Auditorium","Report-Walking: Using Search and Rescue Reports to Find Unmapped Caves","Angelica Mucciarone Brewer, Tyler Nash, Elby Jones, and Ben Tobin"),
    ("2026-07-07","16:30","16:50","Auditorium","Geology, Mineralogy, Archeology and Exploration History of Hualalai Ranch Cave, Hawaii","Stephan Kempe"),
    ("2026-07-07","14:00","14:20","205","The Restoration of Pleasant Valley Cave","Dave Steward"),
    ("2026-07-07","14:20","14:40","205","Bigger, Better Mobile Caves for STEM Education Outreach","Jester Gibson"),
    ("2026-07-07","14:40","15:00","205","2026 U.S. Cave Animal of the Year – The Slimy Salamander","Matt Niemiller"),
    ("2026-07-07","15:00","15:30","205","Documenting and Describing Two Species of Cave-Adapted Blind Fish in the Tiger Cave System, Phong Nha-Kẻ Bàng National Park, Việt Nam","Prosanta Chakrabarty"),
    ("2026-07-07","15:30","16:00","205","Phong Nha-Kẻ Bàng: Cave Ecotourism for Sustainable Development in Việt Nam","Dien Ha"),
    ("2026-07-07","16:00","16:20","205","Celebrate the Conservation Legacy of Rob Stitt — Stories, Song, Snacks","Aslan Rife"),
    ("2026-07-08","09:00","09:30","Auditorium","PESH 2026","Ede Szigmond"),
    ("2026-07-08","09:30","10:00","Auditorium","Cueva Sin Fin","Donald Davis"),
    ("2026-07-08","10:00","10:30","Auditorium","40 Years of Exploration at Cueva Cheve, Oaxaca, Mexico","Bill Stone"),
    ("2026-07-08","10:30","11:00","Auditorium","Roaming North-Eastern Mexico Surveying Unexplored Caves","Don Broussard"),
    ("2026-07-08","11:00","11:30","Auditorium","New Zealand Expedition, 2026","Neil Silverwood"),
    ("2026-07-08","11:30","12:00","Auditorium","Exploration in Montenegro","Mátyás Gyimesi"),
    ("2026-07-08","08:10","08:30","205","Examining Genetic Diversity and Potential Cryptic Diversity within the Georgia Blind Salamander (Eurycea wallacei) and the Dougherty Plain Cave Crayfish (Cambarus cryptodytes) of the Upper Floridan Aquifer","Jason Moring"),
    ("2026-07-08","08:30","08:50","205","New Surveys of Cave and Groundwater Fauna in the Upper Floridan Aquifer","Rick Toomey"),
    ("2026-07-08","08:50","09:10","205","Mapping Cave Vulnerability and Priority Areas for Biospeleological Conservation","Matthew Niemiller"),
    ("2026-07-08","09:10","09:30","205","Directed Phytokarst: Red-Shifted Phototrophy and Limestone Dissolution in Cave Twilight Zones","Hazel Barton"),
    ("2026-07-08","09:30","09:50","205","Examining Phylogenetic Relationships and Cryptic Diversity in the Genus Scoterpes (Chordeumatida: Trichopetalidae), a Wide-Ranging Genus of North American Cave-Obligate Millipedes","Coral Quering"),
    ("2026-07-08","09:50","10:10","205","Evaluating the Biogenicity of Biovermiculations in Mammoth Cave, KY, USA","Hazel Barton"),
    ("2026-07-08","10:30","10:50","205","Population Monitoring of the Enigmatic Cave Snail, Fontigens antroecetes, in Stemler Cave","Bob Weck"),
    ("2026-07-08","10:50","11:10","205","A Creature from the 'Upside Down': Cryptic Cavefish Diversity in a Long-Studied Karst Cave Ecosystem","Matthew Niemiller"),
    ("2026-07-08","11:10","11:30","205","Sediment Geochemistry, Manganese Oxidation, Human Traffic, and Microbial Community Structure across Three Southern Appalachian Caves","Maria Riley"),
    ("2026-07-08","11:30","11:50","205","Subterranean Isopod Diversity in Caves of the Northern Interior Low Plateaus","Derek Hennen"),
    ("2026-07-08","09:00","09:30","102","Cavers: Who, Why, So What?","Judy Foote"),
    ("2026-07-08","09:30","10:00","102","Creating a Legacy at UA","Brian Roebuck"),
    ("2026-07-08","10:00","10:30","102","Expressing Culture Piece by Piece","Erin Lynch"),
    ("2026-07-08","10:30","11:00","102","Discussion of 'Empowering Women Through Cave Exploration and Conservation' (Article by Ellen Trautner)","Diane Reeves"),
    ("2026-07-08","14:00","14:30","Auditorium","Sternes Cave Project, Crete, Greece","Ari Stathis"),
    ("2026-07-08","14:30","15:00","Auditorium","Beneath the Thunder Dragon: Cave Exploration in Bhutan","Pat Kambesis"),
    ("2026-07-08","15:00","15:30","Auditorium","Mulu Cave Project 2026","Christine Saw and Kevin Liow"),
    ("2026-07-08","15:30","16:00","Auditorium","Mapping the Extensive Caves of the Newly Accessible Lạng Sơn Geopark, Vietnam","Thomas Hawkins"),
    ("2026-07-08","16:00","16:30","Auditorium","Archaeology to Advocacy: Southeast Sulawesi 2025","Cydney Sea"),
    ("2026-07-08","16:30","16:50","Auditorium","Continued Exploration in Mindanao, Philippines","Thomas Hawkins"),
    ("2026-07-09","09:00","09:15","205",'"Camp Rock," aka "The Black Mountain Hotel": Mount Mitchell\'s Historic Rock Shelter',"Joshua Lohnes"),
    ("2026-07-09","09:15","09:40","205","A Brief Overview of the Significant Hoosier Cavers 1850-2025","Bert Ashbrook"),
    ("2026-07-09","09:40","10:10","205","The 130-Year History of the Ohio Cave Survey","Frank Vlchek"),
    ("2026-07-09","10:10","10:30","205","Historic Cave Slides of Lewis David Lamon, NSS2188FE, Taken 1952-1990","William Putnam"),
    ("2026-07-09","10:30","10:50","205","Josiah Mosher Jr. and the Mammoth Cave Hotel","Stephen Bishop"),
    ("2026-07-09","10:50","11:15","205","When Martel was Banished from Mammoth Cave, or On Discovering a Rare Version of Hovey's 1912 Guidebook","Bob Taylor"),
    ("2026-07-09","11:15","11:35","205","Cooper's Cave, New York: A Notable Bicentennial, 1826-2026","Bob Taylor"),
    ("2026-07-09","11:35","11:55","205","Charles Waldack and Mammoth Cave","Bob Taylor"),
    ("2026-07-09","11:55","12:15","205","Pennsylvania's Show Caves","Curt Weinstein"),
    ("2026-07-09","09:00","09:45","254","An Investigation of Permanently Rigged Ropes","Ben Tobin"),
    ("2026-07-09","09:45","10:10","254","NSS Vertical Training Commission: July 2026 Progress Update","Bill Cuddington"),
    ("2026-07-09","10:10","10:35","254","Vertical Caving: Some of My Heretical Opinions","Tom Vines"),
    ("2026-07-09","10:35","11:00","254","Fundamentals of Rigging","Aaron Bird"),
    ("2026-07-09","11:00","11:25","254","The Gauntlet","Aaron Bird"),
    ("2026-07-09","11:25","11:50","254","History of Kernmantle Rope","Bill Cuddington"),
    ("2026-07-09","11:50","12:15","254","From Incident to Insight: A College Grotto's Perspective on a Vertical Rescue in Wind-Hicks Cave","Liam Tobin"),
    ("2026-07-09","12:15","12:40","254","Bolting Considerations for High Traffic Caves and/or Bad Rock Quality: A Brief Introduction to Glue-In's","Aaron Bird"),
    ("2026-07-09","12:40","13:05","254","Fun and Sketchy Things to Do with Rappel Devices","Bill Cuddington"),
    ("2026-07-09","09:05","09:25","102","The Discovery and Recovery of the Shenandoah Caverns Peccaries and Reincarnation of PRIOVAC","Blaine W. Schubert"),
    ("2026-07-09","09:25","09:45","102","Extinct Long-Nosed Peccary Remains from Shenandoah Wild Cave, Virginia: An Update","Blaine W. Schubert"),
    ("2026-07-09","09:45","10:25","102","The Importance of Small Mammals in Cave Paleontology","Blaine W. Schubert"),
    ("2026-07-09","10:25","10:45","102","Advances in Discovering and Managing Paleontological Resources in Tennessee Caves","Jan Simek"),
    ("2026-07-09","10:45","11:05","102","New Interpretation of Sediments and Fossils from a Cave in Sullivan County, Tennessee","Jan Simek"),
    ("2026-07-09","11:05","11:25","102","An Ancient Short-Faced Bear Skeleton and Other Fauna from Cebada, Chiquibul Cave System, Belize","Blaine W. Schubert and Alson Ovando"),
    ("2026-07-09","14:15","14:45","154","Can AI Image Editing Tools Understand a Cave?","Steve Reames"),
    ("2026-07-09","14:45","15:15","154","Why and When to Choose a Cell Phone Over a Conventional Digital Camera for Cave Photography","Phil Swing"),
    ("2026-07-09","15:15","15:45","154","Diffraction Limited Optics and the New Galaxy S25 Ultra 200Mp Lens","Edward Schultz"),
    ("2026-07-09","14:05","14:25","102","Cataloging the National Cave Museum","Bert Ashbrook"),
    ("2026-07-09","14:25","14:45","102","Early Woodland Gypsum Mining at Bluff Cave, Mammoth Cave National Park, Kentucky","Angelo George"),
    ("2026-07-09","14:45","15:05","102","The Salts Cave/Unknown Cave Footprint Project, Mammoth Cave National Park, Kentucky","Angelo George"),
    ("2026-07-10","09:00","09:20","Auditorium","Geologic Characterization of the Glaciovolcanic Caves of Mount Baker, Washington","Peter Sprouse"),
    ("2026-07-10","09:20","09:40","Auditorium","New Paradigms of Speleogenesis in the Ohio River Valley","George Veni"),
    ("2026-07-10","09:40","10:20","Auditorium","Utilizing Structural Lineament Mapping with Digital Elevation Models for Understanding Speleogeneic Patterns in the Mammoth Cave Plateau","Chris Groves"),
    ("2026-07-10","10:20","10:40","Auditorium","Applied Geophysics and LiDAR in Karst: From Environmental Consulting to Cave Discovery","Michael Jones"),
    ("2026-07-10","10:40","11:00","Auditorium","Quantifying and Comparing Sinkhole Morphometry across Different Geospatial Datasets","George Veni"),
    ("2026-07-10","11:00","11:20","Auditorium","Understanding the Variability in Gas Concentrations of Carlsbad Cavern","Hazel Barton"),
    ("2026-07-10","13:30","13:50","Auditorium","Evaluating Speleothem Samples as a Geological Archive for Paleomagnetic Records and Environmental Interpretation","Jon Fong"),
    ("2026-07-10","13:50","14:10","Auditorium","The Importance of Caves in the History of Geology","Art Palmer"),
    ("2026-07-10","14:10","14:30","Auditorium","The Consequences of the Self-Modification of Island Karst Aquifers","George Veni"),
    ("2026-07-10","14:50","15:10","Auditorium","Exploring the Stratigraphic and Structural Context of the Cheve Karst System, Oaxaca, Mexico","Pete Lindsley"),
    ("2026-07-10","15:10","15:30","Auditorium","Talus Caves of Franconia Notch, New Hampshire","Anatoliy Bulychov"),
    ("2026-07-10","15:30","15:50","Auditorium","The Influence of Magnitude and Frequency on the Relative Importance of Chemical and Mechanical Erosion: Examples from J2 and Slot Canyons in the Ozarks","Art Palmer"),
    ("2026-07-10","13:00","13:15","205","Software Defined Cave Symbology","Wil Orndorff"),
    ("2026-07-10","13:15","13:40","205","How Do I Know Where This Drone Image Is?","Peter Sprouse"),
    ("2026-07-10","13:40","14:05","205","Photogrammetry for Fun and Prospecting","Ron Simmons"),
    ("2026-07-10","14:05","14:25","205","Testing and Reviewing the New 3DMakerpro Raven Handheld LiDAR Scanner","Steve Reames"),
    ("2026-07-10","14:25","14:45","205","Speleological Model in ArcGIS","James Thomas"),
    ("2026-07-10","15:00","15:20","205","Developing New Surveyors, Sketchers and Cartographers through Beginner Focused Projects","Kyle Kreutz"),
    ("2026-07-10","15:20","15:45","205","Techniques for Generating High-Definition Karst-Focused Terrain Imagery from LiDAR Surface Data","Thomas Aley"),
    ("2026-07-10","15:45","16:10","205","0Bar Maps: Interactive Maps for Your Cave Phone","Eric Seldman"),
    ("2026-07-10","16:10","16:35","205","Select Methods Using Adobe Illustrator","Pat Kambesis"),
    ("2026-07-10","16:35","17:00","205","Automated Cave Detection from LiDAR: Improved Methods and Broader Access","Aaron Addison"),
]


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


def main():
    dry_run = '--dry-run' in sys.argv

    print("Fetching all submissions...")
    subs = get_all(f"{API}/submissions/?limit=100")
    by_title40 = {}
    for s in subs:
        by_title40.setdefault(s['title'][:40], []).append(s)

    patched = skipped = not_found = errors = 0

    for date, start, end, room, title, speakers in TALKS:
        key = title[:40]
        matches = by_title40.get(key, [])
        if not matches:
            print(f"  NOT FOUND: {title[:60]}")
            not_found += 1
            continue

        sub = next((s for s in matches if s['title'] == title or s['title'] == title[:197] + '...'), matches[0])
        current_desc = (sub.get('description') or '').strip()

        if current_desc == speakers:
            skipped += 1
            continue

        if dry_run:
            print(f"  [dry] [{sub['code']}] {title[:55]}")
            print(f"    was: {current_desc!r}")
            print(f"    now: {speakers!r}")
            patched += 1
        else:
            r = requests.patch(f"{API}/submissions/{sub['code']}/",
                               json={'description': speakers}, headers=HEADERS)
            if r.ok:
                patched += 1
            else:
                print(f"  ERROR [{sub['code']}]: {r.status_code} {r.text[:80]}")
                errors += 1

    print(f"\nDone. {'Would patch' if dry_run else 'Patched'} {patched}, already correct {skipped}, not found {not_found}, errors {errors}.")


if __name__ == '__main__':
    main()
