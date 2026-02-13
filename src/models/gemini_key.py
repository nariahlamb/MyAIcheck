"""
API Key validation model for Gemini API keys
"""
import asyncio
import aiohttp
import csv
import io
import json
import time
import random
from typing import Dict, List, Tuple, Optional


class GeminiKeyValidator:
    """Class for validating Gemini API keys in bulk"""
    
    # API endpoints - 注意Gemini使用查询参数而非Authorization头部
    PRIMARY_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    BACKUP_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent"
    
    # Test message payload
    TEST_PAYLOAD = {
        "contents": [
            {
                "parts": [
                    {"text": "Hello"}
                ]
            }
        ]
    }
    
    @staticmethod
    async def validate_single_key(
        session: aiohttp.ClientSession,
        api_key: str,
        retry_count=2,
        model: Optional[str] = None
    ) -> Dict:
        """
        Validate a single Gemini API key with retry mechanism
        
        Args:
            session: aiohttp client session
            api_key: Gemini API key to validate
            retry_count: Number of retry attempts
            
        Returns:
            Dictionary with validation result
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        effective_model = model.strip() if model else None
        result = {
            "key": api_key,
            "valid": False,
            "error_code": None,
            "error_message": None,
            "selected_model": model,
            "effective_model": None,
            "validation_path": None
        }

        if model:
            result["validation_path"] = "completion"
            result["effective_model"] = effective_model
            try:
                model_url = f"https://generativelanguage.googleapis.com/v1beta/models/{effective_model}:generateContent?key={api_key}"
                response = await session.post(
                    model_url,
                    headers=headers,
                    json=GeminiKeyValidator.TEST_PAYLOAD,
                    timeout=aiohttp.ClientTimeout(total=15)
                )

                status_code = response.status
                if status_code == 200:
                    result["valid"] = True
                elif status_code == 404:
                    result["error_code"] = "INVALID_MODEL"
                    result["error_message"] = f"模型不可用: {effective_model}"
                elif status_code in [400, 403]:
                    response_text = await response.text()
                    if "API key" in response_text:
                        result["error_code"] = "INVALID_KEY"
                        result["error_message"] = "无效的API密钥"
                    else:
                        result["error_code"] = f"HTTP_{status_code}"
                        result["error_message"] = f"请求失败: {response_text[:120]}"
                elif status_code == 429:
                    result["error_code"] = "RATE_LIMIT"
                    result["error_message"] = "Gemini API速率限制"
                else:
                    result["error_code"] = f"HTTP_{status_code}"
                    result["error_message"] = f"HTTP错误: {status_code}"
            except aiohttp.ClientConnectorError as e:
                result["error_code"] = "CONNECTION_ERROR"
                result["error_message"] = f"连接错误: {str(e)}"
            except aiohttp.ClientError as e:
                result["error_code"] = "NETWORK_ERROR"
                result["error_message"] = f"网络错误: {str(e)}"
            except asyncio.TimeoutError:
                result["error_code"] = "TIMEOUT"
                result["error_message"] = "请求超时"
            except Exception as e:
                result["error_code"] = "UNKNOWN_ERROR"
                result["error_message"] = f"未知错误: {str(e)}"
            return result
        
        # 尝试主端点 - Gemini需要在URL中添加key参数
        result["validation_path"] = "models"
        result["effective_model"] = "models-endpoint"
        for attempt in range(retry_count):
            try:
                # 添加随机延迟避免请求过于集中
                if attempt > 0:
                    await asyncio.sleep(random.uniform(1, 2))
                
                url = f"{GeminiKeyValidator.PRIMARY_API_URL}?key={api_key}"
                response = await session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                )
                
                status_code = response.status
                
                try:
                    response_text = await response.text()
                    try:
                        response_json = json.loads(response_text)
                    except:
                        response_json = {"raw_text": response_text[:100]}
                except:
                    response_text = "无法读取响应内容"
                    response_json = {}
                
                # 检查响应状态
                if status_code == 200:
                    result["valid"] = True
                    break
                elif status_code == 400 and "API key not valid" in response_text:
                    # 无效密钥
                    result["valid"] = False
                    result["error_code"] = "INVALID_KEY"
                    result["error_message"] = "无效的API密钥"
                    break
                elif status_code == 403:
                    # 无效权限或密钥
                    result["valid"] = False
                    result["error_code"] = "INVALID_KEY"
                    result["error_message"] = response_json.get("error", {}).get("message", "无效的API密钥或权限不足")
                    break
                elif status_code == 429:  # 速率限制
                    result["error_code"] = "RATE_LIMIT"
                    result["error_message"] = "Gemini API速率限制"
                    await asyncio.sleep(2)
                    continue
                else:
                    # 记录错误信息
                    result["error_code"] = f"HTTP_{status_code}"
                    error_message = response_json.get("error", {}).get("message", "未知错误")
                    result["error_message"] = f"服务器错误: {error_message}"
                    break
                    
            except aiohttp.ClientConnectorError as e:
                result["error_code"] = "CONNECTION_ERROR"
                result["error_message"] = f"连接错误: {str(e)}"
                # 切换到备用端点
                break
            except aiohttp.ClientError as e:
                result["error_code"] = "NETWORK_ERROR"
                result["error_message"] = f"网络错误: {str(e)}"
                break
            except asyncio.TimeoutError:
                result["error_code"] = "TIMEOUT"
                result["error_message"] = "请求超时"
                break
            except Exception as e:
                result["error_code"] = "UNKNOWN_ERROR"
                result["error_message"] = f"未知错误: {str(e)}"
                break
        
        # 如果主端点失败，尝试备用端点
        if not result["valid"] and result["error_code"] in ["CONNECTION_ERROR", "TIMEOUT"]:
            try:
                result["validation_path"] = "completion"
                result["effective_model"] = "gemini-2.5-flash-preview-04-17"
                # 使用POST请求验证 - 仍需在URL中添加key参数
                url = f"{GeminiKeyValidator.BACKUP_API_URL}?key={api_key}"
                response = await session.post(
                    url,
                    headers=headers,
                    json=GeminiKeyValidator.TEST_PAYLOAD,
                    timeout=aiohttp.ClientTimeout(total=15)
                )
                
                status_code = response.status
                
                if status_code == 200:
                    result["valid"] = True
                    result["error_code"] = None
                    result["error_message"] = None
                elif status_code in [400, 403] and "API key" in await response.text():
                    result["valid"] = False
                    result["error_code"] = "INVALID_KEY"
                    result["error_message"] = "无效的API密钥"
                else:
                    try:
                        error_data = await response.json()
                        result["error_code"] = f"HTTP_{status_code}"
                        result["error_message"] = error_data.get("error", {}).get("message", f"HTTP错误: {status_code}")
                    except:
                        result["error_code"] = f"HTTP_{status_code}"
                        result["error_message"] = f"HTTP错误: {status_code}"
            except Exception as e:
                result["error_code"] = "NETWORK_ERROR"
                result["error_message"] = f"网络错误: {str(e)}"
                
        return result
    
    @staticmethod
    async def validate_keys_batch(
        api_keys: List[str],
        batch_size: int = 3,
        model: Optional[str] = None
    ) -> List[Dict]:
        """
        Validate a batch of Gemini API keys with concurrency control
        
        Args:
            api_keys: List of API keys to validate
            batch_size: Number of concurrent validations
            
        Returns:
            List of dictionaries with validation results
        """
        results = []
        
        # 动态调整批量大小，避免大量并发请求
        effective_batch_size = min(batch_size, 3)  # 最大并发不超过3
        
        # 使用更长的超时时间
        timeout = aiohttp.ClientTimeout(
            total=30,         # 总超时时间
            sock_connect=10,  # 连接超时
            sock_read=20      # 读取超时
        )
        
        connector = aiohttp.TCPConnector(
            limit=effective_batch_size,  # 限制连接数
            ssl=False,                   # 禁用SSL验证加速连接
            ttl_dns_cache=300,           # DNS缓存时间
            force_close=True             # 强制关闭连接避免重用问题
        )
        
        # Create batches to control concurrency
        for i in range(0, len(api_keys), effective_batch_size):
            batch = api_keys[i:i+effective_batch_size]
            
            # 处理每个批次之间添加短暂延迟，避免请求风暴
            if i > 0:
                await asyncio.sleep(2)
                
            # Process batch concurrently
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                tasks = [GeminiKeyValidator.validate_single_key(session, key, model=model) for key in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 过滤掉可能的异常结果
                valid_results = []
                for res in batch_results:
                    if isinstance(res, Exception):
                        # 将异常转换为错误结果
                        valid_results.append({
                            "key": "unknown",
                            "valid": False,
                            "error_code": "EXCEPTION",
                            "error_message": f"处理异常: {str(res)}",
                            "selected_model": model,
                            "effective_model": None,
                            "validation_path": None
                        })
                    else:
                        valid_results.append(res)
                        
                results.extend(valid_results)
                
        return results

    @staticmethod
    async def get_models(api_key: str) -> Dict:
        """
        Get available models for the given Gemini API key

        Args:
            api_key: Gemini API key

        Returns:
            Dictionary with models data or error information
        """
        headers = {
            "Content-Type": "application/json"
        }

        timeout = aiohttp.ClientTimeout(total=15)
        connector = aiohttp.TCPConnector(ssl=False, force_close=True)

        try:
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                # Gemini需要在URL中添加key参数
                url = f"{GeminiKeyValidator.PRIMARY_API_URL}?key={api_key}"
                response = await session.get(url, headers=headers)

                if response.status == 200:
                    data = await response.json()
                    # Gemini API返回的格式可能不同，需要适配
                    models = data.get('models', [])
                    return {
                        'success': True,
                        'models': models,
                        'provider': 'gemini'
                    }
                elif response.status in [400, 403]:
                    response_text = await response.text()
                    if "API key not valid" in response_text or "API key" in response_text:
                        return {
                            'success': False,
                            'error': '无效的API密钥'
                        }
                    else:
                        return {
                            'success': False,
                            'error': '权限不足或API密钥无效'
                        }
                else:
                    error_data = await response.json()
                    return {
                        'success': False,
                        'error': error_data.get('error', {}).get('message', f'HTTP错误: {response.status}')
                    }

        except aiohttp.ClientConnectorError:
            return {
                'success': False,
                'error': '连接错误，无法访问Gemini API'
            }
        except aiohttp.ClientError as e:
            return {
                'success': False,
                'error': f'网络错误: {str(e)}'
            }
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': '请求超时'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'未知错误: {str(e)}'
            }

    @staticmethod
    def parse_input_keys(input_text: str) -> List[str]:
        """
        Parse input text to extract API keys
        
        Args:
            input_text: Text containing API keys (one per line)
            
        Returns:
            List of API keys
        """
        # Split by newline and filter out empty lines
        keys = [line.strip() for line in input_text.splitlines()]
        return [key for key in keys if key]
    
    @staticmethod
    def parse_csv_file(file_content: bytes) -> List[str]:
        """
        Parse CSV file content to extract API keys
        
        Args:
            file_content: Content of the CSV file
            
        Returns:
            List of API keys
        """
        keys = []
        try:
            # Try to decode as UTF-8
            text_content = file_content.decode('utf-8')
            csv_reader = csv.reader(io.StringIO(text_content))
            
            for row in csv_reader:
                if row and row[0].strip():
                    keys.append(row[0].strip())
        except Exception:
            # If CSV parsing fails, try line by line
            try:
                text_content = file_content.decode('utf-8')
                keys = [line.strip() for line in text_content.splitlines() if line.strip()]
            except Exception:
                # If all fails, return empty list
                pass
                
        return keys
    
    @staticmethod
    def generate_csv(results: List[Dict], include_details: bool = True) -> str:
        """
        Generate CSV content from validation results
        
        Args:
            results: List of validation results
            include_details: Whether to include validation details
            
        Returns:
            CSV content as string
        """
        output = io.StringIO()
        
        if include_details:
            fieldnames = ["key", "valid", "error_code", "error_message"]
        else:
            fieldnames = ["key"]
            
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            if include_details:
                writer.writerow({
                    "key": result["key"],
                    "valid": result["valid"],
                    "error_code": result["error_code"] or "",
                    "error_message": result["error_message"] or ""
                })
            else:
                writer.writerow({"key": result["key"]})
                
        return output.getvalue() 
