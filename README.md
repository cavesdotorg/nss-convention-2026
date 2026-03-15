# NSS Convention 2026 Schedule Import

Tools for importing the NSS Convention 2026 schedule into Pretalx.

## Source Data

[Schedule Google Sheet](https://docs.google.com/spreadsheets/d/1nv4gmPcHrfDJp62hioi666MGbg9Hz_-b/edit)

## Usage

```sh
# Import rooms and sessions
PRETALX_TOKEN=<token> uv run --with requests python import_schedule.py

# Assign tracks to sessions
PRETALX_TOKEN=<token> uv run --with requests python assign_tracks.py
```

Both scripts are idempotent via `import_state.json`. See `discrepancies.md` for known issues in the source data.
