"""
Main entry point for the Flask application
"""
import sys
import os
from flask import Flask, render_template, send_from_directory # type: ignore

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入蓝图 - 使用try-except以兼容不同环境
try:
    # 尝试相对导入（本地开发）
    from routes.api_key import api_key_bp
    from routes.feedback import feedback_bp
    from routes.advanced import advanced_bp
except ImportError:
    # 如果相对导入失败，尝试绝对导入（Vercel部署）
    from src.routes.api_key import api_key_bp
    from src.routes.feedback import feedback_bp
    from src.routes.advanced import advanced_bp

# Create Flask app with correct static folder
app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Register blueprints
app.register_blueprint(api_key_bp)
app.register_blueprint(feedback_bp)
app.register_blueprint(advanced_bp)

# 使用threading作为默认异步模式
async_mode = 'threading'

# 页面路由
@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/advanced')
def advanced_analysis():
    return render_template('advanced_analysis.html')
    
@app.route('/health')
def health_monitor():
    return render_template('health_monitor.html')

# 添加新路由来提供修复脚本
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# 添加一个修复按钮的路由
@app.route('/fix-buttons')
def fix_buttons():
    return render_template('button_fix.html')

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
