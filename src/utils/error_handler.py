"""
错误处理模块，提供统一的异常处理机制和友好的错误响应
"""
import functools
import json
import traceback
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union
from flask import jsonify, Response

# 定义API错误类型
class APIError(Exception):
    """API错误的基类"""
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class InputValidationError(APIError):
    """输入验证错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(APIError):
    """认证错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTH_ERROR",
            details=details
        )


class RateLimitError(APIError):
    """速率限制错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT",
            details=details
        )


class NotFoundError(APIError):
    """资源未找到错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details
        )


# 错误响应生成器
def create_error_response(error: APIError) -> Tuple[Response, int]:
    """
    从API错误创建一致的错误响应
    
    Args:
        error: APIError实例
        
    Returns:
        Flask响应对象和HTTP状态码的元组
    """
    response_data = {
        "success": False,
        "error": {
            "code": error.error_code,
            "message": error.message
        }
    }
    
    # 仅在开发环境或详细日志选项启用时添加详情
    if error.details:
        response_data["error"]["details"] = error.details
        
    return jsonify(response_data), error.status_code


# 装饰器用于路由错误处理
def handle_errors(func: Callable) -> Callable:
    """
    装饰器，捕获路由处理器中的异常并返回一致的错误响应
    
    Args:
        func: 要装饰的路由处理函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except APIError as e:
            # 处理已知的API错误
            return create_error_response(e)
        except Exception as e:
            # 处理未捕获的通用错误
            error = APIError(
                message="服务器内部错误",
                status_code=500,
                error_code="INTERNAL_ERROR",
                details={"original_error": str(e)}
            )
            # 在生产环境中，可能需要记录详细错误但不返回给客户端
            return create_error_response(error)
    
    return wrapper