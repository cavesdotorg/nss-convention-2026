# NSS Convention 2026 Schedule Import

Tools for importing the NSS Convention 2026 schedule into Pretalx.

## Source Data

[Schedule Google Sheet](https://docs.google.com/spreadsheets/d/1nv4gmPcHrfDJp62hioi666MGbg9Hz_-b/edit)

## Setup

Copy `pretalx.env` and fill in your token:
```sh
cp pretalx.env.example pretalx.env   # or edit pretalx.env directly
```

## Usage

```sh
# Import rooms and sessions
uv run import_schedule.py

# Assign tracks to sessions
uv run assign_tracks.py

# Sync state from Pretalx (after manual edits)
uv run sync_state.py
```

All scripts load credentials from `pretalx.env` automatically. Dependencies are declared inline — no separate install step needed.

Both import scripts are idempotent via `import_state.json`. See `discrepancies.md` for known issues in the source data.

## Venue Map

`map.html` is an interactive Leaflet/OSM map of the convention venues. OSM tiles require an HTTP referer, so open it via a local server rather than directly as a file:

```sh
python -m http.server 8080
# then open http://localhost:8080/map.html
```
