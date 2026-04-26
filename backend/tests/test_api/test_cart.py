"""
Tests for Cart API endpoints.

Tests the full cart lifecycle:
1. Add item to cart
2. View cart
3. Add same item again (quantity increases)
4. Update quantity
5. Remove item

Each test is independent — creates its own users and products.
"""

from app.models.product import Product
from app.models.user import User


def _create_test_user(db_session) -> User:
    # Helper: Create a test user.
    user = User(email="cartuser@test.com", name="Cart Tester")
    db_session.add(user)
    db_session.commit()
    return user


def _create_test_products(db_session) -> list[Product]:
    # Helper: Create test products for cart operations.
    products = [
        Product(name="Widget A", category="Electronics", price=25.00),
        Product(name="Widget B", category="Electronics", price=50.00),
    ]
    db_session.add_all(products)
    db_session.commit()
    return products


class TestAddToCart:
    # Tests for POST /cart/add

    def test_add_item_to_empty_cart(self, client, db_session):
        # Adding an item creates a cart and adds the item.
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        response = client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[0].id,
            "quantity": 2,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user.id
        assert data["item_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["product_name"] == "Widget A"
        assert data["items"][0]["quantity"] == 2
        assert float(data["items"][0]["item_total"]) == 50.00
        assert float(data["cart_total"]) == 50.00

    def test_add_same_item_increases_quantity(self, client, db_session):
        # Adding the same product twice increases quantity (not duplicate entry).
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        # Add 2 of Widget A
        client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[0].id,
            "quantity": 2,
        })

        # Add 3 more of Widget A
        response = client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[0].id,
            "quantity": 3,
        })

        data = response.json()
        assert data["item_count"] == 1  # Still one line item
        assert data["items"][0]["quantity"] == 5  # 2 + 3
        assert float(data["cart_total"]) == 125.00  # 5 * $25

    def test_add_multiple_products(self, client, db_session):
        # Adding different products creates separate line items.
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[0].id,
            "quantity": 1,
        })

        response = client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[1].id,
            "quantity": 2,
        })

        data = response.json()
        assert data["item_count"] == 2
        assert float(data["cart_total"]) == 125.00  # (1*$25) + (2*$50)

    def test_add_to_cart_invalid_user(self, client, db_session):
        # Adding to cart with nonexistent user returns 404.
        products = _create_test_products(db_session)

        response = client.post("/cart/add", json={
            "user_id": 9999,
            "product_id": products[0].id,
            "quantity": 1,
        })

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_add_to_cart_invalid_product(self, client, db_session):
        # Adding nonexistent product to cart returns 404.
        user = _create_test_user(db_session)

        response = client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": 9999,
            "quantity": 1,
        })

        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"


class TestGetCart:
    # Tests for GET /cart/{user_id}

    def test_get_empty_cart(self, client, db_session):
        # New user gets an empty cart (not 404).
        user = _create_test_user(db_session)

        response = client.get(f"/cart/{user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["item_count"] == 0
        assert float(data["cart_total"]) == 0

    def test_get_cart_with_items(self, client, db_session):
        # Returns cart with correct items and totals.
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        # Add items first
        client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[0].id,
            "quantity": 3,
        })

        response = client.get(f"/cart/{user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 1
        assert data["items"][0]["quantity"] == 3
        assert float(data["cart_total"]) == 75.00

    def test_get_cart_invalid_user(self, client, db_session):
        # Getting cart for nonexistent user returns 404.
        response = client.get("/cart/9999")

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"


class TestUpdateCartItem:
    # Tests for PUT /cart/item/{cart_item_id}

    def test_update_item_quantity(self, client, db_session):
        # Updating quantity changes the item and recalculates total.
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        # Add item with quantity 1
        add_response = client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[0].id,
            "quantity": 1,
        })
        cart_item_id = add_response.json()["items"][0]["id"]

        # Update to quantity 5
        response = client.put(f"/cart/item/{cart_item_id}", json={
            "quantity": 5,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["quantity"] == 5
        assert float(data["cart_total"]) == 125.00  # 5 * $25

    def test_update_nonexistent_item(self, client, db_session):
        # Updating nonexistent cart item returns 404.
        response = client.put("/cart/item/9999", json={"quantity": 3})

        assert response.status_code == 404
        assert response.json()["detail"] == "Cart item not found"


class TestRemoveCartItem:
    # Tests for DELETE /cart/item/{cart_item_id}

    def test_remove_item(self, client, db_session):
        # Removing an item returns updated cart without that item.
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        # Add two products
        client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[0].id,
            "quantity": 1,
        })
        add_response = client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[1].id,
            "quantity": 1,
        })

        # Remove the first item
        items = add_response.json()["items"]
        first_item_id = items[0]["id"]

        response = client.delete(f"/cart/item/{first_item_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 1
        assert float(data["cart_total"]) == 50.00  # Only Widget B remains

    def test_remove_last_item(self, client, db_session):
        # Removing the last item leaves an empty cart (not deleted).
        user = _create_test_user(db_session)
        products = _create_test_products(db_session)

        add_response = client.post("/cart/add", json={
            "user_id": user.id,
            "product_id": products[0].id,
            "quantity": 1,
        })
        cart_item_id = add_response.json()["items"][0]["id"]

        response = client.delete(f"/cart/item/{cart_item_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 0
        assert data["items"] == []
        assert float(data["cart_total"]) == 0

    def test_remove_nonexistent_item(self, client, db_session):
        # Removing nonexistent cart item returns 404.
        response = client.delete("/cart/item/9999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Cart item not found"