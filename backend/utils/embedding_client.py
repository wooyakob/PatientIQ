import os
from functools import lru_cache
from typing import List

from openai import AsyncOpenAI


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    endpoint = (os.getenv("EMBEDDING_MODEL_ENDPOINT") or "").rstrip("/")
    token = os.getenv("EMBEDDING_MODEL_TOKEN") or ""

    if not endpoint:
        raise RuntimeError("EMBEDDING_MODEL_ENDPOINT is not set")
    if not token:
        raise RuntimeError("EMBEDDING_MODEL_TOKEN is not set")

    return AsyncOpenAI(api_key=token, base_url=f"{endpoint}/v1")


def _model_name() -> str:
    model = os.getenv("EMBEDDING_MODEL_NAME") or ""
    if not model:
        model = "nvidia/llama-3.2-nv-embedqa-1b-v2"
    return model


async def embedding_vector(text: str) -> List[float]:
    t = str(text or "").strip()
    if not t:
        return []

    resp = await _client().embeddings.create(model=_model_name(), input=t)

    try:
        data = resp.data[0].embedding
    except Exception:
        data = None

    if not isinstance(data, list):
        return []

    return [float(x) for x in data]
