import logging
import random
import asyncio
import time
from collections import deque
from typing import List, Dict, Optional, Tuple
import google.generativeai as genai
from datetime import datetime, UTC

class RateLimiter:
    """API请求限流器"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.last_error_time = 0
    
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
                logging.warning(f"⚠️ 达到API限制，等待 {wait_time:.2f} 秒...")
                await asyncio.sleep(wait_time)
        
        # 记录当前请求
        self.requests.append(now)
        return True
    
    async def handle_429_error(self):
        """处理429错误"""
        now = time.time()
        if now - self.last_error_time > 60:  # 避免频繁重试
            self.last_error_time = now
            logging.warning("🚨 检测到429错误，等待60秒后重试...")
            await asyncio.sleep(60)
        else:
            logging.warning("🚨 429错误，等待额外30秒...")
            await asyncio.sleep(30)

class RateLimitedSoulExplorerBot:
    """带限流器的灵魂探索机器人"""
    
    def __init__(self, api_key: str):
        """初始化带限流器的机器人"""
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 初始化限流器（免费版限制）
        self.rate_limiter = RateLimiter(max_requests=15, time_window=60)  # 每分钟15次
        self.daily_limiter = RateLimiter(max_requests=50, time_window=86400)  # 每天50次
        
        # 初始化状态
        self.total_chapters = 10
        self.current_chapter = 1
        self.user_choices = []
        self.user_choice_texts = []
        self.story_history = []
        self.interaction_history = []
        
        # 两次生成配置
        self.phase1_chapters = {}
        self.phase2_chapters = {}
        self.phase1_complete = False
        self.phase2_complete = False
        self.phase1_count = 5
        self.phase2_count = 5
        
        # 故事状态
        self.current_location = ""
        self.current_time = ""
        self.current_context = ""
        self.story_theme = ""
        
        # 词汇池
        self.adjectives = ["神秘的", "温暖的", "冰冷的", "浪漫的", "紧张的", "平静的"]
        self.nouns = ["灵魂", "心灵", "梦境", "现实", "时间", "空间"]
        self.verbs = ["穿越", "漂浮", "奔跑", "漫步", "思考", "感受"]
        
        logging.info("带限流器的两次生成灵魂探索机器人初始化完成")
    
    async def start_exploration(self, user_input: str) -> str:
        """开始探索 - 第一阶段生成"""
        if user_input.lower() == "start":
            return await self._generate_phase1()
        else:
            return "请输入 'start' 开始探索。"
    
    async def _generate_phase1(self) -> str:
        """第一阶段：生成前5章"""
        system_prompt = self._build_system_prompt()
        
        user_prompt = f"""
**🚀 第一阶段：生成前{self.phase1_count}章**

请生成前{self.phase1_count}章故事，为后续发展预留空间。

**要求：**
1. 生成{self.phase1_count}个章节
2. 每章内容80-120字符
3. 提供A、B、C、D四个选项
4. 故事要有连贯性
5. 为后续章节预留发展空间

**格式：**
第1章：
[故事内容]
A. [选项A]
B. [选项B]
C. [选项C]
D. [选项D]

第2章：
[故事内容]
A. [选项A]
B. [选项B]
C. [选项C]
D. [选项D]

...（继续到第5章）
"""
        
        try:
            # 应用限流
            await self.rate_limiter.acquire()
            await self.daily_limiter.acquire()
            
            logging.info(f"第一阶段：生成前{self.phase1_count}章...")
            start_time = time.time()
            
            response = await self._call_gemini_with_retry(system_prompt, user_prompt)
            
            # 解析前5章
            self.phase1_chapters = self._parse_chapters(response)
            self.phase1_complete = True
            
            generation_time = time.time() - start_time
            logging.info(f"第一阶段完成！耗时：{generation_time:.2f}秒，生成{len(self.phase1_chapters)}章")
            
            # 返回第一章
            return self._get_chapter_content(1)
            
        except Exception as e:
            logging.error(f"第一阶段生成失败: {str(e)}")
            return self._generate_default_chapter(1)
    
    async def _generate_phase2(self) -> str:
        """第二阶段：生成后5章"""
        system_prompt = self._build_system_prompt()
        
        # 构建详细的用户选择历史
        choice_history = " -> ".join([f"第{i+1}章选择{choice}" for i, choice in enumerate(self.user_choices)])
        
        # 获取第5章的选项内容（关键信息）
        chapter_5_options = ""
        if f"chapter_5" in self.phase1_chapters:
            chapter_5 = self.phase1_chapters["chapter_5"]
            options = chapter_5.get('options', [])
            chapter_5_options = "\n".join([f"   {opt}" for opt in options])
        
        # 获取第5章的内容
        chapter_5_content = ""
        if f"chapter_5" in self.phase1_chapters:
            chapter_5 = self.phase1_chapters["chapter_5"]
            chapter_5_content = chapter_5.get('content', '')
        
        user_prompt = f"""
**🎯 第二阶段：生成后{self.phase2_count}章**

**用户选择历史：** {choice_history}

**第5章内容（关键章节）：**
{chapter_5_content}

**第5章选项：**
{chapter_5_options}

**用户在第5章的选择：** {self.user_choices[-1] if self.user_choices else '未知'}

请基于以上信息，特别是第5章的内容和用户的选择，生成第{self.phase1_count + 1}到第{self.total_chapters}章。

**重要要求：**
1. 生成{self.phase2_count}个章节（第{self.phase1_count + 1}-{self.total_chapters}章）
2. 每章内容80-120字符
3. 提供A、B、C、D四个选项
4. **必须基于第5章用户的选择来延续故事**
5. **确保第6章直接承接第5章选择的结果**
6. **保持整个故事的逻辑连贯性**
7. 最后包含灵魂伴侣分析

**格式：**
第{self.phase1_count + 1}章：
[基于第5章选择{self.user_choices[-1] if self.user_choices else 'A'}的故事延续]
A. [选项A]
B. [选项B]
C. [选项C]
D. [选项D]

...（继续到第{self.total_chapters}章）

**灵魂伴侣分析：**
[基于完整选择路径的分析]
"""
        
        try:
            # 应用限流
            await self.rate_limiter.acquire()
            await self.daily_limiter.acquire()
            
            logging.info(f"第二阶段：生成后{self.phase2_count}章...")
            start_time = time.time()
            
            response = await self._call_gemini_with_retry(system_prompt, user_prompt)
            
            # 解析后5章
            self.phase2_chapters = self._parse_chapters(response)
            self.phase2_complete = True
            
            generation_time = time.time() - start_time
            logging.info(f"第二阶段完成！耗时：{generation_time:.2f}秒，生成{len(self.phase2_chapters)}章")
            
            return True
            
        except Exception as e:
            logging.error(f"第二阶段生成失败: {str(e)}")
            return False
    
    async def _call_gemini_with_retry(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
        """带重试机制的Gemini API调用"""
        for attempt in range(max_retries):
            try:
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = self.model.generate_content(full_prompt)
                
                if response.text:
                    return response.text.strip()
                else:
                    raise Exception("Gemini返回空响应")
                    
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Gemini API调用失败 (第{attempt + 1}次): {error_msg}")
                
                if "429" in error_msg or "quota" in error_msg.lower():
                    # 处理429错误
                    await self.rate_limiter.handle_429_error()
                elif attempt < max_retries - 1:
                    # 其他错误，等待后重试
                    wait_time = 2 ** attempt  # 指数退避
                    logging.info(f"等待{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    # 最后一次重试失败
                    raise e
        
        raise Exception("所有重试都失败了")
    
    def _parse_chapters(self, story_text: str) -> Dict[str, Dict]:
        """解析章节文本"""
        chapters = {}
        import re
        
        chapter_pattern = r'第(\d+)章[：:]\s*([\s\S]*?)(?=第\d+章[：:]|灵魂伴侣分析|$)'
        matches = re.findall(chapter_pattern, story_text)
        
        for chapter_num, content in matches:
            lines = content.strip().split('\n')
            story_content = ""
            options = []
            
            for line in lines:
                line = line.strip()
                if line.startswith(('A.', 'B.', 'C.', 'D.')):
                    options.append(line)
                elif line and not line.startswith('第'):
                    story_content += line + '\n'
            
            chapters[f"chapter_{chapter_num}"] = {
                'content': story_content.strip(),
                'options': options[:4]
            }
        
        # 提取灵魂伴侣分析
        analysis_pattern = r'灵魂伴侣分析[：:]\s*([\s\S]*)'
        analysis_match = re.search(analysis_pattern, story_text)
        if analysis_match:
            chapters['soul_analysis'] = analysis_match.group(1).strip()
        
        return chapters
    
    async def process_choice(self, user_choice: str, choice_text: str = "") -> str:
        """处理用户选择 - 两次生成模式"""
        user_choice = user_choice.strip().upper()
        
        if user_choice not in ['A', 'B', 'C', 'D']:
            return "请选择A、B、C或D。"
        
        # 记录选择
        self.user_choices.append(user_choice)
        self.user_choice_texts.append(choice_text)
        
        # 检查是否达到最大章节数
        if self.current_chapter >= self.total_chapters:
            return await self._generate_ending()
        
        # 进入下一章
        self.current_chapter += 1
        
        # 判断是否需要触发第二阶段生成
        if self.current_chapter == self.phase1_count + 1 and not self.phase2_complete:
            # 触发第二阶段生成
            logging.info("触发第二阶段生成...")
            success = await self._generate_phase2()
            if not success:
                return self._generate_default_chapter(self.current_chapter)
        
        # 获取章节内容
        response = self._get_chapter_content(self.current_chapter)
        
        # 记录交互
        self._record_interaction(user_choice, choice_text, response)
        
        return response
    
    def _get_chapter_content(self, chapter_num: int) -> str:
        """获取章节内容"""
        chapter_key = f"chapter_{chapter_num}"
        
        # 优先从第一阶段获取
        if chapter_key in self.phase1_chapters:
            chapter = self.phase1_chapters[chapter_key]
            content = chapter['content']
            options = chapter['options']
            
            response = f"{content}\n\n"
            for option in options:
                response += f"{option}\n"
            
            return response
        
        # 从第二阶段获取
        elif chapter_key in self.phase2_chapters:
            chapter = self.phase2_chapters[chapter_key]
            content = chapter['content']
            options = chapter['options']
            
            response = f"{content}\n\n"
            for option in options:
                response += f"{option}\n"
            
            return response
        
        else:
            return self._generate_default_chapter(chapter_num)
    
    def _generate_default_chapter(self, chapter_num: int) -> str:
        """生成默认章节"""
        return f"你继续探索，来到了第{chapter_num}章。\n\nA. 继续前进\nB. 观察周围\nC. 寻找线索\nD. 改变方向"
    
    async def _generate_ending(self) -> str:
        """生成结尾"""
        if 'soul_analysis' in self.phase2_chapters:
            analysis = self.phase2_chapters['soul_analysis']
        else:
            analysis = "基于你在探索过程中的选择，你展现出了独特的个性特征。你的灵魂伴侣应该是一个能够理解你内心世界的人。"
        
        ending = f"""经过这次灵魂探索之旅，你发现了自己内心深处的真实想法。

---

**灵魂伴侣类型分析**
{analysis}

---

再一次进入探索之旅吗？"""
        
        return ending
    
    def _record_interaction(self, user_choice: str, choice_text: str, ai_response: str):
        """记录交互历史"""
        interaction = {
            'chapter': self.current_chapter,
            'timestamp': datetime.now(UTC),
            'user_choice': user_choice,
            'choice_text': choice_text,
            'ai_response': ai_response
        }
        self.interaction_history.append(interaction)
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""
你是一个专业的灵魂探索机器人。

**核心原则：**
1. 故事内容简洁有趣（80-120字符）
2. 提供A、B、C、D四个选项
3. **故事连贯性是最高优先级**
4. 最多{self.total_chapters}个章节

**连贯性要求：**
- 每个章节必须基于前一章的选择结果
- 选项之间要有逻辑关联
- 故事发展要符合用户的选择路径
- 避免突然的场景跳跃或逻辑断裂

当前状态：
- 当前章节：{self.current_chapter}
- 用户选择：{self.user_choices}
- 第一阶段完成：{self.phase1_complete}
- 第二阶段完成：{self.phase2_complete}
"""
    
    def get_session_info(self) -> Dict:
        """获取会话信息"""
        return {
            'current_chapter': self.current_chapter,
            'total_chapters': self.total_chapters,
            'user_choices': self.user_choices,
            'phase1_complete': self.phase1_complete,
            'phase2_complete': self.phase2_complete,
            'phase1_chapters': len(self.phase1_chapters),
            'phase2_chapters': len(self.phase2_chapters),
            'interaction_history': len(self.interaction_history),
            'api_calls': 2 if self.phase2_complete else 1,
            'rate_limit_info': {
                'minute_requests': len(self.rate_limiter.requests),
                'daily_requests': len(self.daily_limiter.requests)
            }
        }
    
    def reset_session(self):
        """重置会话"""
        self.current_chapter = 1
        self.user_choices = []
        self.user_choice_texts = []
        self.story_history = []
        self.interaction_history = []
        self.phase1_chapters = {}
        self.phase2_chapters = {}
        self.phase1_complete = False
        self.phase2_complete = False
        logging.info("带限流器的两次生成会话已重置") 