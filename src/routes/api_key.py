"""
Routes for the OpenAI API key validator application
"""
from flask import Blueprint, request, jsonify, render_template, send_file
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from src.models.api_key import OpenAIKeyValidator
from src.models.claude_key import ClaudeKeyValidator 
from src.models.gemini_key import GeminiKeyValidator

# Create blueprint
api_key_bp = Blueprint('api_key', __name__)

# 创建线程池，减少最大工作线程数
executor = ThreadPoolExecutor(max_workers=3)

# API验证器映射
API_VALIDATORS = {
    'openai': OpenAIKeyValidator,
    'claude': ClaudeKeyValidator,
    'gemini': GeminiKeyValidator
}

@api_key_bp.route('/validate', methods=['POST'])
def validate_keys():
    """
    Endpoint to validate API keys
    """
    try:
        # Get input method
        input_method = request.form.get('input_method', 'text')
        # 获取API类型
        api_type = request.form.get('api_type', 'openai')
        
        # 检查API类型是否支持
        if api_type not in API_VALIDATORS:
            return jsonify({'error': f'不支持的API类型: {api_type}'}), 400
            
        # 获取对应的验证器
        validator = API_VALIDATORS[api_type]
        
        api_keys = []
        
        # Process input based on method
        if input_method == 'text':
            # Get keys from text input
            input_text = request.form.get('keys', '')
            api_keys = validator.parse_input_keys(input_text)
        elif input_method == 'file':
            # Get keys from uploaded file
            if 'file' not in request.files:
                return jsonify({'error': '没有上传文件'}), 400
                
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': '文件名为空'}), 400
                
            # Read file content
            file_content = file.read()
            api_keys = validator.parse_csv_file(file_content)
        
        # Validate keys
        if not api_keys:
            return jsonify({'error': '输入中未找到API密钥'}), 400
            
        # 限制单次验证的密钥数量，避免超时
        if len(api_keys) > 100:
            return jsonify({'error': 'API密钥太多。每个请求最多100个。'}), 400
            
        # 调整批处理大小，避免并发过多
        batch_size = min(3, max(1, len(api_keys) // 50))  # Dynamic batch sizing
        
        # 使用同步方式处理，增加超时控制
        def run_validation():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(validator.validate_keys_batch(api_keys, batch_size))
            finally:
                loop.close()
        
        # 在线程池中执行异步操作，添加超时控制
        future = executor.submit(run_validation)
        try:
            # 设置超时时间，根据密钥数量动态调整，但不超过60秒避免Vercel超时
            timeout = min(60, max(30, len(api_keys) * 1.5))  # 至少30秒，每个密钥额外1.5秒，最多60秒
            results = future.result(timeout=timeout)
        except TimeoutError:
            return jsonify({
                'error': '验证超时。请减少API密钥数量或稍后重试。',
                'tip': '如果全部为网络错误，可能是Vercel服务器无法连接到API。请尝试使用浏览器端验证。'
            }), 504
        except Exception as e:
            return jsonify({'error': f'验证失败: {str(e)}'}), 500
        
        # 如果所有密钥都是网络错误，添加特殊提示
        all_network_errors = all(r.get('error_code') in ['NETWORK_ERROR', 'CONNECTION_ERROR'] for r in results)
        
        # Return results
        response_data = {
            'total': len(results),
            'valid': sum(1 for r in results if r['valid']),
            'invalid': sum(1 for r in results if not r['valid']),
            'results': results
        }
        
        # 添加帮助信息
        if all_network_errors:
            response_data['network_issue'] = True
            response_data['message'] = '检测到Vercel服务器可能无法连接到API。建议使用浏览器端验证。'
        
        return jsonify(response_data)
    except Exception as e:
        # 全局异常处理
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@api_key_bp.route('/export', methods=['POST'])
def export_keys():
    """
    Endpoint to export validation results as CSV
    """
    try:
        # Get export options
        include_details = request.form.get('include_details', 'true') == 'true'
        
        # Get results from request
        results_data = request.json
        if not results_data or 'results' not in results_data:
            return jsonify({'error': '未提供结果数据'}), 400
            
        results = results_data['results']
        
        # Generate CSV
        api_type = request.form.get('api_type', 'openai')
        validator = API_VALIDATORS.get(api_type, OpenAIKeyValidator)
        csv_content = validator.generate_csv(results, include_details)
        
        # Create in-memory file
        buffer = io.BytesIO()
        buffer.write(csv_content.encode('utf-8'))
        buffer.seek(0)
        
        # Send file
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'{api_type}_api_keys_validation.csv',
            mimetype='text/csv'
        )
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500

@api_key_bp.route('/')
def index():
    """
    Main page
    """
    return render_template('index.html')
