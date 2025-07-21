#!/usr/bin/env python3
"""
优化版灵魂探索机器人
- 实现指数退避重试机制
- 管理会话历史以减少令牌数
- 优化API调用效率
"""

import logging
import random
import asyncio
import time
from typing import List, Dict, Optional, Tuple
import google.generativeai as genai
from datetime import datetime, UTC
from config import Config

class ExponentialBackoffRetry:
    """指数退避重试机制"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, max_retries: int = 5):
        """
        初始化指数退避重试器
        
        Args:
            base_delay (float): 基础延迟时间（秒）
            max_delay (float): 最大延迟时间（秒）
            max_retries (int): 最大重试次数
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
    
    async def execute(self, func, *args, **kwargs):
        """
        执行函数，失败时使用指数退避重试
        
        Args:
            func: 要执行的函数
            *args, **kwargs: 函数参数
            
        Returns:
            函数执行结果
            
        Raises:
            Exception: 所有重试都失败后抛出最后一个异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    # 最后一次尝试失败，抛出异常
                    logging.error(f"所有重试都失败，最后异常: {str(e)}")
                    raise last_exception
                
                # 计算延迟时间（指数退避）
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                
                logging.warning(f"第 {attempt + 1} 次尝试失败: {str(e)}，等待 {delay:.2f} 秒后重试")
                await asyncio.sleep(delay)
        
        raise last_exception

class ConversationHistoryManager:
    """会话历史管理器"""
    
    def __init__(self, max_history_length: int = 5, max_summary_length: int = 200):
        """
        初始化会话历史管理器
        
        Args:
            max_history_length (int): 最大历史记录长度
            max_summary_length (int): 最大摘要长度
        """
        self.max_history_length = max_history_length
        self.max_summary_length = max_summary_length
        self.story_history = []
        self.interaction_history = []
        self.summary = ""
    
    def add_story_entry(self, chapter: int, story_text: str):
        """添加故事条目"""
        entry = {
            'chapter': chapter,
            'text': story_text,
            'timestamp': datetime.now(UTC)
        }
        self.story_history.append(entry)
        self._trim_history()
    
    def add_interaction_entry(self, user_choice: str, choice_text: str, ai_response: str):
        """添加交互条目"""
        entry = {
            'user_choice': user_choice,
            'choice_text': choice_text,
            'ai_response': ai_response,
            'timestamp': datetime.now(UTC)
        }
        self.interaction_history.append(entry)
        self._trim_history()
    
    def _trim_history(self):
        """修剪历史记录长度"""
        if len(self.story_history) > self.max_history_length:
            # 保留最新的记录
            self.story_history = self.story_history[-self.max_history_length:]
        
        if len(self.interaction_history) > self.max_history_length:
            # 保留最新的记录
            self.interaction_history = self.interaction_history[-self.max_history_length:]
    
    def get_optimized_context(self) -> str:
        """获取优化后的上下文（减少令牌数）"""
        context_parts = []
        
        # 添加摘要
        if self.summary:
            context_parts.append(f"故事摘要: {self.summary}")
        
        # 添加最近的故事历史（限制长度）
        recent_stories = self.story_history[-3:]  # 只保留最近3章
        if recent_stories:
            story_summary = []
            for entry in recent_stories:
                # 截取故事文本的前100个字符
                story_text = entry['text'][:100] + "..." if len(entry['text']) > 100 else entry['text']
                story_summary.append(f"第{entry['chapter']}章: {story_text}")
            context_parts.append("最近故事: " + " | ".join(story_summary))
        
        # 添加最近的交互历史（限制长度）
        recent_interactions = self.interaction_history[-2:]  # 只保留最近2次交互
        if recent_interactions:
            interaction_summary = []
            for entry in recent_interactions:
                interaction_summary.append(f"选择{entry['user_choice']}: {entry['choice_text'][:50]}...")
            context_parts.append("最近选择: " + " | ".join(interaction_summary))
        
        return " | ".join(context_parts) if context_parts else "故事开始"
    
    def update_summary(self, new_summary: str):
        """更新故事摘要"""
        self.summary = new_summary[:self.max_summary_length]
    
    def clear_history(self):
        """清空历史记录"""
        self.story_history.clear()
        self.interaction_history.clear()
        self.summary = ""

class SoulExplorerBotOptimized:
    """优化版灵魂探索机器人 - 基于AI的剧本编导和灵魂伴侣行为分析师"""
    
    def __init__(self, api_key: str):
        """初始化优化版灵魂探索机器人
        
        Args:
            api_key (str): Gemini API密钥
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 初始化重试机制
        self.retry_handler = ExponentialBackoffRetry(
            base_delay=1.0,  # 基础延迟1秒
            max_delay=30.0,  # 最大延迟30秒
            max_retries=3    # 最大重试3次
        )
        
        # 初始化会话历史管理器
        self.history_manager = ConversationHistoryManager(
            max_history_length=5,  # 最多保留5条历史记录
            max_summary_length=200  # 摘要最多200字符
        )
        
        # 初始化状态
        self.total_chapters = 5  # 总回合数设为5
        self.current_chapter = 0
        self.user_choices = []  # 记录用户选择
        self.user_choice_texts = []  # 记录用户选择的具体文本内容
        self.is_custom_mode = False  # 是否为自定义模式
        self.custom_scene = ""  # 自定义场景
        self.custom_character = ""  # 自定义角色
        
        # 故事状态跟踪
        self.current_location = ""  # 当前地点
        self.current_time = ""  # 当前时间
        self.current_context = ""  # 当前情境
        self.story_theme = ""  # 故事主题
        
        # 词汇片段池
        self.adjectives = [
            "神秘的", "温暖的", "冰冷的", "浪漫的", "紧张的", "平静的", 
            "喧嚣的", "寂静的", "明亮的", "昏暗的", "古老的", "现代的",
            "梦幻的", "现实的", "抽象的", "具体的", "复杂的", "简单的"
        ]
        
        self.nouns = [
            "灵魂", "心灵", "梦境", "现实", "时间", "空间", "记忆", "未来",
            "过去", "现在", "爱情", "友情", "亲情", "自由", "束缚", "希望",
            "绝望", "勇气", "恐惧", "智慧", "愚昧", "善良", "邪恶"
        ]
        
        self.verbs = [
            "穿越", "漂浮", "奔跑", "漫步", "思考", "感受", "观察", "倾听",
            "触摸", "拥抱", "分离", "相遇", "成长", "改变", "选择", "决定",
            "探索", "发现", "创造", "毁灭", "治愈", "伤害"
        ]
        
        # 加载提示词
        self.prompts = self._load_prompts()
        
        logging.info("优化版灵魂探索机器人初始化完成")
    
    def _load_prompts(self) -> Dict[str, str]:
        """加载提示词文件"""
        prompts = {}
        prompt_files = {
            'role': 'prompt/soul_explorer_role.md',
            'object': 'prompt/soul_explorer_object.md', 
            'skill': 'prompt/soul_explorer_skill.md',
            'constraint': 'prompt/soul_explorer_constraint.md',
            'workflow': 'prompt/soul_explorer_workflow.md'
        }
        
        for key, file_path in prompt_files.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    prompts[key] = f.read()
            except FileNotFoundError:
                logging.warning(f"提示词文件未找到: {file_path}")
                prompts[key] = ""
        
        return prompts
    
    def _generate_random_elements(self) -> Tuple[str, str, str]:
        """生成随机元素用于剧情创作"""
        adj = random.choice(self.adjectives)
        noun = random.choice(self.nouns)
        verb = random.choice(self.verbs)
        return adj, noun, verb
    
    def _build_optimized_system_prompt(self) -> str:
        """构建优化的系统提示词（减少令牌数）"""
        # 获取优化后的上下文
        context = self.history_manager.get_optimized_context()
        
        system_prompt = f"""
You must answer and interact with the user in English only. Do not use any Chinese.

{self.prompts.get('role', '')}

{self.prompts.get('object', '')}

{self.prompts.get('skill', '')}

{self.prompts.get('constraint', '')}

{self.prompts.get('workflow', '')}

Important Rules:
1. Each story must be within 100-150 characters.
2. Provide A, B, C, D four options.
3. Strictly advance the story based on user choices.
4. Maximum 10 chapters.
5. Perform soulmate type analysis at the end.
6. Do not answer questions about yourself or the process.

Current State:
- Total Chapters: {self.total_chapters}
- Current Chapter: {self.current_chapter}
- User Choice History: {self.user_choices}
- Custom Mode: {self.is_custom_mode}
- Story Context: {context}
"""
        system_prompt = "You must answer and interact with the user in English only. Do not use any Chinese.\n" + system_prompt
        return system_prompt
    
    async def _call_gemini_with_retry(self, system_prompt: str, user_prompt: str) -> str:
        """使用重试机制调用Gemini API"""
        import traceback
        async def _call_gemini():
            try:
                # 构建完整提示词
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                logging.info(f"[AI调用] 开始Gemini请求，prompt片段: {full_prompt[:100]} ...")
                response = self.model.generate_content(full_prompt)
                if response.text:
                    logging.info(f"[AI调用] Gemini返回内容长度: {len(response.text)}")
                    return response.text.strip()
                else:
                    raise Exception("Gemini返回空响应")
            except Exception as e:
                logging.error(f"[AI调用异常] Gemini API调用失败: {str(e)}\n{traceback.format_exc()}")
                raise e
        # 使用指数退避重试机制
        try:
            return await self.retry_handler.execute(_call_gemini)
        except Exception as e:
            logging.error(f"[AI调用异常] Gemini重试后仍失败: {str(e)}\n{traceback.format_exc()}")
            raise e
    
    async def start_exploration(self, user_input: str) -> str:
        """开始灵魂探索"""
        user_input = user_input.strip().lower()
        
        if user_input == "start":
            # 随机模式
            self.is_custom_mode = False
            adj, noun, verb = self._generate_random_elements()
            return await self._generate_random_story(adj, noun, verb)
        
        elif user_input == "自定义":
            # 自定义模式
            self.is_custom_mode = True
            return "请告诉我你想要的场景和角色设定。例如：'场景：一个神秘的图书馆，角色：一位寻找答案的学者'"
        
        else:
            return "请发送 'start' 开始随机探索，或发送 '自定义' 进行自定义设置。"
    
    async def _generate_random_story(self, adj: str, noun: str, verb: str) -> str:
        """生成随机故事"""
        try:
            system_prompt = self._build_optimized_system_prompt()
            
            user_prompt = f"""
Please generate a soul exploration story beginning based on the following elements:
- Adjective: {adj}
- Noun: {noun}
- Verb: {verb}

Requirements:
1. Story beginning must be within 100-150 characters.
2. Provide A, B, C, D four options.
3. Options must reflect different personality traits.
4. Leave room for development in subsequent chapters.

Format:
[Story Content]

A. [Option A]
B. [Option B]
C. [Option C]
D. [Option D]
"""
            
            response = await self._call_gemini_with_retry(system_prompt, user_prompt)
            
            # 记录到历史管理器
            self.history_manager.add_story_entry(self.current_chapter, response)
            
            return response
            
        except Exception as e:
            logging.error(f"生成随机故事失败: {str(e)}")
            return self._generate_default_story()
    
    async def process_choice(self, user_choice: str, choice_text: str = "") -> str:
        """处理用户选择"""
        try:
            logging.info(f"[流程] 用户选择: {user_choice}, 当前章节: {self.current_chapter+1}/{self.total_chapters}")
            self.user_choices.append(user_choice)
            if choice_text:
                self.user_choice_texts.append(choice_text)
            self.history_manager.add_interaction_entry(user_choice, choice_text, "")
            # 先生成剧情，再自增章节
            if self.current_chapter < self.total_chapters - 1:
                response = await self._generate_next_chapter(user_choice, choice_text)
                self.current_chapter += 1
                logging.info(f"[流程] 进入下一章节: {self.current_chapter+1}")
                return response
            else:
                # 最后一轮剧情，生成后直接进入结尾
                response = await self._generate_next_chapter(user_choice, choice_text)
                self.current_chapter += 1
                logging.info(f"[流程] 进入结尾分析, 当前章节: {self.current_chapter}, 用户选择历史: {self.user_choices}")
                ending = await self._generate_ending()
                return response + "\n\n" + ending
        except Exception as e:
            logging.error(f"处理用户选择失败: {str(e)}")
            return self._generate_default_chapter(user_choice)
    
    async def _generate_next_chapter(self, previous_choice: str, choice_text: str = "") -> str:
        """生成下一章节"""
        try:
            system_prompt = self._build_optimized_system_prompt()
            
            user_prompt = f"""
Based on the user's choice '{previous_choice}' and option text '{choice_text}', please generate the story content for Chapter {self.current_chapter}.

Requirements:
1. Story content must be within 100-150 characters.
2. Provide A, B, C, D four options.
3. Advance the story based on user choices.
4. Maintain story coherence and attractiveness.

Format:
[Story Content]

A. [Option A]
B. [Option B]
C. [Option C]
D. [Option D]
"""
            
            response = await self._call_gemini_with_retry(system_prompt, user_prompt)
            
            # 记录到历史管理器
            self.history_manager.add_story_entry(self.current_chapter, response)
            
            return response
            
        except Exception as e:
            logging.error(f"生成下一章节失败: {str(e)}")
            return self._generate_default_chapter(previous_choice)
    
    async def _generate_ending(self) -> str:
        """生成结尾分析"""
        try:
            system_prompt = self._build_optimized_system_prompt()
            
            user_prompt = f"""
Based on the user's complete choice history {self.user_choices}, please provide a soulmate type analysis.

Analyze the user's personality traits and choice patterns, and determine their soulmate type:
- Explorer: likes adventure and new things
- Logical: values logic and thinking
- Emotional: values feelings and intuition
- Destiny: believes in fate and destiny

Format:
After this soul exploration journey, you have discovered your true thoughts deep inside. Each choice reflects your personality traits and values.
---
**Soulmate Type Analysis**
[Detailed analysis, including type judgment and explanation]

IMPORTANT: Please output ONLY in English. Do NOT output any options, prompts, or any Chinese text. If you output anything else, this round will be considered invalid."""
            logging.info(f"[流程] 生成结尾分析，system_prompt片段: {system_prompt[:100]} ... user_prompt片段: {user_prompt[:100]} ...")
            response = await self._call_gemini_with_retry(system_prompt, user_prompt)
            logging.info(f"[AI原始结尾输出] {response}")
            # 更新故事摘要
            summary = f"User choice history: {self.user_choices}, final analysis complete"
            self.history_manager.update_summary(summary)
            
            return response
            
        except Exception as e:
            logging.error(f"生成结尾分析失败: {str(e)}")
            return self._generate_default_ending()
    
    def _generate_default_story(self) -> str:
        """生成默认故事"""
        default_stories = [
            """You stand at a mysterious crossroads, surrounded by a faint mist. There are three different paths leading to unknown horizons. Your heart is filled with curiosity and anticipation, wanting to explore this mysterious world.\n\nA. Choose the left path, where there are warm lights.\nB. Choose the middle path, where there are ancient stone steps.\nC. Choose the right path, where there are clear bird chirps.\nD. Stay in place and observe the surroundings.""",
            """You find yourself in an ancient library, with towering bookcases and a scent of books. A mysterious book falls from the shelf, emitting a crisp sound. You feel a mysterious attraction.\n\nA. Immediately pick up that book, open it and read.\nB. First observe the surroundings, ensure safety.\nC. Ask the librarian about the information about this book.\nD. Put the book back to its original place, continue searching for other books."""
        ]
        return random.choice(default_stories)
    
    def _generate_default_chapter(self, previous_choice: str) -> str:
        """生成默认章节"""
        default_chapters = [
            """You continue forward and find a small wooden house. The door of the wooden house is slightly ajar, and warm light shines from inside. You feel a sense of warmth at home.\n\nA. Enter the wooden house, explore the interior.\nB. Wait outside the door, observe the situation.\nC. Go around, continue forward.\nD. Return to the original path, look for other directions.""",
            """You encounter a mysterious old man, who is pruning flowers in the garden. The old man looked at you, his eyes gleaming with wisdom.\n\nA. Actively approach, ask for the way.\nB. Keep a distance, observe the old man's behavior.\nC. Wait for the old man to speak first.\nD. Leave silently, do not disturb the old man."""
        ]
        return random.choice(default_chapters)
    
    def _generate_default_ending(self) -> str:
        """Generate default ending in English only"""
        return """After this soul exploration journey, you have discovered your true thoughts deep inside. Each choice reflects your personality traits and values.\n\n---\n\n**Soulmate Type Analysis**\nBased on your choices, you have shown unique personality traits. You tend to think carefully before acting and value your inner feelings and intuition. Your soulmate should be someone who understands your inner world, can communicate deeply with you, and grow together with you."""
    
    def reset_session(self):
        """重置会话"""
        self.current_chapter = 0
        self.user_choices.clear()
        self.user_choice_texts.clear()
        self.is_custom_mode = False
        self.custom_scene = ""
        self.custom_character = ""
        self.current_location = ""
        self.current_time = ""
        self.current_context = ""
        self.story_theme = ""
        
        # 清空历史管理器
        self.history_manager.clear_history()
        
        logging.info("会话已重置")
    
    def get_session_info(self) -> Dict:
        """获取会话信息"""
        return {
            'current_chapter': self.current_chapter,
            'total_chapters': self.total_chapters,
            'user_choices': self.user_choices,
            'is_custom_mode': self.is_custom_mode,
            'history_length': len(self.history_manager.story_history),
            'interaction_length': len(self.history_manager.interaction_history)
        } 