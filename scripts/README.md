# Scripts

This folder contains small utilities for working with the CKO repo.

## Environment variables

The endpoint test scripts load variables from the repo root `.env` file (if present) and will not overwrite variables that are already set in your shell.

Required variables:

- `LLM_ENDPOINT`
- `LLM_TOKEN`
- `LLM_NAME`

## test_llm_endpoint.sh

Quick `curl`-based smoke test for the chat endpoint:

```bash
bash scripts/test_llm_endpoint.sh
```

## test_llm_endpoint.py

Python smoke test for both the chat and completion endpoints.

Chat:

```bash
python3 scripts/test_llm_endpoint.py --mode chat --prompt "Say hello in one sentence"
```

Completion:

```bash
python3 scripts/test_llm_endpoint.py --mode completion --prompt "Write a one-line haiku about lungs."
```

You can also pass the prompt via stdin:

```bash
echo "Summarize COPD management." | python3 scripts/test_llm_endpoint.py --mode chat
```

## install_git_hooks.sh

Installs the repo git hooks from `githooks/`.

```bash
bash scripts/install_git_hooks.sh
```
