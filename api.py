from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flasgger import swag_from
import logging
from app import db
from models import Product, ProductRecommendation, ApiKey, User, Transaction
from recommendation import get_recommendations, batch_process_transactions
from auth import api_key_required

# Configure logging
logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health Check
    ---
    tags:
      - System
    responses:
      200:
        description: Service is healthy
        schema:
          properties:
            status:
              type: string
              example: "ok"
            version:
              type: string
              example: "1.0.0"
    """
    return jsonify({
        'status': 'ok',
        'version': '1.0.0'
    }), 200


@api_bp.route('/recommend', methods=['POST'])
@api_key_required
def recommend_products():
    """
    Get product recommendations with enhanced contextual relevance
    ---
    tags:
      - Recommendations
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - product_ids
          properties:
            product_ids:
              type: array
              description: List of product IDs to get recommendations for
              items:
                type: string
              example: ["P12345", "P67890"]
            limit:
              type: integer
              description: Maximum number of recommendations to return
              default: 5
              example: 5
            min_confidence:
              type: number
              description: Minimum confidence score (0-1)
              default: 0.1
              example: 0.1
            time_of_day:
              type: string
              description: Override current time of day for recommendations
              enum: [morning, midday, evening, late_night]
              example: "evening"
            ignore_seasonal:
              type: boolean
              description: Ignore seasonal factors in recommendations
              default: false
              example: false
    responses:
      200:
        description: Product recommendations
        schema:
          properties:
            recommendations:
              type: array
              items:
                type: object
                properties:
                  product_id:
                    type: string
                  recommended_products:
                    type: array
                    items:
                      type: object
                      properties:
                        product_id:
                          type: string
                        name:
                          type: string
                        confidence:
                          type: number
                        support:
                          type: number
                        score:
                          type: number
                        category:
                          type: string
                        is_seasonal:
                          type: boolean
                        is_time_relevant:
                          type: boolean
                        time_of_day:
                          type: string
            context:
              type: object
              properties:
                algorithm_version:
                  type: string
                time_of_day:
                  type: string
                current_month:
                  type: integer
                seasonal_boost_applied:
                  type: boolean
                time_boost_applied:
                  type: boolean
      400:
        description: Invalid request parameters
      404:
        description: Products not found
    """
    from datetime import datetime
    from recommendation import get_time_of_day
    
    data = request.json
    if not data or 'product_ids' not in data:
        return jsonify({'error': 'Missing product_ids parameter'}), 400
    
    product_ids = data.get('product_ids', [])
    if not product_ids or not isinstance(product_ids, list):
        return jsonify({'error': 'product_ids must be a non-empty array'}), 400
    
    limit = data.get('limit', 5)
    min_confidence = data.get('min_confidence', 0.1)
    
    # Optional parameters for enhanced recommendations
    time_of_day = data.get('time_of_day')  # Override the current time of day
    ignore_seasonal = data.get('ignore_seasonal', False)  # Ignore seasonal factors
    
    # Validate optional parameters
    if time_of_day and time_of_day not in ['morning', 'midday', 'evening', 'late_night']:
        return jsonify({'error': 'time_of_day must be one of: morning, midday, evening, late_night'}), 400
    
    # Get current context for enhanced recommendations
    current_time_period = time_of_day if time_of_day else get_time_of_day()
    current_month = datetime.now().month
    
    try:
        # Get recommendations for the provided product IDs
        recommendations = get_recommendations(product_ids, limit, min_confidence)
        
        if not recommendations:
            return jsonify({
                'recommendations': [],
                'message': 'No recommendations found for the given products',
                'context': {
                    'algorithm_version': '3.0',
                    'time_of_day': current_time_period,
                    'current_month': current_month,
                    'seasonal_boost_applied': not ignore_seasonal,
                    'time_boost_applied': time_of_day is not None
                }
            }), 404
        
        # Return recommendations with enhanced context information
        return jsonify({
            'recommendations': recommendations,
            'context': {
                'algorithm_version': '3.0',
                'time_of_day': current_time_period,
                'current_month': current_month,
                'seasonal_boost_applied': not ignore_seasonal,
                'time_boost_applied': True
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return jsonify({'error': 'Failed to get recommendations', 'details': str(e)}), 500


@api_bp.route('/transactions', methods=['POST'])
@api_key_required
def upload_transactions():
    """
    Upload transaction data for recommendation training
    ---
    tags:
      - Data Management
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - transactions
          properties:
            transactions:
              type: array
              items:
                type: object
                required:
                  - transaction_id
                  - products
                properties:
                  transaction_id:
                    type: string
                  timestamp:
                    type: string
                    format: date-time
                  products:
                    type: array
                    items:
                      type: string
                  metadata:
                    type: object
    responses:
      202:
        description: Transactions accepted for processing
      400:
        description: Invalid request data
    """
    data = request.json
    if not data or 'transactions' not in data:
        return jsonify({'error': 'Missing transactions parameter'}), 400
    
    transactions = data.get('transactions', [])
    if not transactions or not isinstance(transactions, list):
        return jsonify({'error': 'transactions must be a non-empty array'}), 400
    
    # Get current user ID from API key
    api_key = request.headers.get('X-API-Key')
    api_key_obj = ApiKey.query.filter_by(key=api_key, active=True).first()
    user_id = api_key_obj.user_id
    
    try:
        # Process the transactions asynchronously
        # In a real production environment, this would be a background job
        job_id = batch_process_transactions(transactions, user_id)
        
        return jsonify({
            'status': 'accepted',
            'message': 'Transactions accepted for processing',
            'job_id': job_id
        }), 202
    
    except Exception as e:
        logger.error(f"Error processing transactions: {str(e)}")
        return jsonify({'error': 'Failed to process transactions', 'details': str(e)}), 500


@api_bp.route('/products', methods=['POST'])
@api_key_required
def add_products():
    """
    Add or update product data
    ---
    tags:
      - Data Management
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - products
          properties:
            products:
              type: array
              items:
                type: object
                required:
                  - product_id
                  - name
                properties:
                  product_id:
                    type: string
                  name:
                    type: string
                  category:
                    type: string
                  subcategory:
                    type: string
                  metadata:
                    type: object
    responses:
      200:
        description: Products added or updated successfully
      400:
        description: Invalid request data
    """
    data = request.json
    if not data or 'products' not in data:
        return jsonify({'error': 'Missing products parameter'}), 400
    
    products = data.get('products', [])
    if not products or not isinstance(products, list):
        return jsonify({'error': 'products must be a non-empty array'}), 400
    
    # Get current user ID from API key
    api_key = request.headers.get('X-API-Key')
    api_key_obj = ApiKey.query.filter_by(key=api_key, active=True).first()
    user_id = api_key_obj.user_id
    
    try:
        added = 0
        updated = 0
        
        for product_data in products:
            product_id = product_data.get('product_id')
            if not product_id:
                continue
                
            # Check if product already exists
            product = Product.query.filter_by(product_id=product_id).first()
            
            if product:
                # Update existing product
                product.name = product_data.get('name', product.name)
                product.category = product_data.get('category', product.category)
                product.subcategory = product_data.get('subcategory', product.subcategory)
                
                # Update product_metadata if provided
                if 'metadata' in product_data:
                    product.product_metadata = product_data['metadata']
                
                updated += 1
            else:
                # Create new product
                product = Product(
                    product_id=product_id,
                    name=product_data.get('name', 'Unknown'),
                    category=product_data.get('category'),
                    subcategory=product_data.get('subcategory'),
                    product_metadata=product_data.get('metadata', {}),
                    created_by=user_id
                )
                db.session.add(product)
                added += 1
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'added': added,
            'updated': updated,
            'total': added + updated
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding products: {str(e)}")
        return jsonify({'error': 'Failed to add products', 'details': str(e)}), 500


@api_bp.route('/jobs/<int:job_id>', methods=['GET'])
@api_key_required
def get_job_status(job_id):
    """
    Get status of a recommendation generation job
    ---
    tags:
      - Data Management
    parameters:
      - name: job_id
        in: path
        type: integer
        required: true
        description: ID of the job to check
    responses:
      200:
        description: Job status information
      404:
        description: Job not found
    """
    from models import RecommendationJob
    
    # Get current user ID from API key
    api_key = request.headers.get('X-API-Key')
    api_key_obj = ApiKey.query.filter_by(key=api_key, active=True).first()
    user_id = api_key_obj.user_id
    
    job = RecommendationJob.query.filter_by(id=job_id, user_id=user_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    result = {
        'job_id': job.id,
        'status': job.status,
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
    }
    
    if job.status == 'completed':
        result['result_stats'] = job.result_stats
    elif job.status == 'failed':
        result['error'] = job.error
    
    return jsonify(result), 200


@api_bp.route('/config', methods=['GET', 'PUT'])
@api_key_required
def manage_config():
    """
    Get or update API configuration
    ---
    tags:
      - Configuration
    parameters:
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            min_confidence:
              type: number
              description: Minimum confidence for recommendations
              example: 0.1
            min_support:
              type: number
              description: Minimum support for recommendations
              example: 0.01
            max_recommendations:
              type: integer
              description: Default maximum recommendations to return
              example: 5
    responses:
      200:
        description: Current configuration
      400:
        description: Invalid configuration data
    """
    # Get current API key
    api_key = request.headers.get('X-API-Key')
    api_key_obj = ApiKey.query.filter_by(key=api_key, active=True).first()
    
    if request.method == 'GET':
        # Return current configuration
        config = api_key_obj.config or {
            'min_confidence': 0.1,
            'min_support': 0.01,
            'max_recommendations': 5
        }
        return jsonify(config), 200
    
    else:  # PUT
        data = request.json
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        # Get current config and update with new values
        current_config = api_key_obj.config or {}
        
        # Update config with new values
        for key, value in data.items():
            current_config[key] = value
        
        # Save updated config
        api_key_obj.config = current_config
        db.session.commit()
        
        return jsonify(current_config), 200
