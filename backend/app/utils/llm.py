import asyncio
import json

import httpx

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

FALLBACK_MODELS = [
    "openai/gpt-oss-120b:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "nvidia/nemotron-3-ultra:free",
    "google/gemma-4-26b-a4b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/auto",
]

_RETRYABLE = {429, 500, 502, 503, 504}


class LLMClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )

    async def complete(self, prompt: str, response_model: type | None = None) -> str | dict:
        for attempt in range(3):
            try:
                resp = await self._client.post(
                    "/chat/completions",
                    json={
                        "models": FALLBACK_MODELS,
                        "route": "fallback",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                    },
                )
                if resp.status_code in _RETRYABLE:
                    await asyncio.sleep(2**attempt)
                    continue
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                break
            except httpx.TimeoutException:
                if attempt == 2:
                    raise
                await asyncio.sleep(2**attempt)
        else:
            raise RuntimeError("LLM request failed after 3 attempts")

        if response_model is not None:
            try:
                return response_model(**json.loads(content))
            except (json.JSONDecodeError, ValueError):
                return content
        return content

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.post(
            "/embeddings",
            json={
                "model": "openai/text-embedding-3-small",
                "input": text,
            },
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    async def close(self):
        await self._client.aclose()