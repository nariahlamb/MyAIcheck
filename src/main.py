"""
Main entry point for the Flask application
"""
import sys
import os
from flask import Flask, render_template # type: ignore
from src.routes.api_key import api_key_bp

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Create Flask app with correct static folder
app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Register blueprints
app.register_blueprint(api_key_bp)

# 使用threading作为默认异步模式
async_mode = 'threading'

# Main route
@app.route('/')
def index():
    return render_template('index.html')

# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template('error.html', error='File too large, maximum size is 16MB'), 413

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', error='Internal server error'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
