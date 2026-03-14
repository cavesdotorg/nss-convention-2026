# NSS 2026 Schedule Discrepancies
_Identified during import on 2026-03-14_

---

## 1. Room Name Inconsistencies

| Sheet value | Canonical used | Rows |
|---|---|---|
| `Jr. High Gym` | `Junior High Gym` | Row 29 (Mon afternoon) |
| `campground` (lowercase) | `Campground` | Row 39 (Fri evening) |
| `Vendors area catwalk` | — | Row 35 — differs from `Vendors Area` in capitalization |
| `Cave Conservation &  Science` | — | Row 28 — double space vs `Cave Conservation & Science` |

---

## 2. Numbered Rooms Have No Building Name

Rooms 100, 102, 104, 110, 112, 154, 205, 228, 254 have no building prefix.
Building name unknown — needs to be confirmed with organizers and added to the sheet.

---

## 3. Time Format Inconsistencies

| Event | Time as written | Issue |
|---|---|---|
| Opening Ceremony (Mon) | `8:30 -9:00` | Space before dash |
| BOG Meeting (Closed) (Mon) | `2:00 - 5:00` | Spaces around dash |
| Howdy Party (Mon) | `6:30 - Midnight` | Spaces around dash |
| Video Salon Viewing (Fri) | `9:00 - Noon` | Spaces around dash |
| NSS Awards Banquet (Fri) | `6:30 - 8:30` | Spaces around dash |
| Climbing contests (Tue) | `1:00-5::00` | Double colon — typo, likely `1:00-5:00` |
| Cave Conservation & Science (Tue) | `2:00-5:01` | Likely typo, should be `5:00` |
| Planned Giving (Thu) | `9-Noon` | Missing `:00` on start |
| State Cave Surveys (Thu) | `9-Noon` | Missing `:00` on start |
| Vertical Section session (Thu) | `9-Noon` | Missing `:00` on start |
| Paleontology (Thu) | `9-Noon` | Missing `:00` on start |
| Carlsbad Caverns Listening Session (Mon) | `9:00-noon` | Lowercase `noon` |
| The Caving Podcast Live (Fri) | `noon-1:00` | Lowercase `noon` |

---

## 4. Missing End Times (defaulted to 60 min)

| Event | Day | Time as written |
|---|---|---|
| Vertical Climbing Contests | Mon | `12:30 start` |
| Vertical climbing contests | Tue | `12:30 start` |
| NSS Auction | Wed | `7:00 start` |
| Open Mic | Tue | `8:00 start` |
| Campground Party | Wed | `9:00 start` |
| NSS Awards Committee | Thu | `2:00-3:00 open  4:00-5:00 closed` (split session — only first half imported) |

---

## 5. Missing Location

| Event | Day | Issue |
|---|---|---|
| NSS Awards Banquet | Fri | No room/location listed in sheet |

---

## 6. Title Inconsistencies / Extra Whitespace

| Sheet value | Issue |
|---|---|
| `Cave Conservation &  Science` | Double space around `&` (appears on Tue afternoon) |
| `Cave Writers  Workshop` | Double space (appears Mon and Fri) |
| `Speleothem Repair    Workshop` | Four spaces (Tue morning) vs `Speleothem Repair Workshop Part II` (Wed) |
| `Vertical Training Commission (VTC)  (30 seats, 1 table)` | Room capacity note embedded in event title |
| `Geology  and Geography` | Double space (Thu morning) vs `Geology and Geography` (Thu afternoon/Fri) |

---

## 7. Duplicate Event Entries

| Event | Issue |
|---|---|
| `Photo Workshop` (Tue) | Appears 3 times in the Tuesday column (rows 15, 21, 30) — only imported once |
| `Cave Conservation & Science` (Tue) | Appears in both morning (9:00-Noon) and lunch (Noon-1:00) blocks |

---

## 8. Multi-Day / Week-Long Events Not Imported

These appear in the header rows (rows 1–4) and were skipped:

| Event | Duration | Location |
|---|---|---|
| Fine Arts Salon | All week | Library |
| Junior Speleological Society | All week | Band Room |
| Caver Co-Op | All week | TBD |
| Ballad Listening Kiosk | All week | LOC |
| Video Kiosk | All week | LOC |
| Vendors | All week | Auxiliary Gym |
| Quiet Room | All week | 228 |
| NSS Bookstore | All week | TBD |
| Cartography Salon | All week | Aux. Gym Catwalk |
| Sketching Contest | Mon & Tue | in-cave |
| CaveSim | Mon & Tue | Next to registration |

---

## 9. Vendor Hours Note (not an event)

Row 4 contains: _"Vendors Schedule: Monday 8-5; Tues-Wed-Thursday 8 to 8; Friday 8-12"_ — this is a note in the schedule grid, not an event, and was not imported.
