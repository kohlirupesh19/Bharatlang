"""Public list of the documents the corpus is built from, read from manifest.json.

Only fields a citizen can use are exposed (title, issuing department, GR number, date,
status and the official download link). Build-only fields such as file paths, hashes,
OCR settings and internal notes never leave the server.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

SourceStatus = Literal["current", "superseded"]
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class CorpusSourcesError(Exception):
    """The manifest is missing, unreadable or has an invalid document entry."""


class CorpusSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    doc_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    gr_number: Optional[str] = None
    department: Optional[str] = None
    issue_date: Optional[str] = None
    language: Optional[str] = None
    status: SourceStatus = "current"
    url: Optional[str] = None

    @field_validator("issue_date")
    @classmethod
    def _iso_date(cls, value: Optional[str]) -> Optional[str]:
        # Exactly YYYY-MM-DD: ordering compares these strings, and fromisoformat alone
        # would also accept forms such as 20230615 or 2023-W24-4.
        if value is not None:
            if not ISO_DATE.fullmatch(value):
                raise ValueError(f"issue_date must be YYYY-MM-DD, got {value!r}")
            date.fromisoformat(value)  # rejects impossible dates such as 2023-02-30
        return value

    @field_validator("url")
    @classmethod
    def _https_only(cls, value: Optional[str]) -> Optional[str]:
        # The page renders this as a link, so anything but an https URL is dropped.
        return value if value and value.startswith("https://") else None


def _ordered(sources: list[CorpusSource]) -> list[CorpusSource]:
    """Current documents first; within each group newest first, undated last."""
    dated = sorted((s for s in sources if s.issue_date), key=lambda s: s.issue_date, reverse=True)
    undated = [s for s in sources if not s.issue_date]
    return sorted(dated + undated, key=lambda s: s.status != "current")  # stable sort keeps date order


def load_corpus_sources(manifest_path: Path) -> list[CorpusSource]:
    """Return the manifest's documents, current ones first and newest first."""
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CorpusSourcesError(f"cannot read corpus manifest {manifest_path}: {exc}") from exc

    entries = manifest.get("documents") if isinstance(manifest, dict) else None
    if not isinstance(entries, list):
        raise CorpusSourcesError(f"corpus manifest {manifest_path} has no 'documents' list")

    sources: list[CorpusSource] = []
    for index, entry in enumerate(entries):
        try:
            sources.append(CorpusSource.model_validate(entry))
        except ValidationError as exc:
            raise CorpusSourcesError(f"invalid manifest document #{index}: {exc}") from exc

    seen: set[str] = set()
    for source in sources:
        if source.doc_id in seen:
            raise CorpusSourcesError(f"duplicate doc_id {source.doc_id!r} in corpus manifest")
        seen.add(source.doc_id)
    return _ordered(sources)
