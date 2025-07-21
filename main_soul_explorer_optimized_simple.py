#!/usr/bin/env python3
"""
简化版优化灵魂探索机器人主程序
使用指数退避重试机制和会话历史管理
"""

import asyncio
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import pymongo
from datetime import datetime, UTC
from config import Config
from soul_explorer_bot_optimized import SoulExplorerBotOptimized
import re
import traceback

# 彻底清理AI输出中的选项和引导语
# 中文注释：去掉“请选择你的下一步行动”、A/B/C/D选项、“你选择了...”等冗余内容
# 并去除多余空行，保证结尾输出干净

def clean_final_response(response: str) -> str:
    # 去掉“请选择你的下一步行动”及其后内容（多次出现也清理）
    response = re.sub(r'请选择你的下一步行动[:：]?.*', '', response, flags=re.DOTALL)
    # 去掉所有A. B. C. D.等选项（支持多种格式和无换行）
    response = re.sub(r'[\n\r]?[A-D][.．、:：\\s][^\n\r]*', '', response)
    # 去掉“你选择了...”等冗余
    response = re.sub(r'你选择了[^\n\r]*', '', response)
    # 去掉多余空行
    response = re.sub(r'\n{2,}', '\n', response)
    return response.strip()

# 配置日志
logging.basicConfig(
    format=Config.Logging.LOG_FORMAT,
    level=getattr(logging, Config.Logging.LOG_LEVEL),
    handlers=[
        logging.FileHandler('soul_explorer_optimized.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SoulExplorerTelegramBot:
    """优化版灵魂探索Telegram机器人"""
    
    def __init__(self):
        """初始化机器人"""
        self.api_key = Config.API.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY 未设置")
        
        # 初始化灵魂探索机器人
        self.soul_bot = SoulExplorerBotOptimized(self.api_key)
        
        # 初始化MongoDB连接
        self.mongo_client = pymongo.MongoClient(Config.Database.get_auth_uri())
        self.db = self.mongo_client[Config.Database.MONGO_DATABASE]
        self.sessions_collection = self.db[Config.Database.SESSIONS_COLLECTION]
        
        logger.info("优化版灵魂探索Telegram机器人初始化完成")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or "未知用户"
            
            logger.info(f"用户 {username} ({user_id}) 开始会话")
            
            # 重置机器人会话
            self.soul_bot.reset_session()
            
            # 保存会话到数据库
            session_data = {
                'user_id': user_id,
                'username': username,
                'start_time': datetime.now(UTC),
                'status': 'started',
                'bot_session': self.soul_bot.get_session_info()
            }
            
            self.sessions_collection.update_one(
                {'user_id': user_id},
                {'$set': session_data},
                upsert=True
            )
            
            # 创建欢迎消息和按钮
            welcome_text = Config.Bot.WELCOME_MESSAGE
            keyboard = [
                [InlineKeyboardButton(Config.Bot.START_EXPERIENCE_BUTTON, callback_data="start_exploration")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"处理 /start 命令时出错: {str(e)}")
            await update.message.reply_text(Config.Bot.ERROR_PROCESSING_MESSAGE)
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理按钮回调"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            username = update.effective_user.username or "未知用户"
            
            if query.data == "start_exploration":
                await self.start_exploration(update, context)
            elif query.data == "view_male_answers":
                await self.view_male_answers(update, context)
            elif query.data.startswith("choice_"):
                choice = query.data.split("_")[1]
                await self.handle_choice(update, context, choice)
                
        except Exception as e:
            logger.error(f"处理回调查询时出错: {str(e)}")
            await update.callback_query.edit_message_text(Config.Bot.ERROR_PROCESSING_MESSAGE)
    
    async def start_exploration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """开始灵魂探索"""
        try:
            query = update.callback_query
            
            # 显示准备消息
            await query.edit_message_text("🚀 正在准备你的灵魂探索之旅...")
            
            # 开始探索
            response = await self.soul_bot.start_exploration("start")
            
            # 更新会话信息
            user_id = update.effective_user.id
            session_data = {
                'user_id': user_id,
                'last_activity': datetime.now(UTC),
                'status': 'exploring',
                'bot_session': self.soul_bot.get_session_info()
            }
            self.sessions_collection.update_one(
                {'user_id': user_id},
                {'$set': session_data}
            )
            
            # 解析响应并创建选项按钮
            story_text, options = self._parse_story_response(response)
            
            keyboard = []
            for i, option in enumerate(options):
                choice_letter = chr(65 + i)  # A, B, C, D
                keyboard.append([InlineKeyboardButton(
                    f"{choice_letter}. {option}",
                    callback_data=f"choice_{choice_letter}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 发送新消息（不覆盖历史）
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"{story_text}\n\n请选择你的下一步行动：",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"开始探索时出错: {str(e)}")
            await update.callback_query.edit_message_text(Config.Bot.ERROR_PROCESSING_MESSAGE)
    
    async def handle_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE, choice: str):
        """处理用户选择"""
        try:
            query = update.callback_query
            
            # 获取选择文本
            choice_text = self._get_choice_text(query.message.reply_markup, choice)
            
            # 回复用户选择
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"你选择了 {choice}：{choice_text}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # 处理选择
            response = await self.soul_bot.process_choice(choice, choice_text)
            
            # ====== 实时写入/更新 telegram_session_story 集合 ======
            user_id = update.effective_user.id
            username = update.effective_user.username or "未知用户"
            # 用 start_time 作为本次会话唯一标识
            session_start_time = getattr(self.soul_bot, 'session_start_time', None)
            if not session_start_time:
                session_start_time = datetime.now(UTC)
                self.soul_bot.session_start_time = session_start_time
            session_id = f"{user_id}_{session_start_time.strftime('%Y%m%d%H%M%S')}"
            
            # 尝试提取最终分析和灵魂伴侣类型
            final_analysis = None
            soulmate_type = None
            if self.soul_bot.current_chapter >= self.soul_bot.total_chapters:
                final_analysis = response
                # 简单正则提取类型关键词
                match = re.search(r"类型[:：]\s*([\u4e00-\u9fa5A-Za-z]+)", response)
                if match:
                    soulmate_type = match.group(1)
                else:
                    # 兜底：找“探索型/理性型/情绪型/命运型”关键词
                    for t in ["探索型", "理性型", "情绪型", "命运型"]:
                        if t in response:
                            soulmate_type = t
                            break
            
            # 组装数据
            story_data = {
                'user_id': user_id,
                'username': username,
                'session_id': session_id,
                'start_time': session_start_time,
                'last_update_time': datetime.now(UTC),
                'current_chapter': self.soul_bot.current_chapter,
                'total_rounds': len(self.soul_bot.user_choices),
                'choices': self.soul_bot.user_choices,
                'choice_texts': self.soul_bot.user_choice_texts,
                'story_history': self.soul_bot.history_manager.story_history,
                'final_analysis': final_analysis,
                'soulmate_type': soulmate_type,
            }
            # 实时upsert
            if not hasattr(self, 'story_sessions_collection'):
                self.story_sessions_collection = self.db[Config.Database.STORY_SESSIONS_COLLECTION]
            self.story_sessions_collection.update_one(
                {'user_id': user_id, 'session_id': session_id},
                {'$set': story_data},
                upsert=True
            )
            # ====== END ======
            
            # 更新会话信息
            session_data = {
                'user_id': user_id,
                'last_activity': datetime.now(UTC),
                'bot_session': self.soul_bot.get_session_info()
            }
            self.sessions_collection.update_one(
                {'user_id': user_id},
                {'$set': session_data}
            )
            
            # 检查是否到达结尾
            if self.soul_bot.current_chapter >= self.soul_bot.total_chapters:
                # 故事结束
                logger.info(f"[流程] 进入结尾分支，AI原始输出: {response}")
                clean_response = clean_final_response(response)
                logger.info(f"[流程] 结尾清理后输出: {clean_response}")
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=clean_response,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f'发送画像总结失败: {e}\n{traceback.format_exc()}')
                try:
                    logger.info("准备发送thank you引导消息")
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Well, that brings our chat to a close! Thanks so much for your feedback. It really helps me improve and become more helpful. If you're looking to get matched or need more emotional support, feel free to join our channel! 👉https://t.me/lovelush_soulmate"
                    )
                    logger.info("thank you引导消息已发送")
                except Exception as e:
                    logger.error(f'发送引导消息失败: {e}\n{traceback.format_exc()}')
                    try:
                        logger.info("尝试发送中文简短感谢语")
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="感谢你的参与，祝你生活愉快！"
                        )
                        logger.info("中文感谢语已发送")
                    except Exception as e2:
                        logger.error(f'发送中文感谢语仍然失败: {e2}\n{traceback.format_exc()}')
                self.soul_bot.reset_session()
                
            else:
                # 继续故事，发送新消息
                story_text, options = self._parse_story_response(response)
                
                keyboard = []
                for i, option in enumerate(options):
                    choice_letter = chr(65 + i)  # A, B, C, D
                    keyboard.append([InlineKeyboardButton(
                        f"{choice_letter}. {option}",
                        callback_data=f"choice_{choice_letter}"
                    )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"{story_text}\n\n请选择你的下一步行动：",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            
        except Exception as e:
            logger.error(f"处理选择时出错: {str(e)}")
            await update.callback_query.edit_message_text(Config.Bot.ERROR_PROCESSING_MESSAGE)
    
    async def view_male_answers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """查看男生答案"""
        try:
            query = update.callback_query
            
            # 这里可以添加查看男生答案的逻辑
            response_text = "📊 男生答案统计功能正在开发中...\n\n敬请期待！"
            
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="start_exploration")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                response_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"查看男生答案时出错: {str(e)}")
            await update.callback_query.edit_message_text(Config.Bot.ERROR_PROCESSING_MESSAGE)
    
    def _parse_story_response(self, response: str) -> tuple:
        """解析故事响应，提取故事文本和选项"""
        lines = response.strip().split('\n')
        story_lines = []
        options = []
        
        for line in lines:
            line = line.strip()
            if line.startswith(('A.', 'B.', 'C.', 'D.')):
                # 提取选项文本
                option_text = line[2:].strip()
                if option_text:
                    options.append(option_text)
            elif line and not line.startswith('---'):
                # 故事文本
                story_lines.append(line)
        
        story_text = '\n'.join(story_lines)
        return story_text, options
    
    def _get_choice_text(self, reply_markup, choice: str) -> str:
        """从按钮中获取选择文本"""
        if not reply_markup or not reply_markup.inline_keyboard:
            return ""
        
        for row in reply_markup.inline_keyboard:
            for button in row:
                if button.callback_data == f"choice_{choice}":
                    # 移除选项字母前缀（如 "A. "）
                    text = button.text
                    if '. ' in text:
                        return text.split('. ', 1)[1]
                    return text
        
        return ""
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理文本消息"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or "未知用户"
            message_text = update.message.text
            
            logger.info(f"收到来自 {username} ({user_id}) 的消息: {message_text}")
            
            # 检查是否是命令
            if message_text.startswith('/'):
                await update.message.reply_text("请使用 /start 命令开始灵魂探索之旅！")
                return
            
            # 检查是否是开始探索
            if message_text.lower() in ['start', '开始', '开始探索']:
                await self.start_exploration(update, context)
                return
            
            # 默认回复
            await update.message.reply_text(
                "请使用 /start 命令开始你的灵魂探索之旅！\n\n"
                "或者点击下方按钮开始体验：",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(Config.Bot.START_EXPERIENCE_BUTTON, callback_data="start_exploration")
                ]])
            )
            
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            await update.message.reply_text(Config.Bot.ERROR_PROCESSING_MESSAGE)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """错误处理器"""
        logger.error(f"更新 {update} 导致错误 {context.error}")
        
        try:
            if update.effective_message:
                await update.effective_message.reply_text(Config.Bot.ERROR_PROCESSING_MESSAGE)
        except Exception as e:
            logger.error(f"发送错误消息时出错: {str(e)}")

def main():
    """主函数"""
    try:
        # 验证配置
        if not Config.validate_config():
            logger.error("配置验证失败")
            return
        
        # 创建机器人实例
        bot = SoulExplorerTelegramBot()
        
        # 创建应用
        application = Application.builder().token(Config.get_bot_token()).build()
        
        # 添加处理器
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CallbackQueryHandler(bot.handle_callback_query))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        
        # 添加错误处理器
        application.add_error_handler(bot.error_handler)
        
        # 启动机器人
        logger.info("优化版灵魂探索机器人启动中...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"启动机器人时出错: {str(e)}")
        raise

if __name__ == "__main__":
    main() 