#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Local bootstrap, no magic:

Terminal 1:
  make api

Terminal 2:
  make ui

Terminal 3:
  make worker

Hermes connector env:
  export HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000
  export HERMES_RUNTIME_API_KEY=dev-runtime-key

Smoke check:
  make smoke
EOF
