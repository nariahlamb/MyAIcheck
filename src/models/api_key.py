"""
API Key validation model for OpenAI API keys
"""
import asyncio
import aiohttp
import csv
import io
from typing import Dict, List, Tuple, Optional


class OpenAIKeyValidator:
    """Class for validating OpenAI API keys in bulk"""
    
    # OpenAI API endpoint for validation
    API_URL = "https://api.openai.com/v1/models"
    
    @staticmethod
    async def validate_single_key(session: aiohttp.ClientSession, api_key: str) -> Dict:
        """
        Validate a single OpenAI API key
        
        Args:
            session: aiohttp client session
            api_key: OpenAI API key to validate
            
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
        
        try:
            async with session.get(OpenAIKeyValidator.API_URL, headers=headers) as response:
                if response.status == 200:
                    result["valid"] = True
                else:
                    error_data = await response.json()
                    result["error_code"] = str(response.status)
                    result["error_message"] = error_data.get("error", {}).get("message", "Unknown error")
        except aiohttp.ClientError as e:
            result["error_code"] = "CLIENT_ERROR"
            result["error_message"] = str(e)
        except asyncio.TimeoutError:
            result["error_code"] = "TIMEOUT"
            result["error_message"] = "Request timed out"
        except Exception as e:
            result["error_code"] = "UNKNOWN_ERROR"
            result["error_message"] = str(e)
            
        return result
    
    @staticmethod
    async def validate_keys_batch(api_keys: List[str], batch_size: int = 10) -> List[Dict]:
        """
        Validate a batch of OpenAI API keys with concurrency control
        
        Args:
            api_keys: List of API keys to validate
            batch_size: Number of concurrent validations
            
        Returns:
            List of dictionaries with validation results
        """
        results = []
        
        # Create batches to control concurrency
        for i in range(0, len(api_keys), batch_size):
            batch = api_keys[i:i+batch_size]
            
            # Process batch concurrently
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                tasks = [OpenAIKeyValidator.validate_single_key(session, key) for key in batch]
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                
        return results
    
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
