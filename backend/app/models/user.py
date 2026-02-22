# User model for A/B testing platform

from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # - historical_spend: Strongly correlated with future revenue (our primary metric)
    # - days_since_signup: Captures user maturity / engagement level
    # - order_count: Captures purchase frequency behavior
    # The higher the correlation with the outcome metric, the more variance CUPED reduces
    historical_spend = Column(Numeric(10, 2), default=0)
    days_since_signup = Column(Integer, default=0)
    order_count = Column(Integer, default=0)

    orders = relationship("Order", back_populates="user")
    carts = relationship("Cart", back_populates="user")
    assignments = relationship("Assignment", back_populates="user")
    events = relationship("Event", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"

    
