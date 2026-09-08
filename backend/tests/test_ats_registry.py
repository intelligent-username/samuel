"""Tests for ATSRegistry."""

import pathlib

from app.schemas.ats import ATSResult
from app.services.ats_base import ATSProvider
from app.services.ats_registry import ATSRegistry


class Dummy(ATSProvider):
    @property
    def provider_name(self) -> str:
        return "dummy"

    async def evaluate(self, pdf_bytes, jd, resume_text=None):  # type: ignore[override]
        return ATSResult(score=75)


def test_registry_case_insensitive():
    r = ATSRegistry()
    d = Dummy()
    r.register("LLM", d)
    assert r.get("llm") is d
    assert r.get("LLM") is d
    assert r.get("LlM") is d
    assert "llm" in r.list_providers()
    assert r.list_providers() == sorted(r.list_providers())


def test_register_overwrite_and_empty_name():
    r = ATSRegistry()
    d1 = Dummy()
    d2 = Dummy()
    r.register("llm", d1)
    r.register("llm", d2)
    assert r.get("llm") is d2
    try:
        r.register("", d1)
        assert False, "should raise ValueError"
    except ValueError:
        pass
    try:
        r.register("   ", d1)
        assert False, "should raise ValueError"
    except ValueError:
        pass


def test_get_default_fallback(monkeypatch):
    from app.config import settings

    r = ATSRegistry()
    d = Dummy()
    r.register("llm", d)
    # unknown provider falls back to llm
    monkeypatch.setattr(settings, "ats_provider", "unknown")
    assert r.get_default() is d
    # case-insensitive get_default
    monkeypatch.setattr(settings, "ats_provider", "LLM")
    assert r.get_default() is d
    # correct provider returned when set
    r2 = ATSRegistry()
    r2.register("matching", d)
    r2.register("llm", d)
    monkeypatch.setattr(settings, "ats_provider", "matching")
    assert r2.get_default() is d


def test_get_default_no_provider_raises():
    from app.config import settings

    r = ATSRegistry()
    # ensure settings points to missing
    original = settings.ats_provider
    try:
        settings.ats_provider = "nonexistent"  # type: ignore[assignment]
        try:
            r.get_default()
            assert False, "should raise RuntimeError"
        except RuntimeError as e:
            assert "no ATS provider" in str(e)
    finally:
        settings.ats_provider = original  # type: ignore[assignment]


def test_checklist_comment_exists():
    text = pathlib.Path("backend/app/main.py").read_text(encoding="utf-8")
    assert "CHECKLIST: verify registry.get_default()" in text


def test_no_secret_logging(caplog):
    import logging

    r = ATSRegistry()
    d = Dummy()
    with caplog.at_level(logging.DEBUG):
        r.register("llm", d)
        _ = r.get("llm")
        _ = r.list_providers()
        _ = r.get("LLM")
    combined = " ".join(caplog.messages).lower()
    assert "pdf_bytes" not in combined
    assert "secret" not in combined
    assert "openrouter" not in combined
