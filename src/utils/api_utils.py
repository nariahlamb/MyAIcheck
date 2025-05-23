"""
API工具模块，提供与API密钥和端点相关的通用功能
"""
import re
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Set, Any
from .security import sanitize_api_key, mask_api_key

# 支持的API类型和对应的识别模式
API_KEY_PATTERNS = {
    "OpenAI": r'^sk-[A-Za-z0-9]{32,}$',
    "Claude": r'^sk-ant-api[0-9]{2}-[A-Za-z0-9-_]{56,}$',
    "Gemini": r'^AIza[A-Za-z0-9_-]{35,}$',
    "Cohere": r'^[A-Za-z0-9]{40,}$',
    "Mistral": r'^[A-Za-z0-9]{32,}$'
}

# 可用模型映射
MODEL_MAPPINGS = {
    "OpenAI": [
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-instruct",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "dall-e-3",
        "text-embedding-ada-002",
        "text-moderation-latest"
    ],
    "Claude": [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-2.1",
        "claude-2.0",
        "claude-instant-1.2"
    ],
    "Gemini": [
        "gemini-pro",
        "gemini-pro-vision",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "embedding-001"
    ]
}

def detect_api_type(api_key: str) -> Optional[str]:
    """
    基于密钥格式检测API类型
    
    Args:
        api_key: 要检测的API密钥
        
    Returns:
        API类型或None（如果无法识别）
    """
    clean_key = sanitize_api_key(api_key)
    
    # 尝试匹配所有已知类型的模式
    for api_type, pattern in API_KEY_PATTERNS.items():
        if re.match(pattern, clean_key):
            return api_type
            
    # 如果没有精确匹配，尝试更宽松的启发式检测
    if clean_key.startswith("sk-"):
        if len(clean_key) > 50:
            return "Claude"  # Claude密钥通常更长
        else:
            return "OpenAI"  # OpenAI密钥相对短一些
            
    if clean_key.startswith("AIza"):
        return "Gemini"
        
    # 如果无法确定
    return None
    

def get_api_provider_url(api_type: str) -> str:
    """
    获取API提供商的基础URL
    
    Args:
        api_type: API类型
        
    Returns:
        API提供商的基础URL
    """
    providers = {
        "OpenAI": "https://api.openai.com/v1",
        "Claude": "https://api.anthropic.com/v1",
        "Gemini": "https://generativelanguage.googleapis.com/v1beta",
        "Cohere": "https://api.cohere.ai/v1",
        "Mistral": "https://api.mistral.ai/v1"
    }
    
    return providers.get(api_type, "unknown")


def get_available_models(api_type: str) -> List[str]:
    """
    获取指定API类型的可用模型列表
    
    Args:
        api_type: API类型
        
    Returns:
        可用模型列表
    """
    return MODEL_MAPPINGS.get(api_type, [])


def calculate_cost_estimate(api_type: str, model: str, tokens: int) -> float:
    """
    估算API使用成本
    
    Args:
        api_type: API类型
        model: 使用的模型
        tokens: 使用的令牌数量
        
    Returns:
        估计成本（美元）
    """
    # 价格表（每1000个令牌的美元价格）
    price_per_1k = {
        "OpenAI": {
            "gpt-3.5-turbo": 0.0005,
            "gpt-3.5-turbo-instruct": 0.0015,
            "gpt-4": 0.03,
            "gpt-4-turbo": 0.01,
            "gpt-4o": 0.01,
            "text-embedding-ada-002": 0.0001
        },
        "Claude": {
            "claude-3-opus-20240229": 0.015,
            "claude-3-sonnet-20240229": 0.003,
            "claude-3-haiku-20240307": 0.00025,
            "claude-2.1": 0.008,
            "claude-2.0": 0.008
        },
        "Gemini": {
            "gemini-pro": 0.00025,
            "gemini-1.5-pro": 0.0035,
            "gemini-1.5-flash": 0.0005
        }
    }
    
    # 获取模型价格或默认值
    model_price = price_per_1k.get(api_type, {}).get(model, 0.01)
    
    # 计算成本
    return (tokens / 1000) * model_price