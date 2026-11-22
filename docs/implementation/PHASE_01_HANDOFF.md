# Phase 1 Handoff — Operations Centre Shell

Branch: `phase-1-operations-centre` (not pushed, not merged)
Date: 2026-11-22
Phase: 1 (with ADR-009 tray residency and ADR-010 login autostart added by owner direction)

## 1. Scope

- **Assigned roadmap phase:** Phase 1 — Project foundation and Operations Centre.
- **Requested task:** Implement the Phase 1 shell, plus tray residency (window close
  minimises, tray owns quit) and Windows login autostart.
- **Explicit exclusions:** real inference, model host, agent, task engine, permission
  gateway, memory, experience capture, learning, voice, automation, project
  intelligence, delegation, gaming, SQLite/migrations, network access, Windows Service
  registration.

## 2. Implementation

### Behaviour delivered

- Installable `orion-workstation` package (`python -m orion`, console script
  `orion-workstation`).
- Dark Operations Centre window with a nine-destination navigation rail.
- Command Centre: agent/model status cards, active tasks, recent events, objective
  composer with `Ctrl+Enter`.
- Bottom activity console: expand/collapse, minimum-severity filter, bounded buffer,
  credential redaction.
- Eight non-implemented destinations render an honest "planned" panel naming the
  delivering phase, with no interactive controls.
- Settings page: storage paths, lifecycle explanation, login-startup control, version.
- Versioned JSON settings in `%APPDATA%\Orion\settings.json` with validation,
  per-field fallback, atomic writes, corrupt-file quarantine, and refusal to overwrite
  a newer schema.
- Tray residency: close hides; tray menu restores or quits; `Ctrl+Q` always quits;
  one-time notification on first hide.
- Single instance: Win32 named mutex for exclusivity, named-pipe activation with an
  acknowledgement, so a second launch raises the existing window.
- Login autostart: `HKCU\...\Run\OrionWorkstation`, `pythonw -m orion --minimised`,
  explicit one-time consent, registry read-back, drift reporting, exact-match deletion.
- `--minimised` starts with no visible window when a tray exists; falls back to a
  visible window when it does not.

### Important design decisions

1. **`StateProvider` protocol** is the Phase 2 seam. The window never imports the mock;
   it receives a provider. Replacing the mock with a Core client is a composition
   change, not a UI rewrite.
2. **`StatusKind.MOCK` is a first-class state**, so no mock can render as connected.
3. **Only `TaskState.SIMULATED` exists.** Real lifecycle states are deferred to Phase 4
   rather than invented now, so the shell cannot display an outcome nothing produces.
4. **View models import no Qt.** Verified by a subprocess test that asserts no
   `PySide6` module is loaded.
5. **Design tokens are defined once** in `ui/theme.py`; widgets consume tokens or
   stylesheet selectors, never raw hex values.
6. **Exclusivity uses a kernel mutex, not `QLocalServer.listen()`.** Measured: two
   servers on the same pipe name both report success on Windows, so listen failure
   cannot detect an existing instance.
7. **Activation is acknowledged.** An immediate disconnect truncates the message; the
   secondary waits for an `ack` inside a nested event loop before exiting.
8. **Tray availability is injected**, because the offscreen platform has no tray. The
   policy is therefore tested; Qt's tray rendering is verified manually.
9. **Settings are written when the window hides**, not only at exit, because the
   process may run for days.
10. **The single-instance check runs before the window is built.** A second launch
    therefore never flashes a duplicate tray icon or writes settings it does not own;
    it only signals the primary and exits (measured: 330 ms).

### Interfaces and contracts

- `orion.state.provider.StateProvider` — `is_mock`, `snapshot()`, `submit_command()`.
- `orion.state.models` — `AppSnapshot`, `ComponentStatus`, `TaskSummary`, `EventRecord`,
  `CommandResult`, `StatusKind`, `TaskState`, `MAX_COMMAND_LENGTH`.
- `orion.config.store.SettingsStore` — `load() -> LoadResult`, `save(Settings)`.
- `orion.startup.StartupController` — `status()`, `set_enabled()`, `mark_prompted()`.

### Configuration changes

- New file `%APPDATA%\Orion\settings.json`, schema version 1, sections: `window`,
  `navigation`, `console`, `appearance`, `startup`, `ui`.
- New optional per-run override `ORION_DATA_DIR` / `--data-dir` (non-security value).

## 3. Files

### Created

| File | Reason |
|---|---|
| `pyproject.toml` | Package metadata, Python 3.12 policy, dev dependencies, pytest/ruff config |
| `.gitignore` | Exclude venv, caches, runtime settings, logs, evidence artifacts |
| `src/orion/__init__.py` | Product identity and version |
| `src/orion/__main__.py` | `python -m orion` entry point |
| `src/orion/navigation.py` | Qt-free destination metadata shared by settings and UI |
| `src/orion/app.py` | Bootstrap: args, settings, startup, single instance, event loop |
| `src/orion/single_instance.py` | Named-mutex exclusivity plus acknowledged activation pipe |
| `src/orion/startup.py` | Registry backend, registration, drift reporting, controller |
| `src/orion/config/paths.py` | `%APPDATA%` resolution with override, no hard-coded paths |
| `src/orion/config/settings.py` | Typed, validated, versioned settings document |
| `src/orion/config/store.py` | Atomic persistence, quarantine, newer-schema refusal |
| `src/orion/state/models.py` | Immutable presentation state models |
| `src/orion/state/provider.py` | State-provider protocol (Phase 2 seam) |
| `src/orion/mock/state_provider.py` | Deterministic, explicitly simulated provider |
| `src/orion/ui/theme.py` | Design tokens and generated stylesheet |
| `src/orion/ui/main_window.py` | Shell, navigation, console, tray lifecycle, persistence |
| `src/orion/ui/console_panel.py` | Expandable, filterable console renderer |
| `src/orion/ui/tray.py` | Tray icon, menu, hide/restore policy, programmatic icon |
| `src/orion/ui/widgets/*.py` | Card, StatusPill, MockBadge, NavItem, repolish helper |
| `src/orion/ui/pages/*.py` | Command Centre, planned pages, Settings |
| `src/orion/ui/viewmodels/*.py` | Qt-free console and command-centre view models |
| `tests/conftest.py`, `tests/helpers.py` | Offscreen setup, isolated data dir, fake registry |
| `tests/unit/*.py` | Settings schema/store, mock provider, view models, startup, single instance |
| `tests/qt/*.py` | Shell navigation, console, tray lifecycle, settings startup control |
| `scripts/smoke_launch.py` | Launch the real window, capture a screenshot, exit |
| `docs/decisions/ADR-009-tray-residency.md` | Tray lifecycle decision |
| `docs/decisions/ADR-010-login-autostart.md` | Login autostart decision |
| `docs/implementation/PHASE_01_HANDOFF.md` | This report |

### Modified

| File | Reason |
|---|---|
| `README.md` | Status updated; verified setup/run/test commands added |
| `docs/decisions/README.md` | Register ADR-009 and ADR-010 |
| `docs/agent-guides/PHASE_01_OPERATIONS_CENTRE.md` | In-scope, instructions 9–10, acceptance, implementation status |
| `docs/operations/WINDOWS_DEVELOPMENT.md` | Confirmed Python/Qt/test tool versions |

## 4. Validation

All commands run from the repository root (shown as `<OrionRepository>`).

| Check | Command | Result |
|---|---|---|
| Unit + Qt tests | `.\.venv\Scripts\python.exe -m pytest` | **118 passed**, 0 failed, 0 skipped |
| Lint | `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| Type checks | not configured | Not run; mypy is deliberately not part of Phase 1 |
| Launch (real platform) | `.\.venv\Scripts\python.exe scripts\smoke_launch.py` | platform `windows`, 1440×900, exits cleanly, screenshot saved |
| Launch, Settings page | `.\.venv\Scripts\python.exe scripts\smoke_launch.py --page settings` | platform `windows`, exits cleanly, screenshot saved |

### Defects found and fixed during verification

These were real failures observed on the running application, not style preferences.

1. **Activation message was truncated.** The second instance wrote `activate` and
   disconnected immediately; the primary read zero bytes. Fixed with an `ack`
   handshake: the secondary waits inside a nested event loop before exiting.
2. **Access violation on socket teardown.** Per-connection closures let the Python
   wrapper die while the C++ socket was live. Fixed by retaining connections in a
   list and dispatching through `sender()`.
3. **The startup prompt blocked application shutdown.** `QApplication.quit()` closes
   windows, which reached the modal consent dialog with no one to answer it. The smoke
   launch hung and `faulthandler` located it. Consent now happens once at first
   interactive launch (`prompt_startup_if_needed()`), never in `closeEvent`, and tests
   assert that closing and quitting never open the dialog.
4. **An unchecked checkbox rendered as a filled accent square** in the Settings page,
   because Fusion's default indicator inherited the highlight palette. Explicit
   `QCheckBox::indicator` states were added to the theme.

### Manual verification performed

1. **Real tray availability** — `QSystemTrayIcon.isSystemTrayAvailable() == True`;
   `window.tray_installed == True`; `quitOnLastWindowClosed == False`.
2. **Two-process single instance and restore** — primary started with a temporary data
   directory and `--minimised`. Before the second launch: two Orion processes (venv
   launcher plus the application) and **no** visible window titled `Orion Workstation`.
   The second launch exited with code 0 in 330 ms and left no extra process. After it,
   the same two processes remained and the primary owned a visible `Orion Workstation`
   window. The activation signal was also confirmed in the primary's log
   (`activation request received from a second instance`).
3. **`--minimised`** — the running instance had no visible top-level window (checked
   with `EnumWindows`), and logged `starting minimised to the notification area`.
4. **Real registry round-trip** — under a throwaway key
   `HKCU\Software\Orion\Phase1RegistryProbe`: register → read matches → unregister →
   absent. The throwaway key was then deleted. The real `Run` key was never written
   during validation.
5. **Screenshots** — `artifacts/phase1-command-centre.png`,
   `artifacts/phase1-settings.png`, and `artifacts/phase1-settings-checked.png`
   (a prepared state showing the drift message: "The saved preference and the
   registry disagree").

### Not verified

- Actual sign-out/sign-in with the startup entry enabled (would require a session
  restart; the registry mechanism itself was verified).
- Tray icon appearance in the Windows 11 overflow flyout, and recovery after an
  `explorer.exe` restart.
- Windows shutdown/logoff interaction with the hide-on-close policy.

### Environment note discovered during verification

`.venv\Scripts\python.exe` is CPython's venv **launcher**, not a copy of the
interpreter: it re-executes the base `python.exe` as a child process. Consequences:

- Process-watching tools must look at the child, not the pid returned by
  `Start-Process`; an early probe of mine watched the launcher and wrongly concluded
  that activation did not restore the window.
- The login `Run` entry therefore produces a launcher process plus the real
  application process. They exit together when Orion quits, so this is benign, but the
  handoff should not claim a single process.
- `resolve_launch_command()` still correctly points at `pythonw.exe`, because the
  launcher is what suppresses the console window.

## 5. Safety and regressions

- **Permission checks:** none required in this phase; no side-effecting capability
  exists. The only system write is the opt-in startup value.
- **Logging:** no credentials, prompts, or private payloads are logged. Console output
  is redacted for bearer tokens, `sk-` keys, and `password`/`token`/`api_key` values.
- **Failure behaviour:** settings read failure → defaults and no write; newer schema →
  refuse writes; registry write failure → preference not claimed as enabled; no tray →
  window closes and the process exits.
- **Idempotency:** `request_quit()` is idempotent; unregister is a no-op when absent;
  repeated `set_enabled` calls converge.
- **Known regressions:** none; this is the first implementation.

## 6. Remaining work

- Phase 2 replaces `MockStateProvider` with a Core client and retargets the tray and
  the login entry to Orion Core (ADR-009, ADR-010).
- Settings page has no theme/scale controls; `ui_scale` is persisted but unused.
- `console.height` is persisted but the splitter ratio is recomputed on expand rather
  than restored exactly.
- The tray-readiness retry described in ADR-010 is implemented and tested
  (`TrayController` retries with a bounded timer and emits `installed`), but the
  sign-in race itself has not been reproduced on a slow-booting session.
- No rotating log file; logging goes to stderr only.
- Tray icon is drawn programmatically; a designed icon can replace it later.

## 7. Repository hygiene

- Branch `phase-1-operations-centre`, created from `main`; it contains the Phase 1
  changes only.
- Committed as a single Phase 1 commit and tagged `phase-1-verified` (see section 9).
  Not pushed and not merged into `main`.
- Diff reviewed file by file; no generated weights, datasets, logs, caches, or
  credentials are tracked. `.venv/`, `artifacts/`, `settings.json` are ignored.
- No unrelated project or repository was modified.

## 8. How to run

```powershell
Set-Location <OrionRepository>
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Launch
.\.venv\Scripts\python.exe -m orion

# Checks
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .

# Evidence screenshots (any page id; exits on its own)
.\.venv\Scripts\python.exe scripts\smoke_launch.py
.\.venv\Scripts\python.exe scripts\smoke_launch.py --page settings --output artifacts\phase1-settings.png

# Isolated run that cannot touch real settings
.\.venv\Scripts\python.exe -m orion --data-dir "$env:TEMP\orion-test"
```

Quit with the tray menu, or press `Ctrl+Q` while the window is open. Closing the window
hides it. Launching Orion again restores the hidden window.

## 9. Verified baseline

- **Status:** approved by the product owner on 2026-11-22 as the Phase 1 baseline.
- **Branch:** `phase-1-operations-centre`.
- **Tag:** `phase-1-verified` (annotated).
- **Not pushed, not merged.** `main` is unchanged.

Phase 1 is deliberately closed at this point. The following are the agreed inputs to
the next validation pass, in priority order, and are not Phase 1 defects:

| Priority | Item |
|---|---|
| High | Windows sign-out/sign-in with autostart enabled (needs a real session restart). |
| Medium | Tray recovery after restarting Windows Explorer. |
| Medium | Rotating application log file with bounded retention. |

Deferred on purpose: `ui_scale` and `console.height` stay persisted but unused until
the UI features that consume them exist. Persisting a preference before its consumer is
implemented is acceptable; inventing the consumer now is not.
