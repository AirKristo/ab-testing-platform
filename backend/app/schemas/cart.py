"""
Pydantic schemas for Cart API requests and responses.

CartAddRequest: What the frontend sends when user clicks "Add to Cart"
CartUpdateRequest: What the frontend sends to change quantity
CartItemResponse: A single item in the cart (includes product details)
CartResponse: The full cart with all items and a computed total

The cart response includes product name and price
(denormalized) so the frontend doesn't need a second API call to display
the cart.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class CartAddRequest(BaseModel):
    # Request body for adding an item to the cart.
    user_id: int = Field(..., gt=0, examples=[1])
    product_id: int = Field(..., gt=0, examples=[42])
    quantity: int = Field(1, gt=0, le=99, examples=[1])


class CartUpdateRequest(BaseModel):
    # Request body for updating item quantity in the cart.
    quantity: int = Field(..., gt=0, le=99, examples=[3])


class CartItemResponse(BaseModel):
    # A single item in the cart, enriched with product details.
    id: int
    product_id: int
    product_name: str
    product_price: Decimal
    quantity: int
    item_total: Decimal  # product_price * quantity
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    # Full cart response with all items and computed total.

    cart_id: int
    user_id: int
    items: list[CartItemResponse]
    cart_total: Decimal
    item_count: int