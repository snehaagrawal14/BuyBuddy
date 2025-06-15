from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FloatField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, EqualTo
from werkzeug.security import generate_password_hash
import json
import secrets
from flask_login import login_user as flask_login_user, logout_user, login_required, current_user
from app import db
from models import User, ApiKey, Product
from auth import register_user, login_user as auth_login_user, create_api_key, revoke_api_key
from recommendation import generate_recommendations

# Create demo blueprint
demo_bp = Blueprint('demo', __name__, template_folder='templates')


class LoginForm(FlaskForm):
    """Login form"""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class RegisterForm(FlaskForm):
    """Registration form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])


class ProductForm(FlaskForm):
    """Product form"""
    product_id = StringField('Product ID', validators=[DataRequired()])
    name = StringField('Product Name', validators=[DataRequired()])
    category = StringField('Category', validators=[Optional()])
    subcategory = StringField('Subcategory', validators=[Optional()])
    metadata = TextAreaField('Metadata (JSON)', validators=[Optional()])


class ConfigForm(FlaskForm):
    """Configuration form"""
    min_confidence = FloatField('Minimum Confidence', validators=[
        DataRequired(), NumberRange(min=0.01, max=1.0)
    ], default=0.1)
    min_support = FloatField('Minimum Support', validators=[
        DataRequired(), NumberRange(min=0.001, max=1.0)
    ], default=0.01)
    max_recommendations = IntegerField('Max Recommendations', validators=[
        DataRequired(), NumberRange(min=1, max=20)
    ], default=5)


class ProfileForm(FlaskForm):
    """User profile form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=120)])
    current_password = PasswordField('Current Password', validators=[Optional(), Length(min=8)])
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(), 
        EqualTo('new_password', message='Passwords must match')
    ])


@demo_bp.route('/')
@login_required
def index():
    """Demo homepage"""
    return render_template('index.html')


@demo_bp.route('/dashboard')
@login_required
def dashboard():
    """Demo dashboard with enhanced information"""
    # Get current time information
    from datetime import datetime
    from recommendation import get_time_of_day
    
    # Get sample product data for the demo
    products = Product.query.all()
    
    # Get user API keys
    api_keys = ApiKey.query.filter_by(user_id=current_user.id, active=True).all()
    
    # Get time of day for context-aware recommendations
    time_of_day = get_time_of_day()
    now = datetime.now()
    
    return render_template('dashboard.html', 
                          products=products, 
                          user=current_user,
                          api_keys=api_keys,
                          time_of_day=time_of_day,
                          now=now)


@demo_bp.route('/documentation')
@login_required
def documentation():
    """API documentation"""
    return render_template('documentation.html')


@demo_bp.route('/sample', methods=['GET', 'POST'])
@login_required
def sample_recommendations():
    """Sample recommendation demo with enhanced features"""
    # Get current time and date information for context
    import logging
    from datetime import datetime
    from recommendation import get_time_of_day
    
    # Configure logging
    logger = logging.getLogger(__name__)
    
    current_time = datetime.now()
    time_of_day = get_time_of_day()
    month_name = current_time.strftime('%B')
    
    # Create context object to display current recommendation factors
    context = {
        'current_time': current_time.strftime('%H:%M'),
        'time_of_day': time_of_day.title(),
        'current_date': current_time.strftime('%Y-%m-%d'),
        'current_month': month_name,
        'algorithm_version': '3.0'
    }
    
    # Get featured categories based on time of day and season
    if time_of_day == 'morning':
        featured_categories = ['Breakfast Cereals', 'Dairy', 'Coffee & Tea', 'Breakfast']
    elif time_of_day == 'midday':
        featured_categories = ['Bakery', 'Deli', 'Produce', 'Lunch Meats']
    elif time_of_day == 'evening':
        featured_categories = ['Dinner Ingredients', 'Meat', 'Pasta & Rice', 'Produce']
    else:  # late_night
        featured_categories = ['Snacks', 'Frozen Foods', 'Ice Cream', 'Candy']
    
    # Add seasonal categories for current month
    if month_name in ['December']:
        featured_categories.extend(['Holiday Foods', 'Christmas Candy', 'Baking Supplies'])
    elif month_name in ['January']:
        featured_categories.extend(['Healthy Foods', 'Diet Products', 'Detox Products'])
    elif month_name in ['February']:
        featured_categories.extend(['Valentine Candy', 'Chocolate', 'Wine'])
    elif month_name in ['March', 'April']:
        featured_categories.extend(['Spring Cleaning', 'Gardening', 'Fresh Produce'])
    elif month_name in ['May']:
        featured_categories.extend(['Grilling', 'Outdoor Dining', 'Picnic Supplies'])
    elif month_name in ['June', 'July', 'August']:
        featured_categories.extend(['Grilling', 'Ice Cream', 'Cold Beverages'])
    elif month_name in ['September']:
        featured_categories.extend(['Back to School', 'Lunch Box Items', 'Quick Dinner Ingredients'])
    elif month_name in ['October']:
        featured_categories.extend(['Halloween Candy', 'Pumpkin Products', 'Fall Decorating'])
    elif month_name in ['November']:
        featured_categories.extend(['Thanksgiving Foods', 'Turkey', 'Pumpkin Pie'])
    
    # Keep unique categories only
    featured_categories = list(set(featured_categories))
    
    # Handle form submission
    if request.method == 'POST':
        # Get selected products from form
        selected_products = request.form.getlist('products')
        
        if not selected_products:
            flash('Please select at least one product', 'warning')
            return redirect(url_for('demo.sample_recommendations'))
        
        # Get enhanced recommendations with time and seasonal boosting
        from recommendation import get_recommendations
        # Note: Check if the get_recommendations function accepts time_of_day parameter
        try:
            recommendations = get_recommendations(
                selected_products, 
                limit=8,  # Increased limit for more recommendations
                min_confidence=0.05  # Lower threshold to show more recommendations
            )
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            flash(f"Error getting recommendations: {str(e)}", "danger")
            recommendations = []
        
        # If no recommendations, show empty state
        if not recommendations:
            flash('No recommendations found for selected products', 'info')
        
        # Get all products for selection with featured categories highlighted
        products = Product.query.all()
        
        # Get the names of selected products for display
        selected_product_names = []
        for product in products:
            if product.product_id in selected_products:
                selected_product_names.append(product.name)
        
        # Count total recommended products
        total_recommendations = 0
        for rec in recommendations:
            total_recommendations += len(rec.get('recommended_products', []))
        
        # Add recommendation stats to context as strings
        context['total_recommendations'] = str(total_recommendations)
        context['seasonal_boost_applied'] = "True"
        context['time_boost_applied'] = "True"
        
        return render_template(
            'demo.html', 
            products=products, 
            recommendations=recommendations,
            selected=selected_products, 
            selected_names=selected_product_names,
            featured_categories=featured_categories,
            context=context
        )
    
    # GET request - show form with popular products pre-selected
    # Get popular products from different categories for better recommendations
    popular_products = []
    
    # Try to get a few products from each featured category
    for category in featured_categories:
        category_products = Product.query.filter(
            Product.category.ilike(f"%{category}%")
        ).limit(2).all()
        
        for product in category_products:
            if product.product_id not in [p.product_id for p in popular_products]:
                popular_products.append(product)
                
                # Limit to 5 featured products
                if len(popular_products) >= 5:
                    break
                    
        if len(popular_products) >= 5:
            break
    
    # If we couldn't find enough featured products, get any products
    if len(popular_products) < 5:
        remaining = 5 - len(popular_products)
        additional_products = Product.query.filter(
            ~Product.product_id.in_([p.product_id for p in popular_products])
        ).limit(remaining).all()
        
        popular_products.extend(additional_products)
    
    # Get all products for the selection dropdown
    all_products = Product.query.all()
    
    # Sort popular products by name for consistency
    popular_products.sort(key=lambda x: x.name)
    
    return render_template(
        'demo.html', 
        products=all_products, 
        popular_products=popular_products,
        featured_categories=featured_categories,
        context=context
    )


@demo_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    # If already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('demo.dashboard'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        # Use the auth login function to check credentials
        result, status = auth_login_user(form.username.data, form.password.data)
        
        if status == 200:
            # Get user from database
            user = User.query.filter_by(username=form.username.data).first()
            if user:
                # Use Flask-Login to create user session
                flask_login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('demo.dashboard'))
        else:
            flash(result.get('error', 'Login failed'), 'danger')
    
    return render_template('login.html', form=form)


@demo_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    # If already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('demo.dashboard'))
        
    form = RegisterForm()
    
    if form.validate_on_submit():
        result, status = register_user(
            form.username.data,
            form.email.data,
            form.password.data,
            form.company_name.data
        )
        
        if status == 201:
            # Get the newly created user and log them in
            user = User.query.filter_by(username=form.username.data).first()
            if user:
                # Use Flask-Login to create user session
                flask_login_user(user)
                flash('Registration successful! Your API key has been generated.', 'success')
                return redirect(url_for('demo.dashboard'))
            else:
                flash('Registration successful but login failed. Please login manually.', 'warning')
                return redirect(url_for('demo.login'))
        else:
            flash(result.get('error', 'Registration failed'), 'danger')
    
    return render_template('register.html', form=form)


@demo_bp.route('/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    """Add product page"""
    form = ProductForm()
    
    if form.validate_on_submit():
        # Parse metadata JSON
        metadata = {}
        if form.metadata.data:
            try:
                metadata = json.loads(form.metadata.data)
            except json.JSONDecodeError:
                flash('Invalid JSON in metadata field', 'danger')
                return render_template('add_product.html', form=form)
        
        # Check if product already exists
        existing = Product.query.filter_by(product_id=form.product_id.data).first()
        
        if existing:
            # Update existing product
            existing.name = form.name.data
            existing.category = form.category.data
            existing.subcategory = form.subcategory.data
            existing.product_metadata = metadata
            db.session.commit()
            flash('Product updated successfully', 'success')
        else:
            # Create new product
            product = Product()
            product.product_id = form.product_id.data
            product.name = form.name.data
            product.category = form.category.data
            product.subcategory = form.subcategory.data
            product.product_metadata = metadata
            db.session.add(product)
            db.session.commit()
            flash('Product added successfully', 'success')
        
        return redirect(url_for('demo.dashboard'))
    
    return render_template('add_product.html', form=form)


@demo_bp.route('/api-keys')
@login_required
def api_keys():
    """Manage API keys"""
    # Get actual API keys for the logged-in user
    user_keys = ApiKey.query.filter_by(user_id=current_user.id, active=True).all()
    
    # Create a new API key if the user has none
    if not user_keys:
        new_key = ApiKey()
        new_key.key = 'user_' + secrets.token_hex(16)
        new_key.name = 'Default API Key'
        new_key.user_id = current_user.id
        new_key.config = {
            'min_confidence': 0.1,
            'min_support': 0.01,
            'max_recommendations': 5
        }
        db.session.add(new_key)
        db.session.commit()
        flash('Created a new API key for your account', 'success')
        user_keys = [new_key]
    
    return render_template('api_keys.html', keys=user_keys)


@demo_bp.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    """Configuration page"""
    form = ConfigForm()
    
    if form.validate_on_submit():
        # In a real application, this would update the user's configuration
        flash('Configuration updated successfully', 'success')
        return redirect(url_for('demo.dashboard'))
    
    return render_template('config.html', form=form)


@demo_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    form = ProfileForm()
    
    # Pre-populate form with user data
    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.company_name.data = current_user.company_name
    
    if form.validate_on_submit():
        # If current password is provided, verify it
        if form.current_password.data:
            # Check if password matches
            from werkzeug.security import check_password_hash
            if not check_password_hash(current_user.password_hash, form.current_password.data):
                flash('Current password is incorrect', 'danger')
                return render_template('profile.html', form=form)
            
            # If new password is provided, update it
            if form.new_password.data:
                current_user.password_hash = generate_password_hash(form.new_password.data)
        
        # Update other fields
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.company_name = form.company_name.data
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('demo.dashboard'))
    
    return render_template('profile.html', form=form)


@demo_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account"""
    # Get the password from form
    password = request.form.get('password', '')
    
    # Verify password
    from werkzeug.security import check_password_hash
    if not check_password_hash(current_user.password_hash, password):
        flash('Password is incorrect', 'danger')
        return redirect(url_for('demo.profile'))
    
    # Delete user's API keys
    ApiKey.query.filter_by(user_id=current_user.id).delete()
    
    # Store user ID for flashing message
    user_id = current_user.id
    
    # Logout user
    logout_user()
    
    # Delete user
    User.query.filter_by(id=user_id).delete()
    db.session.commit()
    
    flash('Your account has been deleted', 'success')
    return redirect(url_for('demo.login'))


@demo_bp.route('/logout')
def logout():
    """Logout user and redirect to home"""
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('demo.index'))


@demo_bp.route('/generate-sample-data')
@login_required
def generate_sample_data():
    """Generate sample data for the demo"""
    # Check if we already have sample data
    if Product.query.count() > 0:
        flash('Sample data already exists', 'info')
        return redirect(url_for('demo.dashboard'))
    
    # Create sample products
    sample_products = [
        {'product_id': 'P001', 'name': 'Milk', 'category': 'Dairy'},
        {'product_id': 'P002', 'name': 'Bread', 'category': 'Bakery'},
        {'product_id': 'P003', 'name': 'Eggs', 'category': 'Dairy'},
        {'product_id': 'P004', 'name': 'Cheese', 'category': 'Dairy'},
        {'product_id': 'P005', 'name': 'Butter', 'category': 'Dairy'},
        {'product_id': 'P006', 'name': 'Apple', 'category': 'Fruits'},
        {'product_id': 'P007', 'name': 'Banana', 'category': 'Fruits'},
        {'product_id': 'P008', 'name': 'Chicken', 'category': 'Meat'},
        {'product_id': 'P009', 'name': 'Beef', 'category': 'Meat'},
        {'product_id': 'P010', 'name': 'Rice', 'category': 'Grains'},
        {'product_id': 'P011', 'name': 'Pasta', 'category': 'Grains'},
        {'product_id': 'P012', 'name': 'Tomato', 'category': 'Vegetables'},
        {'product_id': 'P013', 'name': 'Onion', 'category': 'Vegetables'},
        {'product_id': 'P014', 'name': 'Potato', 'category': 'Vegetables'},
        {'product_id': 'P015', 'name': 'Cereal', 'category': 'Breakfast'},
    ]
    
    for p in sample_products:
        product = Product()
        product.product_id = p['product_id']
        product.name = p['name']
        product.category = p['category']
        db.session.add(product)
    
    # Create a test user
    user = User.query.filter_by(username='demo').first()
    if not user:
        user = User()
        user.username = 'demo'
        user.email = 'demo@example.com'
        user.password_hash = generate_password_hash('password')
        user.company_name = 'Demo Company'
        db.session.add(user)
        db.session.flush()
        
        # Create API key for the user
        api_key = ApiKey()
        api_key.key = 'demo_' + secrets.token_hex(16)
        api_key.name = 'Demo API Key'
        api_key.user_id = user.id
        db.session.add(api_key)
    
    db.session.commit()
    
    # Generate sample recommendations
    from utils import generate_sample_transactions
    generate_sample_transactions(user.id)
    
    flash('Sample data generated successfully', 'success')
    return redirect(url_for('demo.dashboard'))
