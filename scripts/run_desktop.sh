#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir/apps/desktop"
exec flutter run -d macos "--dart-define=SCROBBLER_PROJECT_DIR=$project_dir" "$@"
