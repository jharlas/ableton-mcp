# Personal fork baseline

This is a historical record of the `baseline-2026-11-14` tag, not the
current version. For later changes, see [CHANGELOG.md](CHANGELOG.md); for
current usage and verification status, see [README.md](README.md) and the
[capability map](AbletonMCP_Remote_Script/CAPABILITIES.md).

Recorded on 2026-11-14. This fork starts from
[Tompz/ableton-mcp](https://github.com/Tompz/ableton-mcp) at
`c47a2c340c5e07e0a72bc7eff7db1f542cfd8c1a`, preserving its history and MIT
license. The original project is
[ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp).

The `baseline-2026-11-14` tag records the existing working installation plus
the previously developed snapshot fixes. It is a rollback/reference point,
not a release of the proposed extended feature set.

## Versions and preserved fixes

- Python package metadata: `1.4.0`.
- Remote Script and installer expected version: `1.18.1`.
- Session-info and full-snapshot reads are scheduled on Live's main thread
  and reacquire the current Song binding there.
- Snapshot serialization isolates unsupported properties while retaining
  tracebacks and object paths. Core Song failures remain fatal.
- The installer-bundled Remote Script matches the source script exactly.
- Regression tests cover thread dispatch, fresh Song bindings, snapshot
  options, fault isolation, MCP forwarding, and installer synchronization.

The large bundled-script diff also incorporates the existing Tompz Remote
Script capabilities that had not previously been synchronized into the
installer bundle.

## Validation at capture

- 27 tests passed; `git diff --check` passed.
- Source, installer bundle, and locally installed Remote Script had the
  same SHA-256:
  `98f4e8d0c5075cc2e53b36bfe05c924059b901f14423b1325765b5174a23d854`.
- Capturing this baseline did not reinstall the script, restart Live or
  the tunnel, or exercise editing tools against the active Set.

Run the existing test suite without synchronizing the runtime environment:

```sh
ABLETON_MCP_DISABLE_TELEMETRY=1 \
ABLETON_MCP_DISABLE_DATASET=1 \
ABLETON_MCP_ENABLE_DATASET=0 \
ABLETON_MCP_TELEMETRY_CONSENT=false \
uv run --no-sync --with pytest python -m pytest -q
```

## Baseline limitations

This capture intentionally preserves existing behavior: telemetry code and
its dependency remain, the Live bridge binds to all interfaces, the
long-operation timeout overwrite remains, and several Remote Script
capabilities still lack MCP wrappers. Privacy cleanup, transport fixes,
new wrappers, and selected Extended features are subsequent work.

Machine-specific service configuration, credentials, and Live projects are
not part of this repository. Keep the source script, bundled copy, and
installer expected version synchronized in future changes; deploying a
changed Remote Script requires a separate Live restart and verification.
