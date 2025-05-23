"""
API健康状态检查模块，提供对各种AI平台的连接质量和服务可用性监控
"""
import asyncio
import aiohttp
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from src.utils.logging_util import setup_logger

# 设置日志记录器
logger = setup_logger(name="health_checker")

class APIHealthChecker:
    """API健康和连接质量检查类"""
    
    # 支持的API提供商端点和检查配置
    API_ENDPOINTS = {
        "OpenAI": {
            "url": "https://api.openai.com/v1/models",
            "method": "GET",
            "headers": {"Content-Type": "application/json"}
        },
        "Claude": {
            "url": "https://api.anthropic.com/v1/models",
            "method": "GET",
            "headers": {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
        },
        "Gemini": {
            "url": "https://generativelanguage.googleapis.com/v1beta/models",
            "method": "GET",
            "headers": {"Content-Type": "application/json"}
        },
        "Cohere": {
            "url": "https://api.cohere.ai/v1/models",
            "method": "GET",
            "headers": {"Content-Type": "application/json"}
        },
        "Mistral": {
            "url": "https://api.mistral.ai/v1/models",
            "method": "GET",
            "headers": {"Content-Type": "application/json"}
        }
    }
    
    def __init__(self, test_count: int = 3, timeout: int = 10):
        """
        初始化健康检查器
        
        Args:
            test_count: 每个API运行的检查次数
            timeout: 每次请求的超时时间(秒)
        """
        self.test_count = test_count
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.last_check_time = None
        self.results_cache = {}  # 缓存最近的结果
        self.cache_ttl = 300  # 缓存有效期(秒)
    
    async def check_all_providers(self) -> Dict[str, Any]:
        """
        检查所有支持的API提供商的健康状态
        
        Returns:
            包含每个API提供商健康状态的字典
        """
        # 如果缓存有效，返回缓存结果
        current_time = time.time()
        if (self.last_check_time and 
            current_time - self.last_check_time < self.cache_ttl and
            self.results_cache):
            # 添加缓存信息
            cached_results = self.results_cache.copy()
            cached_results["from_cache"] = True
            cached_results["cache_age"] = int(current_time - self.last_check_time)
            return cached_results
            
        # 执行新的健康检查
        results = {
            "timestamp": datetime.now().isoformat(),
            "from_cache": False,
            "providers": {}
        }
        
        # 创建所有API提供商的检查任务
        tasks = []
        for provider, config in self.API_ENDPOINTS.items():
            tasks.append(self.check_provider_health(provider, config))
            
        # 并发执行所有检查
        provider_results = await asyncio.gather(*tasks)
        
        # 整合结果
        for provider, health_data in zip(self.API_ENDPOINTS.keys(), provider_results):
            results["providers"][provider] = health_data
            
        # 计算总体健康状态
        statuses = [data["status"] for data in results["providers"].values()]
        if all(status == "operational" for status in statuses):
            results["overall_status"] = "全部正常"
        elif all(status == "down" for status in statuses):
            results["overall_status"] = "全部故障"
        else:
            operational_count = sum(1 for status in statuses if status == "operational")
            results["overall_status"] = f"部分可用 ({operational_count}/{len(statuses)})"
            
        # 更新缓存
        self.results_cache = results
        self.last_check_time = current_time
        
        return results
    
    async def check_provider_health(self, provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查单个API提供商的健康状态
        
        Args:
            provider: API提供商名称
            config: API端点配置
            
        Returns:
            健康状态结果字典
        """
        url = config["url"]
        method = config["method"]
        headers = config["headers"]
        
        result = {
            "status": "unknown",
            "latency_ms": None,
            "success_rate": 0,
            "error": None,
            "last_checked": datetime.now().isoformat()
        }
        
        # 执行多次测试以计算成功率和平均延迟
        latencies = []
        success_count = 0
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for _ in range(self.test_count):
                try:
                    start_time = time.time()
                    
                    if method == "GET":
                        async with session.get(url, headers=headers) as response:
                            elapsed = (time.time() - start_time) * 1000  # 转换为毫秒
                            
                            # 状态码在200-299范围内视为成功
                            if 200 <= response.status < 300:
                                success_count += 1
                                latencies.append(elapsed)
                    else:
                        # 对于其他方法，如POST
                        async with session.post(url, headers=headers, json={}) as response:
                            elapsed = (time.time() - start_time) * 1000
                            
                            if 200 <= response.status < 300:
                                success_count += 1
                                latencies.append(elapsed)
                                
                    # 避免过于频繁的请求
                    await asyncio.sleep(0.5)
                    
                except asyncio.TimeoutError:
                    result["error"] = "请求超时"
                except aiohttp.ClientError as e:
                    result["error"] = f"连接错误: {str(e)}"
                except Exception as e:
                    result["error"] = f"未知错误: {str(e)}"
        
        # 计算成功率
        result["success_rate"] = (success_count / self.test_count) * 100 if self.test_count > 0 else 0
        
        # 设置状态
        if result["success_rate"] >= 80:
            result["status"] = "operational"
        elif result["success_rate"] > 0:
            result["status"] = "degraded"
        else:
            result["status"] = "down"
            
        # 如果有成功的请求，计算延迟统计
        if latencies:
            result["latency_ms"] = {
                "min": round(min(latencies), 2),
                "max": round(max(latencies), 2),
                "avg": round(statistics.mean(latencies), 2),
                "median": round(statistics.median(latencies), 2)
            }
            
        return result
    
    async def check_specific_provider(self, provider: str) -> Dict[str, Any]:
        """
        检查特定API提供商的健康状态
        
        Args:
            provider: 要检查的API提供商名称
            
        Returns:
            健康状态结果
        """
        if provider not in self.API_ENDPOINTS:
            return {"error": f"不支持的API提供商: {provider}"}
            
        config = self.API_ENDPOINTS[provider]
        result = await self.check_provider_health(provider, config)
        
        return {
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            "health": result
        }
        
    async def get_global_status(self) -> Dict[str, Any]:
        """
        获取全球各地区的API连接状态
        目前仅模拟数据，未来可扩展实现真实多地区检测
        
        Returns:
            全球状态报告
        """
        # 模拟多地区数据
        regions = ["亚太", "北美", "欧洲", "南美"]
        providers = list(self.API_ENDPOINTS.keys())
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "regions": {}
        }
        
        # 模拟各地区数据
        for region in regions:
            region_data = {
                "status": "operational",
                "providers": {}
            }
            
            for provider in providers:
                # 随机生成模拟数据(在实际实现中会替换为真实检测)
                import random
                success_rate = random.uniform(70, 100)
                latency = random.uniform(100, 500)
                
                status = "operational" if success_rate > 90 else "degraded"
                
                region_data["providers"][provider] = {
                    "status": status,
                    "latency_ms": round(latency, 2),
                    "success_rate": round(success_rate, 2)
                }
                
                # 更新区域整体状态
                if status != "operational" and region_data["status"] == "operational":
                    region_data["status"] = "degraded"
                    
            result["regions"][region] = region_data
            
        return result