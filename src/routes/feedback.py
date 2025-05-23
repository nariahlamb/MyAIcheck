"""
用户反馈处理模块
"""
import json
import os
import time
from datetime import datetime
from flask import Blueprint, request, jsonify
from src.utils.error_handler import handle_errors, APIError
from src.utils.logging_util import setup_logger

# 创建蓝图
feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')

# 设置日志记录器
logger = setup_logger(name="feedback")

# 反馈数据存储路径
# 检测是否在Vercel环境中
is_vercel = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV') is not None

if is_vercel:
    # 在Vercel环境中使用内存存储
    FEEDBACK_DIR = None
    # 用于存储反馈的内存存储
    feedback_storage = []
else:
    # 本地环境使用文件系统
    FEEDBACK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'feedback')
    try:
        os.makedirs(FEEDBACK_DIR, exist_ok=True)
    except OSError:
        logger.warning(f"无法创建反馈目录: {FEEDBACK_DIR}, 切换到内存存储")
        FEEDBACK_DIR = None
        feedback_storage = []

@feedback_bp.route('/submit', methods=['POST'])
@handle_errors
def submit_feedback():
    """处理用户提交的反馈"""
    try:
        data = request.json
        
        # 必需字段验证
        if not data:
            raise APIError("无效的请求数据", status_code=400)
            
        feedback_type = data.get('type', '').strip()
        feedback_content = data.get('content', '').strip()
        
        if not feedback_type or not feedback_content:
            raise APIError("反馈类型和内容不能为空", status_code=400)
            
        # 可选字段
        email = data.get('email', '').strip()
        rating = data.get('rating')
        
        # 准备反馈数据
        feedback_data = {
            'type': feedback_type,
            'content': feedback_content,
            'timestamp': datetime.now().isoformat(),
            'ip': request.remote_addr
        }
        
        # 添加可选字段
        if email:
            feedback_data['email'] = email
        if rating is not None:
            feedback_data['rating'] = rating
            
        # 生成唯一ID
        timestamp = int(time.time())
        feedback_id = f"feedback_{timestamp}"
        
        # 根据环境选择存储方式
        if FEEDBACK_DIR is not None:
            # 文件系统存储
            try:
                filename = f"{feedback_id}.json"
                filepath = os.path.join(FEEDBACK_DIR, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(feedback_data, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"收到新反馈: {feedback_type} | 评分: {rating} | 文件: {filename}")
            except (OSError, IOError) as e:
                # 如果无法写入文件，切换到内存存储
                logger.warning(f"无法写入反馈文件: {str(e)}, 切换到内存存储")
                global feedback_storage
                if 'feedback_storage' not in globals():
                    feedback_storage = []
                feedback_data['id'] = feedback_id
                feedback_storage.append(feedback_data)
        else:
            # 内存存储
            feedback_data['id'] = feedback_id
            feedback_storage.append(feedback_data)
            logger.info(f"收到新反馈: {feedback_type} | 评分: {rating} | ID: {feedback_id}")
        
        return jsonify({
            'success': True,
            'message': '反馈提交成功',
            'feedbackId': timestamp
        })
    
    except Exception as e:
        logger.error(f"处理反馈时出错: {str(e)}")
        raise APIError("处理反馈时出错", details={'error': str(e)})
        

@feedback_bp.route('/recent', methods=['GET'])
@handle_errors
def get_recent_feedback():
    """获取最近的反馈，仅供管理员使用"""
    # 简单的API密钥验证(实际生产中应使用更安全的方法)
    api_key = request.headers.get('X-Admin-Key')
    if not api_key or api_key != os.environ.get('ADMIN_API_KEY', 'default_admin_key'):
        raise APIError("未授权", status_code=401)
        
    try:
        limit = min(int(request.args.get('limit', 10)), 50)
        
        # 根据存储方式获取反馈
        recent_feedback = []
        
        if FEEDBACK_DIR is not None and os.path.exists(FEEDBACK_DIR):
            try:
                # 从文件系统加载
                feedback_files = [f for f in os.listdir(FEEDBACK_DIR) if f.endswith('.json')]
                feedback_files.sort(reverse=True)  # 最新的在前
                
                # 加载最新的反馈
                for filename in feedback_files[:limit]:
                    try:
                        filepath = os.path.join(FEEDBACK_DIR, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            feedback_data = json.load(f)
                            feedback_data['id'] = filename.replace('feedback_', '').replace('.json', '')
                            recent_feedback.append(feedback_data)
                    except (IOError, json.JSONDecodeError) as e:
                        logger.error(f"读取反馈文件失败 {filename}: {str(e)}")
                        continue
            except OSError as e:
                logger.error(f"读取反馈目录失败: {str(e)}")
        else:
            # 从内存获取
            global feedback_storage
            if 'feedback_storage' in globals() and feedback_storage:
                # 按时间戳排序（假设每个反馈有ID格式为 feedback_TIMESTAMP）
                sorted_feedback = sorted(feedback_storage, 
                                       key=lambda x: int(x.get('id', '').replace('feedback_', '')) if x.get('id', '').startswith('feedback_') else 0, 
                                       reverse=True)
                recent_feedback = sorted_feedback[:limit]
                
        return jsonify({
            'success': True,
            'count': len(recent_feedback),
            'feedback': recent_feedback
        })
        
    except Exception as e:
        logger.error(f"获取反馈时出错: {str(e)}")
        raise APIError("获取反馈时出错", details={'error': str(e)})