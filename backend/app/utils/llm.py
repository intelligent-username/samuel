import json

import httpx

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o"


class LLMClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

    async def complete(self, prompt: str, response_model: type | None = None) -> str | dict:
        resp = await self._client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

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