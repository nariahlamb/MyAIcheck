import sys
import os
import json
from typing import List
from src.models.api_key import OpenAIKeyValidator

# 兼容Vercel Python Serverless Function规范
def handler(request):
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method Not Allowed'})
        }

    try:
        data = request.json() if callable(request.json) else request.json
    except Exception:
        try:
            data = json.loads(request.body.decode())
        except Exception:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON'})
            }

    api_keys = data.get('keys', [])
    batch_size = int(data.get('batch_size', 20))
    if not isinstance(api_keys, list) or not api_keys:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'No API keys provided'})
        }
    # 限制最大批量，防止超时
    batch_size = max(1, min(batch_size, 50))

    # 异步批量校验
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(OpenAIKeyValidator.validate_keys_batch(api_keys, batch_size))
    loop.close()

    # 统计
    valid_count = sum(1 for r in results if r['valid'])
    invalid_count = len(results) - valid_count

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'total': len(results),
            'valid': valid_count,
            'invalid': invalid_count,
            'results': results
        })
    } 