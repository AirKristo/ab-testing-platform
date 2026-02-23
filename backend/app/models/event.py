# Assignment and Event models for experiment tracking

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    variant_name = Column(String(100), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())

    # Each user can only be assigned once per experiment
    __table_args__ = (
        UniqueConstraint("experiment_id", "user_id", name="uq_assignment_experiment_user"),
    )

    experiment = relationship("Experiment", back_populates="assignments")
    user = relationship("User", back_populates="assignments")

    def __repr__(self) -> str:
        return (
            f"<Assignment(experiment_id={self.experiment_id}, "
            f"user_id={self.user_id}, variant='{self.variant_name}')>"
        )

class Event(Base):
    # Tracks user actions during an experiment

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    variant_name = Column(String(100), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    event_value = Column(Numeric(10, 2), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())
    event_metadata = Column(JSONB, nullable=True)

    experiment = relationship("Experiment", back_populates="events")
    user = relationship("User", back_populates="events")

    def __repr__(self) -> str:
        return (
            f"<Event(experiment_id={self.experiment_id}, "
            f"user_id={self.user_id}, type='{self.event_type}')>"
        )

