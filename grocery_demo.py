"""
Grocery Recommendation Demo

This script demonstrates the advanced recommendation algorithm with real grocery data.
It loads real grocery data, generates recommendations, and provides visualizations
of the recommendation effectiveness.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import random
from datetime import datetime
from app import app, db
from models import User, Product, Transaction, ProductRecommendation
from data_loader import load_grocery_data_into_db
from recommendation import generate_recommendations, get_recommendations
from utils import generate_sample_transactions
import matplotlib.pyplot as plt
import seaborn as sns

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_demo_account():
    """
    Create a demo account for the grocery recommendation demo
    
    Returns:
        User: The demo user
    """
    username = "grocery_demo"
    demo_user = User.query.filter_by(username=username).first()
    
    if not demo_user:
        logger.info("Creating demo user account")
        from werkzeug.security import generate_password_hash
        demo_user = User(
            username=username,
            email="demo@buybuddy.example",
            password_hash=generate_password_hash("demo_password"),
            company_name="Grocery Demo Store"
        )
        db.session.add(demo_user)
        db.session.commit()
    
    return demo_user


def load_grocery_data(user_id):
    """
    Load grocery data for the demo
    
    Args:
        user_id (int): User ID to associate data with
        
    Returns:
        dict: Statistics about the loaded data
    """
    logger.info("Loading grocery data into database")
    result = load_grocery_data_into_db(user_id)
    logger.info(f"Loaded grocery data: {result}")
    return result


def generate_demo_recommendations(user_id):
    """
    Generate recommendations for the grocery demo
    
    Args:
        user_id (int): User ID to generate recommendations for
        
    Returns:
        dict: Statistics about the generated recommendations
    """
    logger.info("Generating recommendations for grocery demo")
    result = generate_recommendations(user_id, min_support=0.01, min_confidence=0.05)
    logger.info(f"Generated recommendations: {result}")
    return result


def create_sample_baskets(num_baskets=5):
    """
    Create sample grocery baskets for recommendation demo
    
    Args:
        num_baskets (int): Number of sample baskets to create
        
    Returns:
        list: List of sample baskets, each a list of product IDs
    """
    # Get some popular grocery items
    popular_items = (
        Product.query
        .filter(Product.category.in_(['Dairy', 'Produce', 'Bakery', 'Beverages', 'Snacks']))
        .order_by(db.func.random())
        .limit(num_baskets * 3)
        .all()
    )
    
    if not popular_items:
        logger.warning("No products found for sample baskets")
        return []
    
    # Create baskets with 2-4 items each
    baskets = []
    items_pool = popular_items.copy()
    
    for i in range(num_baskets):
        basket_size = random.randint(2, 4)
        # Ensure we don't run out of items
        basket_size = min(basket_size, len(items_pool))
        
        # Randomly select items for this basket
        basket_items = random.sample(items_pool, basket_size)
        # Remove selected items from the pool to ensure diversity
        for item in basket_items:
            if item in items_pool:
                items_pool.remove(item)
        
        basket = [item.product_id for item in basket_items]
        baskets.append(basket)
    
    return baskets


def get_basket_recommendations(basket, limit=5):
    """
    Get recommendations for a basket of products
    
    Args:
        basket (list): List of product IDs in the basket
        limit (int): Maximum number of recommendations to return
        
    Returns:
        list: List of recommended products
    """
    logger.info(f"Getting recommendations for basket with {len(basket)} items")
    recommendations = get_recommendations(basket, limit=limit, min_confidence=0.05)
    
    # Extract unique recommended products
    recommended_products = []
    for rec in recommendations:
        for prod in rec.get('recommended_products', []):
            if prod.get('product_id') not in recommended_products:
                recommended_products.append(prod)
    
    logger.info(f"Got {len(recommended_products)} unique recommended products")
    return recommended_products


def print_basket_with_recommendations(basket, recommendations_limit=5):
    """
    Print a basket with its recommendations in a readable format
    
    Args:
        basket (list): List of product IDs in the basket
        recommendations_limit (int): Maximum number of recommendations to display
    """
    basket_products = Product.query.filter(Product.product_id.in_(basket)).all()
    product_map = {p.product_id: p for p in basket_products}
    
    print("\n" + "="*80)
    print("GROCERY BASKET:")
    print("-"*80)
    
    for prod_id in basket:
        if prod_id in product_map:
            product = product_map[prod_id]
            print(f"• {product.name} ({product.category})")
    
    print("\nRECOMMENDED ITEMS:")
    print("-"*80)
    
    recommendations = get_recommendations(basket, limit=recommendations_limit, min_confidence=0.05)
    
    if not recommendations:
        print("No recommendations found for this basket.")
        return
    
    # Process all recommendations
    all_recommended_products = []
    for rec in recommendations:
        source_product_id = rec.get('product_id')
        source_product = Product.query.filter_by(product_id=source_product_id).first()
        source_name = source_product.name if source_product else "Unknown Product"
        
        for prod in rec.get('recommended_products', []):
            prod_id = prod.get('product_id')
            if prod_id not in all_recommended_products:
                all_recommended_products.append(prod_id)
                
                # Get the score and other metrics
                score = prod.get('score', 0)
                confidence = prod.get('confidence', 0)
                is_seasonal = prod.get('is_seasonal', False)
                is_time_relevant = prod.get('is_time_relevant', False)
                time_of_day = prod.get('time_of_day', '')
                
                # Format the score and confidence as percentages
                score_pct = f"{score*100:.1f}%" if score else "N/A"
                confidence_pct = f"{confidence*100:.1f}%" if confidence else "N/A"
                
                # Create recommendation labels
                labels = []
                if is_seasonal:
                    labels.append("Seasonal")
                if is_time_relevant:
                    labels.append(f"{time_of_day.title()} item")
                    
                labels_str = f" [{', '.join(labels)}]" if labels else ""
                
                print(f"• {prod.get('name', 'Unknown')} ({prod.get('category', 'Unknown')})")
                print(f"  Score: {score_pct} | Confidence: {confidence_pct}{labels_str}")
    
    print("="*80)


def run_grocery_demo():
    """
    Run the grocery recommendation demo
    """
    print("\n" + "="*80)
    print("BUYBUDDY GROCERY RECOMMENDATION DEMO")
    print("="*80)
    print("This demo showcases BuyBuddy's advanced recommendation engine with real grocery data.")
    print("The system generates personalized product recommendations based on shopping patterns,")
    print("seasonal trends, time of day, and collaborative filtering.\n")
    
    with app.app_context():
        # Create demo account
        demo_user = create_demo_account()
        
        # Load grocery data
        data_stats = load_grocery_data(demo_user.id)
        
        if 'error' in data_stats:
            print(f"Error loading grocery data: {data_stats['error']}")
            return
        
        print(f"Loaded {data_stats.get('products_total', 0)} grocery products")
        print(f"Processed {data_stats.get('transactions_total', 0)} shopping transactions")
        
        # Generate recommendations
        rec_stats = generate_demo_recommendations(demo_user.id)
        
        if 'error' in rec_stats:
            print(f"Error generating recommendations: {rec_stats['error']}")
            return
        
        print(f"Generated {rec_stats.get('recommendations_saved', 0)} product recommendations")
        print(f"Algorithm version: {rec_stats.get('algorithm_version', 'Unknown')}")
        
        # Get enhanced features
        features = rec_stats.get('features', {})
        if features:
            print("\nADVANCED FEATURES ENABLED:")
            for feature, enabled in features.items():
                if enabled:
                    print(f"✓ {feature.replace('_', ' ').title()}")
        
        # Current context
        print(f"\nCurrent time period: {rec_stats.get('current_time_period', 'Unknown').title()}")
        current_month = rec_stats.get('current_month', 0)
        month_name = datetime(2020, current_month, 1).strftime('%B') if 1 <= current_month <= 12 else 'Unknown'
        print(f"Current month: {month_name}")
        
        # Create sample baskets for recommendation demo
        print("\nGenerating sample grocery baskets for recommendation demo...")
        baskets = create_sample_baskets(num_baskets=3)
        
        if not baskets:
            print("Error: Could not create sample baskets")
            return
        
        # Show each basket with recommendations
        for i, basket in enumerate(baskets):
            print(f"\nBASKET {i+1} OF {len(baskets)}")
            print_basket_with_recommendations(basket, recommendations_limit=4)


if __name__ == "__main__":
    run_grocery_demo()