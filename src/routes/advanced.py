"""
高级分析功能路由模块，提供对API密钥的深度分析和健康监控功能
"""
import asyncio
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
# 导入模块 - 使用try-except以兼容不同环境
try:
    # 尝试相对导入（本地开发）
    from models.key_analyzer import KeyAnalyzer
    from models.health_checker import APIHealthChecker
    from utils.error_handler import handle_errors, APIError
    from utils.security import sanitize_api_key
    from utils.logging_util import setup_logger
except ImportError:
    # 如果相对导入失败，尝试绝对导入（Vercel部署）
    from src.models.key_analyzer import KeyAnalyzer
    from src.models.health_checker import APIHealthChecker
    from src.utils.error_handler import handle_errors, APIError
    from src.utils.security import sanitize_api_key
    from src.utils.logging_util import setup_logger

# 创建蓝图
advanced_bp = Blueprint('advanced', __name__, url_prefix='/api/advanced')

# 设置日志记录器
logger = setup_logger(name="advanced")

# 创建健康检查器实例
health_checker = APIHealthChecker()

@advanced_bp.route('/analyze', methods=['POST'])
@handle_errors
def analyze_key():
    """执行单个API密钥的深度分析"""
    try:
        data = request.json
        if not data:
            raise APIError("无效的请求数据", status_code=400)
            
        api_key = data.get('api_key', '').strip()
        check_models = data.get('check_models', True)
        check_quota = data.get('check_quota', True)
        check_performance = data.get('check_performance', False)
        
        if not api_key:
            raise APIError("API密钥不能为空", status_code=400)
            
        # 安全处理API密钥
        api_key = sanitize_api_key(api_key)
        
        # 使用密钥分析器执行分析
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        analyzer = KeyAnalyzer()
        result = loop.run_until_complete(analyzer.analyze_key(api_key))
        loop.close()
        
        # 添加分析时间戳
        result["timestamp"] = datetime.now().isoformat()
        
        # 如果未启用特定检查，移除相关字段
        if not check_models:
            result.pop("models", None)
        if not check_quota:
            result.pop("quota", None)
            result.pop("expiration", None)
        
        # 记录日志(不包含完整密钥)
        safe_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
        logger.info(f"分析密钥 {safe_key}, 类型: {result.get('api_type', '未知')}, 有效: {result.get('valid', False)}")
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        logger.error(f"分析密钥时出错: {str(e)}")
        raise APIError("分析过程中出错", details={'error': str(e)})


@advanced_bp.route('/health', methods=['GET'])
@handle_errors
def get_health_status():
    """获取所有API提供商的健康状态"""
    try:
        # 执行健康检查
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        health_data = loop.run_until_complete(health_checker.check_all_providers())
        loop.close()
        
        return jsonify({
            "success": True,
            "health": health_data
        })
        
    except Exception as e:
        logger.error(f"获取健康状态时出错: {str(e)}")
        raise APIError("获取健康状态时出错", details={'error': str(e)})


@advanced_bp.route('/health/<provider>', methods=['GET'])
@handle_errors
def get_provider_health(provider):
    """获取特定API提供商的健康状态"""
    try:
        # 执行单个提供商的健康检查
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        health_data = loop.run_until_complete(health_checker.check_specific_provider(provider))
        loop.close()
        
        return jsonify({
            "success": True,
            "health": health_data
        })
        
    except Exception as e:
        logger.error(f"获取{provider}健康状态时出错: {str(e)}")
        raise APIError(f"获取{provider}健康状态时出错", details={'error': str(e)})


@advanced_bp.route('/health/global', methods=['GET'])
@handle_errors
def get_global_health():
    """获取全球各地区的API服务健康状态"""
    try:
        # 获取全球健康状态
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        global_data = loop.run_until_complete(health_checker.get_global_status())
        loop.close()
        
        return jsonify({
            "success": True,
            "global_health": global_data
        })
        
    except Exception as e:
        logger.error(f"获取全球健康状态时出错: {str(e)}")
        raise APIError("获取全球健康状态时出错", details={'error': str(e)})


# 页面路由
@advanced_bp.route('/ui/analyze', methods=['GET'])
def analyze_page():
    """显示高级分析页面"""
    return render_template('advanced_analysis.html')


@advanced_bp.route('/ui/health', methods=['GET'])
def health_page():
    """显示健康监控页面"""
    return render_template('health_monitor.html')