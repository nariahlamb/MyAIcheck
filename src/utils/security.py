"""
安全性工具模块，用于加强API密钥处理和验证过程的安全性
"""
import hashlib
import re
import secrets
import string
from typing import Dict, List, Optional


def sanitize_api_key(api_key: str) -> str:
    """
    清理和安全处理API密钥，移除可能的XSS或注入攻击向量
    
    Args:
        api_key: 未处理的API密钥
        
    Returns:
        安全处理后的API密钥
    """
    # 移除前后空白字符
    cleaned_key = api_key.strip()
    
    # 移除可能的HTML/JS注入
    cleaned_key = re.sub(r'<[^>]*>', '', cleaned_key)
    
    # 避免命令注入，只保留API密钥可能包含的合法字符
    # OpenAI密钥格式: sk-...
    # Claude密钥格式: sk_...
    # Gemini密钥格式: AIza...
    cleaned_key = re.sub(r'[^a-zA-Z0-9_\-\.]', '', cleaned_key)
    
    return cleaned_key


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """
    对API密钥进行掩码处理，只显示部分字符
    
    Args:
        api_key: 完整API密钥
        visible_chars: 前缀和后缀的可见字符数
        
    Returns:
        掩码处理后的API密钥
    """
    if not api_key or len(api_key) <= visible_chars * 2:
        return "***" 
        
    prefix = api_key[:visible_chars]
    suffix = api_key[-visible_chars:]
    masked_length = len(api_key) - (visible_chars * 2)
    
    return f"{prefix}{'*' * masked_length}{suffix}"


def generate_csrf_token() -> str:
    """
    生成随机CSRF令牌用于表单保护
    
    Returns:
        随机生成的CSRF令牌
    """
    # 生成32字节的随机数据并转换为十六进制
    return secrets.token_hex(32)


def validate_batch_size(batch_size: int, min_size: int = 1, max_size: int = 20) -> int:
    """
    验证并限制批量大小在安全范围内
    
    Args:
        batch_size: 用户请求的批量大小
        min_size: 最小允许的批量大小
        max_size: 最大允许的批量大小
        
    Returns:
        限制在安全范围内的批量大小
    """
    return max(min_size, min(batch_size, max_size))