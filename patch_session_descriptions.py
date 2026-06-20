#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "python-dotenv"]
# ///
"""
Patch session block descriptions extracted manually from the PDF program guide
(pages 45-59). Matches by title substring; applies to all matching submissions.
"""

import os, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "pretalx.env")

TOKEN = os.environ["PRETALX_TOKEN"]
HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
API = "https://talks.caving.dev/api/events/nss-convention-2026"

# (title_substring, description) — substring matched case-insensitively against submission title.
# For sessions with multiple instances (e.g. Yoga Tue + Thu), same description applied to all.
DESCRIPTIONS = [
    ("Vertical Training Commission",
     "This is the annual business meeting of the NSS Vertical Training Commission (VTC). Chartered in December 2021, VTC's mission is to develop and implement a national vertical training program for U.S. cavers. At the annual meeting, we will provide an update on our progress and plans for the next few years, and solicit input and feedback from NSS members. Everyone is welcome to attend."),

    ("Communications & Electronics",
     "The Communications and Electronics Session covers all applications of electronics in caving including surveying, photography, wired and wireless communications, lighting, data logging, and radiolocation. Amateur Ham radio may also be used in the pursuit of these goals. Informal talks and demonstrations will follow the formal presentations."),

    ("Vertical Climbing Contests",
     "One of the highlights at each NSS Convention is the Vertical Climbing Contest, where rope climbers of every age group can test their skills and equipment for ascending 11mm caving rope using Single Rope Techniques (SRT)."),

    ("Yoga",
     "Join us Tuesday and Thursday from 8:00–9:00 a.m. for a free yoga session designed for all experience levels. Space is limited to 20 people per session, and participants must sign up at Registration by the evening before class. Participants should bring their own mats or other props."),

    ("Coffee & Karst",
     "Grab a coffee and donut and join fellow cavers and karst professionals for informal, peer-driven discussions on real-world challenges. Come with a question, an answer, or both. Multiple topic-focused discussions each day — no microphones, no slides, just honest conversation and shared expertise."),

    ("Cavers Against Sexual Harassment",
     "Join fellow cavers, grottos, and organizations for an open discussion on handling sexual harassment in our community by hearing lessons learned, exploring available resources, and working together to build a safer, more supportive caving culture."),

    ("Cave Conservation & Management",
     "Conservation Management Talks explore how conservation touches every aspect of caving and speleology. Through talks, panels, and open discussion, sessions cover minimum-impact stewardship, science-based exploration, karst watershed protection, bat biology, WNS decontamination, habitat ecosystems, cave restoration, and more. Join us for spirited presentations and evidence-informed strategies for protecting caves and karst as the interconnected agroecosystems they are."),

    ("Discover Vertical Caving",
     "Introduction to vertical training. Participants will learn basic terminology, equipment, rappelling, and ascending techniques from experienced instructors. This course is ideal for beginners or anyone wanting to review the fundamentals before choosing or purchasing vertical gear. Students must provide their own helmet, gloves, and secure closed-toe footwear."),

    ("Convention Planning",
     "If you are planning a future NSS Convention or considering planning one, it is important that you attend this meeting. You will be able to learn from the experiences of those who have organized past conventions or are working on near-future conventions. You can ask questions you know that you need to be answered and, even better, discover important information you did not realize you needed."),

    ("Congress of Grottos",
     "The Congress of Grottos (COG) is the annual meeting of NSS Internal Organizations (IOs), including grottos, sections, regional associations, and surveys. The COG is made up of delegates from the IOs and functions as an advisory body to the NSS Board of Governors. The Congress provides a structure for receiving feedback from members through their IOs, discussing ideas and formulating recommendations based on the results of its annual meeting. Resolutions are presented to the NSS Board for consideration."),

    ("Pottery Demonstration",
     "Join Peter Jones, an accomplished potter, experienced caver, and cave photographer, for a pottery demonstration at the NSS Convention. This session offers a chance to watch his creative process and learn how his artistic work is informed by a lifetime of exploration, observation, and appreciation of caves."),

    ("NSS Auction",
     "This annual convention event offers caving-related treasures, collectibles, gear, artwork, and memorabilia for bidding, with proceeds supporting NSS-designated funds."),

    ("Campground Party",
     "The traditional Wednesday night party. Music will be provided by Muchos Garcias. There will be cold beverages of various types to keep everyone hydrated."),

    ("Contingency Considerations in Caving",
     "This hands-on clinic teaches cavers practical self-rescue skills for preventing and managing common underground mishaps, including contingency rigging, improvised vertical systems, haul systems, loaded-line conversions, and basic medical considerations. Pre-registration is required. Proceeds from the class will be donated to NCRC and VTC gear cache funds."),

    ("Cave Photography Workshop",
     "In-cave workshop led by Dave Bunnell. Limited to 10 participants (pre-registration and fee required). Carpooling to the cave site is recommended. There is a short hike through a wooded area to the cave entrance and a minimal amount of crawling/stooping before reaching a large multi-level chamber. Entering the main chamber generally requires the use of a handline to navigate down a flowstone slope; cavers who wish additional protection may opt to wear a simple harness with a handled ascender. Sack lunch will be provided."),

    ("Planned Giving",
     "The NSS presents planned giving as a way to include the Society in your financial or estate plans and create a lasting legacy for cave exploration, science, conservation, and caving culture. These gifts help strengthen the NSS now and help grow the Society for the future."),

    ("NCKMS Steering Committee",
     "The annual meeting of the National Cave and Karst Management Symposium (NCKMS) Steering Committee. They will discuss plans for 2027 and 2029. All Steering Committee representatives should plan to attend. This meeting is also open to all other interested cavers. The meeting starts at noon and will finish in time to get lunch before the afternoon sessions start."),

    ("Cave Diving Exploration",
     "The Cave Diving Exploration Session is the underwater partner of the US and International Exploration sessions. Please watch the daily news sheet for updated speakers or agenda."),

    ("Convention Debrief",
     "At this meeting, the organizers will discuss what worked, failed, and needed adjustment. They will describe good and bad surprises and how they think they could have improved things. They will explain why they made certain decisions. Then they will listen to you: your questions, concerns, complaints, and, they hope, some praises. The intention is that time spent at this meeting, talking and listening, will help improve future Conventions."),

    ("NSS Preserves & Acquisitions",
     "The NSS owns 23 Nature Preserves and manages four others that belong to private cave landowners and conservancies. A team of committed NSS volunteers manages each NSS Nature Preserve, ensuring conservation efforts, facilitating stewardship and management efforts, and overseeing access for exploration, surveys, and research. At our annual meeting, NSS Preserve Managers provide updates on conservation, management, visitation, research, and stewardship activities. The NSS Preserves & Acquisitions Committee will also share plans for capital projects and pending acquisitions."),

    ("NSS Awards Committee",
     "The Awards Committee reviews NSS member nominations and makes recommendations on who receives awards. Presentation of the awards are made at the NSS Awards Banquet on Friday night. If you are interested in how the process works, want to provide helpful suggestions, or are just curious about what the committee does, the Awards Committee conducts an open meeting on Thursday between 2:00–3:00pm."),

    ("Sketching Contest Results",
     "Results from the in-cave sketching contest will be discussed and awards announced."),

    ("NSF Trustees Meeting (open)",
     "The National Speleological Foundation is the money and endowment managing organization associated with the NSS and other cave-related organizations. Come and meet the Trustees and learn a little bit more about the financial side of caving. Everyone is welcome."),

    ("Survey & Cartography Session",
     "The purpose of the Survey and Cartography Section (SACS) is to improve the state of cave documentation and survey, cave data manipulation, and all forms of cave cartography. SACS is made up of a diverse group of cavers who are interested in sharing ideas, technology and opinions on the science and art of producing digital and traditional cave maps, on methods of cave data collection and reduction, and for improving the digital manipulation and representation of cave survey data. Anyone interested in cave mapping and cartography is welcome to join."),

    ("Geology and Geography",
     "The Geology and Geography Session includes a variety of topics on caves and karst including karst hydrogeology, speleogenesis, cave structure and stratigraphy, cave morphologies and morphometrics, geochemistry, microclimatology, and karst geomorphology."),

    ("Collegiate Grotto Challenges",
     "College grottos face a challenge no other caving organization does: complete membership turnover every four years. In order to be sustainable they have to recruit new members, develop student leaders and maintain a collection of equipment and resources all while racing against the clock of graduation. College grotto members are encouraged to attend and talk about what works, what doesn't, and how to empower newer members to carry the program forward long after current leaders move on."),

    ("NSS Awards Banquet",
     "The NSS Annual Awards Banquet is a highlight of convention week, bringing cavers together to celebrate service, achievement, exploration, science, conservation, and leadership within the Society. During the banquet, the NSS presents its annual awards and recognizes individuals and groups whose contributions have strengthened the caving community and advanced the mission of the NSS."),

    ("Cave Digging Section",
     "The section meeting is open to anyone interested in finding new cave and expanding existing caves. There will be a short business meeting and election of section officers followed by presentations on a variety of dig projects, with an informal question and answer session at the end."),

    ("Fellows & New Members Reception",
     "Reception will take place at Harrison County Discovery Center (233 N Capitol Avenue, Corydon, IN 47112) from 6:30–8:30 pm. NSS Fellows and any new members (NSS# 75240 or higher) are invited to attend. Light refreshments will be served."),

    ("Keynote Speaker: Genevieve von Petzinger",
     "Corydon High School Auditorium, 9:00 pm — open to all Convention attendees. Presentation will be live from Abu Dhabi. Genevieve von Petzinger is an internationally recognized paleoanthropologist and cave art researcher. She is best known for her work cataloging and analyzing the geometric signs found in Ice Age cave art across Europe, and is the author of The First Signs."),

    ("10 Years of The Caving Podcast",
     "An Oral History of Indiana Caving. Matt Pelsor shares audio clips from The Caving Podcast of Indiana cavers recounting exploration highlights and caving stories."),

    ("Fine Arts Salon Opening",
     "The Fine Arts Salons will host an Opening Reception starting at noon to celebrate the public opening of the Salons. Please do not visit the Salons before the reception. Light refreshments will be served."),

    ("NCRC Annual Meeting",
     "This is the annual business meeting of the National Cave Rescue Commission."),

    ("Arts & Letters",
     "Have you considered writing a book about your cave exploration projects? An article for your local newspaper on your grotto's conservation work? Do you have cave poetry or stories that deserve a wider audience? The Arts and Letters Workshop invites cavers to share a story or poem with the group. The workshop is held in conjunction with the Arts and Letters Salon — join the Salon for the annual lunch at noon, or simply drop in and become part of the conversation. Subscribers to Illuminations are automatically part of the Salon. There will be a short excursion to Squire Boone Caverns for inspiration."),

    ("Sketching Contest",
     "Sign in at the Cartography Salon area (catwalk above the Vendor area) and take one bag of paper sheets. Sketching days are Monday and Tuesday, self-guided in-cave (8:00am–7:00pm). Wednesday is guided in-cave sketching (1:00–5:00pm, in-cave). Completed sketches must be turned in to the Cartography Salon by 3:00pm Thursday."),

    ("Introduction to Sketching",
     "Learn the basics of cave sketching — both paper and digital. Half day in the classroom (morning) and half day underground. Details in class. Registration required."),

    ("Speleology for Cavers",
     "Workshop on cave geology for cavers, led by Steve Stokowski. Participants will learn the difference between strike and dip, vadose and phreatic zones, speleothem types, and more. Registration required."),

    ("BOG Open Meeting",
     "The Board of Governors sets policy for the management of the Society. This open meeting consists of reports from officers and committees. Newly elected board members will be introduced. The meeting is open to all members. Take the opportunity to observe board members in action and learn about some of the Society's business."),

    ("Photo Salon and Salon Awards",
     "The Thursday evening program provides a venue to celebrate art and caves. Each of the NSS Salons displays photographs, paintings, prints, sketches, ballads, and videos created by cavers. The short show runs 5:30–7:00pm; the full show runs 7:30–10:00pm. Both are held in the Auditorium."),

    ("State Cave Surveys",
     "Representatives from state and regional cave surveys present updates on survey progress, significant new discoveries, and ongoing projects across the country."),
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
    # Only consider empty ones
    empty = [s for s in subs
             if not (s.get('abstract') or '').strip()
             and not (s.get('description') or '').strip()]
    print(f"  {len(empty)} empty sessions\n")

    patched = skipped = no_match = 0

    for substring, desc in DESCRIPTIONS:
        matches = [s for s in empty if substring.lower() in s['title'].lower()]
        if not matches:
            print(f"  NO MATCH: {substring!r}")
            no_match += 1
            continue
        for s in matches:
            code = s['code']
            if dry_run:
                print(f"  [dry] [{code}] {s['title'][:65]}")
                print(f"        {desc[:80]!r}")
                patched += 1
            else:
                r = requests.patch(f"{API}/submissions/{code}/",
                                   json={'abstract': desc}, headers=HEADERS)
                if r.ok:
                    print(f"  patched [{code}] {s['title'][:65]}")
                    patched += 1
                else:
                    print(f"  ERROR [{code}]: {r.status_code} {r.text[:80]}")

    print(f"\nDone. {'Would patch' if dry_run else 'Patched'} {patched}, no match {no_match}.")


if __name__ == '__main__':
    main()
