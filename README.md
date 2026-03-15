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
