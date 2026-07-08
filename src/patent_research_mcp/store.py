"""JSON file storage for Patent Research MCP.

Manages reading/writing JSON and Markdown files under the data/ directory tree.
All paths are relative to PATENT_RESEARCH_HOME env var (default: ~/patent-research-mcp/data).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .schemas import ArchitectureCard, ClaimsFirewall, PatternCard

# ── Path resolution ───────────────────────────────────────────────────


def _home() -> Path:
    """Resolve the data home directory.

    Uses PATENT_RESEARCH_DATA env var if set, otherwise defaults to
    $CWD/data (data/ subdirectory of the current working directory).
    """
    env = os.environ.get("PATENT_RESEARCH_DATA")
    if env:
        return Path(env)
    return Path.cwd() / "data"


def _ensure_dir(subdir: str) -> Path:
    d = _home() / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── JSON helpers ──────────────────────────────────────────────────────


def _write_json(subdir: str, filename: str, data: dict[str, Any]) -> str:
    dir_path = _ensure_dir(subdir)
    path = dir_path / filename
    path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    return str(path)


def _read_json(subdir: str, filename: str) -> dict[str, Any] | None:
    path = _home() / subdir / filename
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _list_json(subdir: str, suffix: str = ".json") -> list[Path]:
    dir_path = _home() / subdir
    if not dir_path.exists():
        return []
    return sorted(dir_path.glob(f"*{suffix}"))


def _write_markdown(subdir: str, filename: str, content: str) -> str:
    dir_path = _ensure_dir(subdir)
    path = dir_path / filename
    path.write_text(content)
    return str(path)


# ── Raw patent storage ────────────────────────────────────────────────


def save_raw_html(pub_num: str, html: str) -> str:
    return _write_json("raw", f"{pub_num}.html", {"html": html})


def save_raw_text(pub_num: str, text: str) -> str:
    path = _home() / "raw" / f"{pub_num}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return str(path)


def load_raw_html(pub_num: str) -> str | None:
    data = _read_json("raw", f"{pub_num}.html")
    if data:
        return data.get("html")
    return None


def load_raw_text(pub_num: str) -> str | None:
    path = _home() / "raw" / f"{pub_num}.txt"
    if path.exists():
        return path.read_text()
    return None


# ── Sections storage ──────────────────────────────────────────────────


def save_sections(pub_num: str, data: dict[str, Any] | Any) -> str:
    """Save structured sections. Accepts dict or Pydantic model."""
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    return _write_json("sections", f"{pub_num}.sections.json", data)


def load_sections(pub_num: str) -> dict[str, Any] | None:
    return _read_json("sections", f"{pub_num}.sections.json")


# ── Architecture card storage ─────────────────────────────────────────


def save_architecture_card(card: ArchitectureCard) -> str:
    return _write_json("cards", f"{card.publication_number}.architecture.json", card.model_dump())


def load_architecture_card(pub_num: str) -> ArchitectureCard | None:
    data = _read_json("cards", f"{pub_num}.architecture.json")
    if data:
        return ArchitectureCard(**data)
    return None


# ── Claims firewall storage ───────────────────────────────────────────


def save_claims_firewall(firewall: ClaimsFirewall) -> str:
    return _write_json("claims", f"{firewall.publication_number}.claims_firewall.json", firewall.model_dump())


def load_claims_firewall(pub_num: str) -> ClaimsFirewall | None:
    data = _read_json("claims", f"{pub_num}.claims_firewall.json")
    if data:
        return ClaimsFirewall(**data)
    return None


# ── Pattern storage ───────────────────────────────────────────────────


def save_pattern(pattern: PatternCard) -> str:
    return _write_json("patterns", f"{pattern.slug}.pattern.json", pattern.model_dump())


def load_pattern(slug: str) -> PatternCard | None:
    data = _read_json("patterns", f"{slug}.pattern.json")
    if data:
        return PatternCard(**data)
    return None


def list_patterns() -> list[PatternCard]:
    cards: list[PatternCard] = []
    for path in _list_json("patterns"):
        data = json.loads(path.read_text())
        cards.append(PatternCard(**data))
    return cards


# ── Export storage ────────────────────────────────────────────────────


def save_export(filename: str, markdown: str) -> str:
    return _write_markdown("exports", filename, markdown)


# ── Convenience helpers ───────────────────────────────────────────────


def raw_exists(pub_num: str) -> bool:
    return (_home() / "raw" / f"{pub_num}.txt").exists()
