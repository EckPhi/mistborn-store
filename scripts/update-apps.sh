#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"

usage() {
  printf '%s\n' \
    "Usage: scripts/update-apps.sh [--dry-run]" \
    "" \
    "Checks every app image with Renovate and creates one local commit per update." \
    "The current branch must be clean." \
    "" \
    "Options:" \
    "  --dry-run  Report available updates without creating commits" \
    "  -h, --help Show this help"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

dry_run=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

command -v git >/dev/null || die "git is required"
command -v bunx >/dev/null || die "bunx is required"

cd "$REPO_ROOT"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a Git repository"

printf 'Checking app images with Renovate...\n'
if [[ "$dry_run" == true ]]; then
  if [[ "${LOG_LEVEL:-info}" == debug ]]; then
    LOG_LEVEL=debug bunx renovate --platform=local --dry-run=lookup
  else
    LOG_LEVEL=debug LOG_FORMAT=json bunx renovate --platform=local --dry-run=lookup 2>&1 \
      | bun "$SCRIPT_DIR/renovate-updates.ts"
  fi
  exit 0
fi

if [[ -n "$(git status --porcelain)" ]]; then
  die "working tree is not clean; commit or stash existing changes first"
fi

updates_file="$(mktemp)"
trap 'rm -f -- "$updates_file"' EXIT

LOG_LEVEL=debug LOG_FORMAT=json bunx renovate --platform=local --dry-run=lookup 2>&1 \
  | bun "$SCRIPT_DIR/renovate-updates.ts" --json > "$updates_file"

if [[ ! -s "$updates_file" ]]; then
  printf 'All app images are up to date.\n'
  exit 0
fi

commits_created=0
while IFS=$'\t' read -r package_file dep_name current_value new_value update_type; do
  config_file="$(dirname -- "$package_file")/config.json"
  printf 'Updating %s: %s -> %s (%s)\n' "$dep_name" "$current_value" "$new_value" "$update_type"

  bun -e '
    const [file, name, from, to] = process.argv.slice(1);
    const oldImage = `"image": "${name}:${from}"`;
    const newImage = `"image": "${name}:${to}"`;
    const contents = await Bun.file(file).text();
    if (!contents.includes(oldImage)) throw new Error(`Image not found: ${name}:${from}`);
    await Bun.write(file, contents.replaceAll(oldImage, newImage));
  ' "$package_file" "$dep_name" "$current_value" "$new_value"
  bun "$SCRIPT_DIR/update-config.ts" "$package_file" "$new_value"

  if ! bun run test; then
    git restore -- "$package_file" "$config_file"
    die "tests failed for $dep_name $new_value"
  fi

  git add -- "$package_file" "$config_file"
  if ! git commit -m "chore(deps): update $dep_name to $new_value"; then
    git restore --staged --worktree -- "$package_file" "$config_file"
    die "failed to commit $dep_name $new_value"
  fi
  commits_created=$((commits_created + 1))
done < <(
  bun -e '
    const input = await Bun.stdin.text();
    for (const line of input.trim().split("\n")) {
      if (!line) continue;
      const update = JSON.parse(line);
      console.log([update.packageFile, update.depName, update.currentValue, update.newValue, update.updateType].join("\t"));
    }
  ' < "$updates_file"
)

printf 'Created %d update commit(s).\n' "$commits_created"
