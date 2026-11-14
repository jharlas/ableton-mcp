# Personal fork changes

## Remote Script 1.18.3 — 2026-11-14

Add `get_arrangement_clip_notes(track_index, clip_index, offset=0, limit=64)`.
A full snapshot can complete successfully yet exceed the client's response
limit. Reading one Arrangement MIDI clip no longer requires that snapshot
or copying the clip into Session view.

The new tool returns compact JSON pages capped at 24,000 bytes, with
`total_note_count`, `returned_note_count`, `has_more`, and `next_offset`.
The requested limit must be 1–128; the byte budget may reduce the page size.
Follow the returned offset until complete. Indices are zero-based and come
from `get_arrangement_clips`, which now explicitly labels each `clip_index`.
Both Arrangement reads execute through the main-thread queue.

Notes are sorted by start time, pitch, and note ID. Times remain in absolute
clip beats; Arrangement placement and clip/loop markers are returned
separately. `get_all_notes_extended` includes source notes outside markers,
as documented in the [Live Object Model](https://docs.cycling74.com/apiref/lom/clip/#get_all_notes_extended).
This does not expand loop repetitions into an Arrangement performance.
Avoid editing the clip while paging; restart pagination after edits.
Audio clips and API failures produce errors instead of misleading empty notes.

After installing, save and restart Live, then restart Claude Desktop so its
MCP server reloads and exposes the new tool. Verify the Remote Script reports
1.18.3 before testing the live command. Automated tests cover paging without
gaps, byte limits, cropped notes, errors, and main-thread dispatch.

## Remote Script 1.18.2 — 2026-11-14

Fix the cross-thread handoff for `get_session_info` and
`get_session_snapshot`. Socket workers previously called Live's
`schedule_message`; inspection of the installed framework and an isolated
race reproduction showed that concurrent task additions can be lost when
the scheduler replaces its task list. Historical timeouts happened before
snapshot execution began, consistent with this race.

Requests now enter a thread-safe queue drained by Live's main-thread
`update_display` callback. Each read reacquires the current Song. The queue
holds at most 32 pending requests and processes at most two per tick.
The existing eight-second deadline is retained: expired queued work is
skipped, and results from already-running reads are discarded if late.
Disconnect releases waiting callers. Request IDs and separate queue-wait
and execution timings distinguish dispatch delays from expensive reads.

Regression coverage includes concurrent callers, enqueueing during a drain,
queue capacity, expiration before and during execution, disconnect,
exception propagation, main-thread affinity, and snapshot serialization.
The installer bundle and expected version are synchronized.

Restart Live after installation; reselecting the control surface may retain
cached code. Verify `get_remote_script_info` reports `1.18.2`, then repeat
read-only snapshots with notes and parameters both enabled and disabled.
Unit tests do not establish that the new script is loaded in Live.

This change covers the two session read commands; other command dispatch
paths are unchanged.
