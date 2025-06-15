import os
import logging
import datetime

# Try to load environment variables from .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed, skipping .env loading")

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_jwt_extended import JWTManager
from flasgger import Swagger
from flask_login import LoginManager


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "buybuddy-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database with the DATABASE_URL
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/buybuddy")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# JWT configuration
app.config["JWT_SECRET_KEY"] = os.environ.get("SESSION_SECRET", "buybuddy-jwt-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 86400  # 24 hours in seconds

# Configure Swagger for API documentation
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "BuyBuddy API",
        "description": "Machine Learning-powered Grocery Recommendation API",
        "version": "1.0.0",
        "contact": {
            "email": "support@buybuddy.com"
        }
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
        }
    },
    "security": [
        {"Bearer": []}
    ]
}

# Initialize extensions
db.init_app(app)
jwt = JWTManager(app)
swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'demo.login'  # type: ignore # Set the login view to redirect unauthenticated users

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Initialize app
with app.app_context():
    # Import models here to ensure they're registered with SQLAlchemy
    from models import User, Product, Transaction, ApiKey
    db.create_all()
    
    # Initialize database with default data if needed
    from utils import init_db
    init_db()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("BuyBuddy API Service initialized")
