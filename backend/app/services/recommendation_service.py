"""
Product recommendation service.

Implements two recommendation strategies:
1. Collaborative Filtering (simple item-based): "Users who bought X also bought Y"
2. Random: Baseline for A/B testing against collaborative filtering

"""

import random as rand_module
from collections import Counter

from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.utils.logging import get_logger

logger = get_logger(__name__)


def get_collaborative_filtering_recommendations(
    db: Session,
    user_id: int,
    limit: int = 5,
) -> list[dict]:
    """
    Recommend products using simple item-based collaborative filtering.
    """
    logger.info(f"Generating collaborative filtering recommendations for user_id={user_id}")

    # Step 1: Get products the target user has purchased
    user_orders = db.query(Order).filter(Order.user_id == user_id).all()
    user_order_ids = [order.id for order in user_orders]

    if not user_order_ids:
        # New user with no orders — fall back to popular products
        logger.info(f"User {user_id} has no orders, falling back to popular products")
        return _get_popular_products(db, limit)

    user_product_ids = set(
        item.product_id
        for item in db.query(OrderItem).filter(OrderItem.order_id.in_(user_order_ids)).all()
    )

    if not user_product_ids:
        return _get_popular_products(db, limit)

    logger.info(f"User {user_id} has purchased {len(user_product_ids)} unique products")

    # Step 2: Find similar users (who bought at least one same product)
    # Get order_ids that contain any of the user's products
    similar_order_items = (
        db.query(OrderItem)
        .filter(OrderItem.product_id.in_(user_product_ids))
        .all()
    )
    similar_order_ids = {item.order_id for item in similar_order_items}

    # Get user_ids from those orders (excluding the target user)
    similar_orders = (
        db.query(Order)
        .filter(Order.id.in_(similar_order_ids), Order.user_id != user_id)
        .all()
    )
    similar_user_ids = {order.user_id for order in similar_orders}

    if not similar_user_ids:
        logger.info(f"No similar users found for user {user_id}")
        return _get_popular_products(db, limit)

    logger.info(f"Found {len(similar_user_ids)} similar users")

    # Step 3: Get products those similar users purchased
    similar_user_orders = (
        db.query(Order)
        .filter(Order.user_id.in_(similar_user_ids))
        .all()
    )
    similar_user_order_ids = [order.id for order in similar_user_orders]

    similar_user_items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id.in_(similar_user_order_ids))
        .all()
    )

    # Step 4: Count frequency, excluding products the user already bought
    product_counts = Counter()
    for item in similar_user_items:
        if item.product_id not in user_product_ids:
            product_counts[item.product_id] += 1

    if not product_counts:
        logger.info("Similar users have no new products to recommend")
        return _get_popular_products(db, limit)

    # Step 5: Normalize scores to 0.0-1.0
    max_count = max(product_counts.values())
    recommendations = [
        {"product_id": pid, "score": round(count / max_count, 2)}
        for pid, count in product_counts.most_common(limit)
    ]

    logger.info(f"Generated {len(recommendations)} collaborative filtering recommendations")
    return recommendations


def get_random_recommendations(
    db: Session,
    user_id: int,
    limit: int = 5,
) -> list[dict]:
    """
    Recommend random products (baseline for A/B testing).

    Exclude products the user already purchased to avoid
    recommending things they've already bought.
    """
    logger.info(f"Generating random recommendations for user_id={user_id}")

    # Get products the user already purchased
    user_orders = db.query(Order).filter(Order.user_id == user_id).all()
    user_order_ids = [order.id for order in user_orders]

    purchased_product_ids = set()
    if user_order_ids:
        purchased_items = (
            db.query(OrderItem)
            .filter(OrderItem.order_id.in_(user_order_ids))
            .all()
        )
        purchased_product_ids = {item.product_id for item in purchased_items}

    # Get all products except ones already purchased
    available_products = (
        db.query(Product)
        .filter(~Product.id.in_(purchased_product_ids) if purchased_product_ids else True)
        .all()
    )

    # Randomly sample
    if len(available_products) <= limit:
        selected = available_products
    else:
        selected = rand_module.sample(available_products, limit)

    # Random recommendations get a flat score
    recommendations = [
        {"product_id": p.id, "score": round(rand_module.uniform(0.3, 0.7), 2)}
        for p in selected
    ]

    logger.info(f"Generated {len(recommendations)} random recommendations")
    return recommendations


def _get_popular_products(db: Session, limit: int = 5) -> list[dict]:
    """
    Fallback: Recommend most frequently ordered products.
    """
    logger.info("Falling back to popular products")

    # Count how often each product appears in orders
    order_items = db.query(OrderItem).all()
    product_counts = Counter(item.product_id for item in order_items)

    if not product_counts:
        # No orders at all — just return some products
        products = db.query(Product).limit(limit).all()
        return [{"product_id": p.id, "score": 0.5} for p in products]

    max_count = max(product_counts.values())
    return [
        {"product_id": pid, "score": round(count / max_count, 2)}
        for pid, count in product_counts.most_common(limit)
    ]