"""
FastAPI application entry point for the A/B Testing Platform.

"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logging import setup_logging, get_logger
from app.api.products import router as products_router
from app.api.cart import router as cart_router
from app.api.orders import router as orders_router
from app.api.recommendations import router as recommendations_router
from app.api.experiments import router as experiments_router

settings = get_settings()
setup_logging(level="DEBUG" if settings.DEBUG else "INFO")
logger = get_logger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade A/B testing platform with advanced statistical methods",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"Starting {settings.APP_NAME} v0.1.0")

# ---- Register API Routers ----
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(recommendations_router)
app.include_router(experiments_router)

@app.get("/health")
def health_check() -> dict:
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "0.1.0",
    }

