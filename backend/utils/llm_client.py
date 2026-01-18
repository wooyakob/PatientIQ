import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    endpoint = (os.getenv("LLM_ENDPOINT") or "").rstrip("/")
    token = os.getenv("LLM_TOKEN") or ""

    if not endpoint:
        raise RuntimeError("LLM_ENDPOINT is not set")
    if not token:
        raise RuntimeError("LLM_TOKEN is not set")

    return AsyncOpenAI(api_key=token, base_url=f"{endpoint}/v1")


def _model_name() -> str:
    model = os.getenv("LLM_NAME") or ""
    if not model:
        raise RuntimeError("LLM_NAME is not set")
    return model


async def chat_completion_text(
    *,
    messages: List[Dict[str, str]],
    max_tokens: int = 400,
    temperature: float = 0.2,
    model: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    m = model or _model_name()
    resp = await _client().chat.completions.create(
        model=m,
        messages=messages,
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    text = ""
    try:
        if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
            text = str(resp.choices[0].message.content)
    except Exception:
        text = ""

    return text, resp.model_dump()
