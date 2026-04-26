"""
Tests for Checkout and Order API endpoints.

Tests the full purchase lifecycle:
1. Add items to cart
2. Checkout (cart → order)
3. Verify order details
4. Verify cart is cleared
5. Verify user covariates updated (for CUPED)

Edge cases:
- Checkout with empty cart
- Checkout with nonexistent user
- Multiple orders for same user
"""

from decimal import Decimal

from app.models.product import Product
from app.models.user import User


def _create_test_user(db_session) -> User:
    # Create a user with known CUPED covariates.
    user = User(
        email="shopper@test.com",
        name="Test Shopper",
        historical_spend=100.00,
        order_count=3,
        days_since_signup=60,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _create_test_products(db_session) -> list[Product]:
    # Create products with known prices.
    products = [
        Product(name="Alpha Widget", category="Electronics", price=25.00),
        Product(name="Beta Widget", category="Electronics", price=50.00),
        Product(name="Gamma Widget", category="Clothing", price=30.00),
    ]
    db_session.add_all(products)
    db_session.commit()
    return products


def _add_items_to_cart(client, user_id: int, items: list[dict]) -> None:
    # Add multiple items to a user's cart.
    for item in items:
        client.post("/cart/add", json={
            "user_id": user_id,
            "product_id": item["product_id"],
            "quantity": item["quantity"],
        })


class TestCheckout:
    # Tests for POST /orders/checkout

    def test_successful_checkout(self, client, db_session):
        """
        Full checkout flow:
        - Cart with 2 items → order created
        - Correct total, correct item prices
        """
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        # Add items to cart: 2x Alpha ($25) + 1x Beta ($50)
        _add_items_to_cart(client, user.id, [
            {"product_id": products[0].id, "quantity": 2},
            {"product_id": products[1].id, "quantity": 1},
        ])

        # Checkout
        response = client.post("/orders/checkout", json={"user_id": user.id})

        assert response.status_code == 200
        data = response.json()
        assert float(data["total_amount"]) == 100.00  # (2*$25) + (1*$50)
        assert data["item_count"] == 2
        assert data["user_id"] == user.id

        # Verify individual items
        items_by_name = {item["product_name"]: item for item in data["items"]}
        assert float(items_by_name["Alpha Widget"]["price_at_purchase"]) == 25.00
        assert items_by_name["Alpha Widget"]["quantity"] == 2
        assert float(items_by_name["Beta Widget"]["price_at_purchase"]) == 50.00

    def test_checkout_clears_cart(self, client, db_session):
        # After checkout, the user's cart should be empty.
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        _add_items_to_cart(client, user.id, [
            {"product_id": products[0].id, "quantity": 1},
        ])

        # Checkout
        client.post("/orders/checkout", json={"user_id": user.id})

        # Verify cart is empty
        cart_response = client.get(f"/cart/{user.id}")
        cart_data = cart_response.json()
        assert cart_data["item_count"] == 0
        assert cart_data["items"] == []

    def test_checkout_updates_cuped_covariates(self, client, db_session):
        """
        Checkout should update user's historical_spend and order_count.
        """
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        # User starts with historical_spend=100, order_count=3
        _add_items_to_cart(client, user.id, [
            {"product_id": products[0].id, "quantity": 2},  # 2 * $25 = $50
        ])

        client.post("/orders/checkout", json={"user_id": user.id})

        # Refresh user from database
        db_session.refresh(user)
        assert user.order_count == 4  # Was 3, now 4
        assert float(user.historical_spend) == 150.00  # Was $100, added $50

    def test_checkout_empty_cart(self, client, db_session):
        """Checkout with empty cart returns 400 error."""
        user = _create_test_user(db_session)

        response = client.post("/orders/checkout", json={"user_id": user.id})

        assert response.status_code == 400
        assert response.json()["detail"] == "Cart is empty"

    def test_checkout_nonexistent_user(self, client, db_session):
        """Checkout with nonexistent user returns 404."""
        response = client.post("/orders/checkout", json={"user_id": 9999})

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_multiple_checkouts(self, client, db_session):
        """A user can checkout multiple times, creating separate orders."""
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        # First order
        _add_items_to_cart(client, user.id, [
            {"product_id": products[0].id, "quantity": 1},
        ])
        first_order = client.post("/orders/checkout", json={"user_id": user.id})

        # Second order
        _add_items_to_cart(client, user.id, [
            {"product_id": products[1].id, "quantity": 2},
        ])
        second_order = client.post("/orders/checkout", json={"user_id": user.id})

        assert first_order.status_code == 200
        assert second_order.status_code == 200

        # Orders should have different IDs
        assert first_order.json()["id"] != second_order.json()["id"]

        # Covariates should reflect both orders
        db_session.refresh(user)
        assert user.order_count == 5  # Was 3, +2 checkouts
        assert float(user.historical_spend) == 225.00  # 100 + 25 + 100

    def test_checkout_snapshots_price(self, client, db_session):
        """
        price_at_purchase captures the price AT checkout time.
        """
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        _add_items_to_cart(client, user.id, [
            {"product_id": products[0].id, "quantity": 1},  # $25
        ])

        response = client.post("/orders/checkout", json={"user_id": user.id})

        data = response.json()
        assert float(data["items"][0]["price_at_purchase"]) == 25.00
        assert float(data["total_amount"]) == 25.00


class TestGetUserOrders:
    """Tests for GET /orders/user/{user_id}"""

    def test_get_user_orders(self, client, db_session):
        """Returns all orders for a user."""
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        # Create two orders
        _add_items_to_cart(client, user.id, [
            {"product_id": products[0].id, "quantity": 1},
        ])
        client.post("/orders/checkout", json={"user_id": user.id})

        _add_items_to_cart(client, user.id, [
            {"product_id": products[1].id, "quantity": 1},
        ])
        client.post("/orders/checkout", json={"user_id": user.id})

        # Fetch orders
        response = client.get(f"/orders/user/{user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["orders"]) == 2

    def test_get_user_orders_empty(self, client, db_session):
        """User with no orders gets empty list (not 404)."""
        user = _create_test_user(db_session)

        response = client.get(f"/orders/user/{user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["orders"] == []

    def test_get_user_orders_invalid_user(self, client, db_session):
        """Nonexistent user returns 404."""
        response = client.get("/orders/user/9999")

        assert response.status_code == 404


class TestGetOrder:
    """Tests for GET /orders/{order_id}"""

    def test_get_order_by_id(self, client, db_session):
        """Returns correct order details."""
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        _add_items_to_cart(client, user.id, [
            {"product_id": products[0].id, "quantity": 3},
        ])
        checkout_response = client.post("/orders/checkout", json={"user_id": user.id})
        order_id = checkout_response.json()["id"]

        # Fetch by ID
        response = client.get(f"/orders/{order_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order_id
        assert float(data["total_amount"]) == 75.00
        assert data["item_count"] == 1
        assert data["items"][0]["quantity"] == 3

    def test_get_order_not_found(self, client, db_session):
        """Nonexistent order returns 404."""
        response = client.get("/orders/9999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found"