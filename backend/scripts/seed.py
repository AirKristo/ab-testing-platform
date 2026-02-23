# Seed script for the A/B Testing Platform.

#Usage:
#    cd backend
#    python -m scripts.seed

import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, Base
from app.models import User, Product

fake = Faker()
Faker.seed(42)
random.seed(42)

PRODUCT_CATEGORIES = {
    "Electronics": {
        "price_range": (19.99, 999.99),
        "items": [
            "Wireless Earbuds", "Bluetooth Speaker", "Phone Case", "USB-C Hub",
            "Portable Charger", "Smart Watch Band", "Webcam", "Mouse Pad",
            "LED Desk Lamp", "Cable Organizer", "Screen Protector", "Phone Stand",
            "Keyboard", "Wireless Mouse", "Laptop Stand", "Ring Light",
            "Power Strip",
        ],
    },
    "Clothing": {
        "price_range": (14.99, 149.99),
        "items": [
            "Cotton T-Shirt", "Hoodie", "Joggers", "Denim Jacket",
            "Running Shorts", "Polo Shirt", "Wool Sweater", "Baseball Cap",
            "Athletic Socks", "Rain Jacket", "Flannel Shirt", "Cargo Pants",
            "Beanie", "Zip-Up Fleece", "Graphic Tee", "Linen Shirt",
            "Chino Shorts",
        ],
    },
    "Home & Kitchen": {
        "price_range": (9.99, 199.99),
        "items": [
            "Coffee Mug", "Cutting Board", "Kitchen Scale", "Water Bottle",
            "Throw Blanket", "Scented Candle", "Plant Pot", "Coasters",
            "Dish Towels", "Spice Rack", "French Press", "Mixing Bowls",
            "Baking Sheet", "Ice Cube Tray", "Oven Mitts", "Utensil Holder",
            "Trivet Set",
        ],
    },
    "Books": {
        "price_range": (7.99, 34.99),
        "items": [
            "Python Cookbook", "Data Science Handbook", "Statistics Fundamentals",
            "Machine Learning Guide", "SQL Deep Dive", "System Design Manual",
            "Clean Code", "Design Patterns", "Algorithms Explained",
            "Bayesian Methods", "A/B Testing Guide", "Causal Inference Intro",
            "Deep Learning Basics", "Product Analytics", "Lean Startup",
            "The Signal and the Noise", "Thinking Fast and Slow",
        ],
    },
    "Sports & Outdoors": {
        "price_range": (12.99, 139.99),
        "items": [
            "Yoga Mat", "Resistance Bands", "Jump Rope", "Foam Roller",
            "Water Bottle Belt", "Workout Gloves", "Tennis Balls",
            "Basketball", "Hiking Socks", "Dry Bag", "Headband",
            "Grip Tape", "Wrist Wraps", "Knee Sleeve", "Duffel Bag",
            "Cooling Towel",
        ],
    },
    "Health & Beauty": {
        "price_range": (5.99, 79.99),
        "items": [
            "Lip Balm", "Sunscreen", "Hand Cream", "Face Wash",
            "Shampoo Bar", "Deodorant", "Vitamin D Supplements",
            "First Aid Kit", "Sleep Mask", "Nail Clippers",
            "Cotton Swabs", "Hair Ties", "Body Lotion", "Eye Drops",
            "Toothbrush Heads", "Floss Picks", "Moisturizer",
        ],
    },
}


def generate_products() -> list[Product]:
    # Generate 100 products across all categories.

    products = []
    product_count = 0

    for category, config in PRODUCT_CATEGORIES.items():
        min_price, max_price = config["price_range"]

        for item_name in config["items"]:
            if product_count >= 100:
                break

            # Generate a realistic price within the category range
            price = round(random.uniform(min_price, max_price), 2)

            product = Product(
                name=item_name,
                category=category,
                price=price,
                description=fake.sentence(nb_words=12),
                # Placeholder image URL, replace with real images later
                image_url=f"https://placehold.co/400x400?text={item_name.replace(' ', '+')}",
            )
            products.append(product)
            product_count += 1

        if product_count >= 100:
            break

    print(f"  Generated {len(products)} products across {len(PRODUCT_CATEGORIES)} categories")
    return products

def generate_users(count: int = 50) -> list[User]:
    # Generate users with realistic, correlated pre-experiment covariates.

    users = []

    # Define user segments with correlated covariate ranges
    user_segments = [
        {
            "name": "new_user",
            "weight": 0.30,  # 30% of users are new
            "days_range": (1, 30),
            "orders_range": (0, 2),
            "spend_range": (0, 50),
        },
        {
            "name": "moderate_user",
            "weight": 0.35,  # 35% are moderate
            "days_range": (31, 180),
            "orders_range": (2, 10),
            "spend_range": (50, 500),
        },
        {
            "name": "established_user",
            "weight": 0.25,  # 25% are established
            "days_range": (181, 365),
            "orders_range": (10, 30),
            "spend_range": (500, 2000),
        },
        {
            "name": "power_user",
            "weight": 0.10,  # 10% are power users
            "days_range": (366, 730),
            "orders_range": (30, 100),
            "spend_range": (2000, 10000),
        },
    ]

    # Build a weighted list of segments to sample from
    segment_choices = []
    for segment in user_segments:
        segment_choices.extend([segment] * int(segment["weight"] * 100))

    for i in range(count):
        # Pick a segment based on weights
        segment = random.choice(segment_choices)

        # Generate correlated covariates within the segment's ranges
        days_since_signup = random.randint(*segment["days_range"])
        order_count = random.randint(*segment["orders_range"])
        historical_spend = round(random.uniform(*segment["spend_range"]), 2)

        user = User(
            email=fake.unique.email(),
            name=fake.name(),
            days_since_signup=days_since_signup,
            order_count=order_count,
            historical_spend=historical_spend,
        )
        users.append(user)

    # Print segment distribution for verification
    print(f"  Generated {len(users)} users")
    return users


def seed_database() -> None:
    # Main seed function — creates all fake data in the database.

    print("=" * 50)
    print("Seeding database...")
    print("=" * 50)

    # Create a database session
    db: Session = SessionLocal()

    try:
        print("\nClearing existing data...")
        db.query(Product).delete()
        db.query(User).delete()
        db.commit()
        print("  Done.")

        # Generate and insert products
        print("\nGenerating products...")
        products = generate_products()
        db.add_all(products)
        db.commit()

        # Generate and insert users
        print("\nGenerating users...")
        users = generate_users(count=50)
        db.add_all(users)
        db.commit()

        # Print summary
        print("\n" + "=" * 50)
        print("Seed complete!")
        print(f"  Products: {db.query(Product).count()}")
        print(f"  Users:    {db.query(User).count()}")
        print("=" * 50)

    except Exception as e:
        print(f"\nError seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()