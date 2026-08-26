import asyncio
import json
import logging
import re

import httpx

logger = logging.getLogger(__name__)


def extract_json(text: str) -> dict | list | None:
    """Best-effort extraction of JSON from LLM output (strips code fences and prose)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GROQ_BASE = "https://api.groq.com/openai/v1"

GROQ_MODELS = [
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound",
    "groq/compound-mini",
]

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
    def __init__(self, api_key: str, groq_api_key: str | None = None):
        self.api_key = api_key
        self.groq_api_key = groq_api_key
        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )
        self._groq_client = (
            httpx.AsyncClient(
                base_url=GROQ_BASE,
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120,
            )
            if groq_api_key
            else None
        )

    async def complete(self, prompt: str, response_model: type | None = None) -> str | dict:
        content = None
        if self._groq_client is not None:
            content = await self._complete_groq(prompt)
        if content is None:
            content = await self._complete_openrouter(prompt)

        if response_model is not None:
            data = extract_json(content)
            if isinstance(data, dict):
                fields = response_model.model_fields
                filtered = {k: v for k, v in data.items() if k in fields}
                try:
                    return response_model(**filtered)
                except ValueError:
                    logger.warning("LLM output failed %s validation", response_model.__name__)
            return content
        return content

    async def _chat(self, client: httpx.AsyncClient, model: str | list[str], prompt: str) -> str | None:
        """Single chat completion. Returns content, or None on retryable/exhausted failure."""
        payload: dict = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }
        if isinstance(model, list):
            payload["models"] = model
            payload["route"] = "fallback"
        else:
            payload["model"] = model

        for attempt in range(3):
            try:
                resp = await client.post("/chat/completions", json=payload)
                if resp.status_code in _RETRYABLE:
                    await asyncio.sleep(2**attempt)
                    continue
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except httpx.TimeoutException:
                if attempt == 2:
                    logger.warning("LLM request timed out (model=%s)", model)
                    return None
                await asyncio.sleep(2**attempt)
            except httpx.HTTPError as e:
                logger.warning("LLM request failed (model=%s): %s", model, e)
                return None
        return None

    async def _complete_groq(self, prompt: str) -> str | None:
        """Try each Groq model in priority order; return first success."""
        if self._groq_client is None:
            return None
        for model in GROQ_MODELS:
            content = await self._chat(self._groq_client, model, prompt)
            if content is not None:
                return content
        logger.warning("All Groq models failed; falling back to OpenRouter")
        return None

    async def _complete_openrouter(self, prompt: str) -> str:
        for attempt in range(3):
            content = await self._chat(self._client, FALLBACK_MODELS, prompt)
            if content is not None:
                return content
            await asyncio.sleep(2**attempt)
        raise RuntimeError("LLM request failed after 3 attempts")

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
        if self._groq_client is not None:
            await self._groq_client.aclose()
