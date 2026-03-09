# Tests for Product API endpoints.

# Validates that the API contract matches what the frontend expects

# Each test creates its own data (via db_session fixture)
# Tests are independent — order doesn't matter


from app.models.product import Product


def _create_sample_products(db_session) -> list[Product]:
    # Helper: Insert sample products for testing.

    products = [
        Product(name="Wireless Earbuds", category="Electronics", price=49.99,
                description="High-quality wireless earbuds with noise cancellation"),
        Product(name="Bluetooth Speaker", category="Electronics", price=79.99,
                description="Portable bluetooth speaker with deep bass"),
        Product(name="Cotton T-Shirt", category="Clothing", price=19.99,
                description="Comfortable cotton t-shirt"),
        Product(name="Python Cookbook", category="Books", price=34.99,
                description="Advanced Python programming recipes"),
        Product(name="Yoga Mat", category="Sports", price=24.99,
                description="Non-slip yoga mat for home workouts"),
    ]
    db_session.add_all(products)
    db_session.commit()
    return products


class TestGetProducts:
    """Tests for GET /products endpoint."""

    def test_get_products_returns_list(self, client, db_session):
        """Basic test: returns products in expected format."""
        _create_sample_products(db_session)

        response = client.get("/products")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert len(data["products"]) == 5

    def test_get_products_empty_database(self, client, db_session):
        """Returns empty list when no products exist (not an error)."""
        response = client.get("/products")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["products"] == []

    def test_get_products_pagination(self, client, db_session):
        """Verify pagination returns correct subset."""
        _create_sample_products(db_session)

        # Request page 1 with 2 items per page
        response = client.get("/products?page=1&per_page=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) == 2
        assert data["total"] == 5  # Total is still 5, we just get 2 per page
        assert data["page"] == 1
        assert data["per_page"] == 2

    def test_get_products_pagination_page_2(self, client, db_session):
        """Verify page 2 returns the next set of products."""
        _create_sample_products(db_session)

        response = client.get("/products?page=2&per_page=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) == 2
        assert data["page"] == 2

    def test_get_products_filter_by_category(self, client, db_session):
        """Verify category filter returns only matching products."""
        _create_sample_products(db_session)

        response = client.get("/products?category=Electronics")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(p["category"] == "Electronics" for p in data["products"])

    def test_get_products_filter_nonexistent_category(self, client, db_session):
        """Filtering by nonexistent category returns empty list (not 404)."""
        _create_sample_products(db_session)

        response = client.get("/products?category=Nonexistent")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestGetProduct:
    """Tests for GET /products/{id} endpoint."""

    def test_get_product_by_id(self, client, db_session):
        """Returns correct product for valid ID."""
        products = _create_sample_products(db_session)
        product_id = products[0].id

        response = client.get(f"/products/{product_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Wireless Earbuds"
        assert data["category"] == "Electronics"
        assert float(data["price"]) == 49.99

    def test_get_product_not_found(self, client, db_session):
        """Returns 404 for nonexistent product ID."""
        response = client.get("/products/9999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"


class TestSearchProducts:
    """Tests for GET /products/search endpoint."""

    def test_search_by_name(self, client, db_session):
        """Search matches product names (case-insensitive)."""
        _create_sample_products(db_session)

        response = client.get("/products/search?q=earbuds")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["products"][0]["name"] == "Wireless Earbuds"

    def test_search_by_description(self, client, db_session):
        """Search also matches product descriptions."""
        _create_sample_products(db_session)

        # "bass" appears only in the Bluetooth Speaker description
        response = client.get("/products/search?q=bass")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["products"][0]["name"] == "Bluetooth Speaker"

    def test_search_case_insensitive(self, client, db_session):
        """Search is case-insensitive (ILIKE)."""
        _create_sample_products(db_session)

        response = client.get("/products/search?q=PYTHON")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_search_no_results(self, client, db_session):
        """Returns empty list for no matches (not 404)."""
        _create_sample_products(db_session)

        response = client.get("/products/search?q=xyznotfound")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_search_requires_query(self, client, db_session):
        """Search without query parameter returns 422 validation error."""
        response = client.get("/products/search")

        assert response.status_code == 422