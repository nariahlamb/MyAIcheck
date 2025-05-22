"""
Routes for the OpenAI API key validator application
"""
from flask import Blueprint, request, jsonify, render_template, send_file
import io
import threading
from concurrent.futures import ThreadPoolExecutor
from src.models.api_key import OpenAIKeyValidator

# Create blueprint
api_key_bp = Blueprint('api_key', __name__)

# 创建线程池
executor = ThreadPoolExecutor(max_workers=10)

@api_key_bp.route('/validate', methods=['POST'])
def validate_keys():
    """
    Endpoint to validate OpenAI API keys
    """
    # Get input method
    input_method = request.form.get('input_method', 'text')
    
    api_keys = []
    
    # Process input based on method
    if input_method == 'text':
        # Get keys from text input
        input_text = request.form.get('keys', '')
        api_keys = OpenAIKeyValidator.parse_input_keys(input_text)
    elif input_method == 'file':
        # Get keys from uploaded file
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty file name'}), 400
            
        # Read file content
        file_content = file.read()
        api_keys = OpenAIKeyValidator.parse_csv_file(file_content)
    
    # Validate keys
    if not api_keys:
        return jsonify({'error': 'No API keys found in input'}), 400
        
    # Validate keys with appropriate batch size based on count
    batch_size = min(20, max(5, len(api_keys) // 50))  # Dynamic batch sizing
    
    # 使用同步方式处理
    def run_validation():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(OpenAIKeyValidator.validate_keys_batch(api_keys, batch_size))
    
    # 在线程池中执行异步操作
    results = executor.submit(run_validation).result()
    
    # Return results
    return jsonify({
        'total': len(results),
        'valid': sum(1 for r in results if r['valid']),
        'invalid': sum(1 for r in results if not r['valid']),
        'results': results
    })

@api_key_bp.route('/export', methods=['POST'])
def export_keys():
    """
    Endpoint to export validation results as CSV
    """
    # Get export options
    include_details = request.form.get('include_details', 'true') == 'true'
    
    # Get results from request
    results_data = request.json
    if not results_data or 'results' not in results_data:
        return jsonify({'error': 'No results provided'}), 400
        
    results = results_data['results']
    
    # Generate CSV
    csv_content = OpenAIKeyValidator.generate_csv(results, include_details)
    
    # Create in-memory file
    buffer = io.BytesIO()
    buffer.write(csv_content.encode('utf-8'))
    buffer.seek(0)
    
    # Send file
    return send_file(
        buffer,
        as_attachment=True,
        download_name='openai_api_keys_validation.csv',
        mimetype='text/csv'
    )

@api_key_bp.route('/')
def index():
    """
    Main page
    """
    return render_template('index.html')
