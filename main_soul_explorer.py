import logging
import os
import asyncio
from datetime import datetime, UTC
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from soul_explorer_bot import SoulExplorerBot
from config import Config
import re

# MongoDB setup with authentication
from pymongo import MongoClient
client = MongoClient(Config.Database.get_auth_uri())
db = client[Config.Database.MONGO_DATABASE]
soul_explorer_sessions = db['soul_explorer_sessions']  # 新的集合名
story_sessions = db[Config.Database.STORY_SESSIONS_COLLECTION]  # 故事会话集合

logging.basicConfig(
    format=Config.Logging.LOG_FORMAT,
    level=getattr(logging, Config.Logging.LOG_LEVEL)
)

# Store user bot instances
user_bots = {}
# Store user session stage
user_stage = {}  # 记录每个用户的会话阶段
# Store user exploration status
user_exploration_started = {}  # 记录用户是否已经开始探索
# Store user choice texts
user_choice_texts = {}  # 记录用户选择的具体文本内容

# Test MongoDB connection
def test_mongodb_connection():
    """Test MongoDB connection and authentication."""
    try:
        collections = db.list_collection_names()
        logging.info(f"MongoDB connection successful. Available collections: {collections}")
        return True
    except Exception as e:
        logging.error(f"MongoDB connection failed: {str(e)}")
        return False

# MongoDB helper functions
def save_session_to_mongodb(user_id: int, session_data: dict):
    """Save session data to MongoDB using user_id as the document ID."""
    try:
        session_data['_id'] = user_id
        session_data['created_at'] = datetime.now(UTC)
        soul_explorer_sessions.replace_one({'_id': user_id}, session_data, upsert=True)
        logging.info(f"Session saved to MongoDB for user {user_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving session to MongoDB for user {user_id}: {str(e)}")
        return False

def get_session_from_mongodb(user_id: int):
    """Get session data from MongoDB using user_id."""
    try:
        return soul_explorer_sessions.find_one({'_id': user_id})
    except Exception as e:
        logging.error(f"Error getting session from MongoDB for user {user_id}: {str(e)}")
        return None

def _extract_and_store_choice_texts(user_id: int, response_text: str):
    """从响应文本中提取选项文本并存储"""
    try:
        # 初始化用户的选择文本存储
        if user_id not in user_choice_texts:
            user_choice_texts[user_id] = {}
        
        # 使用正则表达式提取选项文本
        import re
        choice_pattern = r'([A-D])\.\s*([^\n]+)'
        matches = re.findall(choice_pattern, response_text)
        
        for choice, text in matches:
            user_choice_texts[user_id][choice] = text.strip()
            logging.info(f"存储用户 {user_id} 的选择文本: {choice} -> {text.strip()}")
            
    except Exception as e:
        logging.error(f"提取选项文本失败: {str(e)}")

def save_exploration_result_to_mongodb(user_id: int, exploration_data: dict):
    """Save exploration result to MongoDB."""
    try:
        soul_explorer_sessions.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'exploration_result': exploration_data,
                    'completed_at': datetime.now(UTC)
                },
                '$inc': {'exploration_count': 1}
            },
            upsert=True
        )
        logging.info(f"Exploration result saved to MongoDB for user {user_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving exploration result to MongoDB for user {user_id}: {str(e)}")
        return False

def save_story_session_to_mongodb(user_id: int, story_data: dict):
    """Save story session data to MongoDB."""
    try:
        story_sessions.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'last_updated': datetime.now(UTC),
                    'current_session': story_data
                },
                '$inc': {'total_sessions': 1}
            },
            upsert=True
        )
        logging.info(f"Story session saved to MongoDB for user {user_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving story session to MongoDB for user {user_id}: {str(e)}")
        return False

def save_story_completion_to_mongodb(user_id: int, completion_data: dict):
    """Save story completion data to MongoDB."""
    try:
        story_sessions.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'last_completion': datetime.now(UTC),
                    'completion_data': completion_data
                },
                '$push': {
                    'completion_history': {
                        'timestamp': datetime.now(UTC),
                        'data': completion_data
                    }
                },
                '$inc': {'total_completions': 1}
            },
            upsert=True
        )
        logging.info(f"Story completion saved to MongoDB for user {user_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving story completion to MongoDB for user {user_id}: {str(e)}")
        return False

def get_story_session_from_mongodb(user_id: int):
    """Get story session data from MongoDB."""
    try:
        return story_sessions.find_one({'_id': user_id})
    except Exception as e:
        logging.error(f"Error getting story session from MongoDB for user {user_id}: {str(e)}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    if not update.message:
        return
    
    user_id = update.effective_user.id if update.effective_user else None
    if user_id:
        # 重置用户状态，允许重新开始
        if user_id in user_bots:
            del user_bots[user_id]
        if user_id in user_stage:
            del user_stage[user_id]
        if user_id in user_exploration_started:
            del user_exploration_started[user_id]
        if user_id in user_choice_texts:
            del user_choice_texts[user_id]
        
        # 设置用户状态为等待开始
        user_stage[user_id] = "awaiting_start"
    
    # 创建欢迎消息和按钮
    keyboard = [
        [KeyboardButton("start"), KeyboardButton("自定义")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    welcome_message = """
🌟 欢迎来到灵魂探索之旅！ 🌟

这里是灵魂之旅的入口，你可以：
• 输入 "start" 开始随机探索
• 输入 "自定义" 创建专属故事

准备好开始你的灵魂探索了吗？
    """
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def _keep_typing(bot, chat_id: int):
    """Keep showing typing indicator until cancelled."""
    while True:
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(Config.Bot.TYPING_DURATION)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Error in typing indicator: {str(e)}")
            break

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return
    
    text = update.message.text.strip()
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    # 处理 /start 命令
    if text == "/start":
        await start(update, context)
        return
    
    # 处理 /reset 命令
    if text == "/reset":
        if user_id in user_bots:
            user_bots[user_id].reset_session()
            del user_bots[user_id]
        if user_id in user_stage:
            del user_stage[user_id]
        if user_id in user_exploration_started:
            del user_exploration_started[user_id]
        await update.message.reply_text("会话已重置。输入 /start 重新开始探索。")
        return
    
    # 如果用户还没有开始探索
    if user_id not in user_bots:
        # 检查是否是开始探索的输入
        if text.lower() in ["start", "自定义"]:
            # 初始化机器人
            api_key = Config.API.GEMINI_API_KEY
            if not api_key:
                await update.message.reply_text("配置错误：缺少Gemini API密钥")
                return
            
            user_bots[user_id] = SoulExplorerBot(api_key)
            user_stage[user_id] = "in_exploration"
            user_exploration_started[user_id] = True
            
            # 开始探索
            start_typing = asyncio.create_task(_keep_typing(context.bot, chat_id))
            try:
                response = await user_bots[user_id].start_exploration(text)
                
                # 提供选择按钮
                keyboard = [
                    [KeyboardButton("A"), KeyboardButton("B")],
                    [KeyboardButton("C"), KeyboardButton("D")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                
                # 添加重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await update.message.reply_text(response, reply_markup=reply_markup)
                        # 提取并存储选项文本
                        _extract_and_store_choice_texts(user_id, response)
                        break
                    except Exception as e:
                        logging.error(f"发送消息失败 (第 {attempt + 1} 次): {str(e)}")
                        if attempt == max_retries - 1:
                            # 最后一次重试失败，尝试发送简单消息
                            try:
                                await update.message.reply_text("故事开始中...请稍等片刻。")
                            except:
                                logging.error("无法发送任何消息给用户")
                        else:
                            await asyncio.sleep(1)
                
                # 保存会话数据
                session_data = {
                    'user_id': user_id,
                    'stage': 'in_exploration',
                    'started_at': datetime.now(UTC),
                    'exploration_type': text.lower()
                }
                save_session_to_mongodb(user_id, session_data)
                
                # 保存故事会话数据
                story_session_data = {
                    'user_id': user_id,
                    'session_start': datetime.now(UTC),
                    'exploration_type': text.lower(),
                    'current_chapter': 1,
                    'total_chapters': 10,
                    'user_choices': [],
                    'interaction_history': []
                }
                save_story_session_to_mongodb(user_id, story_session_data)
                
            finally:
                start_typing.cancel()
                try:
                    await start_typing
                except asyncio.CancelledError:
                    pass
            return
        
        else:
            # 无效输入，提示用户
            await update.message.reply_text("你可以随时回来开始灵魂之旅。你可以输入'start'或'自定义'来开启这次灵魂探索!!!")
            return
    
    # 用户已经在探索中
    bot_instance = user_bots[user_id]
    
    # 检查是否在自定义设置阶段
    if user_stage.get(user_id) == "in_exploration" and bot_instance.is_custom_mode and not bot_instance.custom_scene:
        # 处理自定义设置
        start_typing = asyncio.create_task(_keep_typing(context.bot, chat_id))
        try:
            response = await bot_instance.handle_custom_setup(text)
            
            # 如果自定义设置成功，提供选择按钮
            if "格式错误" not in response and "请使用正确格式" not in response:
                keyboard = [
                    [KeyboardButton("A"), KeyboardButton("B")],
                    [KeyboardButton("C"), KeyboardButton("D")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                
                # 添加重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await update.message.reply_text(response, reply_markup=reply_markup)
                        # 提取并存储选项文本
                        _extract_and_store_choice_texts(user_id, response)
                        break
                    except Exception as e:
                        logging.error(f"发送消息失败 (第 {attempt + 1} 次): {str(e)}")
                        if attempt == max_retries - 1:
                            # 最后一次重试失败，尝试发送简单消息
                            try:
                                await update.message.reply_text("故事开始中...请稍等片刻。")
                            except:
                                logging.error("无法发送任何消息给用户")
                        else:
                            await asyncio.sleep(1)
            else:
                # 添加重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await update.message.reply_text(response)
                        break
                    except Exception as e:
                        logging.error(f"发送消息失败 (第 {attempt + 1} 次): {str(e)}")
                        if attempt == max_retries - 1:
                            logging.error("无法发送任何消息给用户")
                        else:
                            await asyncio.sleep(1)
        finally:
            start_typing.cancel()
            try:
                await start_typing
            except asyncio.CancelledError:
                pass
        return
    
                # 检查是否是选择选项 (A/B/C/D)
    if text.upper() in ['A', 'B', 'C', 'D']:
        start_typing = asyncio.create_task(_keep_typing(context.bot, chat_id))
        try:
            # 获取用户选择的具体文本内容
            choice_text = ""
            if user_id in user_choice_texts and text.upper() in user_choice_texts[user_id]:
                choice_text = user_choice_texts[user_id][text.upper()]
            
            response = await bot_instance.process_choice(text, choice_text)
            
            # 更新故事会话数据
            session_info = bot_instance.get_session_info()
            story_session_data = {
                'user_id': user_id,
                'last_updated': datetime.now(UTC),
                'current_chapter': session_info['current_chapter'],
                'total_chapters': session_info['total_chapters'],
                'user_choices': session_info['user_choices'],
                'user_choice_texts': session_info['user_choice_texts'],
                'interaction_history': session_info['interaction_history'],
                'current_location': session_info['current_location'],
                'current_time': session_info['current_time'],
                'current_context': session_info['current_context'],
                'story_theme': session_info['story_theme'],
                'is_custom_mode': session_info['is_custom_mode'],
                'custom_scene': session_info['custom_scene'],
                'custom_character': session_info['custom_character']
            }
            save_story_session_to_mongodb(user_id, story_session_data)
            
            # 检查是否探索结束
            if "再一次进入探索之旅吗？" in response:
                user_stage[user_id] = "exploration_completed"
                
                # 保存探索结果
                session_info = bot_instance.get_session_info()
                exploration_data = {
                    'choices': session_info['user_choices'],
                    'total_chapters': session_info['total_chapters'],
                    'is_custom_mode': session_info['is_custom_mode'],
                    'custom_scene': session_info['custom_scene'],
                    'custom_character': session_info['custom_character'],
                    'result': response
                }
                save_exploration_result_to_mongodb(user_id, exploration_data)
                
                # 保存故事完成数据
                completion_data = {
                    'user_id': user_id,
                    'completion_time': datetime.now(UTC),
                    'total_chapters': session_info['total_chapters'],
                    'user_choices': session_info['user_choices'],
                    'user_choice_texts': session_info['user_choice_texts'],
                    'interaction_history': session_info['interaction_history'],
                    'final_result': response,
                    'exploration_type': 'random' if not session_info['is_custom_mode'] else 'custom',
                    'custom_scene': session_info['custom_scene'],
                    'custom_character': session_info['custom_character']
                }
                save_story_completion_to_mongodb(user_id, completion_data)
                
                # 提供重新开始选项
                keyboard = [
                    [KeyboardButton("是"), KeyboardButton("否")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                
                # 添加重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await update.message.reply_text(response, reply_markup=reply_markup)
                        # 探索结束时不需要提取选项文本
                        break
                    except Exception as e:
                        logging.error(f"发送消息失败 (第 {attempt + 1} 次): {str(e)}")
                        if attempt == max_retries - 1:
                            # 最后一次重试失败，尝试发送简单消息
                            try:
                                await update.message.reply_text("故事继续中...请稍等片刻。")
                            except:
                                logging.error("无法发送任何消息给用户")
                        else:
                            await asyncio.sleep(1)
            else:
                # 提供选择按钮
                keyboard = [
                    [KeyboardButton("A"), KeyboardButton("B")],
                    [KeyboardButton("C"), KeyboardButton("D")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                
                # 添加重试机制
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await update.message.reply_text(response, reply_markup=reply_markup)
                        # 提取并存储选项文本
                        _extract_and_store_choice_texts(user_id, response)
                        break
                    except Exception as e:
                        logging.error(f"发送消息失败 (第 {attempt + 1} 次): {str(e)}")
                        if attempt == max_retries - 1:
                            # 最后一次重试失败，尝试发送简单消息
                            try:
                                await update.message.reply_text("故事继续中...请稍等片刻。")
                            except:
                                logging.error("无法发送任何消息给用户")
                        else:
                            await asyncio.sleep(1)
            
        finally:
            start_typing.cancel()
            try:
                await start_typing
            except asyncio.CancelledError:
                pass
        return
    
    # 检查是否要重新开始探索
    if user_stage.get(user_id) == "exploration_completed":
        if text.lower() in ["是", "yes", "y"]:
            # 重置并重新开始
            bot_instance.reset_session()
            user_stage[user_id] = "awaiting_start"
            await start(update, context)
        else:
            await update.message.reply_text("感谢你的参与！期待下次与你相遇。输入 /start 随时重新开始探索。")
            # 清理会话
            if user_id in user_bots:
                del user_bots[user_id]
            if user_id in user_stage:
                del user_stage[user_id]
            if user_id in user_exploration_started:
                del user_exploration_started[user_id]
            if user_id in user_choice_texts:
                del user_choice_texts[user_id]
        return
    
    # 其他输入，提示用户选择选项
    await update.message.reply_text("请选择A、B、C或D来决定你的下一步行动。")

if __name__ == '__main__':
    # Test MongoDB connection before starting the bot
    if not test_mongodb_connection():
        logging.error("Failed to connect to MongoDB. Please check your credentials and connection settings.")
        exit(1)
    
    # Validate configuration
    if not Config.validate_config():
        logging.error("Configuration validation failed. Please check your environment variables.")
        exit(1)
    
    # 配置网络连接设置
    import httpx
    from telegram.request import HTTPXRequest
    
    # 创建自定义的HTTP请求客户端
    request = HTTPXRequest(
        connection_pool_size=16,
        connect_timeout=15.0,
        read_timeout=15.0,
        write_timeout=15.0,
        pool_timeout=10.0,
    )
    
    # 构建应用
    application = ApplicationBuilder().token(Config.API.TELEGRAM_BOT_TOKEN).request(request).build()
    
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    # 添加错误处理器
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理机器人错误"""
        logging.error(f"机器人出现错误: {context.error}")
        if update and hasattr(update, 'message') and update.message:
            try:
                await update.message.reply_text("抱歉，出现了一些技术问题。请稍后再试。")
            except:
                logging.error("无法发送错误消息给用户")
    
    application.add_error_handler(error_handler)
    
    # 添加错误处理和重试逻辑
    logging.info("正在启动灵魂探索机器人...")
    logging.info(f"使用Token: {Config.API.TELEGRAM_BOT_TOKEN[:10]}...")
    
    # 网络连接诊断
    def test_network_connectivity():
        """测试网络连接"""
        import subprocess
        import socket
        
        try:
            socket.gethostbyname("api.telegram.org")
            logging.info("✅ DNS解析正常")
        except socket.gaierror:
            logging.error("❌ DNS解析失败，无法解析 api.telegram.org")
            return False
        
        try:
            result = subprocess.run(['ping', '-c', '1', '-W', '5', '8.8.8.8'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logging.info("✅ 网络连通性正常")
            else:
                logging.error("❌ 网络连通性异常")
                return False
        except Exception as e:
            logging.error(f"❌ 网络测试失败: {str(e)}")
            return False
        
        return True
    
    # 执行网络诊断
    if not test_network_connectivity():
        logging.error("网络连接有问题，请检查网络设置或代理配置")
        exit(1)
    
    try:
        # 尝试启动机器人
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logging.info(f"尝试启动灵魂探索机器人 (第 {retry_count + 1} 次)")
                application.run_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                    close_loop=False,
                    timeout=10,
                    bootstrap_retries=3
                )
                break
            except Exception as e:
                retry_count += 1
                logging.error(f"启动失败 (第 {retry_count} 次): {str(e)}")
                if retry_count < max_retries:
                    wait_time = min(5 * retry_count, 30)
                    logging.info(f"等待 {wait_time} 秒后重试...")
                    import time
                    time.sleep(wait_time)
                else:
                    logging.error("所有重试都失败了，退出程序")
                    raise e
                    
    except KeyboardInterrupt:
        logging.info("收到中断信号，正在关闭机器人...")
    except Exception as e:
        logging.error(f"机器人运行出错: {str(e)}")
        logging.error("请检查网络连接和Token是否正确") 