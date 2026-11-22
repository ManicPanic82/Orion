# ADR-009: Tray Residency

- **Status:** Accepted
- **Date:** 2026-11-22
- **Supersedes:** nothing
- **Related:** ADR-002 (independent Core), ADR-010 (login autostart)

## Context

Phase 1 was originally specified as a shell that "exits cleanly and does not spawn
an unmanaged background process", with tray lifecycle controls listed under Phase 2.

The product owner requires Orion to be resident: closing the window must minimise it
to the notification area, the process must keep running, and quitting must be an
explicit tray action. That makes the process, not the window, the unit of residency,
which is a lifecycle decision rather than a cosmetic preference.

## Decision

1. The window is a view that can be hidden. Closing it hides it and the process
   continues.
2. The tray menu owns **Quit Orion**. `Ctrl+Q` is the equivalent quit path whenever the
   window has focus. It is not a global hotkey: a hidden window receives no keys, so
   the tray remains authoritative once Orion is resident. The guarantee that a user is
   never trapped is the single-instance activation path — launching Orion again always
   restores the hidden window (verified with two real processes), and the window then
   offers `Ctrl+Q` and the tray menu.
3. The tray is created only when the platform reports one. When it does not, the
   window closes normally and the application exits; residency is never achieved by
   leaving an invisible process behind.
4. A single-instance guard prevents duplicate windows and competing settings writers.
   Exclusivity is enforced by a per-session Win32 named mutex, not by `QLocalServer`:
   Win32 named pipes accept multiple server instances, so a second `listen()`
   succeeds and cannot detect an existing instance. The guard is acquired before the
   window is constructed, so a rejected launch never creates a second tray icon.
5. The named pipe carries only an "activate" message. The secondary instance waits
   for an acknowledgement before exiting, because an immediate disconnect truncates
   the message.
6. `setQuitOnLastWindowClosed(False)` is applied only when a tray icon exists.

## Alternatives considered

- **Exit on window close, as originally specified.** Rejected: contradicts the
  requirement that Orion is always running.
- **`QLocalServer.listen()` failure as the exclusivity test.** Rejected after
  measurement: two servers on the same pipe name both report success on Windows.
- **A lock file with exclusive creation.** Viable but weaker than a kernel mutex:
  stale files survive crashes and require manual recovery.
- **A hidden process with no tray icon.** Rejected: invisible operation violates the
  product principle that persistent operation is never invisible operation.

## Consequences

- Phase 2 inherits a UI process that outlives its window. The tray must become a
  client of Orion Core's lifecycle, and "Quit Orion" must be distinct from "Stop
  Core". This ADR fixes the semantics so that migration is a composition change.
- Settings are written when the window is hidden, not only at exit, because the
  process may run for days and be terminated externally.
- The window object is never destroyed on close, so in-memory console history
  survives hiding.
- `QApplication.closingDown()` is respected so that an OS shutdown is not blocked.

## Security and privacy impact

- No new authority is granted. The tray exposes only restore and quit.
- The mutex and pipe are per-session (`Local\` namespace), so they do not cross user
  sessions and do not listen on the network.

## Migration implications

- Phase 2 must retarget the tray to the Core process and add Start/Stop Core actions.
  Until then the tray controls only the UI process, and the UI must not imply
  otherwise.
- The notification shown on first hide is recorded in settings
  (`ui.tray_notice_shown`) so it is not repeated.

## References

- `src/orion/ui/tray.py`, `src/orion/single_instance.py`, `src/orion/ui/main_window.py`
- `docs/agent-guides/PHASE_01_OPERATIONS_CENTRE.md`
