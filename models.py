from app import db
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime


class User(UserMixin, db.Model):
    """User model for API service accounts"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    company_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.now)
    active = db.Column(db.Boolean, default=True)
    
    # Relationships
    api_keys = db.relationship('ApiKey', backref='user', lazy='dynamic')


class ApiKey(db.Model):
    """API key for service authentication"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_used = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)
    
    # Configuration
    config = db.Column(JSONB, default={})  # Store configuration options as JSON


class Product(db.Model):
    """Product model to represent grocery items"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(64), unique=True, nullable=False)  # External product ID
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(64))
    subcategory = db.Column(db.String(64))
    product_metadata = db.Column(JSONB, default={})  # Additional product metadata
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    recommendations = db.relationship(
        'ProductRecommendation',
        foreign_keys='ProductRecommendation.product_id',
        backref='product',
        lazy='dynamic'
    )


class Transaction(db.Model):
    """Transaction model to store purchase history"""
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(64), nullable=False)  # External transaction ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    products = db.Column(JSONB, nullable=False)  # Array of product IDs in this transaction
    transaction_metadata = db.Column(JSONB, default={})  # Additional transaction metadata


class ProductRecommendation(db.Model):
    """Model to store product recommendations"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    recommended_product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    confidence = db.Column(db.Float, nullable=False)  # Confidence score (0-1)
    support = db.Column(db.Float, nullable=False)  # Support score
    lift = db.Column(db.Float)  # Lift score
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    # Define a unique constraint to avoid duplicates
    __table_args__ = (
        db.UniqueConstraint('product_id', 'recommended_product_id', name='unique_recommendation'),
    )
    
    # Relationship to access the recommended product's details
    recommended_product = db.relationship('Product', foreign_keys=[recommended_product_id])


class RecommendationJob(db.Model):
    """Model to track recommendation generation jobs"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    config = db.Column(JSONB, default={})  # Job configuration parameters
    result_stats = db.Column(JSONB, default={})  # Summary statistics of the job
    error = db.Column(db.Text)  # Error message if job failed
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    completed_at = db.Column(db.DateTime)
