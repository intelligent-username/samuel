import logging

from app.services.ats_base import ATSProvider

logger = logging.getLogger(__name__)


class ATSRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ATSProvider] = {}

    def register(self, name: str, provider: ATSProvider) -> None:
        if not name or not name.strip():
            raise ValueError("provider name required")
        key = name.strip().lower()
        if key in self._providers:
            logger.debug("ATS provider overwritten: %s", key)
        self._providers[key] = provider

    def get(self, name: str) -> ATSProvider | None:
        if not name:
            return None
        return self._providers.get(name.strip().lower())

    def get_default(self) -> ATSProvider:
        from app.config import settings

        provider = self.get(settings.ats_provider)
        if provider is not None:
            return provider
        fallback = self.get("llm")
        if fallback is not None:
            return fallback
        raise RuntimeError("no ATS provider registered")

    def list_providers(self) -> list[str]:
        return sorted(self._providers.keys())


registry = ATSRegistry()
