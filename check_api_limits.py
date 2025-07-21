#!/usr/bin/env python3
"""
检查API使用情况和限制
"""

import os
import requests
import time
from config import Config

def check_gemini_api_limits():
    """检查Gemini API的使用限制"""
    print("🔍 检查Gemini API使用情况")
    print("=" * 50)
    
    api_key = Config.API.GEMINI_API_KEY
    if not api_key:
        print("❌ 错误：缺少Gemini API密钥")
        return
    
    # Gemini API的已知限制
    print("📋 Gemini API已知限制：")
    print("   - 免费版：每分钟15次请求")
    print("   - 免费版：每小时150次请求")
    print("   - 免费版：每天1500次请求")
    print("   - 付费版：每分钟60次请求")
    print("   - 付费版：每小时3600次请求")
    print("   - 付费版：每天无限制")
    
    # 检查当前API密钥类型
    print(f"\n🔑 当前API密钥：{api_key[:10]}...")
    
    # 尝试一个简单的API调用来测试
    print("\n🧪 测试API调用...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        start_time = time.time()
        response = model.generate_content("Hello")
        end_time = time.time()
        
        print(f"✅ API调用成功！耗时：{end_time - start_time:.2f}秒")
        print(f"📝 响应长度：{len(response.text)}字符")
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ API调用失败：{error_msg}")
        
        if "429" in error_msg or "Too Many Requests" in error_msg:
            print("\n🚨 检测到429错误 - 达到API调用限制！")
            print("💡 解决方案：")
            print("   1. 等待1分钟后重试")
            print("   2. 检查是否达到每小时/每天限制")
            print("   3. 考虑升级到付费版")
            print("   4. 使用多个API密钥轮换")
        
        elif "403" in error_msg or "Forbidden" in error_msg:
            print("\n🚨 检测到403错误 - API密钥无效或权限不足！")
            print("💡 解决方案：")
            print("   1. 检查API密钥是否正确")
            print("   2. 确认API密钥是否已激活")
            print("   3. 检查是否有足够的配额")
        
        elif "400" in error_msg or "Bad Request" in error_msg:
            print("\n🚨 检测到400错误 - 请求格式错误！")
            print("💡 解决方案：")
            print("   1. 检查请求参数")
            print("   2. 确认模型名称正确")
            print("   3. 检查输入内容格式")
        
        else:
            print(f"\n🚨 未知错误：{error_msg}")

def check_telegram_api_limits():
    """检查Telegram API的使用限制"""
    print("\n🔍 检查Telegram API使用情况")
    print("=" * 50)
    
    bot_token = Config.API.TELEGRAM_BOT_TOKEN
    if not bot_token:
        print("❌ 错误：缺少Telegram Bot Token")
        return
    
    print("📋 Telegram Bot API限制：")
    print("   - 消息发送：每秒30条")
    print("   - 消息编辑：每秒30条")
    print("   - 轮询更新：无限制")
    print("   - 文件上传：50MB")
    
    # 测试Telegram API
    print(f"\n🔑 当前Bot Token：{bot_token[:10]}...")
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Telegram API连接成功！")
            print(f"📝 Bot名称：{data['result']['first_name']}")
            print(f"📝 Bot用户名：@{data['result']['username']}")
        else:
            print(f"❌ Telegram API连接失败：{response.status_code}")
            
    except Exception as e:
        print(f"❌ Telegram API测试失败：{str(e)}")

def suggest_optimizations():
    """建议优化方案"""
    print("\n💡 API使用优化建议")
    print("=" * 50)
    
    print("🚀 针对429错误的优化策略：")
    print("   1. 实现请求限流（Rate Limiting）")
    print("   2. 添加指数退避重试机制")
    print("   3. 使用多个API密钥轮换")
    print("   4. 缓存常用响应")
    print("   5. 批量处理请求")
    
    print("\n🎯 针对灵魂探索机器人的具体优化：")
    print("   1. 使用两次生成模式（仅2次API调用）")
    print("   2. 实现本地缓存机制")
    print("   3. 添加请求队列和延迟")
    print("   4. 监控API使用量")
    print("   5. 设置自动降级策略")

def create_rate_limiter_example():
    """创建限流器示例"""
    print("\n🔧 限流器示例代码")
    print("=" * 50)
    
    example_code = '''
import time
import asyncio
from collections import deque

class RateLimiter:
    """API请求限流器"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    async def acquire(self):
        """获取请求许可"""
        now = time.time()
        
        # 清理过期的请求记录
        while self.requests and now - self.requests[0] > self.time_window:
            self.requests.popleft()
        
        # 检查是否超过限制
        if len(self.requests) >= self.max_requests:
            # 等待最早的请求过期
            wait_time = self.requests[0] + self.time_window - now
            if wait_time > 0:
                print(f"⚠️ 达到API限制，等待 {wait_time:.2f} 秒...")
                await asyncio.sleep(wait_time)
        
        # 记录当前请求
        self.requests.append(now)
        return True

# 使用示例
gemini_limiter = RateLimiter(max_requests=15, time_window=60)  # 每分钟15次
telegram_limiter = RateLimiter(max_requests=30, time_window=1)  # 每秒30次

async def safe_api_call():
    await gemini_limiter.acquire()
    # 执行API调用
    pass
'''
    
    print(example_code)

if __name__ == "__main__":
    print("🚀 启动API限制检查...")
    
    check_gemini_api_limits()
    check_telegram_api_limits()
    suggest_optimizations()
    create_rate_limiter_example()
    
    print("\n✨ 检查完成！") 