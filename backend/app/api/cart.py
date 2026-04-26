"""
Cart API endpoints.

These endpoints handle the shopping cart functionality:
- Add item to cart (creates cart if none exists)
- View cart with all items
- Update item quantity
- Remove item from cart
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import (
    CartAddRequest,
    CartUpdateRequest,
    CartItemResponse,
    CartResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/cart",
    tags=["cart"],
)


def _get_or_create_cart(db: Session, user_id: int) -> Cart:
    # Get the user's active cart, or create one if it doesn't exist.

    cart = db.query(Cart).filter(Cart.user_id == user_id).first()

    if cart is None:
        logger.info(f"Creating new cart for user_id={user_id}")
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)

    return cart


def _build_cart_response(cart: Cart, db: Session) -> CartResponse:
    # Build a CartResponse with denormalized product details and computed totals.

    items = []
    cart_total = Decimal("0.00")

    for cart_item in cart.items:
        # Join with product to get name and price
        product = db.query(Product).filter(Product.id == cart_item.product_id).first()

        if product is None:
            # Product was deleted — skip it
            logger.warning(f"Product {cart_item.product_id} not found for cart item {cart_item.id}")
            continue

        item_total = product.price * cart_item.quantity
        cart_total += item_total

        items.append(CartItemResponse(
            id=cart_item.id,
            product_id=cart_item.product_id,
            product_name=product.name,
            product_price=product.price,
            quantity=cart_item.quantity,
            item_total=item_total,
            added_at=cart_item.added_at,
        ))

    return CartResponse(
        cart_id=cart.id,
        user_id=cart.user_id,
        items=items,
        cart_total=cart_total,
        item_count=len(items),
    )


@router.post("/add", response_model=CartResponse)
def add_to_cart(
    request: CartAddRequest,
    db: Session = Depends(get_db),
) -> CartResponse:
    """
    Add a product to the user's cart.

    Behavior:
    - If the user has no cart, creates one
    - If the product is already in the cart, increases quantity
    - If the product is new to the cart, adds it
    - Returns the full updated cart

    """
    logger.info(
        f"Adding to cart: user_id={request.user_id}, "
        f"product_id={request.product_id}, quantity={request.quantity}"
    )

    # Validate that the user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate that the product exists
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get or create the user's cart
    cart = _get_or_create_cart(db, request.user_id)

    # Check if this product is already in the cart
    existing_item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.product_id == request.product_id)
        .first()
    )

    if existing_item:
        # Product already in cart — increase quantity
        existing_item.quantity += request.quantity
        logger.info(f"Updated quantity: cart_item_id={existing_item.id}, new_qty={existing_item.quantity}")
    else:
        # New product — add to cart
        new_item = CartItem(
            cart_id=cart.id,
            product_id=request.product_id,
            quantity=request.quantity,
        )
        db.add(new_item)
        logger.info(f"Added new item to cart: product_id={request.product_id}")

    db.commit()
    db.refresh(cart)

    return _build_cart_response(cart, db)


@router.get("/{user_id}", response_model=CartResponse)
def get_cart(
    user_id: int,
    db: Session = Depends(get_db),
) -> CartResponse:
    # Get the user's current cart with all items.

    logger.info(f"Fetching cart for user_id={user_id}")

    # Validate user exists
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    cart = _get_or_create_cart(db, user_id)
    return _build_cart_response(cart, db)


@router.put("/item/{cart_item_id}", response_model=CartResponse)
def update_cart_item(
    cart_item_id: int,
    request: CartUpdateRequest,
    db: Session = Depends(get_db),
) -> CartResponse:

    # Update the quantity of an item in the cart.


    logger.info(f"Updating cart item: cart_item_id={cart_item_id}, quantity={request.quantity}")

    cart_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if cart_item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    cart_item.quantity = request.quantity
    db.commit()

    # Return the full updated cart
    cart = db.query(Cart).filter(Cart.id == cart_item.cart_id).first()
    return _build_cart_response(cart, db)


@router.delete("/item/{cart_item_id}", response_model=CartResponse)
def remove_cart_item(
    cart_item_id: int,
    db: Session = Depends(get_db),
) -> CartResponse:
    # Remove an item from the cart entirely.

    logger.info(f"Removing cart item: cart_item_id={cart_item_id}")

    cart_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if cart_item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Save cart_id before deleting the item (we need it for the response)
    cart_id = cart_item.cart_id

    db.delete(cart_item)
    db.commit()

    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    return _build_cart_response(cart, db)