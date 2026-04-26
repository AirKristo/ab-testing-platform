"""
Tests for Recommendations API.
"""

from app.models.product import Product
from app.models.user import User


def _setup_recommendation_data(db_session):
    """
    Create users, products, and purchase history for recommendation tests.
    """
    users = [
        User(email="user1@test.com", name="User One"),
        User(email="user2@test.com", name="User Two"),
        User(email="user3@test.com", name="User Three"),
    ]
    db_session.add_all(users)
    db_session.commit()

    products = [
        Product(name="Product A", category="Electronics", price=10.00),
        Product(name="Product B", category="Electronics", price=20.00),
        Product(name="Product C", category="Electronics", price=30.00),
        Product(name="Product D", category="Clothing", price=40.00),
        Product(name="Product E", category="Clothing", price=50.00),
    ]
    db_session.add_all(products)
    db_session.commit()

    return users, products


def _checkout_products(client, user_id: int, product_ids: list[int]) -> None:
    """Helper: Add products to cart and checkout."""
    for pid in product_ids:
        client.post("/cart/add", json={
            "user_id": user_id,
            "product_id": pid,
            "quantity": 1,
        })
    client.post("/orders/checkout", json={"user_id": user_id})


class TestCollaborativeFiltering:
    """Tests for collaborative filtering recommendations."""

    def test_recommends_from_similar_users(self, client, db_session):
        """
        User 1 bought A, B. User 2 bought A, B, C.
        User 1 should be recommended C (from similar user 2).
        """
        users, products = _setup_recommendation_data(db_session)

        # User 1 buys A and B
        _checkout_products(client, users[0].id, [products[0].id, products[1].id])

        # User 2 buys A, B, and C
        _checkout_products(client, users[1].id, [products[0].id, products[1].id, products[2].id])

        # Get recommendations for user 1
        response = client.get(
            f"/recommendations/{users[0].id}?algorithm=collaborative_filtering"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "collaborative_filtering"
        assert len(data["products"]) > 0

        # Product C should be recommended (User 2 bought it, User 1 hasn't)
        recommended_names = [p["name"] for p in data["products"]]
        assert "Product C" in recommended_names

    def test_new_user_gets_fallback(self, client, db_session):
        """User with no purchase history still gets recommendations (fallback)."""
        users, products = _setup_recommendation_data(db_session)

        response = client.get(
            f"/recommendations/{users[0].id}?algorithm=collaborative_filtering"
        )

        assert response.status_code == 200
        data = response.json()
        # Should get some recommendations even without history
        assert len(data["products"]) > 0


class TestRandomRecommendations:
    """Tests for random baseline recommendations."""

    def test_returns_random_products(self, client, db_session):
        """Random algorithm returns products with scores."""
        users, products = _setup_recommendation_data(db_session)

        response = client.get(
            f"/recommendations/{users[0].id}?algorithm=random"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "random"
        assert len(data["products"]) > 0

        # Each product should have a score
        for product in data["products"]:
            assert 0.0 <= product["score"] <= 1.0

    def test_excludes_purchased_products(self, client, db_session):
        """Random recommendations exclude products the user already bought."""
        users, products = _setup_recommendation_data(db_session)

        # User 1 buys products A and B
        _checkout_products(client, users[0].id, [products[0].id, products[1].id])

        response = client.get(
            f"/recommendations/{users[0].id}?algorithm=random&limit=20"
        )

        data = response.json()
        recommended_names = [p["name"] for p in data["products"]]
        assert "Product A" not in recommended_names
        assert "Product B" not in recommended_names


class TestRecommendationsEdgeCases:
    """Edge cases and error handling."""

    def test_invalid_user(self, client, db_session):
        """Nonexistent user returns 404."""
        response = client.get("/recommendations/9999")
        assert response.status_code == 404

    def test_invalid_algorithm(self, client, db_session):
        """Invalid algorithm name returns 400."""
        users, _ = _setup_recommendation_data(db_session)

        response = client.get(
            f"/recommendations/{users[0].id}?algorithm=invalid_algo"
        )
        assert response.status_code == 400

    def test_limit_parameter(self, client, db_session):
        """Limit parameter controls number of recommendations."""
        users, _ = _setup_recommendation_data(db_session)

        response = client.get(
            f"/recommendations/{users[0].id}?algorithm=random&limit=2"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) <= 2