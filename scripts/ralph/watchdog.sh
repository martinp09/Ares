#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRD="${PRD_PATH:-$SCRIPT_DIR/prd.json}"
PROMPT_TEMPLATE="${PROMPT_TEMPLATE:-$SCRIPT_DIR/session-prompt.md}"
PROGRESS="${PROGRESS_PATH:-$SCRIPT_DIR/progress.txt}"
LAST_MESSAGE="${LAST_MESSAGE_PATH:-$SCRIPT_DIR/last-message.txt}"
CODEX_BIN="${CODEX_BIN:-codex}"
MODEL="${RALPH_MODEL:-gpt-5.3-codex}"
MAX_RUNS="${RALPH_MAX_RUNS:-100}"
SLEEP_SECONDS="${RALPH_SLEEP_SECONDS:-15}"
CODEX_EXECUTION_MODE="${RALPH_CODEX_EXECUTION_MODE:-bypass}"
SANDBOX_MODE="${RALPH_SANDBOX_MODE:-workspace-write}"
DRY_RUN="${RALPH_DRY_RUN:-0}"

require_file() {
  local path="$1"
  [[ -f "$path" ]] || {
    echo "Missing required file: $path" >&2
    exit 1
  }
}

remaining_count() {
  jq '[.userStories[] | select((.deferred // false) | not) | select(.passes == false)] | length' "$PRD"
}

blocked_story_id() {
  jq -r '
    .userStories[]
    | select((.deferred // false) | not)
    | select(.passes == false and ((.status // "todo") == "blocked"))
    | .id
  ' "$PRD" | head -n 1
}

next_story_id() {
  jq -r '
    .userStories[]
    | select((.deferred // false) | not)
    | select(.passes == false and ((.status // "todo") != "blocked"))
    | .id
  ' "$PRD" | head -n 1
}

render_board_summary() {
  jq -r '
    .userStories[]
    | "- [" + (if .passes then "x" else " " end) + "] " + .id + " — " + .title + " (status=" + (.status // "todo") + ")"
  ' "$PRD"
}

render_story_block() {
  local story_id="$1"
  jq -r --arg story_id "$story_id" '
    .userStories[]
    | select(.id == $story_id)
    | (
        [
          "Story ID: " + .id,
          "Title: " + .title,
          "Goal: " + .goal,
          "Status: " + (.status // "todo"),
          "Acceptance gate: " + .acceptanceGate,
          "",
          "Files:",
          (.files[] | "- " + .),
          "",
          "Tasks:",
          (.tasks[] | "- " + .),
          "",
          "Verification:",
          (.verification[] | "- " + .)
        ] | join("\n")
      )
  ' "$PRD"
}

render_deferred_block() {
  jq -r '
    .deferredStories
    | if length == 0 then "- none" else map("- " + .id + " — " + .title + " (" + .reason + ")") | join("\n") end
  ' "$PRD"
}

render_progress_tail() {
  tail -n 40 "$PROGRESS" 2>/dev/null || true
}

last_message_status() {
  [[ -f "$LAST_MESSAGE" ]] || return 0
  python - <<'PY' "$LAST_MESSAGE"
from pathlib import Path
import re
import sys
path = Path(sys.argv[1])
text = path.read_text(errors='ignore')
match = re.search(r'^status:\s*`?([A-Za-z_ -]+)`?\s*$', text, re.MULTILINE)
print(match.group(1).strip().lower() if match else "")
PY
}

sync_story_status_from_last_message() {
  local story_id="$1"
  local status="$2"
  local tmp_json
  [[ -n "$status" ]] || return 0
  tmp_json="$(mktemp)"
  jq --arg story_id "$story_id" --arg status "$status" '
    .userStories = (
      .userStories | map(if .id == $story_id then .status = $status else . end)
    )
  ' "$PRD" > "$tmp_json"
  mv "$tmp_json" "$PRD"
}

run_codex_exec() {
  if [[ "$CODEX_EXECUTION_MODE" == "bypass" ]]; then
    "$CODEX_BIN" exec \
      -m "$MODEL" \
      --dangerously-bypass-approvals-and-sandbox \
      -C "$ROOT" \
      -o "$LAST_MESSAGE" \
      - < "$1"
  else
    "$CODEX_BIN" exec \
      -m "$MODEL" \
      --sandbox "$SANDBOX_MODE" \
      -C "$ROOT" \
      -o "$LAST_MESSAGE" \
      - < "$1"
  fi
}

run_once() {
  local iteration="$1"
  local story_id
  local prompt_file
  local exit_code
  local worker_status

  story_id="$(next_story_id)"
  if [[ -z "$story_id" ]]; then
    echo "No remaining runnable stories."
    return 0
  fi

  prompt_file="$(mktemp)"
  cat "$PROMPT_TEMPLATE" > "$prompt_file"
  {
    echo
    echo "## Current board summary"
    render_board_summary
    echo
    echo "## Deferred stories (do not execute in this pass)"
    render_deferred_block
    echo
    echo "## Current story"
    render_story_block "$story_id"
    echo
    echo "## Recent progress tail"
    render_progress_tail
  } >> "$prompt_file"

  printf '\n[%s] watchdog iteration %s starting %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$iteration" "$story_id" >> "$PROGRESS"

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY RUN"
    echo "root=$ROOT"
    echo "story=$story_id"
    echo "model=$MODEL"
    echo "execution_mode=$CODEX_EXECUTION_MODE"
    echo "sandbox=$SANDBOX_MODE"
    echo "prompt_file=$prompt_file"
    rm -f "$prompt_file"
    return 0
  fi

  set +e
  run_codex_exec "$prompt_file"
  exit_code=$?
  set -e

  worker_status="$(last_message_status)"
  if [[ "$worker_status" == "blocked" ]]; then
    sync_story_status_from_last_message "$story_id" "$worker_status"
    printf '[%s] watchdog iteration %s worker_status=%s story=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$iteration" "$worker_status" "$story_id" >> "$PROGRESS"
    printf '[%s] watchdog stopping on blocked worker result for %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$story_id" >> "$PROGRESS"
    rm -f "$prompt_file"
    return 42
  fi

  printf '[%s] watchdog iteration %s exit=%s story=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$iteration" "$exit_code" "$story_id" >> "$PROGRESS"

  rm -f "$prompt_file"
  return "$exit_code"
}

main() {
  require_file "$PRD"
  require_file "$PROMPT_TEMPLATE"
  require_file "$PROGRESS"

  command -v "$CODEX_BIN" >/dev/null 2>&1 || {
    echo "Missing Codex binary: $CODEX_BIN" >&2
    exit 1
  }
  command -v jq >/dev/null 2>&1 || {
    echo "Missing jq binary" >&2
    exit 1
  }

  local remaining
  local blocked
  local iteration=1

  while (( iteration <= MAX_RUNS )); do
    blocked="$(blocked_story_id)"
    if [[ -n "$blocked" ]]; then
      echo "Board is blocked on $blocked. Resolve that story before continuing." >&2
      exit 2
    fi

    remaining="$(remaining_count)"
    if [[ "$remaining" == "0" ]]; then
      echo "All runnable stories are marked passing."
      exit 0
    fi

    echo "=== Ralph watchdog iteration $iteration / $MAX_RUNS ==="
    echo "Remaining stories: $remaining"
    if run_once "$iteration"; then
      :
    else
      run_status=$?
      if [[ "$run_status" == "42" ]]; then
        echo "Worker reported blocked status. Stopping watchdog instead of looping." >&2
        exit 2
      fi
      echo "Writer run exited non-zero; sleeping $SLEEP_SECONDS seconds before retry." >&2
    fi

    if [[ "$DRY_RUN" == "1" ]]; then
      echo "Dry run completed after one iteration."
      exit 0
    fi

    remaining="$(remaining_count)"
    if [[ "$remaining" == "0" ]]; then
      echo "All runnable stories are marked passing."
      exit 0
    fi

    sleep "$SLEEP_SECONDS"
    iteration=$((iteration + 1))
  done

  echo "Reached RALPH_MAX_RUNS=$MAX_RUNS with unfinished stories still remaining." >&2
  exit 3
}

main "$@"
