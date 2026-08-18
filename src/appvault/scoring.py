from dataclasses import dataclass
from datetime import date, timedelta
 
from appvault.models import Application, ApplicationStatus

DEFAULT_RESPONSE_BENCHMARK_DAYS = 14
 
_STATUS_BASE_POINTS = {
    ApplicationStatus.OFFER: 40,
    ApplicationStatus.INTERVIEW: 30,
    ApplicationStatus.PENDING: 10,
}
 
_EXCLUDED_STATUSES = {ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}
 
_MAX_DAYS_OVERDUE_POINTS = 30
_INTEREST_POINTS_PER_STAR = 4
_MOMENTUM_BONUS = 10
_SILENCE_PENALTY = 5
 
 
@dataclass
class ScoredApplication:
    application: Application
    total_score: float
    reasons: list[str]
 
 
def _days_since_applied(application: Application, as_of: date) -> int:
    return (as_of - application.applied_date).days
 
 
def _score_status(application: Application) -> tuple[float, str | None]:
    base = _STATUS_BASE_POINTS.get(application.status, 0)
    if application.status in (ApplicationStatus.OFFER, ApplicationStatus.INTERVIEW):
        return base, f"status is {application.status.value} ({base} pts)"
    return base, None
 
 
def _score_days_overdue(days_since: int, benchmark: int) -> tuple[float, str | None]:
    overdue = days_since - benchmark
    if overdue <= 0:
        return 0, None
    # Linear ramp: 1 point per day overdue, capped at _MAX_DAYS_OVERDUE_POINTS
    points = min(overdue, _MAX_DAYS_OVERDUE_POINTS)
    return points, f"{overdue} day(s) past the {benchmark}-day benchmark ({points} pts)"
 
 
def _score_interest(application: Application) -> tuple[float, str | None]:
    if application.interest_rating is None:
        return 0, None
    points = application.interest_rating * _INTEREST_POINTS_PER_STAR
    return points, f"interest rating {application.interest_rating}/5 ({points} pts)"
 
 
def _score_momentum(application: Application, days_since: int, benchmark: int) -> tuple[float, str | None]:
    if application.status in (ApplicationStatus.OFFER, ApplicationStatus.INTERVIEW):
        return _MOMENTUM_BONUS, f"status has progressed beyond pending (+{_MOMENTUM_BONUS} pts)"
 
    if (
        application.status == ApplicationStatus.PENDING
        and application.last_contact_date is None
        and days_since > benchmark
    ):
        return -_SILENCE_PENALTY, f"total silence since applying, no contact logged (-{_SILENCE_PENALTY} pts)"
 
    return 0, None
 
 
def score_applications(
    applications: list[Application],
    as_of: date | None = None,
    benchmark_days: int = DEFAULT_RESPONSE_BENCHMARK_DAYS,
) -> list[ScoredApplication]:
    """
    Score and rank applications by follow-up priority.
 
    Excludes REJECTED and WITHDRAWN applications entirely -- there's
    nothing actionable about them. Returns a list sorted highest score
    first; the caller decides how many to highlight as "top picks."
    """
    as_of = as_of or date.today()
    scored = []
 
    for application in applications:
        if application.status in _EXCLUDED_STATUSES:
            continue
 
        days_since = _days_since_applied(application, as_of)
        reasons = []
        total = 0.0
 
        for scorer in (
            lambda: _score_status(application),
            lambda: _score_days_overdue(days_since, benchmark_days),
            lambda: _score_interest(application),
            lambda: _score_momentum(application, days_since, benchmark_days),
        ):
            points, reason = scorer()
            total += points
            if reason:
                reasons.append(reason)
 
        if not reasons:
            reasons.append("no strong signals either way")
 
        scored.append(ScoredApplication(application=application, total_score=total, reasons=reasons))
 
    scored.sort(key=lambda s: s.total_score, reverse=True)
    return scored