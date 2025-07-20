import logging
import os
import asyncio
from datetime import datetime, UTC
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from matchmaker_bot_requests import MatchmakerBot
from config import Config
import re  # 新增：导入正则模块

# MongoDB setup with authentication
from pymongo import MongoClient
client = MongoClient(Config.Database.get_auth_uri())
db = client[Config.Database.MONGO_DATABASE]
sessions_collection = db[Config.Database.SESSIONS_COLLECTION]

logging.basicConfig(
    format=Config.Logging.LOG_FORMAT,
    level=getattr(logging, Config.Logging.LOG_LEVEL)
)

# Store user bot instances
user_bots = {}
# Store user session stage (e.g., waiting_ready, in_interview)
user_stage = {}  # 记录每个用户的会话阶段
# Store user gender detection status
user_gender_detected = {}  # 记录用户是否已经完成性别识别

# Test MongoDB connection
def test_mongodb_connection():
    """Test MongoDB connection and authentication."""
    try:
        # Test the connection by listing collections
        collections = db.list_collection_names()
        logging.info(f"MongoDB connection successful. Available collections: {collections}")
        return True
    except Exception as e:
        logging.error(f"MongoDB connection failed: {str(e)}")
        return False

# MongoDB helper functions
def save_session_to_mongodb(user_id: int, gender: str):
    """Save initial session data to MongoDB using user_id as the document ID."""
    try:
        session_data = {
            '_id': user_id,
            'gender': gender,
            'final_string': None,
            'started_at': datetime.now(UTC),
            'created_at': datetime.now(UTC)
        }
        sessions_collection.replace_one({'_id': user_id}, session_data, upsert=True)
        logging.info(f"Session saved to MongoDB for user {user_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving session to MongoDB for user {user_id}: {str(e)}")
        return False

def get_session_from_mongodb(user_id: int):
    """Get session data from MongoDB using user_id."""
    try:
        return sessions_collection.find_one({'_id': user_id})
    except Exception as e:
        logging.error(f"Error getting session from MongoDB for user {user_id}: {str(e)}")
        return None

def save_gemini_response_to_mongodb(user_id: int, final_string: str):
    """Save final string to MongoDB when #end tag is detected."""
    try:
        sessions_collection.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'final_string': final_string
                }
            }
        )
        logging.info(f"Final string saved to MongoDB for user {user_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving final string to MongoDB for user {user_id}: {str(e)}")
        return False

# ========== 新增：保存完整会话信息到MongoDB ==========
def save_final_session_to_mongodb(user_id: int, gender: str, turns: int, started_at, ended_at, final_string: str, filter_questions: str, user_rating: float):
    """保存完整会话信息到MongoDB，包括用户id、性别、轮数、时间、总结、筛选问题、评分。user_rating支持小数。"""
    try:
        sessions_collection.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'gender': gender,
                    'turns': turns,
                    'started_at': started_at,
                    'ended_at': ended_at,
                    'final_string': final_string,
                    'filter_questions': filter_questions,
                    'user_rating': user_rating
                },
                '$inc': {'experience_count': 1}  # 新增：体验次数+1
            },
            upsert=True
        )
        logging.info(f"Final session info saved to MongoDB for user {user_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving final session info to MongoDB for user {user_id}: {str(e)}")
        return False

# ========== 新增：轮数统计 ==========
user_turns = {}  # 记录每个用户的对话轮数
user_started_at = {}  # 记录每个用户的会话开始时间
user_final_string = {}  # 记录每个用户的完整总结
user_filter_questions = {}  # 记录每个用户的筛选问题
user_waiting_rating = {}  # 记录是否等待评分

# ========== 新增：内部白名单用户ID，仅这些用户可反复体验 ==========
INTERNAL_USER_IDS = [7773152103, 8062279607]  # 允许这两个Telegram号反复体验

def detect_gender_from_text(text: str) -> str | None:
    """
    从文本中智能检测性别关键词，优先女性，再男性，使用正则整词匹配，避免 he 匹配到 her
    返回 'male', 'female' 或 None
    """
    text_lower = text.lower().strip()
    
    # 女性关键词集合
    female_keywords = [
        'female', 'woman', 'girl', 'lady', 'sister', 'daughter',
        'she', 'her', 'hers', 'herself'
    ]
    # 男性关键词集合
    male_keywords = [
        'male', 'man', 'boy', 'guy', 'dude', 'gentleman', 'brother', 'son',
        'he', 'him', 'his', 'himself'
    ]
    
    # 添加调试日志
    logging.info(f"检测性别关键词(正则) - 输入文本: '{text}' -> 小写: '{text_lower}'")
    
    # 优先检测女性关键词
    for keyword in female_keywords:
        # 使用正则整词匹配，忽略大小写
        if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
            logging.info(f"检测到女性关键词(正则): '{keyword}'")
            return 'female'
    # 再检测男性关键词
    for keyword in male_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
            logging.info(f"检测到男性关键词(正则): '{keyword}'")
            return 'male'
    logging.info("未检测到性别关键词(正则)")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued. 恢复性别选择，选完直接进入AI对话，无需are you ready。"""
    if not update.message:
        return
    user_id = update.effective_user.id if update.effective_user else None
    if user_id:
        # 新增：非白名单用户只能体验一次
        if user_id not in INTERNAL_USER_IDS:
            session = get_session_from_mongodb(user_id)
            if session and session.get('experience_count', 0) >= 1:
                await update.message.reply_text(
                    "Well, that brings our chat to a close! Thanks so much for your feedback. It really helps me improve and become more helpful. If you're looking to get matched or need more emotional support, feel free to join our channel! 👉https://t.me/lovelush_soulmate"
                )
                return
        # 重置用户状态，允许重新开始
        if user_id in user_bots:
            del user_bots[user_id]
        if user_id in user_stage:
            del user_stage[user_id]
        if user_id in user_gender_detected:
            del user_gender_detected[user_id]
        # 新增：设置用户状态为等待性别选择
        user_stage[user_id] = "awaiting_gender"
    # ======= 恢复性别选择流程 =======
    keyboard = [
        [KeyboardButton(Config.Bot.GENDER_OPTIONS["male"]), KeyboardButton(Config.Bot.GENDER_OPTIONS["female"])]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        Config.Bot.GREETING_MESSAGE,
        reply_markup=reply_markup
    )
    # ======= END =======

# =================== 旧流程相关代码已注释 ===================
# 在 handle_message 里，性别选择、are you ready、waiting_ready等相关分支全部注释掉，仅保留AI对话主流程。
# ==========================================================

async def _keep_typing(bot, chat_id: int):
    """
    Keep showing typing indicator until cancelled.
    
    Args:
        bot: The bot instance
        chat_id (int): The chat ID to show typing in
    """
    while True:
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(Config.Bot.TYPING_DURATION)  # Telegram typing indicator lasts ~5 seconds
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Error in typing indicator: {str(e)}")
            break

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return
    # ========== 新增：内部白名单用户可反复体验 ==========
    if user_id in INTERNAL_USER_IDS:
        pass  # 直接进入后续正常流程
    else:
        # ========== 每位普通用户只能体验一次完整流程 ========== 
        session = get_session_from_mongodb(user_id)
        if session and session.get('experience_count', 0) >= 1:
            # 已体验过，拦截所有消息，只允许 /clear 指令
            if update.message.text.strip().lower() == "/clear":
                # 清除数据库和所有内存状态，允许重新体验
                sessions_collection.delete_one({'_id': user_id})
                for d in [user_bots, user_stage, user_gender_detected, user_turns, user_started_at, user_final_string, user_filter_questions, user_waiting_rating]:
                    d.pop(user_id, None)
                await update.message.reply_text("Session cleared. You can now start a new experience by typing /start.")
            else:
                await update.message.reply_text("Well, that brings our chat to a close! Thanks so much for your feedback. It really helps me improve and become more helpful. If you're looking to get matched or need more emotional support, feel free to join our channel! 👉https://t.me/lovelush_soulmate")
            return
    # ========== 轮数统计 ==========
    if user_id not in user_turns:
        user_turns[user_id] = 0
        user_started_at[user_id] = datetime.now(UTC)
    user_turns[user_id] += 1
    # ========== 评分流程优先判断 ==========
    if user_waiting_rating.get(user_id, False):
        score_text = update.message.text.strip()
        try:
            # 新增：支持英文和小数评分
            score_map = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
            }
            score_lower = score_text.lower()
            # 英文转数字
            if score_lower in score_map:
                score = score_map[score_lower]
            else:
                # 支持小数
                score = float(score_text)
                # 四舍五入到一位小数
                score = round(score, 1)
            if 1 <= score <= 10:
                # 保存到MongoDB（补充评分字段）
                session = get_session_from_mongodb(user_id)
                gender = session.get('gender', '') if session and session.get('gender') else ''
                started_at = user_started_at.get(user_id)
                ended_at = datetime.now(UTC)
                final_string = user_final_string.get(user_id, '')
                filter_questions = user_filter_questions.get(user_id, '')
                save_final_session_to_mongodb(
                    user_id=user_id,
                    gender=gender,
                    turns=user_turns.get(user_id, 0),
                    started_at=started_at,
                    ended_at=ended_at,
                    final_string=final_string,
                    filter_questions=filter_questions,
                    user_rating=score
                )
                await update.message.reply_text("Well, that brings our chat to a close! Thanks so much for your feedback. It really helps me improve and become more helpful. If you're looking to get matched or need more emotional support, feel free to join our channel! 👉https://t.me/lovelush_soulmate")
                # 清理所有会话相关状态
                user_waiting_rating[user_id] = False
                user_turns.pop(user_id, None)
                user_started_at.pop(user_id, None)
                user_final_string.pop(user_id, None)
                user_filter_questions.pop(user_id, None)
                return
            else:
                await update.message.reply_text("Please enter a number between 1 and 10 (decimals and English words are supported).")
                return
        except Exception:
            # 非法输入（非数字/英文），直接提示会话已结束
            await update.message.reply_text("Session ended. To start a new experience, please type /start.")
            # 清理所有会话相关状态，防止反复评分
            user_waiting_rating[user_id] = False
            user_turns.pop(user_id, None)
            user_started_at.pop(user_id, None)
            user_final_string.pop(user_id, None)
            user_filter_questions.pop(user_id, None)
            return
    # ========== 结束后只允许 /start 指令重新开始 ==========
    # 如果用户已不在 user_bots（即会话已结束），只允许 /start，否则一律提示会话已结束
    if user_id not in user_bots:
        # 新增：如果用户处于等待性别选择阶段，允许输入性别选项
        if user_stage.get(user_id) == "awaiting_gender":
            # 检测性别关键词
            text = update.message.text
            user_text = text.lower().strip()
            gender = None
            if user_text in [Config.Bot.GENDER_OPTIONS["male"].lower(), "boy", "male", "man", "我是男孩子", "男"]:
                gender = "male"
            elif user_text in [Config.Bot.GENDER_OPTIONS["female"].lower(), "girl", "female", "woman", "我是女孩子", "女"]:
                gender = "female"
            if gender:
                api_key = Config.API.GEMINI_API_KEY
                if not api_key:
                    await update.message.reply_text(Config.Bot.ERROR_CONFIG_MESSAGE)
                    return
                user_bots[user_id] = MatchmakerBot(api_key, gender=gender)
                user_stage[user_id] = "in_interview"  # 进入AI面试阶段
                # 新增：保存用户性别到数据库，确保gender字段正确
                save_session_to_mongodb(user_id, gender)
                # AI主动发起第一问
                first_question = await user_bots[user_id].send_message_async("")
                await update.message.reply_text(first_question)
                return
            else:
                # 未识别性别，继续提示选择
                keyboard = [
                    [KeyboardButton(Config.Bot.GENDER_OPTIONS["male"]), KeyboardButton(Config.Bot.GENDER_OPTIONS["female"])]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                await update.message.reply_text(
                    Config.Bot.GREETING_MESSAGE,
                    reply_markup=reply_markup
                )
                return
        elif update.message.text.strip().lower() == "/start":
            # 用户主动发送 /start，重新进入性别选择
            await start(update, context)
        else:
            # 其它输入一律提示会话已结束
            await update.message.reply_text("Session ended. To start a new experience, please type /start.")
        return
    # ======= 性别选择分流 =======
    text = update.message.text
    user_text = text.lower().strip()
    if user_id not in user_bots:
        # 检测性别关键词
        gender = None
        if user_text in [Config.Bot.GENDER_OPTIONS["male"].lower(), "boy", "male", "man", "我是男孩子", "男"]:
            gender = "male"
        elif user_text in [Config.Bot.GENDER_OPTIONS["female"].lower(), "girl", "female", "woman", "我是女孩子", "女"]:
            gender = "female"
        if gender:
            api_key = Config.API.GEMINI_API_KEY
            if not api_key:
                await update.message.reply_text(Config.Bot.ERROR_CONFIG_MESSAGE)
                return
            user_bots[user_id] = MatchmakerBot(api_key, gender=gender)
            user_stage[user_id] = "in_interview"
            # 新增：保存用户性别到数据库，确保gender字段正确
            save_session_to_mongodb(user_id, gender)
            # AI主动发起第一问
            first_question = await user_bots[user_id].send_message_async("")
            await update.message.reply_text(first_question)
            return
        else:
            # 未识别性别，提示用户选择
            keyboard = [
                [KeyboardButton(Config.Bot.GENDER_OPTIONS["male"]), KeyboardButton(Config.Bot.GENDER_OPTIONS["female"])]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(
                Config.Bot.GREETING_MESSAGE,
                reply_markup=reply_markup
            )
        return
    # ======= END =======
    
    # 新流程：所有用户直接进入AI对话
    if user_id not in user_bots:
        # 若未初始化，自动初始化
        api_key = Config.API.GEMINI_API_KEY
        if not api_key:
            await update.message.reply_text(Config.Bot.ERROR_CONFIG_MESSAGE)
        return
        user_bots[user_id] = MatchmakerBot(api_key, gender="female")
        user_stage[user_id] = "in_interview"
    
    # AI 面试流程
    try:
        chat_id = update.effective_chat.id if update.effective_chat else None
        if not chat_id:
            return
        # Start typing indicator
        typing_task = asyncio.create_task(
            _keep_typing(context.bot, chat_id)
        )
        try:
            bot_instance = user_bots[user_id]
            # 确保用户输入是安全的UTF-8字符串
            user_text = update.message.text
            if user_text is None:
                user_text = ""
            elif isinstance(user_text, bytes):
                try:
                    user_text = user_text.decode('utf-8')
                except UnicodeDecodeError:
                    user_text = user_text.decode('utf-8', errors='ignore')
            elif not isinstance(user_text, str):
                user_text = str(user_text)
            
            response = await bot_instance.send_message_async(user_text)
            profile_keywords = [
                "Your Ideal Partner Profile",
                "Here is your ideal partner profile", 
                "Here's your ideal partner profile",
                "Your ideal partner profile",
                "Ideal Partner Profile",
                "Partner Profile",
                "Here is the profile",
                "Here's the profile",
                "The profile of your ideal partner",
                "Your perfect match profile",
                "Here is your perfect match",
                "Your ideal match profile"
            ]
            has_profile = any(keyword in response for keyword in profile_keywords)
            if has_profile and "#end" not in response:
                detected_keyword = next(keyword for keyword in profile_keywords if keyword in response)
                logging.info(f"检测到最终总结，Profile关键词: '{detected_keyword}'，准备分割消息")
                parts = bot_instance._split_final_summary(response)
                logging.info(f"分割结果：{len(parts)} 部分")
                if len(parts) == 2:
                    logging.info(f"成功分割，发送第一部分：{len(parts[0])} 字符")
                    await update.message.reply_text(parts[0])
                    await asyncio.sleep(1)
                    logging.info(f"发送第二部分：{len(parts[1])} 字符")
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=parts[1])
                        # ========== 新增：记录完整总结和筛选问题 ==========
                        user_final_string[user_id] = response  # 保存完整AI输出
                        user_filter_questions[user_id] = parts[1]  # 只保存筛选问题部分
                        user_waiting_rating[user_id] = True
                        # ========== 分割后立即保存final_string和filter_questions，评分为-1 ==========
                        session = get_session_from_mongodb(user_id)
                        gender = session.get('gender', '') if session and session.get('gender') else ''
                        started_at = user_started_at.get(user_id)
                        ended_at = None
                        save_final_session_to_mongodb(
                            user_id=user_id,
                            gender=gender,
                            turns=user_turns.get(user_id, 0),
                            started_at=started_at,
                            ended_at=ended_at,
                            final_string=response,
                            filter_questions=parts[1],
                            user_rating=-1
                        )
                        await asyncio.sleep(1)
                        await context.bot.send_message(chat_id=chat_id, text="How do you feel about these filter questions? Please rate them from 1 (not useful) to 10 (very useful).")
                        return
                    except Exception as e:
                        logging.error(f"发送第二部分失败：{str(e)}")
                else:
                    logging.info(f"分割失败，按原样发送")
                    await update.message.reply_text(response)
            else:
                await update.message.reply_text(response)
            if Config.Bot.END_TAG in response:
                save_gemini_response_to_mongodb(user_id, response)
                bot_instance.clear_history()
                if user_id in user_bots:
                    del user_bots[user_id]
                if user_id in user_stage:
                    del user_stage[user_id]
                if user_id in user_gender_detected:
                    del user_gender_detected[user_id]
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=Config.Bot.VIEW_MALE_ANSWERS_MESSAGE,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(text=Config.Bot.VIEW_MALE_ANSWERS_BUTTON, url=Config.Bot.BOT_WEBAPP_URL)]
                    ])
                )
        finally:
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass
        # ========== 新增：每轮对话都存储会话快照 ==========
        session = get_session_from_mongodb(user_id)
        gender = session.get('gender', '') if session and session.get('gender') else ''
        started_at = user_started_at.get(user_id)
        ended_at = None  # 未结束
        # 可选：存完整历史
        history = None
        if hasattr(bot_instance, 'message_history'):
            history = bot_instance.message_history
        # 未到最后一轮，final_string/filter_questions/user_rating 均为 None
        sessions_collection.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'gender': gender,
                    'turns': user_turns.get(user_id, 0),
                    'started_at': started_at,
                    'ended_at': ended_at,
                    'last_user_message': update.message.text,
                    'last_bot_message': response,
                    'message_history': history,
                    'final_string': None,
                    'filter_questions': None,
                    'user_rating': -1  # 未评分时明确为-1
                }
            },
            upsert=True
        )
    except Exception as e:
        logging.error(f"Error processing message for user {user_id}: {str(e)}")
        await update.message.reply_text(Config.Bot.ERROR_PROCESSING_MESSAGE)

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
    
    # 创建自定义的HTTP请求客户端，增加超时和重试设置
    # 增加连接池大小，减少超时时间，避免连接池耗尽
    request = HTTPXRequest(
        connection_pool_size=16,  # 增加连接池大小
        connect_timeout=15.0,     # 减少连接超时
        read_timeout=15.0,        # 减少读取超时
        write_timeout=15.0,       # 减少写入超时
        pool_timeout=10.0,        # 减少池超时，避免长时间等待
    )
    
    # 构建应用时使用自定义请求客户端
    application = ApplicationBuilder().token(Config.API.TELEGRAM_BOT_TOKEN).request(request).build()
    
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    # 添加错误处理和重试逻辑
    logging.info("正在启动Telegram机器人...")
    logging.info(f"使用Token: {Config.API.TELEGRAM_BOT_TOKEN[:10]}...")
    
    # 网络连接诊断
    def test_network_connectivity():
        """测试网络连接"""
        import subprocess
        import socket
        
        # 测试DNS解析
        try:
            socket.gethostbyname("api.telegram.org")
            logging.info("✅ DNS解析正常")
        except socket.gaierror:
            logging.error("❌ DNS解析失败，无法解析 api.telegram.org")
            return False
        
        # 测试网络连通性
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
        logging.error("建议：")
        logging.error("1. 检查网络连接")
        logging.error("2. 配置代理服务器")
        logging.error("3. 检查防火墙设置")
        exit(1)
    
    try:
        # 尝试启动机器人，增加重试机制
        max_retries = 5  # 增加重试次数
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logging.info(f"尝试启动机器人 (第 {retry_count + 1} 次)")
                application.run_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                    close_loop=False,
                    timeout=10,  # 添加轮询超时
                    bootstrap_retries=3  # 添加启动重试
                )
                break  # 如果成功启动，跳出循环
            except Exception as e:
                retry_count += 1
                logging.error(f"启动失败 (第 {retry_count} 次): {str(e)}")
                if retry_count < max_retries:
                    wait_time = min(5 * retry_count, 30)  # 递增等待时间，最大30秒
                    logging.info(f"等待 {wait_time} 秒后重试...")
                    import time
                    time.sleep(wait_time)
                else:
                    logging.error("所有重试都失败了，退出程序")
                    logging.error("可能的原因：")
                    logging.error("1. 网络连接问题")
                    logging.error("2. Telegram API 服务不可用")
                    logging.error("3. Bot Token 无效")
                    logging.error("4. 防火墙或代理阻止连接")
                    raise e
                    
    except KeyboardInterrupt:
        logging.info("收到中断信号，正在关闭机器人...")
    except Exception as e:
        logging.error(f"机器人运行出错: {str(e)}")
        logging.error("请检查网络连接和Token是否正确")