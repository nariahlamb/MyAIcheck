"""
API密钥分析器模块，提供智能检测和详细分析API密钥的功能
"""
import asyncio
import aiohttp
import json
import time
import datetime
from typing import Dict, List, Optional, Any, Tuple
from src.utils.api_utils import detect_api_type, get_api_provider_url, get_available_models
from src.utils.logging_util import setup_logger

# 设置日志记录器
logger = setup_logger(name="key_analyzer")

class KeyAnalyzer:
    """API密钥高级分析类"""
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "MyAIcheck/1.0"
        }
    
    async def analyze_key(self, api_key: str, preferred_model: Optional[str] = None) -> Dict[str, Any]:
        """
        对API密钥进行全面分析
        
        Args:
            api_key: 要分析的API密钥
            
        Returns:
            包含分析结果的字典
        """
        # 基本结果结构
        result = {
            "key": api_key[:4] + "..." + api_key[-4:],  # 安全掩码
            "valid": False,
            "api_type": None,
            "models": [],
            "rate_limits": None,
            "quota": None,
            "expiration": None,
            "organization": None,
            "capabilities": [],
            "error": None,
            "selected_model": preferred_model,
            "effective_model": None
        }
        
        # 检测API类型
        api_type = detect_api_type(api_key)
        if not api_type:
            result["error"] = "无法识别API类型"
            return result
            
        result["api_type"] = api_type
        
        # 根据不同API类型执行分析
        try:
            if api_type == "OpenAI":
                await self._analyze_openai_key(api_key, result, preferred_model=preferred_model)
            elif api_type == "Claude":
                await self._analyze_claude_key(api_key, result, preferred_model=preferred_model)
            elif api_type == "Gemini":
                await self._analyze_gemini_key(api_key, result, preferred_model=preferred_model)
            else:
                # 对于其他类型，尝试通用验证
                await self._analyze_generic_key(api_key, api_type, result)
        except Exception as e:
            logger.error(f"分析密钥时出错: {str(e)}")
            result["error"] = f"分析过程中出错: {str(e)}"
            
        return result
    
    async def _analyze_openai_key(
        self,
        api_key: str,
        result: Dict[str, Any],
        preferred_model: Optional[str] = None
    ) -> None:
        """分析OpenAI API密钥"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # 检查模型列表
            models_url = "https://api.openai.com/v1/models"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {api_key}"
            }
            
            try:
                async with session.get(models_url, headers=headers) as response:
                    if response.status == 200:
                        result["valid"] = True
                        models_data = await response.json()
                        
                        # 提取模型ID
                        if "data" in models_data:
                            result["models"] = [model["id"] for model in models_data["data"][:20]]
                            if preferred_model:
                                result["effective_model"] = preferred_model
                            
                            # 检测支持的功能
                            if any("gpt-4" in model for model in result["models"]):
                                result["capabilities"].append("GPT-4")
                            if any("dall-e" in model for model in result["models"]):
                                result["capabilities"].append("Image Generation")
                            if any("embedding" in model for model in result["models"]):
                                result["capabilities"].append("Embeddings")
                                
                    elif response.status == 401:
                        result["error"] = "无效的API密钥"
                    elif response.status == 429:
                        result["error"] = "速率限制"
                        result["valid"] = True  # 虽然被限制，但密钥有效
                    else:
                        result["error"] = f"API错误: {response.status}"
            except Exception as e:
                result["error"] = f"连接错误: {str(e)}"
                
            # 如果密钥有效，还要检查账户信息
            if result["valid"]:
                try:
                    if preferred_model:
                        chat_url = "https://api.openai.com/v1/chat/completions"
                        model_payload = {
                            "model": preferred_model,
                            "messages": [{"role": "user", "content": "Hello"}],
                            "max_tokens": 1
                        }
                        async with session.post(chat_url, headers=headers, json=model_payload) as response:
                            if response.status not in [200, 201]:
                                if response.status == 404:
                                    result["valid"] = False
                                    result["error"] = f"模型不可用: {preferred_model}"
                                elif response.status == 400:
                                    data = await response.json()
                                    message = data.get("error", {}).get("message", "")
                                    if "model" in message.lower():
                                        result["valid"] = False
                                        result["error"] = f"模型不可用: {preferred_model}"

                    # 查看账单信息以估计配额
                    subscription_url = "https://api.openai.com/dashboard/billing/subscription"
                    async with session.get(subscription_url, headers=headers) as response:
                        if response.status == 200:
                            subscription_data = await response.json()
                            if "hard_limit_usd" in subscription_data:
                                result["quota"] = f"${subscription_data['hard_limit_usd']}/月"
                            if "access_until" in subscription_data and subscription_data["access_until"]:
                                expiry = datetime.datetime.fromtimestamp(subscription_data["access_until"])
                                result["expiration"] = expiry.strftime("%Y-%m-%d")
                except Exception:
                    # 无法获取账单信息不是关键错误
                    pass
    
    async def _analyze_claude_key(
        self,
        api_key: str,
        result: Dict[str, Any],
        preferred_model: Optional[str] = None
    ) -> None:
        """分析Claude API密钥"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # Claude没有专门的模型列表端点，使用消息端点测试
            messages_url = "https://api.anthropic.com/v1/messages"
            headers = {
                **self.headers,
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # 最小测试消息
            payload = {
                "model": preferred_model or "claude-3-haiku-20240307",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hello"}]
            }
            result["effective_model"] = payload["model"]
            
            try:
                async with session.post(messages_url, headers=headers, json=payload) as response:
                    if response.status == 200 or response.status == 201:
                        result["valid"] = True
                        result["models"] = get_available_models("Claude")
                        result["capabilities"] = ["Text Generation", "Function Calling"]
                    elif response.status == 401:
                        result["error"] = "无效的API密钥"
                    elif response.status == 429:
                        result["error"] = "速率限制"
                        result["valid"] = True  # 虽然被限制，但密钥有效
                    elif response.status == 400:
                        # 有时400表示请求无效，但密钥可能有效
                        response_data = await response.json()
                        error_message = response_data.get("error", {}).get("message", "")
                        if preferred_model and "model" in error_message.lower():
                            result["error"] = f"模型不可用: {preferred_model}"
                            result["valid"] = False
                            return
                        
                        if "API key" in error_message and "invalid" in error_message:
                            result["error"] = "无效的API密钥"
                        else:
                            # 可能是请求有问题，密钥可能有效
                            result["valid"] = True
                            result["models"] = get_available_models("Claude")
                            result["error"] = "请求验证错误，密钥可能有效"
                    else:
                        result["error"] = f"API错误: {response.status}"
                        # 尝试解析错误消息
                        try:
                            error_data = await response.json()
                            result["error"] += f" - {error_data.get('error', {}).get('message')}"
                        except:
                            pass
            except Exception as e:
                result["error"] = f"连接错误: {str(e)}"
    
    async def _analyze_gemini_key(
        self,
        api_key: str,
        result: Dict[str, Any],
        preferred_model: Optional[str] = None
    ) -> None:
        """分析Gemini API密钥"""
        # 不需要完整的ClientSession对象，因为Gemini使用密钥作为URL参数
        effective_model = preferred_model or "gemini-pro"
        result["effective_model"] = effective_model
        base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{effective_model}:generateContent"
        request_url = f"{base_url}?key={api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": "Hello"}]}],
            "generationConfig": {"maxOutputTokens": 1}
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.post(request_url, json=payload) as response:
                    if response.status == 200:
                        result["valid"] = True
                        result["models"] = get_available_models("Gemini")
                        result["capabilities"] = ["Text Generation", "Image Understanding"]
                    elif response.status == 400:
                        # 检查错误细节，可能是无效密钥或其他问题
                        response_data = await response.json()
                        error = response_data.get("error", {})
                        if preferred_model and "model" in (error.get("message", "")).lower():
                            result["error"] = f"模型不可用: {preferred_model}"
                            result["valid"] = False
                            return
                        if error.get("status") == "INVALID_ARGUMENT":
                            # 可能是其他参数问题，密钥可能有效
                            result["valid"] = True
                            result["models"] = get_available_models("Gemini")
                            result["error"] = "请求参数错误，密钥可能有效"
                        else:
                            result["error"] = f"API错误: {error.get('message')}"
                    elif response.status == 403:
                        # 403通常意味着权限问题或无效密钥
                        result["error"] = "无效密钥或无权限"
                    else:
                        result["error"] = f"API错误: {response.status}"
            except Exception as e:
                result["error"] = f"连接错误: {str(e)}"
    
    async def _analyze_generic_key(self, api_key: str, api_type: str, result: Dict[str, Any]) -> None:
        """通用API密钥分析，适用于未专门处理的API类型"""
        # 获取通用API基础URL
        base_url = get_api_provider_url(api_type)
        if base_url == "unknown":
            result["error"] = f"未知的API类型: {api_type}"
            return
            
        # 通用模型列表端点（大多数API提供者）
        models_url = f"{base_url}/models"
        
        # 尝试常见的鉴权头格式
        headers_variants = [
            {"Authorization": f"Bearer {api_key}"},
            {"api-key": api_key},
            {"X-API-Key": api_key}
        ]
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # 尝试所有可能的鉴权头
            for headers in headers_variants:
                try:
                    async with session.get(models_url, headers={**self.headers, **headers}) as response:
                        if response.status == 200:
                            result["valid"] = True
                            
                            # 尝试解析模型信息
                            try:
                                data = await response.json()
                                if "data" in data and isinstance(data["data"], list):
                                    result["models"] = [item.get("id", "") for item in data["data"][:10]]
                                elif "models" in data and isinstance(data["models"], list):
                                    result["models"] = data["models"][:10]
                            except:
                                # 如果无法解析，使用默认模型列表
                                result["models"] = get_available_models(api_type) or ["未知模型"]
                                
                            # 尝试推断功能
                            if result["models"]:
                                if any("16k" in model.lower() for model in result["models"]):
                                    result["capabilities"].append("长上下文")
                                if any("vision" in model.lower() for model in result["models"]):
                                    result["capabilities"].append("图像理解")
                                    
                            # 找到有效头后退出循环
                            break
                        elif response.status == 401 or response.status == 403:
                            continue  # 尝试下一个头格式
                        else:
                            # 其他状态码可能需要进一步调查
                            continue
                except Exception:
                    continue  # 发生异常时尝试下一个头格式
            
            # 如果所有头格式都尝试过但仍未认证
            if not result["valid"] and not result["error"]:
                result["error"] = "无法验证API密钥"
                
    @staticmethod
    async def batch_analyze(api_keys: List[str], batch_size: int = 5) -> List[Dict[str, Any]]:
        """
        批量分析多个API密钥
        
        Args:
            api_keys: 要分析的API密钥列表
            batch_size: 并发分析的批量大小
            
        Returns:
            分析结果列表
        """
        analyzer = KeyAnalyzer()
        results = []
        
        # 创建限制并发的信号量
        semaphore = asyncio.Semaphore(batch_size)
        
        async def analyze_with_semaphore(key):
            async with semaphore:
                return await analyzer.analyze_key(key)
        
        # 创建分析任务
        tasks = [analyze_with_semaphore(key) for key in api_keys]
        
        # 并发执行
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        
        return results
