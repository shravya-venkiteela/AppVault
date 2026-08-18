from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

DEFAULT_PATTERNS_PATH = Path(__file__).parent.parent.parent / "examples" / "patterns.yaml"


class ParsedStatus(str, Enum):
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    PENDING = "PENDING"
    INTERVIEW = "INTERVIEW"
    WITHDRAWN = "WITHDRAWN"


@dataclass
class ParsedApplication:
    company: str
    role: str
    status: ParsedStatus


def _compile_patterns(pattern_dicts: list[dict], case_insensitive: bool = True) -> list[re.Pattern]:
    flags = re.IGNORECASE if case_insensitive else 0
    return [re.compile(p["pattern"], flags) for p in pattern_dicts]


class PatternConfig:
    """Loads and compiles all patterns from a patterns.yaml file once,
    at construction time -- not re-parsed on every parse_email() call."""

    def __init__(self, patterns_path: Path | str | None = None):
        path = Path(patterns_path) if patterns_path else DEFAULT_PATTERNS_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"patterns.yaml not found at {path}. AppVault's parser requires "
                f"this config file to detect and extract application data from emails."
            )

        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        self.offer_patterns = _compile_patterns(raw["offer"])
        self.rejected_patterns = _compile_patterns(raw["rejected"])
        self.received_patterns = _compile_patterns(raw["received"])
        self.interview_patterns = _compile_patterns(raw["interview"])

        # NOT globally case-insensitive -- see patterns.yaml's schema comment
        # for why. Compiling these with a global IGNORECASE flag would
        # reintroduce the exact bug that once let "us" match as a company.
        self.company_patterns = _compile_patterns(raw["company_extraction"], case_insensitive=False)
        self.role_patterns = _compile_patterns(raw["role_extraction"], case_insensitive=False)

        self.junk_company_names = set(raw["junk_company_names"])


def _detect_status(text: str, patterns: PatternConfig) -> ParsedStatus | None:
    for pattern in patterns.offer_patterns:
        if pattern.search(text):
            return ParsedStatus.OFFER
    for pattern in patterns.rejected_patterns:
        if pattern.search(text):
            return ParsedStatus.REJECTED
    for pattern in patterns.interview_patterns:
        if pattern.search(text):
            return ParsedStatus.INTERVIEW
    for pattern in patterns.received_patterns:
        if pattern.search(text):
            return ParsedStatus.PENDING
    return None


def _extract_company(text: str, patterns: PatternConfig, sender_display_name: str | None = None) -> str | None:
    for pattern in patterns.company_patterns:
        match = pattern.search(text)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) > 1 and candidate.lower() not in patterns.junk_company_names:
                return candidate

    if sender_display_name:
        cleaned = re.sub(
            r"\b(recruiting|talent acquisition|careers|team|hr)\b",
            "",
            sender_display_name,
            flags=re.IGNORECASE,
        ).strip()
        if cleaned:
            return cleaned

    return None


def _extract_role(text: str, patterns: PatternConfig) -> str | None:
    for pattern in patterns.role_patterns:
        match = pattern.search(text)
        if match:
            role = match.group(1).strip()
            role = re.sub(r"\s*\(\d+\)\s*$", "", role).strip()
            if role:
                return role
    return None


_default_patterns: PatternConfig | None = None


def _get_default_patterns() -> PatternConfig:
    global _default_patterns
    if _default_patterns is None:
        _default_patterns = PatternConfig()
    return _default_patterns


def parse_email(
    body: str,
    sender_display_name: str | None = None,
    patterns: PatternConfig | None = None,
) -> ParsedApplication | None:
    """
    Attempt to parse an email into a ParsedApplication.

    `patterns` defaults to the project's patterns.yaml, loaded once and
    cached. Pass an explicit PatternConfig (e.g. pointing at a test
    fixture) to override.

    Returns None if no status keyword is detected, or if company/role
    cannot be extracted.
    """
    patterns = patterns or _get_default_patterns()

    status = _detect_status(body, patterns)
    if status is None:
        return None

    company = _extract_company(body, patterns, sender_display_name)
    role = _extract_role(body, patterns)

    if company is None or role is None:
        return None

    return ParsedApplication(company=company, role=role, status=status)