import yaml
import uuid
from datetime import date, datetime
from appvault.models import Application, ApplicationStatus
from pathlib import Path
from typing import Optional
from appvault.exceptions import StorageError, AppVaultError
def _serialize(app:Application) -> dict:
    return {
        "company": app.company,
        "role": app.role,
        "applied_date": app.applied_date.isoformat(),
        "application_id": app.application_id,
        "status": app.status.value,
        "interest_rating": app.interest_rating,
        "resume_version": app.resume_version,
        "notes": app.notes,
        "last_contact_date": app.last_contact_date.isoformat() if app.last_contact_date else None,
        "sender": app.sender,
        "received_at": app.received_at.isoformat() if app.received_at else None,
    }

def _deserialize(data:dict) -> Application:
    return Application (
        company= data["company"],
        role= data["role"],
        applied_date=date.fromisoformat(data["applied_date"]),
        application_id=data["application_id"],
        status= ApplicationStatus(data["status"]),
        interest_rating=data["interest_rating"],
        resume_version=data["resume_version"],
        notes=data["notes"],
        last_contact_date= date.fromisoformat(data["last_contact_date"]) if data["last_contact_date"] else None,  # None-guarded date.fromisoformat
        sender=data["sender"],
        received_at= datetime.fromisoformat(data["received_at"]) if data["received_at"] else None

    )

DEFAULT_STORAGE_PATH = Path.home() / ".appvault" / "applications.yaml"

class ApplicationStore:
    def __init__(self, path: Optional[Path]= None):
        self.path = path or DEFAULT_STORAGE_PATH

    def save_all(self, applications: list[Application]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(yaml.safe_dump([_serialize(a) for a in applications], sort_keys=False))
        tmp_path.replace(self.path) 

    def load_all(self) -> list[Application]:
        if not self.path.exists():
            return []
        raw = yaml.safe_load(self.path.read_text()) or []
        return [_deserialize(item) for item in raw]

    def add(self, application: Application) -> Application:
        if not application.application_id:
            application.application_id = str(uuid.uuid4())[:8]
        apps = self.load_all()
        apps.append(application)
        self.save_all(apps)
        return application

    def update_status(self, application_id: str, status: ApplicationStatus) -> Application:
        apps = self.load_all()
        for app in apps:
            if app.application_id == application_id:
                app.status = status
                self.save_all(apps)
                return app
        raise StorageError(f"No application found with id {application_id}")

    def delete(self, application_id: str) -> Application:
        apps = self.load_all()
        for i, app in enumerate(apps):
            if app.application_id == application_id:
                removed = apps.pop(i)
                self.save_all(apps)
                return removed
        raise StorageError(f"No application found with id {application_id}")
