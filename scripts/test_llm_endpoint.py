#!/usr/bin/env python3

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _load_dotenv_if_present(root_dir: Path) -> None:
    dotenv_path = root_dir / ".env"
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip("\n")
        if not line or line.lstrip().startswith("#"):
            continue

        if "=" not in line:
            continue

        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()

        if not (key.startswith("LLM_") or key.startswith("EMBEDDING_")):
            continue

        if os.environ.get(key):
            continue

        if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
            val = val[1:-1]

        os.environ[key] = val


def _require_env(name: str, root_dir: Path) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is not set. Put it in {root_dir}/.env or export it in your shell."
        )
    return value


def _http_post_json(url: str, token: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise SystemExit(f"HTTP {e.code} from {url}:\n{body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Request failed for {url}: {e}")

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise SystemExit(f"Non-JSON response from {url}:\n{body}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Couchbase Model Service LLM endpoints")
    parser.add_argument(
        "--mode",
        choices=["chat", "completion"],
        default="chat",
        help="Which endpoint to call.",
    )
    parser.add_argument(
        "--prompt",
        default="",
        help="Prompt text. If omitted/empty, reads from stdin.",
    )
    parser.add_argument("--max-tokens", type=int, default=100)
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parents[1]
    _load_dotenv_if_present(root_dir)

    endpoint = _require_env("LLM_ENDPOINT", root_dir).rstrip("/")
    token = _require_env("LLM_TOKEN", root_dir)
    model = _require_env("LLM_NAME", root_dir)

    prompt = args.prompt
    if prompt == "":
        prompt = sys.stdin.read()

    if args.mode == "chat":
        url = f"{endpoint}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": args.max_tokens,
        }
    else:
        url = f"{endpoint}/v1/completions"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "max_tokens": args.max_tokens,
        }

    resp = _http_post_json(url, token, payload)
    print(json.dumps(resp, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
