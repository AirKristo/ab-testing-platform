# Product model for the e-commerce demo application


from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"

