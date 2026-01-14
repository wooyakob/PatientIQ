#!/bin/sh
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$ROOT_DIR/.git/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
  echo "Missing .git/hooks directory: $HOOKS_DIR" >&2
  exit 1
fi

install_hook() {
  name="$1"
  src="$ROOT_DIR/githooks/$name"
  dst="$HOOKS_DIR/$name"

  if [ ! -f "$src" ]; then
    echo "Missing hook source: $src" >&2
    exit 1
  fi

  cp "$src" "$dst"
  chmod +x "$dst"
}

install_hook pre-commit
install_hook pre-push

echo "Installed git hooks: pre-commit, pre-push"
