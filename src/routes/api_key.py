"""
Routes for the OpenAI API key validator application
"""
from flask import Blueprint, request, jsonify, render_template, send_file
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
# 导入模型验证器 - 使用try-except以兼容不同环境
try:
    # 尝试相对导入（本地开发）
    from models.api_key import OpenAIKeyValidator
    from models.claude_key import ClaudeKeyValidator
    from models.gemini_key import GeminiKeyValidator
except ImportError:
    # 如果相对导入失败，尝试绝对导入（Vercel部署）
    from src.models.api_key import OpenAIKeyValidator
    from src.models.claude_key import ClaudeKeyValidator
    from src.models.gemini_key import GeminiKeyValidator

# 尝试导入OpenAILikeKeyValidator，如果不存在则忽略
try:
    from models.openai_like_key import OpenAILikeKeyValidator
    HAS_OPENAI_LIKE = True
except ImportError:
    try:
        from src.models.openai_like_key import OpenAILikeKeyValidator
        HAS_OPENAI_LIKE = True
    except ImportError:
        HAS_OPENAI_LIKE = False

# Create blueprint
api_key_bp = Blueprint('api_key', __name__)

# 创建线程池，减少最大工作线程数
executor = ThreadPoolExecutor(max_workers=3)

# API验证器映射
API_VALIDATORS = {
    'openai': OpenAIKeyValidator,
    'claude': ClaudeKeyValidator,
    'gemini': GeminiKeyValidator,
}

# 如果OpenAILikeKeyValidator可用，则添加到验证器映射中
if HAS_OPENAI_LIKE:
    API_VALIDATORS['openai_like'] = OpenAILikeKeyValidator

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

        # 对于 openai_like 类型，获取自定义参数
        custom_api_url = None
        custom_model_name = None
        if api_type == 'openai_like' and HAS_OPENAI_LIKE:
            custom_api_url = request.form.get('custom_api_url')
            custom_model_name = request.form.get('custom_model_name')
            if not custom_api_url or not custom_model_name:
                return jsonify({'error': '自定义API URL和模型名称是必填项。'}), 400
            if not custom_api_url.endswith('/v1'):
                return jsonify({'error': '自定义API URL必须以 /v1 结尾。'}), 400
        
        # 使用同步方式处理，增加超时控制
        def run_validation():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if api_type == 'openai_like' and HAS_OPENAI_LIKE:
                    return loop.run_until_complete(validator.validate_keys_batch(api_keys, batch_size, custom_api_url, custom_model_name))
                else:
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
        all_network_errors = all(r.get('error_code') in ['NETWORK_ERROR', 'CONNECTION_ERROR', 'TIMEOUT'] for r in results)
        
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
        # 获取请求体中的JSON数据
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        results = data.get('results')
        export_type = data.get('export_type', 'all') # 'all' or 'valid'
        api_type = data.get('api_type', 'openai')

        if results is None:
            return jsonify({'error': '未提供结果数据'}), 400

        # 确保API类型存在
        if api_type not in API_VALIDATORS:
            api_type = 'openai'  # 回退到默认类型
            
        validator = API_VALIDATORS.get(api_type)
        
        # 根据导出类型筛选结果
        if export_type == 'valid':
            results_to_export = [r for r in results if r.get('valid')]
            # 如果只导出有效密钥，则不包含错误详情
            csv_content = validator.generate_csv(results_to_export, include_details=False)
        else: # export_type == 'all'
            csv_content = validator.generate_csv(results, include_details=True)
        
        # Create in-memory file
        buffer = io.BytesIO()
        buffer.write(csv_content.encode('utf-8-sig')) # 使用utf-8-sig确保BOM头
        buffer.seek(0)
        
        # Send file
        filename = f"{api_type}_keys_validation_{export_type}.csv"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv; charset=utf-8-sig'
        )
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500

@api_key_bp.route('/models', methods=['POST'])
def get_models():
    """
    Endpoint to get available models for a specific API provider
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        api_type = data.get('api_type', 'openai')
        api_key = data.get('api_key', '')

        if not api_key:
            return jsonify({'error': 'API Key是必填项'}), 400

        # 检查API类型是否支持
        if api_type not in API_VALIDATORS:
            return jsonify({'error': f'不支持的API类型: {api_type}'}), 400

        # 获取对应的验证器
        validator = API_VALIDATORS[api_type]

        # 对于 openai_like 类型，获取自定义参数
        custom_api_url = None
        if api_type == 'openai_like' and HAS_OPENAI_LIKE:
            custom_api_url = data.get('custom_api_url')
            if not custom_api_url:
                return jsonify({'error': '自定义API URL是必填项'}), 400
            if not custom_api_url.endswith('/v1'):
                return jsonify({'error': '自定义API URL必须以 /v1 结尾'}), 400

        # 使用同步方式处理，增加超时控制
        def run_get_models():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if api_type == 'openai_like' and HAS_OPENAI_LIKE:
                    return loop.run_until_complete(validator.get_models(api_key, custom_api_url))
                else:
                    return loop.run_until_complete(validator.get_models(api_key))
            finally:
                loop.close()

        # 在线程池中执行异步操作，添加超时控制
        future = executor.submit(run_get_models)
        try:
            timeout = 30  # 30秒超时
            models_data = future.result(timeout=timeout)
        except TimeoutError:
            return jsonify({
                'error': '获取模型列表超时，请稍后重试'
            }), 504
        except Exception as e:
            return jsonify({'error': f'获取模型列表失败: {str(e)}'}), 500

        return jsonify(models_data)

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@api_key_bp.route('/export-models', methods=['POST'])
def export_models():
    """
    Endpoint to export models list to TXT file
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        api_type = data.get('api_type', 'openai')
        api_key = data.get('api_key', '')
        models_data = data.get('models_data', {})
        custom_api_url = data.get('custom_api_url', '')

        if not api_key:
            return jsonify({'error': 'API Key是必填项'}), 400

        if not models_data:
            return jsonify({'error': '模型数据不能为空'}), 400

        # 对于openai_like类型，将自定义API URL添加到models_data中
        if api_type == 'openai_like' and custom_api_url:
            models_data['api_url'] = custom_api_url

        # 生成TXT文件内容
        txt_content = generate_models_txt(api_type, api_key, models_data)

        # Create in-memory file
        buffer = io.BytesIO()
        buffer.write(txt_content.encode('utf-8-sig'))
        buffer.seek(0)

        # 生成文件名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"models_export_{api_type}_{timestamp}.txt"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain; charset=utf-8-sig'
        )

    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500

def generate_models_txt(api_type: str, api_key: str, models_data: dict) -> str:
    """
    Generate TXT content for models export - Simple format with one model per line
    """
    lines = []

    # 获取模型列表
    models = models_data.get('models', [])

    # 每个模型一行，只显示模型名称
    for model in models:
        model_name = model.get('id', 'N/A')
        lines.append(model_name)

    # 添加空行
    lines.append("")

    # 添加AI Provider信息
    provider_urls = {
        'openai': 'https://api.openai.com/v1',
        'claude': 'https://api.anthropic.com/v1',
        'gemini': 'https://generativelanguage.googleapis.com/v1beta',
        'deepseek': 'https://api.deepseek.com/v1',
        'xai': 'https://api.x.ai/v1',
        'openai_like': models_data.get('api_url', 'Custom API URL')
    }

    provider_url = provider_urls.get(api_type, f'Unknown provider: {api_type}')
    lines.append(f"AIprovider: {provider_url}")

    return '\n'.join(lines)

def mask_api_key(api_key: str) -> str:
    """
    Mask API key for security (show first 4 and last 4 characters)
    """
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}***{api_key[-4:]}"

@api_key_bp.route('/')
def index():
    """
    Main page
    """
    return render_template('index.html')
