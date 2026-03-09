"""
Product API endpoints.

"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.schemas.product import ProductResponse, ProductList
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/products",
    tags=["products"],  # Groups endpoints in the /docs UI
)


@router.get("", response_model=ProductList)
def get_products(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    category: str | None = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
) -> ProductList:
    # Get a paginated list of products, optionally filtered by category.

    logger.info(f"Fetching products: page={page}, per_page={per_page}, category={category}")

    # Start building the query
    query = db.query(Product)

    # Apply category filter if provided
    if category:
        query = query.filter(Product.category == category)

    # Get total count BEFORE pagination (for the frontend to know total pages)
    total = query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    products = query.order_by(Product.id).offset(offset).limit(per_page).all()

    logger.info(f"Returning {len(products)} products (total: {total})")

    return ProductList(
        products=products,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/search", response_model=ProductList)
def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ProductList:
    # Search products by name or description.
    logger.info(f"Searching products: q='{q}'")

    query = db.query(Product).filter(
        # Search in both name and description
        (Product.name.ilike(f"%{q}%")) | (Product.description.ilike(f"%{q}%"))
    )

    total = query.count()
    offset = (page - 1) * per_page
    products = query.order_by(Product.id).offset(offset).limit(per_page).all()

    logger.info(f"Search returned {len(products)} results for '{q}'")

    return ProductList(
        products=products,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
) -> ProductResponse:
    # Get a single product by ID.


    logger.info(f"Fetching product: id={product_id}")

    product = db.query(Product).filter(Product.id == product_id).first()

    if product is None:
        logger.warning(f"Product not found: id={product_id}")
        raise HTTPException(status_code=404, detail="Product not found")

    return product