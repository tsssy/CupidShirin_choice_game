#!/usr/bin/env python3
"""
测试Gemini 2.5 Flash版本
验证新的API限制和使用情况
"""

import asyncio
import time
import logging
from config import Config
import google.generativeai as genai

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_gemini_2_5_flash():
    """测试Gemini 2.5 Flash版本"""
    print("🚀 测试Gemini 2.5 Flash版本")
    print("=" * 50)
    
    api_key = Config.API.GEMINI_API_KEY
    if not api_key:
        print("❌ 错误：缺少Gemini API密钥")
        return
    
    print(f"🔑 当前API密钥：{api_key[:10]}...")
    print(f"📋 配置的模型名称：{Config.API.GEMINI_MODEL_NAME}")
    
    try:
        # 配置Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        print("\n🧪 测试API调用...")
        start_time = time.time()
        
        # 测试简单请求
        response = model.generate_content("Hello, please respond with 'Gemini 2.5 Flash is working!'")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"✅ API调用成功！")
        print(f"📝 响应时间：{response_time:.2f}秒")
        print(f"📝 响应内容：{response.text}")
        print(f"📝 响应长度：{len(response.text)}字符")
        
        # 测试灵魂探索相关的请求
        print("\n🧪 测试灵魂探索请求...")
        start_time = time.time()
        
        exploration_prompt = """
你是一个专业的灵魂探索机器人。

请生成一个简短的灵魂探索故事开头（80-120字符），并提供A、B、C、D四个选项。

格式：
[故事内容]

A. [选项A]
B. [选项B]
C. [选项C]
D. [选项D]
"""
        
        response = model.generate_content(exploration_prompt)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"✅ 灵魂探索请求成功！")
        print(f"📝 响应时间：{response_time:.2f}秒")
        print(f"📝 响应内容：")
        print(response.text)
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ API调用失败：{error_msg}")
        
        if "429" in error_msg or "quota" in error_msg.lower():
            print("\n🚨 检测到429错误 - 达到API调用限制！")
            print("💡 解决方案：")
            print("   1. 等待一段时间后重试")
            print("   2. 检查是否达到每日限制")
            print("   3. 考虑升级到付费版")
        
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
        
        return False

def check_api_limits_2_5_flash():
    """检查2.5 Flash版本的API限制"""
    print("\n📋 Gemini 2.5 Flash API限制信息")
    print("=" * 50)
    
    print("根据官方文档，Gemini 2.5 Flash免费版限制：")
    print("   - 每分钟请求数：15次请求/分钟")
    print("   - 每天请求数：1,500次请求/天")
    print("   - 输入token限制：1M tokens/天")
    print("   - 输出token限制：1M tokens/天")
    
    print("\n🎯 与1.5 Flash版本对比：")
    print("   1.5 Flash：每天50次请求")
    print("   2.5 Flash：每天1,500次请求")
    print("   提升：30倍！")
    
    print("\n💡 使用建议：")
    print("   - 一次完整游戏：11次API调用")
    print("   - 每天可支持：1,500 ÷ 11 = 136次完整游戏")
    print("   - 足够支持多用户并发使用")

async def test_soul_explorer_bot():
    """测试灵魂探索机器人"""
    print("\n🧪 测试灵魂探索机器人")
    print("=" * 50)
    
    try:
        from soul_explorer_bot import SoulExplorerBot
        
        api_key = Config.API.GEMINI_API_KEY
        if not api_key:
            print("❌ 错误：缺少Gemini API密钥")
            return
        
        bot = SoulExplorerBot(api_key)
        print("✅ 灵魂探索机器人初始化成功")
        
        # 测试开始探索
        print("\n📖 测试开始探索...")
        response = await bot.start_exploration("start")
        print(f"✅ 探索开始成功！")
        print(f"📝 响应内容：{response[:200]}...")
        
        # 测试处理选择
        print("\n🎮 测试处理选择...")
        response = await bot.process_choice("A")
        print(f"✅ 选择处理成功！")
        print(f"📝 响应内容：{response[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 灵魂探索机器人测试失败：{str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 启动Gemini 2.5 Flash测试...")
    
    # 检查API限制信息
    check_api_limits_2_5_flash()
    
    # 运行测试
    success = asyncio.run(test_gemini_2_5_flash())
    
    if success:
        # 测试灵魂探索机器人
        asyncio.run(test_soul_explorer_bot())
    
    print("\n✨ 测试完成！") 