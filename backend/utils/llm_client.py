import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI, OpenAI


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    endpoint = (os.getenv("LLM_ENDPOINT") or "").rstrip("/")
    token = os.getenv("LLM_TOKEN") or ""

    if not endpoint:
        raise RuntimeError("LLM_ENDPOINT is not set")
    if not token:
        raise RuntimeError("LLM_TOKEN is not set")

    return AsyncOpenAI(api_key=token, base_url=f"{endpoint}/v1")


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    """
    Get a synchronous OpenAI client instance for tools that need blocking calls.
    Uses the same configuration as the async client.
    """
    endpoint = (os.getenv("AGENT_LLM_ENDPOINT", "https://api.openai.com") or "").rstrip("/")
    token = os.getenv("OPENAI_API_KEY")

    if not endpoint:
        raise RuntimeError("AGENT_LLM_ENDPOINT is not set")
    if not token:
        raise RuntimeError("OPENAI_API_KEY is not set")

    return OpenAI(api_key=token, base_url=f"{endpoint}/v1")


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
