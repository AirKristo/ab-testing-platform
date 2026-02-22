# Experiment and ExperimentResult models

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    status = Column(String(50), default="draft", index=True)

    variants = Column(JSONB, nullable=False)
    metrics = Column(JSONB, nullable=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    assignments = relationship("Assignment", back_populates="experiment")
    events = relationship("Event", back_populates="experiment")
    results = relationship("ExperimentResult", back_populates="experiment")

    def __repr__(self) -> str:
        return f"<Experiment(id={self.id}, name='{self.name}', status='{self.status}')>"


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_name = Column(String(100), nullable=False)
    metric_name = Column(String(100), nullable=False)
    sample_size = Column(Integer, nullable=False)
    mean = Column(Numeric(10, 4), nullable=True)
    std_dev = Column(Numeric(10, 4), nullable=True)
    ci_lower = Column(Numeric(10, 4), nullable=True)
    ci_upper = Column(Numeric(10, 4), nullable=True)
    p_value = Column(Numeric(10, 8), nullable=True)
    calculated_at = Column(DateTime, server_default=func.now())

    experiment = relationship("Experiment", back_populates="results")

    def __repr__(self) -> str:
        return (
            f"<ExperimentResult(experiment_id={self.experiment_id}, "
            f"variant='{self.variant_name}', metric='{self.metric_name}')>"
        )


