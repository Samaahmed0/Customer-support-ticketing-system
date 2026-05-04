from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ReportingCounter(Base):
    """Single-row aggregate store updated from async events."""

    __tablename__ = "reporting_counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tickets_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tickets_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    support_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    support_resolved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
