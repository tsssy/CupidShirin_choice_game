#!/usr/bin/env python3
"""
测试新的Telegram Bot Token
"""

import requests
import json
from config import Config

def test_bot_token():
    """测试Telegram Bot Token是否有效"""
    
    token = Config.API.TELEGRAM_BOT_TOKEN
    print(f"正在测试Token: {token[:10]}...")
    
    # 获取机器人信息
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print("✅ Token有效！")
                print(f"机器人信息:")
                print(f"  - ID: {bot_info.get('id')}")
                print(f"  - 用户名: @{bot_info.get('username')}")
                print(f"  - 名称: {bot_info.get('first_name')}")
                print(f"  - 是否可加入群组: {bot_info.get('can_join_groups', False)}")
                print(f"  - 是否可读取所有群组消息: {bot_info.get('can_read_all_group_messages', False)}")
                print(f"  - 是否支持内联模式: {bot_info.get('supports_inline_queries', False)}")
                return True
            else:
                print(f"❌ API返回错误: {data.get('description', '未知错误')}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {str(e)}")
        return False

def test_webhook_info():
    """测试Webhook信息"""
    
    token = Config.API.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                webhook_info = data.get('result', {})
                print(f"\n📡 Webhook信息:")
                print(f"  - URL: {webhook_info.get('url', '未设置')}")
                print(f"  - 待处理更新数: {webhook_info.get('pending_update_count', 0)}")
                print(f"  - 最后错误时间: {webhook_info.get('last_error_date')}")
                print(f"  - 最后错误消息: {webhook_info.get('last_error_message')}")
                return True
            else:
                print(f"❌ 获取Webhook信息失败: {data.get('description', '未知错误')}")
                return False
        else:
            print(f"❌ 获取Webhook信息HTTP错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 获取Webhook信息错误: {str(e)}")
        return False

def main():
    """主函数"""
    print("🤖 Telegram Bot Token 测试")
    print("=" * 50)
    
    # 测试Token
    if test_bot_token():
        # 测试Webhook信息
        test_webhook_info()
        
        print(f"\n✅ Token测试完成！")
        print(f"机器人地址: https://t.me/CupidShirinBot")
        print(f"你现在可以运行 'python main_soul_explorer.py' 来启动机器人")
    else:
        print(f"\n❌ Token测试失败，请检查配置")

if __name__ == "__main__":
    main() 