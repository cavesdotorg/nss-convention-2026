# NSS Convention 2026 Schedule Import

Tools for importing the NSS Convention 2026 schedule into Pretalx.

## Source Data

**Final source (June 2026):**
- `2026-06-15/PrintCopy - 2026_NSSProgram_FINALv2.pdf` — full program guide; authoritative source
- `2026-06-15/ForPrint NSS2026_Schedule_FINAL_6_14_26 LD.xlsx` — schedule grid embedded in the PDF; used as the structured input for `reimport_schedule.py`

**Original source (March 2026, superseded):**
- [Schedule Google Sheet](https://docs.google.com/spreadsheets/d/1nv4gmPcHrfDJp62hioi666MGbg9Hz_-b/edit)
- `2026-03-15/*.csv` — exported tabs from the Google Sheet

## Setup

Fill in `pretalx.env` with your token:
```
PRETALX_TOKEN=your_token_here
```

## Usage

```sh
# Fresh import from the June 2026 final XLSX (wipes existing submissions first)
uv run reimport_schedule.py --delete-all

# Dry run to preview what will be imported
uv run reimport_schedule.py --dry-run
uv run reimport_schedule.py --delete-all --dry-run

# Assign tracks to sessions
uv run assign_tracks.py

# Sync state from Pretalx (after manual edits in the UI)
uv run sync_state.py
```

All scripts load credentials from `pretalx.env` automatically. Dependencies are declared inline — no separate install step needed.

`reimport_schedule.py` is idempotent via `import_state.json`. It skips any session already marked `scheduled: true` in the state file.

## Venue Map

`map.html` is an interactive Leaflet/OSM map of the convention venues. OSM tiles require an HTTP referer, so open it via a local server rather than directly as a file:

```sh
python -m http.server 8080
# then open http://localhost:8080/map.html
```

See `discrepancies.md` for known data issues in the June 2026 source files.
