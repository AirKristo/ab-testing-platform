# Database connection and model tests.

from app.models import User, Product


class TestDatabaseConnection:
    """Test that we can connect to the test database and perform basic operations."""

    def test_create_user(self, db_session):
        """
        Verify we can create a user and read it back.
        Tests: database connection, User model, session commit/query.
        """
        user = User(
            email="test@example.com",
            name="Test User",
            historical_spend=150.00,
            days_since_signup=30,
            order_count=5,
        )
        db_session.add(user)
        db_session.commit()

        # Query it back
        saved_user = db_session.query(User).filter_by(email="test@example.com").first()

        assert saved_user is not None
        assert saved_user.name == "Test User"
        assert float(saved_user.historical_spend) == 150.00
        assert saved_user.days_since_signup == 30
        assert saved_user.order_count == 5

    def test_create_product(self, db_session):
        """
        Verify we can create a product and read it back.
        Tests: Product model, decimal price handling.
        """
        product = Product(
            name="Test Widget",
            category="Electronics",
            price=29.99,
            description="A test product",
        )
        db_session.add(product)
        db_session.commit()

        saved_product = db_session.query(Product).filter_by(name="Test Widget").first()

        assert saved_product is not None
        assert saved_product.category == "Electronics"
        assert float(saved_product.price) == 29.99

    def test_user_email_unique_constraint(self, db_session):
        from sqlalchemy.exc import IntegrityError
        import pytest

        user1 = User(email="dupe@example.com", name="User 1")
        db_session.add(user1)
        db_session.commit()

        user2 = User(email="dupe@example.com", name="User 2")
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_check(self, client):
        """
        Verify the health endpoint returns correct response.
        Tests: FastAPI app is running, endpoint routing works.
        """
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "A/B Testing Platform"