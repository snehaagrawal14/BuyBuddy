from functools import wraps
from flask import request, jsonify, current_app
import secrets
import string
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
import datetime
from app import db, jwt
from models import User, ApiKey


def generate_api_key(length=32):
    """Generate a secure API key"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def api_key_required(f):
    """Decorator to require API key for endpoint"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'error': 'Missing API key',
                'message': 'API key must be provided in the X-API-Key header'
            }), 401
        
        # Check if API key exists and is active
        key = ApiKey.query.filter_by(key=api_key, active=True).first()
        if not key:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is invalid or inactive'
            }), 401
        
        # Update last used timestamp
        key.last_used = datetime.datetime.now()
        db.session.commit()
        
        return f(*args, **kwargs)
    return decorated_function


def register_user(username, email, password, company_name=None):
    """Register a new user and generate API key"""
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        return {'error': 'Username already exists'}, 400
    
    if User.query.filter_by(email=email).first():
        return {'error': 'Email already exists'}, 400
    
    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        company_name=company_name
    )
    db.session.add(user)
    db.session.flush()  # Get user ID without committing
    
    # Generate API key
    api_key = ApiKey(
        key=generate_api_key(),
        name='Default API Key',
        user_id=user.id,
        config={
            'min_confidence': 0.1,
            'min_support': 0.01,
            'max_recommendations': 5
        }
    )
    db.session.add(api_key)
    
    # Commit transaction
    db.session.commit()
    
    # Generate JWT token
    access_token = create_access_token(identity=user.id)
    
    return {
        'user_id': user.id,
        'username': user.username,
        'api_key': api_key.key,
        'access_token': access_token
    }, 201


def login_user(username, password):
    """Login user and return API key and JWT token"""
    user = User.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return {'error': 'Invalid username or password'}, 401
    
    # Get or create API key
    api_key = ApiKey.query.filter_by(user_id=user.id, active=True).first()
    
    if not api_key:
        # Create new API key if none exists
        api_key = ApiKey(
            key=generate_api_key(),
            name='Default API Key',
            user_id=user.id
        )
        db.session.add(api_key)
        db.session.commit()
    
    # Generate JWT token
    access_token = create_access_token(identity=user.id)
    
    return {
        'user_id': user.id,
        'username': user.username,
        'api_key': api_key.key,
        'access_token': access_token
    }, 200


def create_api_key(user_id, name="API Key"):
    """Create a new API key for a user"""
    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        return {'error': 'User not found'}, 404
    
    # Create API key
    api_key = ApiKey(
        key=generate_api_key(),
        name=name,
        user_id=user_id
    )
    db.session.add(api_key)
    db.session.commit()
    
    return {
        'key_id': api_key.id,
        'key': api_key.key,
        'name': api_key.name,
        'created_at': api_key.created_at.isoformat()
    }, 201


def revoke_api_key(key_id, user_id):
    """Revoke an API key"""
    # Find API key
    api_key = ApiKey.query.filter_by(id=key_id, user_id=user_id).first()
    
    if not api_key:
        return {'error': 'API key not found'}, 404
    
    # Deactivate API key
    api_key.active = False
    db.session.commit()
    
    return {
        'message': 'API key revoked successfully',
        'key_id': api_key.id
    }, 200


@jwt.user_identity_loader
def user_identity_lookup(user_id):
    """Convert user ID to string for JWT identity"""
    return str(user_id)


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    """Load user from database based on JWT identity"""
    identity = jwt_data["sub"]
    return User.query.filter_by(id=identity).one_or_none()
