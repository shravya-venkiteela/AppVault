from difflib import SequenceMatcher
from typing import List, Tuple, Optional
from appvault.models import Application

DEFAULT_SIMILARITY_THRESHOLD = 0.80


def normalize_company_name(name: str) -> str:
    suffixes = ["inc", "llc", "ltd", "corp", "corporation", "co", "company"]
    normalized = name.lower().strip()
    for suffix in suffixes:
        if normalized.endswith(" " + suffix):
            normalized = normalized[: -(len(suffix) + 1)].strip()
        elif normalized.endswith(" " + suffix + "."):
            normalized = normalized[: -(len(suffix) + 2)].strip()
    return normalized


def normalize_role(role: str) -> str:
    return role.lower().strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_company_name(a), normalize_company_name(b)).ratio()


def find_duplicates(
    company: str,
    existing: List[Application],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    role: Optional[str] = None,
) -> List[Tuple[Application, float]]:
    duplicates = []
    for app in existing:
        sim_score = similarity(company, app.company)
        if sim_score < threshold:
            continue

        if role is not None:
            role_score = SequenceMatcher(None, normalize_role(role), normalize_role(app.role)).ratio()
            if role_score < threshold:
                continue

        duplicates.append((app, sim_score))

    duplicates.sort(key=lambda pair: pair[1], reverse=True)
    return duplicates