"""
API Key validation model for OpenAI API keys
"""
import asyncio
import aiohttp
import csv
import io
import time
import random
import json
from typing import Dict, List, Tuple, Optional


class OpenAIKeyValidator:
    """Class for validating OpenAI API keys in bulk"""
    
    # 主要和备用OpenAI API端点
    PRIMARY_API_URL = "https://api.openai.com/v1/models"
    BACKUP_API_URLS = [
        "https://api.openai.com/v1/engines",  # 旧版端点
        "https://api.openai.com/v1/completions"  # 完成端点
    ]
    
    # 用于完成端点的简单请求体
    COMPLETIONS_PAYLOAD = {
        "model": "gpt-3.5-turbo-instruct",
        "prompt": "Hello",
        "max_tokens": 1,
        "temperature": 0
    }
    
    @staticmethod
    async def validate_single_key(session: aiohttp.ClientSession, api_key: str, retry_count=3) -> Dict:
        """
        Validate a single OpenAI API key with retry mechanism and multiple endpoints
        
        Args:
            session: aiohttp client session
            api_key: OpenAI API key to validate
            retry_count: Number of retry attempts
            
        Returns:
            Dictionary with validation result
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        result = {
            "key": api_key,
            "valid": False,
            "error_code": None,
            "error_message": None
        }
        
        # 尝试所有API端点
        endpoints = [OpenAIKeyValidator.PRIMARY_API_URL] + OpenAIKeyValidator.BACKUP_API_URLS
        
        for endpoint_index, endpoint in enumerate(endpoints):
            # 只有主端点失败时才尝试备用端点
            if endpoint_index > 0 and result["valid"]:
                break
                
            # 如果切换到完成端点，需要使用POST请求
            is_completions_endpoint = "completions" in endpoint
                
            for attempt in range(retry_count):
                try:
                    # 添加随机延迟避免请求过于集中
                    if attempt > 0 or endpoint_index > 0:
                        await asyncio.sleep(random.uniform(1, 2))
                    
                    # 根据端点选择GET或POST方法
                    if is_completions_endpoint:
                        response = await session.post(
                            endpoint, 
                            headers=headers, 
                            json=OpenAIKeyValidator.COMPLETIONS_PAYLOAD,
                            timeout=aiohttp.ClientTimeout(total=15)
                        )
                    else:
                        response = await session.get(
                            endpoint, 
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=15)
                        )
                    
                    # 记录详细的响应信息用于调试
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
                    elif status_code == 401:
                        # 明确的无效密钥
                        result["valid"] = False
                        result["error_code"] = "INVALID_KEY"
                        result["error_message"] = response_json.get("error", {}).get("message", "无效的API密钥")
                        break
                    elif status_code == 429:  # 速率限制
                        result["error_code"] = "RATE_LIMIT"
                        result["error_message"] = "OpenAI API速率限制"
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    else:
                        # 记录更详细的错误信息
                        result["error_code"] = f"HTTP_{status_code}"
                        error_message = response_json.get("error", {}).get("message", "未知错误")
                        result["error_message"] = f"服务器错误: {error_message}"
                        
                        # 如果是服务器错误，尝试重试
                        if status_code >= 500:
                            if attempt < retry_count - 1:
                                await asyncio.sleep(1 * (attempt + 1))
                                continue
                        break
                
                except aiohttp.ClientConnectorError as e:
                    result["error_code"] = "CONNECTION_ERROR"
                    result["error_message"] = f"连接错误: {str(e)}"
                    # 非最后一次尝试和非最后一个端点时继续
                    if attempt < retry_count - 1 or endpoint_index < len(endpoints) - 1:
                        continue
                    break
                    
                except aiohttp.ClientError as e:
                    result["error_code"] = "NETWORK"
                    result["error_message"] = f"网络错误: {str(e)}"
                    if attempt < retry_count - 1:
                        await asyncio.sleep(1)
                        continue
                    break
                    
                except asyncio.TimeoutError:
                    result["error_code"] = "TIMEOUT"
                    result["error_message"] = "请求超时"
                    if attempt < retry_count - 1:
                        await asyncio.sleep(1)
                        continue
                    break
                    
                except Exception as e:
                    result["error_code"] = "UNKNOWN_ERROR"
                    result["error_message"] = f"未知错误: {str(e)}"
                    if attempt < retry_count - 1:
                        continue
                    break
            
            # 如果此端点验证成功，不再尝试其他端点
            if result["valid"]:
                break
                
        return result
    
    @staticmethod
    async def validate_keys_batch(api_keys: List[str], batch_size: int = 3) -> List[Dict]:
        """
        Validate a batch of OpenAI API keys with concurrency control
        
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
                tasks = [OpenAIKeyValidator.validate_single_key(session, key) for key in batch]
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
                            "error_message": f"处理异常: {str(res)}"
                        })
                    else:
                        valid_results.append(res)
                        
                results.extend(valid_results)
                
        return results

    @staticmethod
    async def get_models(api_key: str) -> Dict:
        """
        Get available models for the given OpenAI API key

        Args:
            api_key: OpenAI API key

        Returns:
            Dictionary with models data or error information
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        timeout = aiohttp.ClientTimeout(total=15)
        connector = aiohttp.TCPConnector(ssl=False, force_close=True)

        try:
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                response = await session.get(
                    OpenAIKeyValidator.PRIMARY_API_URL,
                    headers=headers
                )

                if response.status == 200:
                    data = await response.json()
                    return {
                        'success': True,
                        'models': data.get('data', []),
                        'provider': 'openai'
                    }
                elif response.status == 401:
                    return {
                        'success': False,
                        'error': '无效的API密钥'
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
                'error': '连接错误，无法访问OpenAI API'
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
