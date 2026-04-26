"""
Pydantic schemas for Order/Checkout API requests and responses.


Checkout converts a cart into an order.
Process:
  1. Validate the cart has items
  2. Snapshot prices at time of purchase (price_at_purchase)
  3. Create the order and order items
  4. Clear the cart
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class CheckoutRequest(BaseModel):
    # Request body for checkout.

    user_id: int = Field(..., gt=0, examples=[1])


class OrderItemResponse(BaseModel):
    # A single item in a completed order.

    id: int
    product_id: int
    product_name: str
    quantity: int
    price_at_purchase: Decimal
    item_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    """
    Full order response with items and total.

    Returned after checkout and when viewing order history.
    """
    id: int
    user_id: int
    total_amount: Decimal
    items: list[OrderItemResponse]
    item_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    # List of orders for a user.

    orders: list[OrderResponse]
    total: int