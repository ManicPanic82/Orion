"""Application bootstrap for Orion Workstation.

Kept deliberately small: parse arguments, resolve settings and startup
registration, construct the Qt application and the main window, enforce a single
instance, and run the event loop. Nothing here performs inference, automation, or
network access in Phase 1.

Ordering matters. The single-instance check runs *before* the window is built, so a
second launch never flashes a duplicate tray icon or writes settings it does not own.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from orion import APP_NAME, ORG_NAME, __version__
from orion.config.paths import DATA_DIR_ENV_VAR, app_data_dir
from orion.config.settings import Settings
from orion.config.store import LoadResult, SettingsStore
from orion.single_instance import SingleInstanceGuard
from orion.startup import (
    StartupController,
    StartupRegistration,
    WinRegBackend,
    resolve_launch_command,
)
from orion.ui.main_window import MainWindow
from orion.ui.theme import build_stylesheet

__all__ = ["create_application", "main", "parse_args"]

log = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="orion-workstation",
        description=(
            "Orion Workstation: local-first Operations Centre with the resident agent "
            "connected through Orion Core."
        ),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Override the application data directory. Intended for testing and "
            "isolated runs; defaults to %APPDATA%\\Orion."
        ),
    )
    parser.add_argument(
        "--minimised",
        action="store_true",
        help=(
            "Start in the notification area without showing the window. Used by the "
            "Windows login autostart entry."
        ),
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (default: WARNING).",
    )
    return parser.parse_args(argv)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def prepare_application(args: argparse.Namespace) -> QApplication:
    """Apply the run-time environment and return a configured ``QApplication``.

    This is the only part of startup that must happen before the single-instance
    check, because the guard's activation channel needs a Qt application object.
    """
    if args.data_dir is not None:
        os.environ[DATA_DIR_ENV_VAR] = str(args.data_dir)

    _configure_logging(args.log_level)

    app = QApplication.instance()
    if app is None:
        app = QApplication([sys.argv[0]])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())

    log.debug("application data directory: %s", app_data_dir())
    return app


def load_settings() -> tuple[SettingsStore, Settings, LoadResult]:
    store = SettingsStore()
    loaded = store.load()
    for problem in loaded.problems:
        log.warning("settings: %s", problem)
    return store, loaded.settings, loaded


def build_startup(store: SettingsStore, settings: Settings) -> StartupController:
    command = resolve_launch_command()
    log.info("login launch command: %s", command)
    return StartupController(
        StartupRegistration(WinRegBackend(), command),
        settings,
        store,
    )


def create_main_window(
    store: SettingsStore,
    settings: Settings,
    startup: StartupController | None = None,
) -> MainWindow:
    window = MainWindow(store=store, settings=settings, startup=startup)
    # Only keep the process alive after the last window closes when there is a
    # tray icon to restore it from. Otherwise closing the window must quit.
    app = QApplication.instance()
    if app is not None:
        app.setQuitOnLastWindowClosed(not window.tray_installed)
    return window


def create_application(
    argv: list[str] | None = None,
) -> tuple[QApplication, MainWindow, SettingsStore, StartupController]:
    """Construct the Qt application and main window without entering the event loop.

    Exposed separately from :func:`main` so smoke tests and Qt tests can drive the
    real window without spawning a second process. It deliberately does *not* enforce
    single-instance exclusivity; that belongs to :func:`main`.
    """
    args = parse_args(argv)
    app = prepare_application(args)
    store, settings, _loaded = load_settings()
    startup = build_startup(store, settings)
    window = create_main_window(store, settings, startup)
    return app, window, store, startup


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    app = prepare_application(args)

    guard = SingleInstanceGuard()
    if not guard.acquire():
        if not guard.notify_existing():
            log.warning("another Orion instance is running but did not respond")
        return 0

    store, settings, _loaded = load_settings()
    startup = build_startup(store, settings)
    window = create_main_window(store, settings, startup)

    def _restore_window() -> None:
        log.info("activation requested by another launch; restoring the window")
        window.restore_from_tray()

    guard.activate_requested.connect(_restore_window)

    if args.minimised and window.tray_installed:
        log.info("starting minimised to the notification area")
    else:
        window.show()
        window.prompt_startup_if_needed()

    try:
        return app.exec()
    finally:
        guard.close()
