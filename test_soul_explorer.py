#!/usr/bin/env python3
"""
灵魂探索机器人测试脚本
用于测试新的灵魂探索机器人功能
"""

import asyncio
import logging
import os
from soul_explorer_bot import SoulExplorerBot
from config import Config

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_soul_explorer():
    """测试灵魂探索机器人"""
    
    # 检查配置
    if not Config.validate_config():
        print("❌ 配置验证失败")
        return
    
    api_key = Config.API.GEMINI_API_KEY
    if not api_key:
        print("❌ 缺少Gemini API密钥")
        return
    
    print("🚀 开始测试灵魂探索机器人...")
    
    try:
        # 创建机器人实例
        bot = SoulExplorerBot(api_key)
        print("✅ 机器人初始化成功")
        
        # 测试1: 随机模式开始
        print("\n📝 测试1: 随机模式开始")
        response = await bot.start_exploration("start")
        print(f"机器人响应:\n{response}")
        
        # 测试2: 处理选择
        print("\n📝 测试2: 处理用户选择")
        response = await bot.process_choice("A")
        print(f"机器人响应:\n{response}")
        
        # 测试3: 继续选择
        print("\n📝 测试3: 继续选择")
        response = await bot.process_choice("B")
        print(f"机器人响应:\n{response}")
        
        # 测试4: 自定义模式
        print("\n📝 测试4: 自定义模式")
        bot.reset_session()
        response = await bot.start_exploration("自定义")
        print(f"机器人响应:\n{response}")
        
        # 测试5: 自定义设置
        print("\n📝 测试5: 自定义设置")
        response = await bot.handle_custom_setup("场景：一个神秘的图书馆，角色：一位寻找答案的学者")
        print(f"机器人响应:\n{response}")
        
        # 测试6: 会话信息
        print("\n📝 测试6: 获取会话信息")
        session_info = bot.get_session_info()
        print(f"会话信息: {session_info}")
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logging.error(f"测试异常: {str(e)}")

async def test_interactive_mode():
    """交互式测试模式"""
    
    api_key = Config.API.GEMINI_API_KEY
    if not api_key:
        print("❌ 缺少Gemini API密钥")
        return
    
    print("🎮 进入交互式测试模式...")
    print("输入 'quit' 退出测试")
    
    bot = SoulExplorerBot(api_key)
    
    while True:
        try:
            user_input = input("\n请输入你的选择: ").strip()
            
            if user_input.lower() == 'quit':
                break
            
            if not bot.user_choices and user_input.lower() in ['start', '自定义']:
                # 开始探索
                response = await bot.start_exploration(user_input)
                print(f"\n🤖 机器人: {response}")
                
            elif bot.is_custom_mode and not bot.custom_scene and "场景：" in user_input:
                # 自定义设置
                response = await bot.handle_custom_setup(user_input)
                print(f"\n🤖 机器人: {response}")
                
            elif user_input.upper() in ['A', 'B', 'C', 'D']:
                # 处理选择
                response = await bot.process_choice(user_input)
                print(f"\n🤖 机器人: {response}")
                
                # 检查是否结束
                if "再一次进入探索之旅吗？" in response:
                    print("\n🎉 探索完成！")
                    break
                    
            else:
                print("❌ 无效输入，请选择A、B、C或D")
                
        except KeyboardInterrupt:
            print("\n👋 测试结束")
            break
        except Exception as e:
            print(f"❌ 错误: {str(e)}")

def main():
    """主函数"""
    print("🌟 灵魂探索机器人测试工具")
    print("=" * 50)
    
    while True:
        print("\n请选择测试模式:")
        print("1. 自动测试")
        print("2. 交互式测试")
        print("3. 退出")
        
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == "1":
            asyncio.run(test_soul_explorer())
        elif choice == "2":
            asyncio.run(test_interactive_mode())
        elif choice == "3":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main() 