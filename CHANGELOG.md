# Personal fork changes

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
