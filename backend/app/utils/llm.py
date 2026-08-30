import asyncio
import json
import logging
import re

import httpx

logger = logging.getLogger(__name__)


def extract_json(text: str) -> dict | list | None:
    """Best-effort extraction of JSON from LLM output (strips code fences, prose, and handles unescaped newlines)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text, strict=False)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try object extraction
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        sub = text[start : end + 1]
        try:
            return json.loads(sub, strict=False)
        except (json.JSONDecodeError, TypeError):
            pass
        # Try repairing raw unescaped newlines inside string literals
        try:
            repaired = re.sub(
                r'(".*?")',
                lambda m: m.group(0).replace("\n", "\\n").replace("\r", "\\r"),
                sub,
                flags=re.DOTALL,
            )
            return json.loads(repaired, strict=False)
        except Exception:
            pass

    # Try array extraction (for project_matcher)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        sub = text[start : end + 1]
        try:
            return json.loads(sub, strict=False)
        except (json.JSONDecodeError, TypeError):
            return None
    return None

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GROQ_BASE = "https://api.groq.com/openai/v1"

GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
]

# OpenRouter fallback — use base slugs (free suffix now 404 for these models). Groq is prioritized; this is backup.
OPENROUTER_MODELS = [
    "deepseek/deepseek-v4-flash-0731",
    "openai/gpt-oss-20b",
    "amazon/nova-micro-v1",
    "nex-agi/nex-n2-mini",
    "mistralai/mistral-nemo",
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
                except Exception:
                    logger.warning("LLM output failed %s validation: %s", response_model.__name__, content[:500] if isinstance(content, str) else content)
            else:
                logger.warning("LLM output for %s was not JSON dict", response_model.__name__)
            return content
        return content

    async def _chat(self, client: httpx.AsyncClient, model: str | list[str], prompt: str) -> str | None:
        """Single chat completion. Returns content, or None on retryable/exhausted failure."""
        payload: dict = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }
        if client == self._client:
            payload["data_collection"] = "deny"
            payload["sort"] = "throughput"

        if isinstance(model, list):
            payload["models"] = model
        else:
            payload["model"] = model

        for attempt in range(3):
            resp = None
            try:
                resp = await client.post("/chat/completions", json=payload)
                if resp.status_code in _RETRYABLE:
                    body = ""
                    try:
                        body = resp.text[:500]
                    except Exception:
                        pass
                    logger.warning("LLM retryable %s (model=%s) body=%s", resp.status_code, model, body)
                    await asyncio.sleep(2**attempt)
                    continue
                if resp.status_code >= 400:
                    body = ""
                    try:
                        body = resp.text[:800]
                    except Exception:
                        pass
                    logger.warning("LLM request failed %s (model=%s) body=%s", resp.status_code, model, body)
                    # 400 is not retryable — try next model immediately
                    return None
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except httpx.TimeoutException:
                if attempt == 2:
                    logger.warning("LLM request timed out (model=%s)", model)
                    return None
                await asyncio.sleep(2**attempt)
            except httpx.HTTPError as e:
                body = ""
                try:
                    if resp is not None:
                        body = resp.text[:800]
                except Exception:
                    pass
                logger.warning("LLM request failed (model=%s): %s body=%s", model, e, body)
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
        # Try each OpenRouter model sequentially (single `model` field) — more reliable than `models` array which 400s
        for model in OPENROUTER_MODELS:
            content = await self._chat(self._client, model, prompt)
            if content is not None:
                return content
        # If all single models failed, raise (Groq already tried via complete())
        raise RuntimeError("LLM request failed after 3 attempts (all Groq + OpenRouter free models)")

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.post(
            "/embeddings",
            json={
                "model": "openai/text-embedding-3-small",
                "input": text,
                "data_collection": "deny",
            },
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    async def close(self):
        await self._client.aclose()
        if self._groq_client is not None:
            await self._groq_client.aclose()
