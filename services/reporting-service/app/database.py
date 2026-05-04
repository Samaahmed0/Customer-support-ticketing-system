from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base, ReportingCounter

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        row = db.get(ReportingCounter, 1)
        if row is None:
            db.add(
                ReportingCounter(
                    id=1,
                    tickets_created=0,
                    tickets_updated=0,
                    support_messages=0,
                    support_resolved=0,
                )
            )
            db.commit()


def increment_counter(db: Session, field: str) -> None:
    row = db.get(ReportingCounter, 1)
    if row is None:
        return
    current = getattr(row, field)
    setattr(row, field, int(current) + 1)
    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()


def get_summary(db: Session) -> ReportingCounter:
    row = db.get(ReportingCounter, 1)
    if row is None:
        raise RuntimeError("Reporting counters not initialized")
    return row
