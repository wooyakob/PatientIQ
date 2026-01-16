#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$ROOT_DIR/.env" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ""|\#*)
        continue
        ;;
    esac

    if [[ "$line" != *"="* ]]; then
      continue
    fi

    key="${line%%=*}"
    val="${line#*=}"

    case "$key" in
      LLM_*|EMBEDDING_*)
        ;;
      *)
        continue
        ;;
    esac

    if [ -n "${!key:-}" ]; then
      continue
    fi

    if [[ "$val" == \"*\" && "$val" == *\" ]]; then
      val="${val:1:${#val}-2}"
    elif [[ "$val" == \'.* && "$val" == *\' ]]; then
      val="${val:1:${#val}-2}"
    fi

    printf -v "$key" '%s' "$val"
    export "$key"
  done < "$ROOT_DIR/.env"
fi

if [ -z "${LLM_ENDPOINT:-}" ]; then
  echo "LLM_ENDPOINT is not set. Put it in $ROOT_DIR/.env or export it in your shell." >&2
  exit 1
fi
if [ -z "${LLM_TOKEN:-}" ]; then
  echo "LLM_TOKEN is not set. Put it in $ROOT_DIR/.env or export it in your shell." >&2
  exit 1
fi
if [ -z "${LLM_NAME:-}" ]; then
  echo "LLM_NAME is not set. Put it in $ROOT_DIR/.env or export it in your shell." >&2
  exit 1
fi

curl -sS -X POST "${LLM_ENDPOINT%/}/v1/chat/completions" \
  -H "Authorization: Bearer $LLM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$LLM_NAME"'",
    "messages": [
      {
        "role": "user",
        "content": "What is Couchbase all about? Write a N1QL query to get top 250 documents in a sorted list of scope, inventory and collection, airlines"
      }
    ],
    "stream": false,
    "max_tokens": 100
  }'