import random
import json
from datetime import datetime, timedelta
from app import db
from models import User, Product, Transaction
from recommendation import generate_recommendations


def init_db():
    """Initialize database with default data if needed"""
    from werkzeug.security import generate_password_hash
    from models import ApiKey
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Create default admin user if no users exist
    if User.query.count() == 0:
        try:
            # Create admin user
            admin_user = User(
                username="admin",
                email="admin@example.com",
                password_hash=generate_password_hash("adminpassword"),
                company_name="BuyBuddy Admin"
            )
            db.session.add(admin_user)
            db.session.flush()  # Get the ID without committing yet
            
            # Create API key for admin
            api_key = ApiKey(
                key="admin-api-key-" + str(admin_user.id),
                name="Default Admin API Key",
                user_id=admin_user.id,
                config={
                    'min_confidence': 0.1,
                    'min_support': 0.01,
                    'max_recommendations': 5
                }
            )
            db.session.add(api_key)
            db.session.commit()
            
            logger.info(f"Created default admin user: username=admin, password=adminpassword")
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            db.session.rollback()
    
    # Create sample products if no products exist
    if Product.query.count() == 0:
        try:
            # Sample grocery products
            sample_products = [
                {"product_id": "P001", "name": "Milk", "category": "Dairy"},
                {"product_id": "P002", "name": "Bread", "category": "Bakery"},
                {"product_id": "P003", "name": "Eggs", "category": "Dairy"},
                {"product_id": "P004", "name": "Cheese", "category": "Dairy"},
                {"product_id": "P005", "name": "Butter", "category": "Dairy"},
                {"product_id": "P006", "name": "Apples", "category": "Produce"},
                {"product_id": "P007", "name": "Bananas", "category": "Produce"},
                {"product_id": "P008", "name": "Chicken", "category": "Meat"},
                {"product_id": "P009", "name": "Beef", "category": "Meat"},
                {"product_id": "P010", "name": "Rice", "category": "Grains"},
                {"product_id": "P011", "name": "Pasta", "category": "Grains"},
                {"product_id": "P012", "name": "Tomatoes", "category": "Produce"},
                {"product_id": "P013", "name": "Onions", "category": "Produce"},
                {"product_id": "P014", "name": "Potatoes", "category": "Produce"},
                {"product_id": "P015", "name": "Cereal", "category": "Breakfast"}
            ]
            
            # Get admin user for product creation
            admin_user = User.query.filter_by(username="admin").first()
            user_id = admin_user.id if admin_user else None
            
            # Add products to database
            for product_data in sample_products:
                product = Product(
                    product_id=product_data["product_id"],
                    name=product_data["name"],
                    category=product_data["category"],
                    created_by=user_id
                )
                db.session.add(product)
            
            db.session.commit()
            logger.info(f"Created {len(sample_products)} sample products")
            
            # Generate sample transactions if we have an admin user
            if admin_user:
                generate_sample_transactions(admin_user.id, num_transactions=50)
                logger.info("Generated sample transactions and recommendations")
        except Exception as e:
            logger.error(f"Error creating sample products: {e}")
            db.session.rollback()


def generate_sample_transactions(user_id, num_transactions=100):
    """
    Generate sample transactions for demo purposes
    
    Args:
        user_id (int): User ID to associate transactions with
        num_transactions (int): Number of transactions to generate
    """
    # Get all products
    products = Product.query.all()
    product_ids = [p.product_id for p in products]
    
    if not products:
        return
    
    # Generate random transactions
    transactions = []
    
    # Common product combinations for realistic data
    common_combinations = [
        # Breakfast items
        ['P001', 'P002', 'P003'],  # Milk, Bread, Eggs
        ['P015', 'P001'],          # Cereal, Milk
        
        # Meal preparation
        ['P008', 'P014', 'P013'],  # Chicken, Potato, Onion
        ['P011', 'P012', 'P013'],  # Pasta, Tomato, Onion
        ['P010', 'P009'],          # Rice, Beef
        
        # Snacks/fruits
        ['P006', 'P007'],          # Apple, Banana
        
        # Dairy combinations
        ['P001', 'P004', 'P005'],  # Milk, Cheese, Butter
    ]
    
    # Generate transactions
    for i in range(num_transactions):
        # Decide whether to use a common combination or random products
        if random.random() < 0.7:  # 70% chance of using common combinations
            # Pick a random common combination
            base_products = random.choice(common_combinations)
            
            # Add some randomness by potentially adding more products
            if random.random() < 0.3:  # 30% chance to add more products
                additional = random.sample(product_ids, k=random.randint(1, 2))
                products_in_tx = list(set(base_products + additional))
            else:
                products_in_tx = base_products
        else:
            # Generate a random transaction
            num_products = random.randint(1, 5)
            products_in_tx = random.sample(product_ids, k=num_products)
        
        # Create transaction
        tx_date = datetime.now() - timedelta(days=random.randint(0, 30))
        tx = Transaction(
            transaction_id=f'TX{i+1:06d}',
            user_id=user_id,
            timestamp=tx_date,
            products=products_in_tx,
            transaction_metadata={'source': 'demo', 'generated': True}
        )
        
        db.session.add(tx)
    
    db.session.commit()
    
    # Generate recommendations from these transactions
    generate_recommendations(user_id, min_support=0.01, min_confidence=0.05)


def format_api_response(data, status_code=200):
    """Format API response"""
    return json.dumps(data), status_code, {'Content-Type': 'application/json'}


def parse_product_ids(product_ids_str):
    """Parse comma-separated product IDs"""
    if not product_ids_str:
        return []
    
    return [pid.strip() for pid in product_ids_str.split(',') if pid.strip()]
