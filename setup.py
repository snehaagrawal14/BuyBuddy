import subprocess
import os
import sys
import time
import platform
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_step(step, description):
    print(f"\n{'='*80}")
    print(f"STEP {step}: {description}")
    print(f"{'='*80}\n")

def run_command(command, error_message):
    try:
        print(f"Running: {command}")
        result = subprocess.run(command, shell=True, check=True, 
                              text=True, capture_output=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {error_message}")
        print(f"Command output: {e.stdout}")
        print(f"Error details: {e.stderr}")
        return False

def create_env_file(db_user, db_password, db_host, db_port, db_name):
    """Create a .env file with the provided database credentials"""
    env_content = f"""DATABASE_URL=postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}
SESSION_SECRET=buybuddy-secret-development-key
FLASK_APP = main.py"""
    with open('.env', 'w') as f:
        f.write(env_content)
    print("Created .env file with database configuration")

def modify_app_py():
    """Modify app.py to use hardcoded database credentials if environment variable is not set"""
    with open('app.py', 'r') as file:
        content = file.read()
    
    # Make sure DATABASE_URL has a fallback
    modified_content = content.replace(
        'app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")',
        'app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/buybuddy")'
    )
    
    with open('app.py', 'w') as file:
        file.write(modified_content)
    
    print("Updated app.py for better local development support")

def init_database(pg_user, pg_password, pg_host, pg_port, db_name):
    """Initialize the database with initial data"""
    try:
        # Check PostgreSQL availability
        if platform.system() == "Windows":
            check_cmd = f'psql -U {pg_user} -h {pg_host} -p {pg_port} -d postgres -c "SELECT version();"'
        else:
            check_cmd = f'PGPASSWORD="{pg_password}" psql -U {pg_user} -h {pg_host} -p {pg_port} -c "SELECT version();"'
        
        subprocess.run(check_cmd, shell=True, check=True, capture_output=True)
        
        # Create database if it doesn't exist
        if platform.system() == "Windows":
            create_db_cmd = f'psql -U {pg_user} -h {pg_host} -p {pg_port} -d postgres -c "CREATE DATABASE {db_name};"'
        else:
            create_db_cmd = f'PGPASSWORD="{pg_password}" psql -U {pg_user} -h {pg_host} -p {pg_port} -c "CREATE DATABASE {db_name};"'
        
        subprocess.run(create_db_cmd, shell=True, check=False, capture_output=True)
        print(f"Database '{db_name}' created or already exists")
        
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

def load_grocery_data_and_generate_recommendations():
    """
    Load grocery data and generate recommendations
    """
    print("\n" + "="*80)
    print("LOADING REAL-TIME GROCERY DATASET AND GENERATING RECOMMENDATIONS")
    print("="*80 + "\n")
    
    try:
        # Import necessary modules within function to avoid circular imports
        from app import app
        from models import User
        from data_loader import load_grocery_data_into_db
        from recommendation import generate_recommendations
        from auth import register_user
        from werkzeug.security import generate_password_hash
    
        with app.app_context():
            # Create or get a demo user
            print("Creating demo user...")
            username = "demo"
            password = "password"
            
            # Check if user exists
            user = User.query.filter_by(username=username).first()
            if not user:
                # Create user
                register_user(
                    username=username,
                    email="demo@example.com",
                    password=password,
                    company_name="Demo Grocery Store"
                )
                print(f"Created demo user: {username} (password: {password})")
            else:
                print(f"Demo user already exists: {username}")

            # Get user ID
            user = User.query.filter_by(username=username).first()
            if not user:
                print("Error: Failed to create or retrieve demo user")
                return False
                
            # Load grocery data
            print("Loading grocery dataset...")
            data_result = load_grocery_data_into_db(user.id)
            
            if 'error' in data_result:
                print(f"Error loading grocery data: {data_result['error']}")
                return False
                
            print(f"Successfully loaded {data_result.get('products_total', 0)} grocery products")
            print(f"Processed {data_result.get('transactions_total', 0)} shopping transactions")
            
            # Generate recommendations
            print("Generating recommendations from grocery data...")
            rec_result = generate_recommendations(user.id, min_support=0.01, min_confidence=0.05)
            
            if 'error' in rec_result:
                print(f"Error generating recommendations: {rec_result['error']}")
                return False
                
            print(f"Generated {rec_result.get('recommendations_saved', 0)} product recommendations")
            
            # Show algorithm details
            print("\nRecommendation algorithm details:")
            print(f"- Algorithm version: {rec_result.get('algorithm_version', 'Unknown')}")
            print(f"- Current time period: {rec_result.get('current_time_period', 'Unknown').title()}")
            
            current_month = rec_result.get('current_month', 0)
            month_name = datetime(2020, current_month, 1).strftime('%B') if 1 <= current_month <= 12 else 'Unknown'
            print(f"- Current month: {month_name}")
            
            # Show enabled features
            features = rec_result.get('features', {})
            if features:
                print("\nEnabled recommendation features:")
                for feature, enabled in features.items():
                    if enabled:
                        print(f"✓ {feature.replace('_', ' ').title()}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error in data loading process: {str(e)}")
        print(f"Error in data loading process: {str(e)}")
        return False

def main():
    print("\nBuyBuddy Setup - Automated Installation\n")
    
    # Step 1: Install requirements
    print_step(1, "Installing required packages")
    print("Make sure you have pip installed on your system.")
    
    requirements = [
        "email-validator", "flasgger", "flask", "flask-jwt-extended", 
        "flask-login", "flask-sqlalchemy", "flask-wtf", "gunicorn", 
        "matplotlib", "mlxtend", "numpy", "pandas", "psycopg2-binary", 
        "python-dotenv", "seaborn", "sqlalchemy", "trafilatura", 
        "werkzeug", "wtforms"
    ]
    
    install_cmd = f"pip install {' '.join(requirements)}"
    if not run_command(install_cmd, "Failed to install required packages"):
        return
    
    # Step 2: Set up PostgreSQL database
    print_step(2, "Setting up PostgreSQL database")
    print("Please provide your PostgreSQL credentials:")
    
    # Get PostgreSQL credentials with defaults
    pg_user = input("PostgreSQL username [postgres]: ") or "postgres"
    pg_password = input("PostgreSQL password [postgres]: ") or "postgres"
    pg_host = input("PostgreSQL host [localhost]: ") or "localhost"
    pg_port = input("PostgreSQL port [5432]: ") or "5432"
    db_name = input("Database name [buybuddy]: ") or "buybuddy"
    
    # Create .env file with database credentials
    create_env_file(pg_user, pg_password, pg_host, pg_port, db_name)
    
    # Modify app.py to work better with local development
    modify_app_py()
    
    # Step 3: Initialize the database
    print_step(3, "Initializing the database")
    if not init_database(pg_user, pg_password, pg_host, pg_port, db_name):
        print("Warning: Database initialization encountered issues.")
        print("You may need to manually create the database.")
    
    # Step 4: Load real-time grocery data and generate recommendations
    print_step(4, "Loading real-time grocery data and generating recommendations")
    print("This may take a few minutes depending on your system...")
    load_grocery_data_and_generate_recommendations()
    
    # Step 5: Start the application
    print_step(5, "Setup Complete - Starting the application")
    print("\nBuyBuddy is now ready to run!")
    print("To start the application, run:")
    print("   python -m flask run --host=0.0.0.0 --port=5000")
    print("\nOr for a production-like environment:")
    print("   gunicorn --bind 0.0.0.0:5000 main:app")
    
    print("\nYou can then access the application at: http://localhost:5000")
    print("Login with the credentials:")
    print("   Username: demo")
    print("   Password: password")
    print("\nThe real-time grocery recommendation demo is available at:")
    print("   http://localhost:5000/sample")
    
    # Ask user if they want to start the application now
    start_now = input("\nWould you like to start the application now? (y/n): ")
    if start_now.lower() == 'y':
        print("\nStarting BuyBuddy application...\n")
        if platform.system() == "Windows":
            os.system("python -m flask run --host=0.0.0.0 --port=5000")
        else:
            os.system("gunicorn --bind 0.0.0.0:5000 main:app")
    else:
        print("\nSetup completed successfully. You can start the application later with the commands above.")

if __name__ == "__main__":
    main()