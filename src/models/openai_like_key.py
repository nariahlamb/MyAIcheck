"""
API Key validation model for OpenAI-like API keys
"""
import asyncio
import aiohttp
import csv
import io
import json
import time
import random
from typing import Dict, List, Tuple, Optional

class OpenAILikeKeyValidator:
    """Class for validating OpenAI-like API keys in bulk"""

    @staticmethod
    async def validate_single_key(session: aiohttp.ClientSession, api_key: str, custom_api_url: str, custom_model_name: str, retry_count=3) -> Dict:
        """
        Validate a single OpenAI-like API key with retry mechanism and multiple endpoints.
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

        # Primary endpoint: custom_api_url (should end with /v1) + /models
        # Backup endpoint: custom_api_url (should end with /v1) + /chat/completions or /completions
        
        # Ensure custom_api_url ends with /v1
        if not custom_api_url.endswith('/v1'):
            # This check should ideally be done before calling, but as a safeguard:
            result["error_code"] = "INVALID_CONFIG"
            result["error_message"] = "Custom API URL must end with /v1"
            return result

        primary_endpoint = f"{custom_api_url.rstrip('/')}/models"
        # Determine a reasonable backup completion endpoint structure
        # Assuming chat completions is more common for /v1 structure
        backup_completion_endpoint = f"{custom_api_url.rstrip('/')}/chat/completions"

        endpoints_to_try = [
            {"url": primary_endpoint, "method": "GET", "payload": None},
            {"url": backup_completion_endpoint, "method": "POST", 
             "payload": {
                 "model": custom_model_name, 
                 "messages": [{"role": "user", "content": "Hello"}], 
                 "max_tokens": 1
             }
            }
        ]
        
        for endpoint_config in endpoints_to_try:
            current_url = endpoint_config["url"]
            current_method = endpoint_config["method"]
            current_payload = endpoint_config["payload"]

            for attempt in range(retry_count):
                try:
                    if attempt > 0:
                        await asyncio.sleep(random.uniform(0.5, 1.5) * attempt) # Shorter delay for faster feedback

                    response = None
                    if current_method == "GET":
                        response = await session.get(
                            current_url,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10) # 10s timeout for custom URLs
                        )
                    elif current_method == "POST":
                        response = await session.post(
                            current_url,
                            headers=headers,
                            json=current_payload,
                            timeout=aiohttp.ClientTimeout(total=15) # 15s for completion attempts
                        )
                    
                    if response is None: # Should not happen
                        result["error_code"] = "INTERNAL_ERROR"
                        result["error_message"] = "Validator internal error"
                        break 

                    status_code = response.status
                    response_text = await response.text()
                    response_json = {}
                    try:
                        response_json = json.loads(response_text)
                    except json.JSONDecodeError:
                        response_json = {"raw_text": response_text[:200]} # Store snippet if not JSON

                    if status_code == 200:
                        result["valid"] = True
                        result["error_code"] = None
                        result["error_message"] = None
                        break # Valid key found, stop trying this endpoint and other endpoints
                    elif status_code == 401: # Unauthorized
                        result["valid"] = False
                        result["error_code"] = "INVALID_KEY"
                        result["error_message"] = response_json.get("error", {}).get("message", "无效的API密钥或认证失败")
                        break 
                    elif status_code == 429: # Rate limit
                        result["error_code"] = "RATE_LIMIT"
                        result["error_message"] = "API速率限制"
                        if attempt < retry_count - 1:
                            await asyncio.sleep(1 * (attempt + 1)) # Exponential backoff for rate limit
                            continue
                        break 
                    else: # Other errors
                        result["error_code"] = f"HTTP_{status_code}"
                        result["error_message"] = response_json.get("error", {}).get("message", f"API请求错误 (状态码: {status_code})")
                        # For potentially transient server errors, retry. For client errors (4xx), usually no point.
                        if status_code >= 500 and attempt < retry_count - 1:
                            continue # Retry server errors
                        break # Don't retry client errors for this endpoint

                except aiohttp.ClientConnectorError as e:
                    result["error_code"] = "CONNECTION_ERROR"
                    result["error_message"] = f"连接错误: {str(e)}"
                    if attempt < retry_count - 1: continue
                    break
                except asyncio.TimeoutError:
                    result["error_code"] = "TIMEOUT"
                    result["error_message"] = "请求超时"
                    if attempt < retry_count - 1: continue
                    break
                except Exception as e:
                    result["error_code"] = "UNKNOWN_CLIENT_ERROR"
                    result["error_message"] = f"客户端未知错误: {str(e)}"
                    break # Unknown error, break from attempts for this endpoint
            
            if result["valid"]:
                break # Key is valid, no need to try other endpoints

        return result

    @staticmethod
    async def validate_keys_batch(api_keys: List[str], batch_size: int = 3, custom_api_url: str = "", custom_model_name: str = "") -> List[Dict]:
        """
        Validate a batch of OpenAI-like API keys.
        Requires custom_api_url and custom_model_name.
        """
        if not custom_api_url or not custom_model_name:
            # Return error for all keys if config is missing
            return [{
                "key": key, "valid": False, 
                "error_code": "CONFIG_MISSING", 
                "error_message": "自定义API URL或模型名称未提供"
            } for key in api_keys]

        if not custom_api_url.endswith('/v1'):
             return [{
                "key": key, "valid": False, 
                "error_code": "INVALID_CONFIG", 
                "error_message": "自定义API URL必须以 /v1 结尾"
            } for key in api_keys]

        results = []
        effective_batch_size = min(batch_size, 3) 

        timeout_config = aiohttp.ClientTimeout(total=30, sock_connect=10, sock_read=20)
        connector = aiohttp.TCPConnector(limit=effective_batch_size, ssl=False, force_close=True, ttl_dns_cache=300)
        
        async with aiohttp.ClientSession(timeout=timeout_config, connector=connector) as session:
            for i in range(0, len(api_keys), effective_batch_size):
                batch = api_keys[i:i+effective_batch_size]
                if i > 0:
                    await asyncio.sleep(random.uniform(0.5, 1.0)) # Small delay between batches
                
                tasks = [OpenAILikeKeyValidator.validate_single_key(session, key, custom_api_url, custom_model_name) for key in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                processed_results = []
                for res_idx, res_item in enumerate(batch_results):
                    if isinstance(res_item, Exception):
                        processed_results.append({
                            "key": batch[res_idx], "valid": False,
                            "error_code": "BATCH_EXCEPTION",
                            "error_message": f"批处理验证异常: {str(res_item)}"
                        })
                    else:
                        processed_results.append(res_item)
                results.extend(processed_results)
        return results

    @staticmethod
    def parse_input_keys(input_text: str) -> List[str]:
        keys = [line.strip() for line in input_text.splitlines()]
        return [key for key in keys if key and not key.isspace()]

    @staticmethod
    def parse_csv_file(file_content: bytes) -> List[str]:
        keys = []
        try:
            text_content = file_content.decode('utf-8-sig') # Handle BOM
            csv_reader = csv.reader(io.StringIO(text_content))
            for row in csv_reader:
                if row and row[0].strip():
                    keys.append(row[0].strip())
        except UnicodeDecodeError:
             # Fallback for other encodings if UTF-8 fails, or treat as plain text
            try:
                text_content = file_content.decode('gbk')
                lines = text_content.splitlines()
                for line in lines:
                    key = line.split(',')[0].strip() # Naive CSV parse if reader fails
                    if key: keys.append(key)
            except: # Final fallback: treat as one key per line plain text
                 text_content = file_content.decode('latin1') # Fallback
                 lines = text_content.splitlines()
                 for line in lines:
                    key = line.strip()
                    if key: keys.append(key)
        except Exception: # Catch other CSV parsing errors
            pass # keys will be empty or partially filled
        
        # Remove duplicates and ensure not just whitespace
        final_keys = []
        seen = set()
        for key in keys:
            if key and not key.isspace() and key not in seen:
                final_keys.append(key)
                seen.add(key)
        return final_keys

    @staticmethod
    def generate_csv(results: List[Dict], include_details: bool = True) -> str:
        output = io.StringIO()
        if include_details:
            fieldnames = ["key", "valid", "error_code", "error_message"]
        else:
            # If only exporting valid keys and no details, just list keys.
            # For this function, we'll assume if include_details is false,
            # it's for the "export valid keys only" button which still implies one column "key".
            fieldnames = ["key"] 
            # The actual filtering of valid keys will happen before calling this for "export valid"

        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        
        for result in results:
            row_to_write = {}
            if include_details:
                row_to_write = {
                    "key": result.get("key", ""),
                    "valid": result.get("valid", False),
                    "error_code": result.get("error_code", ""),
                    "error_message": result.get("error_message", "")
                }
            else: # Only key
                row_to_write = {"key": result.get("key", "")}
            writer.writerow(row_to_write)
                
        return output.getvalue() 