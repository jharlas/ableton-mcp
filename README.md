<div align="center">

# Ableton MCP

Personal fork maintained at [jharlas/ableton-mcp](https://github.com/jharlas/ableton-mcp).
See [BASELINE.md](BASELINE.md) for provenance, the preserved snapshot fixes,
validation, and the `baseline-2026-11-14` reference tag.
See [CHANGELOG.md](CHANGELOG.md) for subsequent fixes, including the
Remote Script 1.18.2 snapshot dispatch fix and 1.18.3 Arrangement note pages.

**Connect Ableton Live to Claude AI**

Prompt-assisted music production, end-to-end track creation, and Live session and arrangement manipulation — driven by AI.

[![PyPI Version](https://img.shields.io/pypi/v/ableton-mcp?color=blue)](https://pypi.org/project/ableton-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-join-5865F2?logo=discord&logoColor=white)](https://discord.gg/JK4hNKGprW)

[**Setup Video**](https://youtu.be/iJWJqyVuPS8) · [**Discord**](https://discord.gg/JK4hNKGprW) · [**Issues**](https://github.com/ahujasid/ableton-mcp/issues)

</div>

---

## Quickstart

**For this personal fork, use [Installing this fork](#installing-this-fork)
below.** The `uvx ableton-mcp` commands in the published-package setup fetch
PyPI; they do not select this repository's changes.

Three steps: install `uv`, point your MCP client at the server, install the Ableton Remote Script.

**1. Install uv**

```bash
# macOS
brew install uv
```

Otherwise, install from [uv's official website](https://docs.astral.sh/uv/getting-started/installation/).

> **Warning:** Do not proceed before installing uv.

**2. Add the MCP server to your client**

<details open>
<summary><b>Claude Desktop</b> — Settings → Developer → Edit Config</summary>

```json
{
    "mcpServers": {
        "AbletonMCP": {
            "command": "uvx",
            "args": [
                "ableton-mcp"
            ]
        }
    }
}
```
</details>

<details>
<summary><b>Cursor</b> — Settings → MCP</summary>

Paste this as a command:

```
uvx ableton-mcp
```
</details>

> **Warning:** Only run one instance of the MCP server (either on Cursor or Claude Desktop), not both.

**3. Install the Ableton Remote Script**

```bash
uvx --from ableton-mcp ableton-mcp-install-script
uvx --from ableton-mcp ableton-mcp-install-script --list-targets   # preview target folders first
```

**4. Connect**

1. Launch Ableton Live
2. Go to **Settings/Preferences → Link, Tempo & MIDI**
3. In the **Control Surface** dropdown, select **AbletonMCP**
4. Set **Input** and **Output** to **None**

That's it — ask Claude to build something.

## What's in this fork

Extends the base Remote Script with a much larger slice of the Live Object
Model: automation envelope writing, device/track/clip/scene deletion, full
mixer control (volume/pan/sends), audio clip properties (gain/pitch/warping),
groove pool assignment, track routing, undo/redo, session record, track/clip
colour, clip launch settings, per-note MIDI editing (targeted note updates
and ranged removal), warp marker editing, note selection, and take lanes.

See [`AbletonMCP_Remote_Script/CAPABILITIES.md`](AbletonMCP_Remote_Script/CAPABILITIES.md)
for current verification status and the historical Live capability audit.
The historical findings are dated observations, not a fresh verification of
every feature on the current Live version.

---

## Table of Contents

- [Quickstart](#quickstart)
- [Features](#features)
- [Components](#components)
- [Installation](#installation)
  - [Installing this fork](#installing-this-fork)
  - [Prerequisites](#prerequisites)
  - [Claude for Desktop Integration](#claude-for-desktop-integration)
  - [Cursor Integration](#cursor-integration)
  - [Installing the Ableton Remote Script](#installing-the-ableton-remote-script)
- [Usage](#usage)
  - [Starting the Connection](#starting-the-connection)
  - [Using with Claude](#using-with-claude)
  - [Capabilities](#capabilities)
  - [Example Commands](#example-commands)
  - [Reading MIDI notes](#reading-midi-notes)
- [Troubleshooting](#troubleshooting)
- [Technical Details](#technical-details)
- [Limitations & Security Considerations](#limitations--security-considerations)
- [Telemetry](#telemetry)
- [Join the Community](#join-the-community)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

---

## Features

| | |
|---|---|
| **Two-way communication** | Connect Claude AI to Ableton Live through a socket-based server |
| **Track manipulation** | Create, modify, and manipulate MIDI and audio tracks |
| **Instrument and effect selection** | Claude can access and load the right instruments, effects and sounds from Ableton's library |
| **Clip creation** | Create and edit MIDI clips with notes |
| **Arrangement view composition** | Build full songs autonomously in Arrangement View, including sections like intro, buildup, drop, breakdown, and outro |
| **Session control** | Start and stop playback, fire clips, and control transport across Session View and Arrangement View |
| **Anonymous telemetry** | Usage tracking to help improve the tool (can be disabled) |

## Components

The system consists of two main components:

1. **Ableton Remote Script** (`AbletonMCP_Remote_Script/__init__.py`) — a MIDI Remote Script for Ableton Live that creates a socket server to receive and execute commands
2. **MCP Server** (`MCP_Server/server.py`) — a Python server that implements the Model Context Protocol and connects to the Ableton Remote Script

---

## Installation

### Prerequisites

- **Ableton Live** — current fork verification uses Live 12.4.16; newer API features are not available in all older Live versions
- **Python** 3.10 or newer for the MCP server (Live runs the Remote Script in its own Python runtime)
- **uv** package manager

If you're on Mac, please install uv as:

```
brew install uv
```

Otherwise, install from [uv's official website](https://docs.astral.sh/uv/getting-started/installation/)

> **Warning:** Do not proceed before installing uv.

### Installing this fork

Use a stable checkout location. For a new checkout:

```sh
git clone https://github.com/jharlas/ableton-mcp.git
cd ableton-mcp
uv sync --frozen
uv run --frozen ableton-mcp-install-script
```

If the checkout already exists, use it rather than creating a second copy.
After reviewing and applying an update, run the same sync and installer
commands from that checkout. The installer backs up the previous Live-side
script as `__init__.py.bak`.

Point the client's MCP server at the same checkout. Example Claude Desktop
server entry (replace both absolute paths for your machine):

```json
{
  "mcpServers": {
    "ableton": {
      "command": "/absolute/path/to/uv",
      "args": [
        "--directory", "/absolute/path/to/ableton-mcp",
        "run", "--frozen", "ableton-mcp"
      ]
    }
  }
}
```

An existing client entry pointing directly to this checkout's
`.venv/bin/ableton-mcp` also uses the fork; no configuration change is needed.

After a Remote Script update, save the Set, fully quit Live, then reopen it.
After server/tool changes, fully quit and reopen Claude Desktop. For a
tunnel-managed server, restart that server process too; reconnect or refresh
the client's tool list if a newly added tool is missing. Restarting the
tunnel alone does not reload Live's Remote Script.

Call `get_remote_script_info` and check `script_version`, `expected_version`,
and `up_to_date`. For the current checkout, both versions should be `1.18.3`
and `up_to_date` should be `true`. The Python package metadata version
(`1.4.0`) is separate from the Remote Script version.

### Claude for Desktop Integration

[Follow along with the setup instructions video](https://youtu.be/iJWJqyVuPS8)

Go to **Claude → Settings → Developer → Edit Config → `claude_desktop_config.json`** to include the following:

```json
{
    "mcpServers": {
        "AbletonMCP": {
            "command": "uvx",
            "args": [
                "ableton-mcp"
            ]
        }
    }
}
```

### Cursor Integration

Run ableton-mcp without installing it permanently through uvx. Go to **Cursor Settings → MCP** and paste this as a command:

```
uvx ableton-mcp
```

> **Warning:** Only run one instance of the MCP server (either on Cursor or Claude Desktop), not both.

### Claude Code Integration

In the terminal, run:

```
claude mcp add AbletonMCP uvx ableton-mcp
```

### Installing the Ableton Remote Script

These `uvx` examples install the published package's script. For this fork,
use the checkout-based commands in [Installing this fork](#installing-this-fork).

[Follow along with the setup instructions video](https://youtu.be/iJWJqyVuPS8)

Install the Remote Script with:

```bash
uvx --from ableton-mcp ableton-mcp-install-script
uvx --from ableton-mcp ableton-mcp-install-script --list-targets   # preview target folders first
```

> If you installed the package with `pip` or `pipx`, the command is on your PATH directly — just run `ableton-mcp-install-script`.

This copies the matching Remote Script into your Ableton **User Library**'s `Remote Scripts` folder — the location Live (10.1.13+) scans for third-party control surface scripts. The installer reads the User Library location from Live's `Library.cfg`, falling back to the default (`~/Music/Ableton/User Library` on macOS, `Documents\Ableton\User Library` on Windows). If a different version of the script is already there, the existing file is backed up to `__init__.py.bak` before being replaced.

If your User Library lives somewhere non-standard and isn't detected, point the installer at it directly:

```bash
uvx --from ableton-mcp ableton-mcp-install-script --target "/path/to/User Library/Remote Scripts"
```

> The legacy `Preferences/User Remote Scripts` folder (used for instant-mapping configs, not Python control surfaces) is no longer targeted by default; pass `--legacy` if you need it for an old Live version.

Then **save your work, fully quit Live, and reopen it** so Live loads the
changed script. Reselecting the control surface can retain cached Python
code. Re-run the installer after upgrading the package, and restart your
MCP client when server code or the tool list changes. Confirm the loaded
and expected versions with `get_remote_script_info`.

> **Note:** The server does **not** install the script on startup. Writing into Ableton's preferences directory is an explicit action, not a side effect of launching a server.

**First-time Ableton setup:**

1. Run `uvx --from ableton-mcp ableton-mcp-install-script`
2. Launch Ableton Live
3. Go to **Settings/Preferences → Link, Tempo & MIDI**
4. In the **Control Surface** dropdown, select **AbletonMCP**
5. Set **Input** and **Output** to **None**

<details>
<summary><b>Manual fallback locations (User Library → Remote Scripts)</b></summary>

- **macOS:** `~/Music/Ableton/User Library/Remote Scripts/AbletonMCP/`
- **Windows:** `C:\Users\[Username]\Documents\Ableton\User Library\Remote Scripts\AbletonMCP\`

If you've moved your User Library, use its actual location (shown in Live under **Preferences → Library → Location of User Library**), and create the `Remote Scripts` folder inside it if it doesn't exist yet.
</details>

The MCP server and Remote Script share a version handshake (`get_remote_script_info`). If they diverge, newer tools degrade gracefully until Live is restarted.

---

## Usage

### Starting the Connection

1. Ensure the Ableton Remote Script is loaded in Ableton Live
2. Make sure the MCP server is configured in Claude Desktop or Cursor
3. The connection should be established automatically when you interact with Claude

### Using with Claude

Once the config file has been set on Claude, and the remote script is running in Ableton, you will see a hammer icon with tools for the Ableton MCP.

### Capabilities

- Get session and track information
- Create and modify MIDI and audio tracks
- Create full song arrangements from start to finish in Arrangement View
- Create, edit, and trigger clips
- Control playback
- Load instruments and effects from Ableton's browser
- Add notes to MIDI clips
- Change tempo and other session parameters

### Example Commands

Here are some examples of what you can ask Claude to do:

| Prompt | Demo |
|---|---|
| *"Create an 80s synthwave track"* | [Watch](https://youtu.be/VH9g66e42XA) |
| *"Create a Metro Boomin style hip-hop beat"* | |
| *"Create a full arrangement with an intro, buildup, drop, breakdown, and outro"* | |
| *"Create a new MIDI track with a synth bass instrument"* | |
| *"Add reverb to my drums"* | |
| *"Create a 4-bar MIDI clip with a simple melody"* | |
| *"Get information about the current Ableton session"* | |
| *"Load a 808 drum rack into the selected track"* | |
| *"Add a jazz chord progression to the clip in track 1"* | |
| *"Set the tempo to 120 BPM"* | |
| *"Play the clip in track 2"* | |

---

### Reading MIDI notes

Choose the smallest read that answers the question:

| Need | Tool |
|---|---|
| Session overview and track names | `get_session_info` |
| Arrangement clips on one track | `get_arrangement_clips(track_index)` |
| MIDI notes in one Arrangement clip | `get_arrangement_clip_notes(track_index, clip_index, offset=0, limit=64)` |
| MIDI notes in a Session clip slot | `get_clip_notes(track_index, clip_index)` |
| Whole-Set metadata without notes or device values | `get_session_snapshot(include_notes=false, include_params=false)` |

`get_clip_notes` addresses **Session slots**. The new Arrangement reader
addresses **Arrangement clips** and never requires a Session copy. Track
and clip indices are zero-based. Find the track with `get_session_info`,
then use the `clip_index` returned by `get_arrangement_clips` for that track.
Indices can change when tracks or clips are added, removed, or reordered.

Example tool arguments, with illustrative indices:

```json
{"track_index": 3, "clip_index": 2, "offset": 0, "limit": 64}
```

The Arrangement reader returns `total_note_count`, `returned_note_count`,
`has_more`, `next_offset`, and `notes`, along with clip and track metadata.
If `has_more` is `true`, call the same tool for the same clip using the
returned `next_offset`. Continue until `has_more` is `false`. Do not advance
by the requested limit: the 24,000-byte compact JSON budget can shorten a
page. The default limit is 64 notes and the allowed range is 1–128.
Avoid editing the clip during pagination; restart at offset zero after edits.

Each note contains `note_id`, `pitch`, `start_time`, `duration`, `velocity`,
and `mute`, plus probability and velocity-expression fields when available.
Times are beats in **absolute clip time**, not positions on the Arrangement
timeline. The response includes `arrangement_start`, `arrangement_end`,
`start_marker`, `end_marker`, `loop_start`, `loop_end`, and `looping` so the
caller can interpret placement. All source notes are included, even outside
the visible markers; loop repetitions are not expanded into repeated notes.
Audio clips are rejected, and API errors are not reported as empty MIDI clips.

Suggested prompt:

> Find the Lead clip on the guitar track with get_arrangement_clips. Read it
> with get_arrangement_clip_notes, following next_offset until has_more is
> false. Distinguish source notes from the audible looped or cropped region.
> Do not modify the Set.

A full snapshot is still available for whole-Set capture. Disabling
`include_params` reduces its size but does not guarantee it fits a client's
response limit. If a response is truncated, use focused reads; retrying the
same full snapshot does not make the payload smaller.

## Troubleshooting

| Problem | Fix |
|---|---|
| **Connection issues / session terminated** | Check the MCP server or tunnel process and the Live-side bridge separately. A healthy tunnel does not prove Live is reachable. Use `get_remote_script_info` for an end-to-end check. |
| **`Timed out waiting for Live main-thread Song read`** | Verify the loaded script is at least 1.18.2. Its request queue fixes a lost-task race in the previous scheduler handoff. In newer errors, `phase=queue` means the read did not start before its deadline; `phase=execution` means the reader started but did not finish before the deadline. Inspect Live's log before attributing the delay to Set size. |
| **Snapshot cut off / response too large** | This is different from a Live timeout. Use `get_arrangement_clip_notes` for Arrangement MIDI notes, and follow every page. Disable snapshot notes and parameters for an overview. The client-specific limit is not measured by the server. |
| **New tool missing from Claude** | Confirm Claude launches this fork, then fully quit and reopen Claude so the MCP process and tool list reload. A `uvx ableton-mcp` entry may launch the published package instead. |
| **New tool visible, but capability missing** | Install the matching Remote Script, save and fully restart Live, then check the version handshake. Version 1.18.3 adds `get_arrangement_clip_notes`. |
| **Loaded and expected versions differ** | Update the script from the same checkout the MCP server uses. Restart Live for script changes and the MCP server for server changes. Reselecting the control surface may retain cached code. |

The queued reads retain an eight-second deadline. Logs include request IDs,
`queue_wait`, `execution`, and completion state. A successful server response
can still be too large for the client to show in full. See the
[capability map](AbletonMCP_Remote_Script/CAPABILITIES.md) for dated test evidence
and [CHANGELOG.md](CHANGELOG.md) for implementation details.

## Technical Details

### Communication Protocol

The system uses a simple JSON-based protocol over TCP sockets:

- **Commands** are sent as JSON objects with a `type` and optional `params`
- **Responses** are JSON objects with a `status` and `result` or `message`

## Limitations & Security Considerations

- Creating complex musical arrangements might need to be broken down into smaller steps
- The tool is designed to work with Ableton's default devices and browser items
- Always save your work before extensive experimentation

---

## Telemetry

AbletonMCP collects usage data to help improve the tool. This includes:

- Anonymous tool usage statistics (which features are used)
- Anonymous session start information (for daily/monthly active user counts)
- Anonymous rates and performance metrics
- Prompts, MIDI notes, track and clip names, and device settings

Telemetry is **on** by default. To see exactly what data is collected, see the [Terms & Data Use](TERMS.md).

### Opting Out

To disable telemetry, set one of these environment variables before starting the MCP server:

```bash
export ABLETON_MCP_DISABLE_TELEMETRY=true
```

Or use any of these alternatives:

- `DISABLE_TELEMETRY=true`
- `MCP_DISABLE_TELEMETRY=true`

For Claude Desktop, add the environment variable to your config:

```json
{
    "mcpServers": {
        "AbletonMCP": {
            "command": "uvx",
            "args": ["ableton-mcp"],
            "env": {
                "ABLETON_MCP_DISABLE_TELEMETRY": "true"
            }
        }
    }
}
```

---

## Join the Community

Give feedback, get inspired, and build on top of the MCP: [**Discord**](https://discord.gg/JK4hNKGprW)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a third-party integration and not made by Ableton. Made by [Siddharth](https://x.com/sidahuj).

---

<div align="center">

**If Ableton MCP is useful to you, consider starring the repo**

</div>
