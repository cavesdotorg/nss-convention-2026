# Debug Context: Pretalx Rooms Page 500 Error

## The Problem
`/orga/event/nss-convention-2026/schedule/rooms/` returns HTTP 500.
Server runs in production mode (DEBUG=False) so no traceback is visible in the browser.

## What I Need
The Django traceback from the server logs for that 500 error.

## Useful Commands

Check recent Django/Pretalx error logs (try whichever applies):
```bash
journalctl -u pretalx -n 100 --no-pager
journalctl -u gunicorn -n 100 --no-pager
journalctl -u uwsgi -n 100 --no-pager
docker logs <pretalx-container> 2>&1 | tail -100
tail -100 /var/log/pretalx/*.log
tail -100 /path/to/pretalx/data/logs/*.log
```

If you can enable DEBUG temporarily, add to pretalx.cfg or local_settings.py:
```
DEBUG=True
```
then restart and reload the page to get a full traceback.

Alternatively, reproduce the error in a Django shell:
```bash
cd /path/to/pretalx
python -m pretalx shell
```
```python
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from pretalx.orga.views.schedule import RoomList  # or similar view

# Or just import the view and call it manually to get the traceback
```

## Recent Changes (most likely culprits)

The error appeared after these API operations on the `nss-convention-2026` event:

1. **Published schedule v1.9** (wrong version — should have been 2.8) then published **v2.8** and **v2.9** in quick succession
2. **Created room 30 "VPI Campground"** via `POST /api/events/nss-convention-2026/rooms/`
3. **Created submission `3GDGVD` "Beer Swap"** (track 12, Social & Events, duration 120 min)
4. **Scheduled slot 2827** for Beer Swap at 2026-07-08T20:00 in room 30
5. Room 30 and submission 3GDGVD have since been **deleted** via the API — but the slot (2827) may still exist as a dangling reference

## Most Likely Cause

Slot 2827 was deleted along with the submission, but it appeared in a published schedule version (v2.9). The rooms view may be trying to render historical schedule data that references the now-deleted slot/room, causing a crash.

Check if slot 2827 or room 30 have any dangling references in the database:
```sql
SELECT * FROM schedule_slot WHERE id = 2827;
SELECT * FROM schedule_room WHERE id = 30;
SELECT * FROM schedule_slot WHERE room_id = 30;
```

Also check published schedule versions referencing these:
```sql
SELECT * FROM schedule_schedule WHERE version IN ('1.9', '2.8', '2.9');
```

## Event Info
- Event slug: `nss-convention-2026`
- API token available if needed for further API calls
