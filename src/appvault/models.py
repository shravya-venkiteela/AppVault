from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional

class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    INTERVIEW = "INTERVIEW"
    REJECTED = "REJECTED"
    OFFER = "OFFER"
    WITHDRAWN = "WITHDRAWN"

@dataclass
class Application:
    company: str
    role: str
    applied_date: date
    application_id: Optional[str] = None
    notes: Optional[str] = None
    last_contact_date: Optional[date] = None
    status: ApplicationStatus = ApplicationStatus.PENDING
    interest_rating: Optional[int] = None
    resume_version: Optional[str] = None
    sender: Optional[str] = None
    received_at: Optional[datetime] = None
    def __post_init__(self):
        if self.interest_rating is not None and not (1 <= self.interest_rating <= 5):
            raise ValueError("interest_rating must be between 1 and 5")
        if not self.company or not self.company.strip():
            raise ValueError("company cannot be empty")
        if not self.role or not self.role.strip():
            raise ValueError("role cannot be empty")