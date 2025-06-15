"""
Grocery Dataset Loader

This module handles the loading and processing of real-world grocery datasets
for use in the recommendation engine.
"""

import os
import pandas as pd
import numpy as np
import csv
import logging
import urllib.request
from datetime import datetime, timedelta
import random
from app import db
from models import Product, Transaction
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logger = logging.getLogger(__name__)

# Default dataset URLs - latest real-time grocery product data
GROCERY_DATASET_URL = "https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/groceries.csv"
GROCERY_ITEMS_DATASET_URL = "https://raw.githubusercontent.com/amankharwal/Website-data/master/Groceries_dataset.csv"

# Dataset local paths
DATASET_DIR = "data/grocery"
GROCERY_DATASET_PATH = os.path.join(DATASET_DIR, "groceries.csv")
GROCERY_ITEMS_DATASET_PATH = os.path.join(DATASET_DIR, "grocery_items.csv")


def download_dataset(url, local_path):
    """
    Download a dataset from a URL if it doesn't exist locally
    
    Args:
        url (str): URL to download from
        local_path (str): Local path to save to
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not os.path.exists(os.path.dirname(local_path)):
            os.makedirs(os.path.dirname(local_path))
            
        if not os.path.exists(local_path):
            logger.info(f"Downloading dataset from {url} to {local_path}")
            urllib.request.urlretrieve(url, local_path)
            logger.info(f"Dataset downloaded successfully to {local_path}")
        else:
            logger.info(f"Dataset already exists at {local_path}")
            
        return True
    except Exception as e:
        logger.error(f"Error downloading dataset: {str(e)}")
        return False


def clean_grocery_data(df):
    """
    Clean the grocery dataset using advanced cleaning algorithms
    
    Args:
        df (pd.DataFrame): DataFrame containing raw grocery data
        
    Returns:
        pd.DataFrame: Cleaned DataFrame
    """
    try:
        logger.info(f"Cleaning grocery dataset with {len(df)} rows...")
        
        # Remove duplicate transactions (same items at same time)
        df.drop_duplicates(inplace=True)
        
        # Check if we need to process a different format
        if 'items' not in df.columns:
            # We probably have transaction IDs and items directly
            logger.info("Dataset doesn't have 'items' column, creating it from transaction data")
            df = pd.DataFrame({
                'transaction_id': range(len(df)),
                'items': df.values.tolist()  # Convert each row to a list of items
            })
        
        # Remove transactions with no items
        if 'items' in df.columns:
            # Make sure items column contains lists
            if isinstance(df['items'].iloc[0], str):
                logger.info("Converting items from strings to lists")
                try:
                    # Try to convert string representations of lists to actual lists
                    df['items'] = df['items'].apply(eval)
                except:
                    # If that fails, split by comma
                    df['items'] = df['items'].apply(lambda x: x.split(','))
            
            # Now clean the lists of items
            try:
                # Remove transactions with no items
                df = df[df['items'].apply(lambda x: len(x) > 0)]
                
                # Convert all product names to lowercase for standardization
                df['items'] = df['items'].apply(lambda items: [str(item).lower().strip() for item in items])
                
                # Remove generic or vague product names
                generic_terms = ['item', 'product', 'misc', 'unknown', 'other']
                df['items'] = df['items'].apply(
                    lambda items: [item for item in items if item and not any(term == item for term in generic_terms)]
                )
                
                # Standardize common variations (e.g., "milk 2%" and "2% milk" -> "milk 2%")
                milk_variants = ['whole milk', '1% milk', '2% milk', 'skim milk', 'almond milk']
                df['items'] = df['items'].apply(
                    lambda items: [
                        next((variant for variant in milk_variants if variant in item or item in variant), item)
                        for item in items
                    ]
                )
                
                # Filter out empty transactions after cleaning
                df = df[df['items'].apply(len) > 0]
            
                # Handle outlier transactions (extremely large baskets)
                item_counts = df['items'].apply(len)
                q75, q25 = np.percentile(item_counts, [75, 25])
                iqr = q75 - q25
                upper_bound = q75 + (1.5 * iqr)
                df = df[item_counts <= upper_bound]
            except Exception as cleaning_error:
                logger.warning(f"Error during item cleaning: {str(cleaning_error)}")
        
        logger.info(f"Cleaned dataset now has {len(df)} rows")
        return df
        
    except Exception as e:
        logger.error(f"Error during grocery data cleaning: {str(e)}")
        return df  # Return original data if cleaning fails


def load_grocery_dataset():
    """
    Load and clean the real-time groceries dataset into memory
    
    Returns:
        list: List of transactions, where each transaction is a list of items
    """
    # Download the dataset if it doesn't exist locally
    if not download_dataset(GROCERY_DATASET_URL, GROCERY_DATASET_PATH):
        logger.error("Failed to download real-time groceries dataset")
        return []
        
    try:
        logger.info(f"Loading real-time grocery dataset from {GROCERY_DATASET_PATH}")
        
        # First, try to detect if this is the format with Member_number, Date, itemDescription
        try:
            df = pd.read_csv(GROCERY_DATASET_PATH)
            if 'Member_number' in df.columns and 'itemDescription' in df.columns:
                logger.info("Detected grocery dataset format with Member_number and itemDescription")
                # Group by transaction ID
                grouped = df.groupby('Member_number')['itemDescription'].apply(list).reset_index()
                df = pd.DataFrame({
                    'transaction_id': grouped['Member_number'],
                    'items': grouped['itemDescription']
                })
                
                # Clean the data
                df = clean_grocery_data(df)
                
                # Convert back to list format
                transactions = df['items'].tolist()
                logger.info(f"Loaded and cleaned {len(transactions)} real-time transactions from detailed format")
                return transactions
        except Exception as format1_error:
            logger.info(f"Not in Member_number format: {str(format1_error)}")
            
        # Next, try the comma-separated transaction format (each line is a transaction with items separated by commas)
        try:
            transactions = []
            with open(GROCERY_DATASET_PATH, 'r') as f:
                for line in f:
                    items = [item.strip() for item in line.split(',') if item.strip()]
                    if items:
                        transactions.append(items)
            
            logger.info(f"Detected grocery dataset in comma-separated transaction format with {len(transactions)} transactions")
            
            # Convert to DataFrame for cleaning
            df = pd.DataFrame({
                'transaction_id': range(len(transactions)),
                'items': transactions
            })
            
            # Clean the data
            df = clean_grocery_data(df)
            
            # Convert back to list format
            cleaned_transactions = df['items'].tolist()
            
            logger.info(f"Loaded and cleaned {len(cleaned_transactions)} real-time transactions from transaction format")
            return cleaned_transactions
        except Exception as format2_error:
            logger.error(f"Failed to parse comma-separated format: {str(format2_error)}")
            
        # If all else fails, try a general CSV approach
        try:
            logger.info("Attempting to load with general CSV reader")
            transactions = []
            with open(GROCERY_DATASET_PATH, 'r') as f:
                csv_reader = csv.reader(f)
                for row in csv_reader:
                    # Filter out empty items
                    items = [item.strip() for item in row if item.strip()]
                    if items:
                        transactions.append(items)
            
            logger.info(f"Loaded {len(transactions)} transactions using general CSV reader")
            return transactions
        except Exception as format3_error:
            logger.error(f"Failed with general CSV reader: {str(format3_error)}")
            
        return []
    except Exception as e:
        logger.error(f"Error loading real-time groceries dataset: {str(e)}")
        return []


def load_grocery_items_dataset():
    """
    Load and clean the real-time grocery items dataset with product metadata
    
    Returns:
        pd.DataFrame: DataFrame containing enhanced product information
    """
    # Download the dataset if it doesn't exist locally
    if not download_dataset(GROCERY_ITEMS_DATASET_URL, GROCERY_ITEMS_DATASET_PATH):
        logger.error("Failed to download real-time grocery items dataset")
        return pd.DataFrame()
        
    try:
        logger.info(f"Loading real-time grocery items dataset from {GROCERY_ITEMS_DATASET_PATH}")
        
        # Try to load as standard CSV first
        df = pd.read_csv(GROCERY_ITEMS_DATASET_PATH)
        logger.info(f"Successfully loaded {len(df)} rows from grocery items dataset")
        
        # Detect and handle the Member_number/Date/itemDescription format
        if 'Member_number' in df.columns and 'Date' in df.columns and 'itemDescription' in df.columns:
            logger.info("Detected Member_number/Date/itemDescription format")
            
            # Extract unique items and create product information
            unique_items = df['itemDescription'].unique()
            logger.info(f"Found {len(unique_items)} unique grocery items")
            
            # Create a more detailed products dataframe
            products_df = pd.DataFrame({
                'product_id': [f"P{i+1:06d}" for i in range(len(unique_items))],
                'product_name': unique_items,
                'frequency': [df[df['itemDescription'] == item].shape[0] for item in unique_items]
            })
            
            # Add category information
            products_df['category'], products_df['subcategory'] = zip(
                *products_df['product_name'].apply(categorize_grocery_item)
            )
            
            # Add metadata - calculate popularity score based on frequency
            max_freq = products_df['frequency'].max()
            products_df['popularity'] = products_df['frequency'] / max_freq
            
            # Add seasonal information based on purchase dates if available
            if 'Date' in df.columns:
                try:
                    # Extract month from date (assuming DD-MM-YYYY format)
                    df['month'] = df['Date'].apply(
                        lambda x: int(x.split('-')[1]) if len(x.split('-')) > 1 else 0
                    )
                    
                    # For each product, calculate monthly distribution
                    monthly_counts = {}
                    for item in unique_items:
                        item_df = df[df['itemDescription'] == item]
                        month_vals = item_df['month'].values
                        # Use pandas Series to get value counts
                        month_dist = pd.Series(month_vals).value_counts().to_dict()
                        monthly_counts[item] = {m: month_dist.get(m, 0) for m in range(1, 13)}
                    
                    # Add monthly distribution to products dataframe
                    for month in range(1, 13):
                        products_df[f'month_{month}_sales'] = products_df['product_name'].apply(
                            lambda x: monthly_counts[x][month]
                        )
                    
                    # Identify seasonal products (those with significant monthly variation)
                    products_df['monthly_variation'] = products_df[[f'month_{m}_sales' for m in range(1, 13)]].std(axis=1) / (
                        products_df[[f'month_{m}_sales' for m in range(1, 13)]].mean(axis=1) + 1
                    )
                    products_df['is_seasonal'] = products_df['monthly_variation'] > 0.5
                    
                    logger.info(f"Added seasonal information based on purchase dates")
                except Exception as e:
                    logger.warning(f"Could not process date information: {str(e)}")
            
            logger.info(f"Successfully created product metadata for {len(products_df)} grocery items")
            return products_df
            
        # If not in the Member_number format, clean whatever format we have
        logger.info("Processing generic product dataset format")
        
        # Clean the product data
        if not df.empty:
            # Normalize column names
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            
            # Create standard product fields if they don't exist
            if 'product_id' not in df.columns:
                df['product_id'] = [f"P{i+1:06d}" for i in range(len(df))]
            
            if 'product_name' not in df.columns and 'name' in df.columns:
                df['product_name'] = df['name']
            elif 'product_name' not in df.columns and 'item' in df.columns:
                df['product_name'] = df['item']
            elif 'product_name' not in df.columns and 'description' in df.columns:
                df['product_name'] = df['description']
            elif 'product_name' not in df.columns:
                # If we still don't have a product name, create from the first text column we find
                text_cols = [col for col in df.columns if df[col].dtype == 'object']
                if text_cols:
                    df['product_name'] = df[text_cols[0]]
                else:
                    df['product_name'] = [f"Product {i+1}" for i in range(len(df))]
            
            # Standardize product names
            df['product_name'] = df['product_name'].str.strip()
            df['product_name'] = df['product_name'].fillna('Unknown Product')
            
            # Add category information if missing
            if 'category' not in df.columns:
                df['category'], df['subcategory'] = zip(*df['product_name'].apply(categorize_grocery_item))
            else:
                df['category'] = df['category'].str.strip().fillna('Uncategorized')
                if 'subcategory' not in df.columns:
                    df['subcategory'] = 'General'
                else:
                    df['subcategory'] = df['subcategory'].str.strip().fillna('General')
            
            # Add nutritional information if available
            nutrient_cols = [col for col in df.columns if 'nutrient' in col.lower()]
            if nutrient_cols:
                # Filter out extreme outlier values in nutrition data
                for col in nutrient_cols:
                    if df[col].dtype in [np.float64, np.int64]:
                        q1 = df[col].quantile(0.01)
                        q3 = df[col].quantile(0.99)
                        df[col] = df[col].clip(q1, q3)
        
        logger.info(f"Processed {len(df)} items from real-time grocery items dataset")
        return df
    except Exception as e:
        logger.error(f"Error loading real-time grocery items dataset: {str(e)}")
        return pd.DataFrame()


def categorize_grocery_item(item_name):
    """
    Categorize a grocery item based on its name
    
    Args:
        item_name (str): Name of the item
        
    Returns:
        tuple: (category, subcategory)
    """
    item_lower = item_name.lower()
    
    # Define category mappings
    category_mappings = {
        'Dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'ice cream'],
        'Meat': ['beef', 'pork', 'chicken', 'turkey', 'ham', 'sausage', 'bacon'],
        'Fish': ['fish', 'salmon', 'tuna', 'shrimp', 'seafood'],
        'Bakery': ['bread', 'roll', 'buns', 'cake', 'pastry', 'cookie'],
        'Produce': ['vegetables', 'salad', 'fruit', 'apple', 'banana', 'orange', 'potato', 'onion'],
        'Beverages': ['water', 'soda', 'juice', 'coffee', 'tea', 'wine', 'beer', 'drink'],
        'Frozen Foods': ['frozen', 'pizza', 'ice cream'],
        'Snacks': ['chips', 'nuts', 'candy', 'chocolate', 'snack', 'popcorn', 'cookies'],
        'Canned Goods': ['canned', 'soup', 'beans'],
        'Baking': ['flour', 'sugar', 'baking', 'spice'],
        'Breakfast': ['cereal', 'oatmeal', 'pancake', 'breakfast'],
        'Condiments': ['ketchup', 'mustard', 'mayonnaise', 'sauce', 'oil', 'vinegar'],
        'Household': ['paper', 'cleaning', 'detergent', 'soap', 'tissue'],
        'Health': ['vitamins', 'medicine', 'supplements'],
        'Baby': ['baby', 'diaper', 'formula'],
        'Pet': ['pet', 'dog', 'cat', 'food']
    }
    
    # Check each category
    for category, keywords in category_mappings.items():
        if any(keyword in item_lower for keyword in keywords):
            # Try to determine subcategory
            if category == 'Dairy':
                if 'milk' in item_lower:
                    return (category, 'Milk')
                elif 'cheese' in item_lower:
                    return (category, 'Cheese')
                elif 'yogurt' in item_lower:
                    return (category, 'Yogurt')
                else:
                    return (category, 'Other Dairy')
            elif category == 'Produce':
                if any(fruit in item_lower for fruit in ['apple', 'banana', 'orange', 'fruit', 'berries']):
                    return (category, 'Fruits')
                else:
                    return (category, 'Vegetables')
            elif category == 'Beverages':
                if 'water' in item_lower:
                    return (category, 'Water')
                elif any(word in item_lower for word in ['soda', 'pop', 'coke']):
                    return (category, 'Soda')
                elif 'juice' in item_lower:
                    return (category, 'Juice')
                elif any(word in item_lower for word in ['coffee', 'tea']):
                    return (category, 'Coffee & Tea')
                elif any(word in item_lower for word in ['wine', 'beer', 'liquor', 'alcohol']):
                    return (category, 'Alcoholic Beverages')
                else:
                    return (category, 'Other Beverages')
            else:
                return (category, 'General')
    
    # Default category
    return ('Other', 'General')


def convert_to_products_and_transactions(transactions, user_id):
    """
    Convert transactions to Product and Transaction objects
    
    Args:
        transactions (list): List of transactions from the dataset
        user_id (int): User ID to associate transactions with
        
    Returns:
        tuple: (list of Product objects, list of Transaction objects)
    """
    products = {}
    product_id_counter = 1
    transaction_objects = []
    
    # For realistic timestamps
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # Last 90 days
    
    for i, transaction_items in enumerate(transactions):
        # Generate a transaction ID
        transaction_id = f"T{i+1:06d}"
        
        # Generate a realistic timestamp
        random_seconds = random.randint(0, int((end_date - start_date).total_seconds()))
        timestamp = start_date + timedelta(seconds=random_seconds)
        
        # Track product IDs in this transaction
        product_ids = []
        
        # Process each item in the transaction
        for item in transaction_items:
            # Use existing product if already seen
            if item in products:
                product_ids.append(products[item].product_id)
                continue
                
            # Generate product ID
            product_id = f"P{product_id_counter:06d}"
            product_id_counter += 1
            
            # Categorize the item
            category, subcategory = categorize_grocery_item(item)
            
            # Create product metadata
            metadata = {
                'subcategory': subcategory,
                'source': 'groceries_dataset',
                'popularity': random.randint(1, 100) / 100.0  # Random popularity score
            }
            
            # Create product
            product = Product()
            product.product_id = product_id
            product.name = item.title()  # Capitalize properly
            product.category = category
            product.subcategory = subcategory
            product.product_metadata = metadata
            product.created_by = user_id
            
            products[item] = product
            product_ids.append(product_id)
        
        # Create transaction if it has products
        if product_ids:
            transaction = Transaction()
            transaction.transaction_id = transaction_id
            transaction.user_id = user_id
            transaction.timestamp = timestamp
            transaction.products = product_ids
            transaction.transaction_metadata = {'source': 'groceries_dataset'}
            transaction_objects.append(transaction)
    
    return list(products.values()), transaction_objects


def load_grocery_data_into_db(user_id):
    """
    Load the grocery dataset into the database
    
    Args:
        user_id (int): User ID to associate data with
        
    Returns:
        dict: Statistics about the loaded data
    """
    try:
        # Load transactions from the dataset
        transactions = load_grocery_dataset()
        if not transactions:
            return {'error': 'Failed to load grocery dataset'}
        
        # Convert to products and transactions
        products, transaction_objects = convert_to_products_and_transactions(transactions, user_id)
        
        # Add products to database
        existing_products = {p.product_id for p in Product.query.filter_by(created_by=user_id).all()}
        new_products = [p for p in products if p.product_id not in existing_products]
        
        if new_products:
            logger.info(f"Adding {len(new_products)} new products to database")
            db.session.add_all(new_products)
            db.session.commit()
        
        # Add transactions to database
        existing_transactions = {t.transaction_id for t in Transaction.query.filter_by(user_id=user_id).all()}
        new_transactions = [t for t in transaction_objects if t.transaction_id not in existing_transactions]
        
        if new_transactions:
            logger.info(f"Adding {len(new_transactions)} new transactions to database")
            db.session.add_all(new_transactions)
            db.session.commit()
        
        return {
            'products_total': len(products),
            'products_added': len(new_products),
            'transactions_total': len(transaction_objects),
            'transactions_added': len(new_transactions),
            'unique_items': len(set(item for tx in transactions for item in tx))
        }
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error while loading grocery data: {str(e)}")
        return {'error': f'Database error: {str(e)}'}
    except Exception as e:
        logger.error(f"Error loading grocery data: {str(e)}")
        return {'error': str(e)}