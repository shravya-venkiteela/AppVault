from datetime import date, timedelta
from appvault.models import Application, ApplicationStatus
from appvault.scoring import score_applications

today = date.today()

apps = [
    Application(company='StaleCo', role='Analyst', applied_date=today - timedelta(days=30), status=ApplicationStatus.PENDING, interest_rating=2),
    Application(company='DreamJob Inc', role='Engineer', applied_date=today - timedelta(days=20), status=ApplicationStatus.PENDING, interest_rating=5),
    Application(company='OfferCo', role='Analyst', applied_date=today - timedelta(days=10), status=ApplicationStatus.OFFER, interest_rating=4),
    Application(company='InterviewCo', role='Analyst', applied_date=today - timedelta(days=5), status=ApplicationStatus.INTERVIEW, interest_rating=3),
    Application(company='RejectedCo', role='Analyst', applied_date=today - timedelta(days=15), status=ApplicationStatus.REJECTED, interest_rating=5),
    Application(company='FreshCo', role='Analyst', applied_date=today - timedelta(days=2), status=ApplicationStatus.PENDING, interest_rating=1),
]

results = score_applications(apps)
for r in results:
    print(f"{r.total_score:>5.0f}  {r.application.company:<15} {r.application.status.value:<10} -> {'; '.join(r.reasons)}")

print(f"\nTotal scored: {len(results)} (RejectedCo should be excluded)")