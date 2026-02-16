"""
Database connection setup for the A/B Testing Platform.

1. create_engine() - Creates a connection pool to PostgreSQL
2. SessionLocal - Factory that creates database sessions
3. get_db() - FastAPI dependency that manages session lifecycle
   (opens session, yields it, closes when request is done)

"""

from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from sqlalchemy import create_engine
from typing import Generator

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

# SessionLocal is a factory - each call creates a new database session
# WHY autocommit=False: We want explicit control over when changes are saved
# WHY autoflush=False: Prevents unexpected writes before we're ready

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    """
        FastAPI dependency that provides a database session.

        Usage in FastAPI endpoints:
            @app.get("/products")
            def get_products(db: Session = Depends(get_db)):
                return db.query(Product).all()
        """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()