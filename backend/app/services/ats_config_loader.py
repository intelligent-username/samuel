from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.services.ats_base import ATEvaluationError

_CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_json(filename: str) -> object:
    try:
        return json.loads((_CONFIG_DIR / filename).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ATEvaluationError("ATS config not found") from e


def _norm_key(k: str) -> str:
    return k.strip().lower()


@lru_cache(maxsize=1)
def load_ats_weights() -> dict[str, float]:
    data = _load_json("ats_weights.json")
    if not isinstance(data, dict):
        raise ValueError("ats_weights.json must be object")
    out: dict[str, float] = {}
    for k, v in data.items():
        out[_norm_key(k)] = float(v)
    total = sum(out.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"weights sum {total} != 1.0")
    for k, v in out.items():
        if not 0 <= v <= 1:
            raise ValueError(f"weight {k} out of range 0-1")
    return out


@lru_cache(maxsize=1)
def load_degree_map() -> dict[str, int]:
    data = _load_json("degree_map.json")
    if not isinstance(data, dict):
        raise ValueError("degree_map.json must be object")
    out: dict[str, int] = {}
    for k, v in data.items():
        if k.startswith("_"):
            continue
        out[_norm_key(k)] = int(v)
    for v in out.values():
        if not 0 <= v <= 4:
            raise ValueError("degree ordinal out of range 0-4")
    return out


@lru_cache(maxsize=1)
def load_seniority_map() -> dict[str, int]:
    data = _load_json("seniority_map.json")
    if not isinstance(data, dict):
        raise ValueError("seniority_map.json must be object")
    out: dict[str, int] = {}
    for k, v in data.items():
        if k.startswith("_"):
            continue
        out[_norm_key(k)] = int(v)
    for v in out.values():
        if not 0 <= v <= 6:
            raise ValueError("seniority ordinal out of range 0-6")
    return out


@lru_cache(maxsize=1)
def load_skills_taxonomy() -> set[str]:
    data = _load_json("skills_taxonomy.json")
    if not isinstance(data, list):
        raise ValueError("skills_taxonomy.json must be array")
    return {_norm_key(str(s)) for s in data if str(s).strip()}


@lru_cache(maxsize=1)
def load_synonyms() -> dict[str, str]:
    data = _load_json("synonyms.json")
    if not isinstance(data, dict):
        raise ValueError("synonyms.json must be object")
    return {_norm_key(k): _norm_key(v) for k, v in data.items()}


@lru_cache(maxsize=1)
def load_header_keywords() -> dict[str, list[str]]:
    data = _load_json("header_keywords.json")
    if not isinstance(data, dict):
        raise ValueError("header_keywords.json must be object")
    out: dict[str, list[str]] = {}
    for k, v in data.items():
        if k.startswith("_"):
            continue
        nk = _norm_key(k)
        if isinstance(v, list):
            out[nk] = [_norm_key(str(x)) for x in v if str(x).strip()]
        else:
            out[nk] = [_norm_key(str(v))]
    return out
