"""
日志工具模块，为应用程序提供统一的日志记录功能
"""
import logging
import os
import sys
import time
from datetime import datetime
from typing import Optional, Any


def setup_logger(
    name: str = "myaicheck", 
    log_level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    配置并返回应用程序日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: 是否将日志写入文件
        log_dir: 日志文件目录
        
    Returns:
        配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 避免重复添加处理器
    if logger.hasHandlers():
        return logger
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 如果需要，还添加文件处理器
    if log_to_file:
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 基于日期的日志文件名
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"{name}_{today}.log")
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 创建默认日志记录器
default_logger = setup_logger()


def log_api_request(
    api_type: str, 
    endpoint: str, 
    status_code: Optional[int] = None,
    response_time: Optional[float] = None,
    error: Optional[str] = None,
    key_fragment: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    记录API请求信息，用于监控和审计
    
    Args:
        api_type: API类型 (OpenAI, Claude, Gemini等)
        endpoint: 请求的端点
        status_code: HTTP状态码
        response_time: 响应时间(秒)
        error: 错误信息(如有)
        key_fragment: API密钥片段(用于跟踪但不泄露完整密钥)
        logger: 要使用的日志记录器，默认使用模块级记录器
    """
    logger = logger or default_logger
    
    # 组织日志消息
    msg_parts = [f"API Request: {api_type}", f"Endpoint: {endpoint}"]
    
    if status_code:
        msg_parts.append(f"Status: {status_code}")
        
    if response_time:
        msg_parts.append(f"Time: {response_time:.2f}s")
        
    if key_fragment:
        # 只记录密钥前4个字符，用于区分不同密钥但不泄露全部
        safe_fragment = key_fragment[:4] + "..."
        msg_parts.append(f"Key: {safe_fragment}")
    
    log_message = " | ".join(msg_parts)
    
    # 根据状态码确定日志级别
    if error:
        logger.error(f"{log_message} | Error: {error}")
    elif status_code and status_code >= 400:
        logger.warning(log_message)
    else:
        logger.info(log_message)