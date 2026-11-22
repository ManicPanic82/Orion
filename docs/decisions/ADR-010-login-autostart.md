# ADR-010: Login Autostart

- **Status:** Accepted
- **Date:** 2026-11-22
- **Related:** ADR-009 (tray residency), ADR-008 (Windows-first)

## Context

If Orion is resident, it is only useful if it is already running when the user needs
it. Starting it at Windows sign-in is therefore part of the residency requirement,
not an unrelated convenience.

Registering a startup entry modifies system state and is visible to the user outside
Orion. `SECURITY.md` places system-modifying actions behind explicit approval, and
`VISION.md` states that persistent operation must never mean invisible operation.

## Decision

1. **Mechanism:** a single value, `OrionWorkstation`, under
   `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. Per-user, no elevation, no
   dependency beyond the standard library, inspectable in Task Manager, trivially
   reversible.
2. **Command:** `"<...>\pythonw.exe" -m orion --minimised`. `pythonw.exe` is used
   because the console launcher flashes a terminal window at sign-in, which reads as
   a fault. A packaged build uses its own executable instead.
3. **No working directory exists in a Run entry.** Nothing in the startup path may
   depend on the current directory.
4. **Consent is explicit.** On first run the user is asked once, with *Yes*
   pre-selected, and the answer is persisted (`startup.prompted`). The Settings page
   carries the same control. Orion never registers itself silently.
5. **The preference never claims success it did not achieve.** After every change the
   controller reads the registry back and reports the real state, including drift
   between the saved preference and the registry.
6. **Deletion is exact-match only.** If the value does not equal the command Orion
   would write, it is reported and left untouched.
7. **`--minimised`** starts with no visible window. If no tray is available the window
   is shown instead, because a hidden application with no tray icon cannot be reached.

## Alternatives considered

- **Startup folder shortcut.** Rejected: requires `IShellLink`/COM or a binary `.lnk`
  in the diff, and is harder to verify programmatically.
- **Task Scheduler entry.** Rejected for this phase: implies elevation and delay
  semantics that are not needed, and is harder to inspect and remove.
- **Registering silently on first launch.** Rejected: violates the no-invisible-action
  principle and would surprise the user.
- **Defaulting the prompt to No.** Rejected by product direction: the owner wants Orion
  available at sign-in, while still asking once.

## Consequences

- One additional startup entry appears in Task Manager → Startup. Some security
  suites flag Run-key additions on first write; the exact command is displayed in
  Settings so a false positive is easy to explain.
- If the user or another tool rewrites the value, Orion reports a foreign entry and
  refuses to delete it.
- Phase 2 must retarget the entry so that login starts Orion Core rather than a
  UI-owned process. Otherwise the resident unit remains the wrong process.
- The tray icon may not be ready in the first moments after sign-in. Availability is
  re-checked with a bounded retry before the no-tray fallback is applied, so an early
  login cannot silently terminate the autostarted instance.

## Security and privacy impact

- HKCU only; no elevation, no machine-wide change, no network exposure.
- The command contains a local path and no secrets.
- Disabling removes the value; no residue is left behind.

## Migration implications

- The Run value is version-independent; changing the interpreter path requires
  re-registration, which the Settings toggle performs.
- If the environment is moved, Orion detects the mismatch as drift rather than
  assuming the old entry still works.

## References

- `src/orion/startup.py`, `src/orion/app.py`
- `docs/operations/WINDOWS_DEVELOPMENT.md`
