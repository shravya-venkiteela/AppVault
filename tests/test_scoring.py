from datetime import date, timedelta

from appvault.models import Application, ApplicationStatus
from appvault.scoring import (
    DEFAULT_RESPONSE_BENCHMARK_DAYS,
    score_applications,
)


def _make_app(
    company: str,
    status: ApplicationStatus = ApplicationStatus.PENDING,
    days_ago: int = 0,
    interest_rating: int | None = None,
    last_contact_days_ago: int | None = None,
    today: date | None = None,
) -> Application:
    today = today or date.today()
    return Application(
        company=company,
        role="Test Role",
        applied_date=today - timedelta(days=days_ago),
        status=status,
        interest_rating=interest_rating,
        last_contact_date=(today - timedelta(days=last_contact_days_ago)) if last_contact_days_ago is not None else None,
    )


def test_rejected_and_withdrawn_are_excluded_from_ranking():
    today = date.today()
    apps = [
        _make_app("RejectedCo", status=ApplicationStatus.REJECTED, today=today),
        _make_app("WithdrawnCo", status=ApplicationStatus.WITHDRAWN, today=today),
        _make_app("PendingCo", status=ApplicationStatus.PENDING, today=today),
    ]
    results = score_applications(apps, as_of=today)
    companies = [r.application.company for r in results]
    assert "RejectedCo" not in companies
    assert "WithdrawnCo" not in companies
    assert "PendingCo" in companies
    assert len(results) == 1


def test_offer_outranks_interview_outranks_pending():
    today = date.today()
    apps = [
        _make_app("PendingCo", status=ApplicationStatus.PENDING, today=today),
        _make_app("InterviewCo", status=ApplicationStatus.INTERVIEW, today=today),
        _make_app("OfferCo", status=ApplicationStatus.OFFER, today=today),
    ]
    results = score_applications(apps, as_of=today)
    ranked_companies = [r.application.company for r in results]
    assert ranked_companies == ["OfferCo", "InterviewCo", "PendingCo"]


def test_higher_interest_rating_scores_higher_all_else_equal():
    today = date.today()
    apps = [
        _make_app("LowInterest", interest_rating=1, today=today),
        _make_app("HighInterest", interest_rating=5, today=today),
    ]
    results = score_applications(apps, as_of=today)
    assert results[0].application.company == "HighInterest"
    assert results[1].application.company == "LowInterest"
    assert results[0].total_score > results[1].total_score


def test_days_overdue_increases_score_past_benchmark():
    today = date.today()
    apps = [
        _make_app("Fresh", days_ago=2, last_contact_days_ago=0, today=today),
        _make_app(
            "Overdue",
            days_ago=DEFAULT_RESPONSE_BENCHMARK_DAYS + 10,
            last_contact_days_ago=0,
            today=today,
        ),
    ]
    results = score_applications(apps, as_of=today)
    assert results[0].application.company == "Overdue"
    assert results[0].total_score > results[1].total_score


def test_overdue_and_silent_now_outranks_fresh_after_penalty_adjustment():
    today = date.today()
    apps = [
        _make_app("Fresh", days_ago=2, today=today),
        _make_app(
            "OverdueAndSilent",
            days_ago=DEFAULT_RESPONSE_BENCHMARK_DAYS + 10,
            last_contact_days_ago=None,
            today=today,
        ),
    ]
    results = score_applications(apps, as_of=today)
    scores = {r.application.company: r.total_score for r in results}
    assert scores["OverdueAndSilent"] > scores["Fresh"]


def test_days_overdue_points_are_capped():
    today = date.today()
    apps = [
        _make_app("Moderate", days_ago=DEFAULT_RESPONSE_BENCHMARK_DAYS + 30, today=today),
        _make_app("Extreme", days_ago=DEFAULT_RESPONSE_BENCHMARK_DAYS + 300, today=today),
    ]
    results = score_applications(apps, as_of=today)
    scores = {r.application.company: r.total_score for r in results}
    assert scores["Moderate"] == scores["Extreme"]


def test_silent_pending_application_gets_penalized():
    today = date.today()
    apps = [
        _make_app(
            "SilentCo",
            days_ago=DEFAULT_RESPONSE_BENCHMARK_DAYS + 5,
            last_contact_days_ago=None,
            today=today,
        ),
        _make_app(
            "ContactedCo",
            days_ago=DEFAULT_RESPONSE_BENCHMARK_DAYS + 5,
            last_contact_days_ago=1,
            today=today,
        ),
    ]
    results = score_applications(apps, as_of=today)
    scores = {r.application.company: r.total_score for r in results}
    assert scores["SilentCo"] < scores["ContactedCo"]


def test_interview_and_offer_get_momentum_bonus_reflected_in_reasons():
    today = date.today()
    apps = [_make_app("InterviewCo", status=ApplicationStatus.INTERVIEW, today=today)]
    results = score_applications(apps, as_of=today)
    assert any("progressed beyond pending" in reason for reason in results[0].reasons)


def test_no_signals_gives_flat_base_score_with_fallback_reason():
    today = date.today()
    apps = [_make_app("FreshCo", days_ago=1, today=today)]
    results = score_applications(apps, as_of=today)
    assert results[0].reasons == ["no strong signals either way"]
    assert results[0].total_score == 10  # PENDING base points only


def test_empty_application_list_returns_empty_result():
    assert score_applications([]) == []


def test_all_rejected_returns_empty_result():
    today = date.today()
    apps = [_make_app("RejectedCo", status=ApplicationStatus.REJECTED, today=today)]
    assert score_applications(apps, as_of=today) == []