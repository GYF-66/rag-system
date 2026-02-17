# -*- coding: utf-8 -*-
"""
测试不同 API 服务商
"""
import asyncio
import httpx

API_KEY = "sk-dae5e6c75e418eb709e88ecc7e0b2aa1"

# 常见的 LLM API 服务商
API_PROVIDERS = [
    {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
    },
    {
        "name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash"
    },
    {
        "name": "Moonshot (月之暗面)",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k"
    },
    {
        "name": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-turbo"
    },
    {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-3.5-turbo"
    },
    {
        "name": "零一万物 (01.AI)",
        "base_url": "https://api.lingyiwanwu.com/v1",
        "model": "yi-lightning"
    },
    {
        "name": "硅基流动 (SiliconFlow)",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct"
    }
]


async def test_provider(provider: dict) -> dict:
    """测试单个服务商"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{provider['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": provider['model'],
                    "messages": [{"role": "user", "content": "你好"}],
                    "max_tokens": 50
                }
            )
            
            status = response.status_code
            if status == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return {"name": provider["name"], "status": "✅ 成功", "response": content[:50]}
            elif status == 401:
                return {"name": provider["name"], "status": "❌ 认证失败", "response": "Key 无效或不属于此服务"}
            elif status == 404:
                return {"name": provider["name"], "status": "⚠️ 接口不存在", "response": ""}
            else:
                return {"name": provider["name"], "status": f"❌ 错误 {status}", "response": response.text[:100]}
                
    except httpx.ConnectError:
        return {"name": provider["name"], "status": "⚠️ 连接失败", "response": "网络或域名问题"}
    except httpx.TimeoutException:
        return {"name": provider["name"], "status": "⚠️ 超时", "response": ""}
    except Exception as e:
        return {"name": provider["name"], "status": f"❌ 异常", "response": str(e)[:50]}


async def main():
    print("=" * 70)
    print(f"测试 API Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    print("=" * 70)
    print()
    
    # 并行测试所有服务商
    tasks = [test_provider(p) for p in API_PROVIDERS]
    results = await asyncio.gather(*tasks)
    
    print(f"{'服务商':<25} {'状态':<15} {'响应'}")
    print("-" * 70)
    
    for r in results:
        print(f"{r['name']:<25} {r['status']:<15} {r['response']}")
    
    print()
    print("=" * 70)
    

if __name__ == "__main__":
    asyncio.run(main())
