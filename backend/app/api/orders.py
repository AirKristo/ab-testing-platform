"""
Order and Checkout API endpoints.

The checkout flow:
1. Validate user exists and has a cart with items
2. Create an Order with total_amount
3. Create OrderItems with price_at_purchase (snapshot current prices)
4. Clear the cart (remove all CartItems)
5. Return the completed order
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.order import (
    CheckoutRequest,
    OrderItemResponse,
    OrderResponse,
    OrderListResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


def _build_order_response(order: Order, db: Session) -> OrderResponse:
    # Build an OrderResponse with denormalized product names.


    items = []
    for order_item in order.items:
        product = db.query(Product).filter(Product.id == order_item.product_id).first()
        product_name = product.name if product else "Unknown Product"

        item_total = order_item.price_at_purchase * order_item.quantity

        items.append(OrderItemResponse(
            id=order_item.id,
            product_id=order_item.product_id,
            product_name=product_name,
            quantity=order_item.quantity,
            price_at_purchase=order_item.price_at_purchase,
            item_total=item_total,
        ))

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        items=items,
        item_count=len(items),
        created_at=order.created_at,
    )


@router.post("/checkout", response_model=OrderResponse)
def checkout(
    request: CheckoutRequest,
    db: Session = Depends(get_db),
) -> OrderResponse:
    """
    Convert the user's cart into a completed order.

    This is a transactional operation:
    - If ANY step fails, the entire checkout is rolled back
    - The user's cart is unchanged if checkout fails
    """
    logger.info(f"Checkout requested: user_id={request.user_id}")

    # Step 1: Validate user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Step 2: Get the user's cart
    cart = db.query(Cart).filter(Cart.user_id == request.user_id).first()
    if cart is None or len(cart.items) == 0:
        raise HTTPException(status_code=400, detail="Cart is empty")

    logger.info(f"Processing checkout: {len(cart.items)} items in cart")

    # Step 3: Calculate total and build order items
    total_amount = Decimal("0.00")
    order_items_data = []

    for cart_item in cart.items:
        product = db.query(Product).filter(Product.id == cart_item.product_id).first()

        if product is None:
            # Product was deleted between adding to cart and checkout
            raise HTTPException(
                status_code=400,
                detail=f"Product {cart_item.product_id} is no longer available",
            )

        # Snapshot the current price — this is what the user pays
        item_total = product.price * cart_item.quantity
        total_amount += item_total

        order_items_data.append({
            "product_id": cart_item.product_id,
            "quantity": cart_item.quantity,
            "price_at_purchase": product.price,
        })

    # Step 4: Create the order (in a single transaction)
    order = Order(
        user_id=request.user_id,
        total_amount=total_amount,
    )
    db.add(order)
    db.flush()  # Get the order.id without committing yet

    # Step 5: Create order items
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=order.id,
            **item_data,
        )
        db.add(order_item)

    # Step 6: Clear the cart
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

    # Step 7: Update user's covariates for CUPED
    user.order_count += 1
    user.historical_spend += total_amount

    # Commit everything at once — atomic transaction
    db.commit()
    db.refresh(order)

    logger.info(
        f"Checkout complete: order_id={order.id}, "
        f"total=${total_amount}, items={len(order_items_data)}"
    )

    return _build_order_response(order, db)


@router.get("/user/{user_id}", response_model=OrderListResponse)
def get_user_orders(
    user_id: int,
    db: Session = Depends(get_db),
) -> OrderListResponse:
    # Get all orders for a user, most recent first.

    logger.info(f"Fetching orders for user_id={user_id}")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    orders = (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    order_responses = [_build_order_response(order, db) for order in orders]

    logger.info(f"Found {len(orders)} orders for user_id={user_id}")

    return OrderListResponse(
        orders=order_responses,
        total=len(order_responses),
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
) -> OrderResponse:

    # Get a single order by ID.

    logger.info(f"Fetching order: order_id={order_id}")

    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return _build_order_response(order, db)