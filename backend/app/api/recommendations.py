"""
Recommendations API endpoint.

"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse, RecommendedProduct
from app.services.recommendation_service import (
    get_collaborative_filtering_recommendations,
    get_random_recommendations,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
)


@router.get("/{user_id}", response_model=RecommendationResponse)
def get_recommendations(
    user_id: int,
    algorithm: str = Query(
        "collaborative_filtering",
        description="Algorithm to use: 'collaborative_filtering' or 'random'",
    ),
    limit: int = Query(5, ge=1, le=20, description="Number of recommendations"),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """
    Get product recommendations for a user.
    """
    logger.info(
        f"Recommendations requested: user_id={user_id}, "
        f"algorithm={algorithm}, limit={limit}"
    )

    # Validate user exists
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Get recommendations from the appropriate algorithm
    if algorithm == "collaborative_filtering":
        raw_recommendations = get_collaborative_filtering_recommendations(db, user_id, limit)
    elif algorithm == "random":
        raw_recommendations = get_random_recommendations(db, user_id, limit)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown algorithm: '{algorithm}'. Use 'collaborative_filtering' or 'random'.",
        )

    # Enrich with full product details
    products = []
    for rec in raw_recommendations:
        product = db.query(Product).filter(Product.id == rec["product_id"]).first()
        if product:
            products.append(RecommendedProduct(
                id=product.id,
                name=product.name,
                category=product.category,
                price=product.price,
                score=rec["score"],
            ))

    logger.info(f"Returning {len(products)} recommendations ({algorithm})")

    return RecommendationResponse(
        user_id=user_id,
        products=products,
        algorithm=algorithm,
    )