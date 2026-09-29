# Scrobbler desktop

Flutter macOS dashboard with an app-owned Python/FastAPI backend. Closing the
window keeps Flutter and the scrobbler running; use the menu bar or Dock to reopen
it. **Quit Scrobbler** (or Cmd+Q) stops the owned backend. The app must remain
running to collect listens; this is not a login daemon.

## Run from this repository

Requirements: macOS 12+, Flutter with macOS tooling, Xcode, Python 3.13+, and `uv`.

1. Run `uv sync` at the repository root.
2. Configure Last.fm credentials in the root `.env` using `.env.example`.
   PostgreSQL is optional for live scrobbling; it is needed for database analytics.
3. Run `./scripts/run_desktop.sh` from the repository root.
4. Allow macOS Automation access to Music/Spotify when prompted.

The launcher supplies the absolute project directory. The desktop app starts
`.venv/bin/python -u -m desktop_backend` from that directory. No separate server
command is needed. The virtual environment and repository must stay in place.
This is a development application; Python is not yet bundled into the `.app`.

## Behavior

- Now playing, source selection, playback controls, and scrobbling toggle use the
  real backend APIs. Session history, pending listens, profile, and connection
  state use backend snapshots. Refreshes do not overlap.
- The menu bar shows the current track and supports opening the dashboard,
  enabling/pausing scrobbling, and quitting.
- The managed server binds an ephemeral `127.0.0.1` port. Flutter generates a
  fresh bearer token each launch and passes it through the child environment.
- A readiness message is emitted only after server startup. Failures appear in
  the app with a retry action. Backend crashes can be recovered via that action.
- An advisory lock rejects another managed backend. Do not separately run the
  TUI, CLI loop, or an unmanaged server while managed scrobbling is active; those
  entry points do not share the managed-process lock.
- Explicit quit sends SIGTERM and waits up to 15 seconds before terminating an
  unresponsive child. The backend also exits when its parent input pipe closes.
- Pending listens are atomically saved before submission, retried every 30
  seconds while scrobbling is enabled, and retain their original listening time.
  Managed quit leaves pending items for the next launch instead of waiting for
  network retries.

Local state is in `~/Library/Application Support/PyScrobbler/` (`pending.json` and
`backend.lock`). `SCROBBLER_STATE_DIR` overrides it for isolated tests. Delivery is
at least once: a crash after Last.fm accepts a listen but before its local removal
may cause a retry. Consecutive repeat detection and recovery from transient
playback gaps still need improvement in the existing engine.

The macOS sandbox is disabled for this development setup because the app launches
an external Python environment and uses Apple Events. It has an Automation usage
description and entitlement. Signing, distribution, bundled Python, and login
startup are not configured.

## External backend mode

Start the existing server separately, then run Flutter with:

```sh
flutter run -d macos \
  --dart-define=SCROBBLER_BACKEND_URL=http://127.0.0.1:8000 \
  --dart-define=SCROBBLER_BACKEND_TOKEN=YOUR_APP_TOKEN
```

Use the server's configured `APP_TOKEN`. These defines are build configuration,
not secure credential storage; use them only for your local development build.
The app never stops an external backend. Otherwise, managed mode is the default.

## Validation

```sh
# Repository root
.venv/bin/python -m unittest discover -s tests -v

# apps/desktop
flutter analyze --no-pub
flutter test --no-pub
flutter build macos --debug --no-pub
```

Tests use fake playback and Last.fm clients; the backend lifecycle test starts a
real loopback subprocess with a fake ASGI application. No live scrobbles are sent.

## Remaining application work

The intended scope includes the full TUI experience: long-term listening history,
artist and album statistics, manual album scrobbling, and yearly Wrapped. This
implementation establishes the background lifecycle and connected dashboard;
those additional screens and their API contracts are still to be implemented.
