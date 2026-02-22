# Cart and CartItem models for the e-commerce demo.

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


    def __repr__(self) -> str:
        return f"<Cart(id={self.id}, user_id={self.user_id})>"



class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    added_at = Column(DateTime, server_default=func.now())

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

    def __repr__(self) -> str:
        return f"<CartItem(cart_id={self.cart_id}, product_id={self.product_id}, qty={self.quantity})>"