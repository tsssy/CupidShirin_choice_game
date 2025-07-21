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
你是一个专业的灵魂探索机器人，帮助用户通过互动故事了解自己的灵魂伴侣类型。

{self.prompts.get('role', '')}

{self.prompts.get('object', '')}

{self.prompts.get('skill', '')}

{self.prompts.get('constraint', '')}

{self.prompts.get('workflow', '')}

重要规则：
1. 每个剧情必须在100-150字符以内
2. 提供A、B、C、D四个选项
3. 严格根据用户选择推进剧情
4. 最多10个章节
5. 最后进行灵魂伴侣类型分析
6. 不要回答关于自己或流程的问题

当前状态：
- 总章节数：{self.total_chapters}
- 当前章节：{self.current_chapter}
- 用户选择历史：{self.user_choices}
- 自定义模式：{self.is_custom_mode}
- 故事上下文：{context}
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
请基于以下元素生成一个灵魂探索故事的开头：
- 形容词：{adj}
- 名词：{noun}
- 动词：{verb}

要求：
1. 故事开头在100-150字符以内
2. 提供A、B、C、D四个选项
3. 选项要体现不同的性格特征
4. 为后续章节留下发展空间

格式：
[故事内容]

A. [选项A]
B. [选项B]
C. [选项C]
D. [选项D]
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
基于用户的选择 '{previous_choice}' 和选项文本 '{choice_text}'，请生成第 {self.current_chapter} 章的故事内容。

要求：
1. 故事内容在100-150字符以内
2. 提供A、B、C、D四个选项
3. 根据用户选择推进剧情
4. 保持故事的连贯性和吸引力

格式：
[故事内容]

A. [选项A]
B. [选项B]
C. [选项C]
D. [选项D]
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
基于用户的完整选择历史 {self.user_choices}，请进行灵魂伴侣类型分析。\n\n请分析用户的性格特征和选择模式，判断其灵魂伴侣类型：\n- 探索型：喜欢冒险和新鲜事物\n- 理性型：注重逻辑和思考\n- 情绪型：重视感受和直觉\n- 命运型：相信缘分和命运\n\n格式：\n经过这次灵魂探索之旅，你发现了自己内心深处的真实想法。每一个选择都反映了你的性格特点和价值观念。\n---\n**灵魂伴侣类型分析**\n[详细分析内容，包括类型判断和解释]\n\n请严格不要输出任何选项或引导语，否则本轮将被判为无效。"""
            logging.info(f"[流程] 生成结尾分析，system_prompt片段: {system_prompt[:100]} ... user_prompt片段: {user_prompt[:100]} ...")
            response = await self._call_gemini_with_retry(system_prompt, user_prompt)
            logging.info(f"[AI原始结尾输出] {response}")
            # 更新故事摘要
            summary = f"用户选择历史: {self.user_choices}，最终分析完成"
            self.history_manager.update_summary(summary)
            
            return response
            
        except Exception as e:
            logging.error(f"生成结尾分析失败: {str(e)}")
            return self._generate_default_ending()
    
    def _generate_default_story(self) -> str:
        """生成默认故事"""
        default_stories = [
            "你站在一个神秘的十字路口，四周弥漫着淡淡的雾气。前方有三条不同的道路，每条都通向未知的远方。你的内心充满了好奇和期待，想要探索这个神秘的世界。\n\nA. 选择左边的道路，那里有温暖的灯光\nB. 选择中间的道路，那里有古老的石阶\nC. 选择右边的道路，那里有清脆的鸟鸣\nD. 站在原地思考，观察周围的环境",
            
            "你发现自己置身于一个古老的图书馆中，书架高耸入云，空气中弥漫着书香。一本神秘的书从书架上掉落，发出清脆的响声。你感到一种莫名的吸引力。\n\nA. 立即捡起那本书，翻开阅读\nB. 先观察周围的环境，确保安全\nC. 询问图书管理员关于这本书的信息\nD. 将书放回原处，继续寻找其他书籍"
        ]
        return random.choice(default_stories)
    
    def _generate_default_chapter(self, previous_choice: str) -> str:
        """生成默认章节"""
        default_chapters = [
            "你继续前行，发现了一个小木屋。木屋的门半开着，里面传来温暖的火光。你感到一种家的温暖。\n\nA. 走进木屋，探索内部\nB. 在门外等待，观察情况\nC. 绕道而行，继续前进\nD. 返回原路，寻找其他方向",
            
            "你遇到了一位神秘的老人，他正在花园里修剪花朵。老人抬头看了你一眼，眼中闪烁着智慧的光芒。\n\nA. 主动上前打招呼，询问道路\nB. 保持距离，观察老人的行为\nC. 等待老人先开口说话\nD. 默默离开，不打扰老人"
        ]
        return random.choice(default_chapters)
    
    def _generate_default_ending(self) -> str:
        """生成默认结尾"""
        return """经过这次灵魂探索之旅，你发现了自己内心深处的真实想法。每一个选择都反映了你的性格特点和价值观念。

---

**灵魂伴侣类型分析**
基于你在探索过程中的选择，你展现出了独特的个性特征。你倾向于在行动前深思熟虑，注重内心的感受和直觉。你的灵魂伴侣应该是一个能够理解你内心世界的人，能够与你进行深层次的交流，共同成长。"""
    
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