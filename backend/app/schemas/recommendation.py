"""
Pydantic schemas for the Recommendations API.
"""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class RecommendedProduct(BaseModel):
    """A product with a relevance score explaining why it was recommended."""
    id: int
    name: str
    category: str | None
    price: Decimal
    score: float  # 0.0 to 1.0, higher = more relevant

    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    """
    List of recommended products for a user.
    """
    user_id: int
    products: list[RecommendedProduct]
    algorithm: str  # "collaborative_filtering" or "random"