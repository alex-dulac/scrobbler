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
  seconds while scrobbling is enabled, and retain their original listening time. The retry loop drains one item at a
  time, one second apart after success, with a 30-second delay after failure.
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

## Listening library and album scrobbling

The dashboard now includes:

- **Listening:** album artwork, source and playback controls, scrobble progress,
  and inline track, album, and artist statistics. Counts, first/latest listens,
  recent timestamps, album track rankings, and artist yearly listening are visible
  without opening detail pages. History refreshes when the recording changes or
  the session gains a scrobble, with a manual refresh for external library syncs.
- **History:** paginated search across tracks, artists, and albums in PostgreSQL.
- **Artist detail:** yearly listening counts and favorite albums/tracks.
- **Wrapped:** selectable years, monthly charts, and top artists/albums/tracks.
  Track counts use artist + title identity; album counts use artist + album.
- **Add a listen:** search an album and specify when you finished it, review the
  track timeline, then explicitly queue the reviewed album. No submission happens
  during preview. Tracks of 30 seconds or less are shown but excluded; missing
  durations produce an error instead of guessed timestamps.
- **Session, Profile, Settings:** pending/submitted listens, lifetime Last.fm
  counts, connection state, and source selection.

History, artist detail, and Wrapped use the existing synced database, not the
entire Last.fm account automatically. If it is unavailable, these pages show an
error and retry action. Configure PostgreSQL and restart the backend to reconnect.
Use the existing `scripts.sync_scrobbles` workflow to import older listening data.

Visited tabs retain their search, selected page/year, and scroll position until
the app closes. Library responses share a bounded in-memory cache (80 entries,
one-minute freshness) scoped to the backend connection. Returning to a tab reuses
fresh results; stale results remain visible while refreshing. New session
scrobbles, database availability changes, and reconnections invalidate cached
results. Refresh buttons bypass freshness, including after an external library
sync. Failed refreshes retain any available results and offer a retry. The cache
is not persisted across app restarts.
Dates in the library retain the database's existing local, timezone-naive convention.

Manual previews expire after 30 minutes. A persisted receipt makes submitting the
same preview safe to retry, including after a backend restart. Unsubmitted previews
must be recreated after restart. Submissions remain queued while scrobbling is
paused. Last.fm acceptance is checked explicitly; ignored or rejected tracks stay
pending. There is not yet a UI for editing/removing a rejected queued listen.

The interface uses restrained lilac accents, compact album artwork, inline data
panels, direct labels, and a persistent player. Duration, release year, genre,
and track number appear when supplied by the current player. Artwork failure falls back to an illustrated record sleeve. To render
screenshots with synthetic data and local macOS fonts, run
`flutter test tool/render_preview.dart` from this directory; outputs are in
`build/previews/`. These fixtures are not part of the live app.

Remaining work includes sync controls in the desktop UI, queue editing/removal,
and repeat/transient-playback detection.
Python packaging, launch-at-login, and distribution remain separate work.

The Listening view includes aligned annual track, album, and artist charts.
Each row is scaled independently, shows exact counts and peak years, fills gaps
with zero counts, and labels the current year as year to date. Long timelines
scroll horizontally. Command confirmations clear after four seconds; command
failures stay visible for eight seconds. Connection errors remain until recovery.
