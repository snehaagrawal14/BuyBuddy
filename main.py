from flask import redirect, url_for
import os
import logging

# Load environment variables from .env file
from load_env import load_dotenv
load_dotenv()

# Ensure we have a session secret
if "SESSION_SECRET" not in os.environ:
    os.environ["SESSION_SECRET"] = "buybuddy-secret-key-dev-env"
    
from app import app
from api import api_bp
from demo import demo_bp

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(demo_bp)  # No prefix to make it the root of the application

# Add a root route to redirect to login page
@app.route('/')
def root():
    return redirect(url_for('demo.login'))

# Swagger docs route
@app.route('/docs')
def docs_redirect():
    return redirect('/docs/')

# Run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
