from datetime import date
from appvault.duplicates import find_duplicates, similarity
from appvault.models import Application


def _make_application(company: str, role: str = "Software Engineer") -> Application:
    return Application(company=company, role=role, applied_date=date.today())


def test_similarity_treats_suffix_variants_as_identical():
    # "Inc" / "Corp" are stripped by normalize_company_name, so these
    # should be a perfect match.
    assert similarity("Acme Corp", "Acme Inc") == 1.0


def test_similarity_treats_different_companies_as_dissimilar():
    score = similarity("Acme Corp", "Globex Corporation")
    assert score < DEFAULT_SIMILARITY_THRESHOLD_FOR_TEST


DEFAULT_SIMILARITY_THRESHOLD_FOR_TEST = 0.80


def test_company_only_match_is_found():
    # Regression test for bug #1 (inverted threshold) and bug #2
    # (append nested under role branch). This call path has no role
    # argument at all -- exactly how the `add` command uses it.
    existing = [_make_application("Acme Inc")]
    result = find_duplicates("Acme Corp", existing)
    assert len(result) == 1
    matched_app, score = result[0]
    assert matched_app.company == "Acme Inc"
    assert score == 1.0


def test_no_match_for_genuinely_different_company():
    existing = [_make_application("Globex Corporation")]
    result = find_duplicates("Acme Corp", existing)
    assert result == []


def test_same_company_different_role_is_not_a_duplicate():
    # Regression test for the original design flaw: sync() logging a
    # second real application to the same company (different role) was
    # being incorrectly flagged as a duplicate before `role` support
    # was added.
    existing = [_make_application("Google", role="Backend Engineer")]
    result = find_duplicates("Google", existing, role="Frontend Engineer")
    assert result == []


def test_same_company_same_role_is_a_duplicate():
    existing = [_make_application("Google", role="Backend Engineer")]
    result = find_duplicates("Google", existing, role="Backend Engineer")
    assert len(result) == 1
    matched_app, score = result[0]
    assert matched_app.role == "Backend Engineer"
    assert score == 1.0


def test_role_matching_is_case_insensitive_and_whitespace_tolerant():
    existing = [_make_application("Google", role="  Backend Engineer  ")]
    result = find_duplicates("Google", existing, role="backend engineer")
    assert len(result) == 1