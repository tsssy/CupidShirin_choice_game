import logging
import random
import asyncio
from typing import List, Dict, Optional, Tuple
import google.generativeai as genai
from datetime import datetime, UTC

class SoulExplorerBot:
    """灵魂探索机器人 - 基于AI的剧本编导和灵魂伴侣行为分析师"""
    
    def __init__(self, api_key: str):
        """初始化灵魂探索机器人
        
        Args:
            api_key (str): Gemini API密钥
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 初始化状态
        self.total_chapters = 10
        self.current_chapter = 1
        self.user_choices = []  # 记录用户选择
        self.user_choice_texts = []  # 记录用户选择的具体文本内容
        self.story_history = []  # 记录故事历史
        self.interaction_history = []  # 记录用户与AI的交互历史
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
        
        logging.info("灵魂探索机器人初始化完成")
    
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
    
    def _build_story_context(self, previous_choice: str) -> str:
        """构建故事上下文，确保连贯性"""
        if self.current_chapter == 1:
            # 第一章，初始化故事状态
            return "故事开始"
        
        # 基于用户选择更新故事状态
        if previous_choice == "A":
            # 用户选择了A，通常是主动探索
            self.current_context = "主动探索当前环境"
        elif previous_choice == "B":
            # 用户选择了B，通常是直觉或信任
            self.current_context = "依靠直觉做出选择"
        elif previous_choice == "C":
            # 用户选择了C，通常是寻求帮助或谨慎
            self.current_context = "谨慎行事，寻求帮助或观察"
        elif previous_choice == "D":
            # 用户选择了D，通常是放弃或离开
            self.current_context = "选择离开或放弃当前路径"
            # 强制清空当前地点，确保场景转换
            self.current_location = ""
            logging.info(f"用户选择D，强制清空地点，准备场景转换")
        
        return f"基于选择{previous_choice}，当前情境：{self.current_context}"
    
    def _extract_story_state(self, story_text: str):
        """从故事文本中提取状态信息"""
        # 提取地点信息
        location_keywords = ["图书馆", "沙滩", "花园", "房间", "街道", "森林", "城堡", "洞穴", "咖啡厅", "公园", "书店", "博物馆", "广场", "小巷", "天台", "地下室"]
        for keyword in location_keywords:
            if keyword in story_text:
                self.current_location = keyword
                break
        
        # 提取时间信息
        time_keywords = ["深夜", "傍晚", "清晨", "白天", "夜晚", "黄昏", "黎明", "午后", "午夜"]
        for keyword in time_keywords:
            if keyword in story_text:
                self.current_time = keyword
                break
        
        # 提取主题信息
        theme_keywords = ["神秘", "探索", "爱情", "友情", "冒险", "发现", "寻找", "解开", "思考", "感受", "体验"]
        for keyword in theme_keywords:
            if keyword in story_text:
                self.story_theme = keyword
                break
    
    def _record_interaction(self, user_choice: str, choice_text: str, ai_response: str):
        """记录用户与AI的交互历史"""
        interaction = {
            'chapter': self.current_chapter,
            'timestamp': datetime.now(UTC),
            'user_choice': user_choice,
            'choice_text': choice_text,
            'ai_response': ai_response,
            'story_state': {
                'location': self.current_location,
                'time': self.current_time,
                'context': self.current_context,
                'theme': self.story_theme
            }
        }
        self.interaction_history.append(interaction)
        logging.info(f"记录交互历史 - 章节: {self.current_chapter}, 选择: {user_choice}")
    
    def _get_story_context_for_ai(self) -> str:
        """获取故事上下文供AI使用"""
        context_parts = []
        
        if self.current_location:
            context_parts.append(f"当前地点：{self.current_location}")
        if self.current_time:
            context_parts.append(f"当前时间：{self.current_time}")
        if self.current_context:
            context_parts.append(f"当前情境：{self.current_context}")
        if self.story_theme:
            context_parts.append(f"故事主题：{self.story_theme}")
        
        if self.user_choices:
            context_parts.append(f"用户选择历史：{self.user_choices}")
        
        return " | ".join(context_parts) if context_parts else "故事开始"
    
    def _check_scene_transition(self, user_choice: str):
        """检查用户选择是否涉及场景转换"""
        # 场景转换关键词
        leave_keywords = ["离开", "走出", "退出", "放弃", "远离"]
        enter_keywords = ["进入", "走进", "来到", "到达", "前往"]
        move_keywords = ["走向", "前往", "去往", "奔向", "跑向"]
        
        # 获取用户选择对应的选项文本（这里需要从上一章的故事中提取）
        # 由于我们无法直接获取选项文本，我们基于选择模式来判断
        
        # 如果用户选择D，通常涉及离开
        if user_choice == "D":
            self.current_location = ""
            logging.info(f"检测到场景转换（选择D），清空当前地点")
        # 如果用户选择A，通常涉及进入或探索
        elif user_choice == "A" and self.current_location:
            # 检查是否在特定场景中
            if "图书馆" in self.current_location:
                # 在图书馆选择A，可能涉及离开
                self.current_location = ""
                logging.info(f"检测到场景转换（在图书馆选择A），清空当前地点")
        
        # 如果当前地点为空，说明需要场景转换
        if not self.current_location:
            logging.info(f"准备场景转换，当前地点已清空")
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        system_prompt = f"""
你是一个专业的灵魂探索机器人，专门帮助用户通过互动故事了解自己的灵魂伴侣类型。

{self.prompts.get('role', '')}

{self.prompts.get('object', '')}

{self.prompts.get('skill', '')}

{self.prompts.get('constraint', '')}

{self.prompts.get('workflow', '')}

重要规则：
1. 每个剧情必须在100-150字符以内
2. 提供A、B、C、D四个选项
3. **严格根据用户选择推进剧情和转换场景**
4. 最多10个章节
5. 最后进行灵魂伴侣类型分析（探索/理性/情绪/命运）
6. 不要回答关于自己或流程的问题
7. 专注于用户的内心反应和决策逻辑
8. **场景转换规则：用户选择离开某地时，必须转移到新场景**

当前状态：
- 总章节数：{self.total_chapters}
- 当前章节：{self.current_chapter}
- 用户选择历史：{self.user_choices}
- 自定义模式：{self.is_custom_mode}
"""
        return system_prompt
    
    async def start_exploration(self, user_input: str) -> str:
        """开始灵魂探索
        
        Args:
            user_input (str): 用户输入
            
        Returns:
            str: 机器人响应
        """
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
            # 无效输入
            return "你可以随时回来开始灵魂之旅。你可以输入'start'或'自定义'来开启这次灵魂探索!!!"
    
    async def _generate_random_story(self, adj: str, noun: str, verb: str) -> str:
        """生成随机故事开头"""
        system_prompt = self._build_system_prompt()
        
        user_prompt = f"""
请基于以下随机元素生成第一个微型剧情（100-150字符）：
- 形容词：{adj}
- 名词：{noun}  
- 动词：{verb}

要求：
1. 包含人物介绍、地点、事件、目的/动机、时间
2. 一个段落格式
3. 提供A、B、C、D四个行为选择
4. 符合常识逻辑，高度互动

格式：
[剧情内容]

A. [选项A]
B. [选项B] 
C. [选项C]
D. [选项D]
"""
        
        try:
            response = await self._call_gemini(system_prompt, user_prompt)
            self.current_chapter = 1
            
            # 提取并设置故事状态
            self._extract_story_state(response)
            logging.info(f"故事状态初始化 - 地点: {self.current_location}, 时间: {self.current_time}, 主题: {self.story_theme}")
            
            return response
        except Exception as e:
            logging.error(f"生成随机故事失败: {str(e)}")
            # 静默重试，不向用户显示错误
            return await self._retry_generate_random_story(adj, noun, verb)
    
    async def handle_custom_setup(self, user_input: str) -> str:
        """处理自定义设置"""
        if not self.is_custom_mode:
            return "请先输入'自定义'来进入自定义模式。"
        
        # 解析用户输入的场景和角色
        if "场景：" in user_input and "角色：" in user_input:
            try:
                scene_part = user_input.split("场景：")[1].split("，角色：")[0]
                character_part = user_input.split("角色：")[1]
                self.custom_scene = scene_part.strip()
                self.custom_character = character_part.strip()
                
                return await self._generate_custom_story()
            except:
                return "格式错误。请使用格式：'场景：[场景描述]，角色：[角色描述]'"
        else:
            return "请使用正确格式：'场景：[场景描述]，角色：[角色描述]'"
    
    async def _generate_custom_story(self) -> str:
        """生成自定义故事开头"""
        system_prompt = self._build_system_prompt()
        
        user_prompt = f"""
请基于以下自定义设定生成第一个微型剧情（100-150字符）：
- 场景：{self.custom_scene}
- 角色：{self.custom_character}

要求：
1. 包含人物介绍、地点、事件、目的/动机、时间
2. 一个段落格式
3. 提供A、B、C、D四个行为选择
4. 符合常识逻辑，高度互动

格式：
[剧情内容]

A. [选项A]
B. [选项B] 
C. [选项C]
D. [选项D]
"""
        
        try:
            response = await self._call_gemini(system_prompt, user_prompt)
            self.current_chapter = 1
            return response
        except Exception as e:
            logging.error(f"生成自定义故事失败: {str(e)}")
            # 静默重试，不向用户显示错误
            return await self._retry_generate_custom_story()
    
    async def process_choice(self, user_choice: str, choice_text: str = "") -> str:
        """处理用户选择
        
        Args:
            user_choice (str): 用户选择 (A/B/C/D)
            choice_text (str): 用户选择的具体文本内容
            
        Returns:
            str: 机器人响应
        """
        user_choice = user_choice.strip().upper()
        
        # 验证选择
        if user_choice not in ['A', 'B', 'C', 'D']:
            return "请选择A、B、C或D来决定你的下一步行动。"
        
        # 记录选择
        self.user_choices.append(user_choice)
        self.user_choice_texts.append(choice_text)  # 记录选择的具体文本
        
        # 检查是否达到最大章节数
        if self.current_chapter >= self.total_chapters:
            return await self._generate_ending()
        
        # 检查用户选择是否涉及场景转换
        self._check_scene_transition(user_choice)
        
        # 生成下一章节
        self.current_chapter += 1
        response = await self._generate_next_chapter(user_choice, choice_text)
        
        # 记录交互历史
        self._record_interaction(user_choice, choice_text, response)
        
        return response
    
    async def _generate_next_chapter(self, previous_choice: str, choice_text: str = "") -> str:
        """生成下一章节"""
        system_prompt = self._build_system_prompt()
        
        # 获取上一章的故事内容作为上下文
        story_context = self._get_story_context_for_ai()
        
        user_prompt = f"""
**🎯 续写模式：基于用户具体选择构建连贯故事！**

当前故事状态：
- 地点：{self.current_location}
- 时间：{self.current_time}
- 情境：{self.current_context}
- 主题：{self.story_theme}

用户选择历史：{self.user_choices}
当前是第{self.current_chapter}章（共{self.total_chapters}章）

**用户刚刚选择了：{previous_choice}**
**用户选择的具体内容：{choice_text}**

**🎯 续写指导原则：**
1. **直接续写用户选择** - 如果用户选择"进入咖啡馆"，直接描述在咖啡馆内的场景和感受
2. **保持行为连贯性** - 用户选择做什么，故事就必须描述这个行为的结果和后续
3. **场景自然延续** - 新场景必须基于用户选择的行为自然发展
4. **情感状态延续** - 保持用户选择时的情感状态和动机

**续写示例：**
- 用户选择"进入咖啡馆" → 描述咖啡馆内的氛围、人物、感受
- 用户选择"拿出手机搜索" → 描述搜索过程、发现的信息、新的选择
- 用户选择"坐在长椅上思考" → 描述思考的内容、周围环境、内心感受
- 用户选择"继续往前走" → 描述前方的新发现、环境变化、新的选择

**禁止行为：**
❌ 忽略用户选择的具体内容
❌ 跳跃到不相关的场景
❌ 重复之前的场景描述
❌ 违背用户选择的行为逻辑

请生成下一个微型剧情（100-150字符），要求：
1. **直接续写用户选择：{choice_text}**
2. **描述选择后的具体场景和感受**
3. **基于选择行为提供新的选项**
4. 一个段落格式
5. 提供A、B、C、D四个行为选择
6. 符合常识逻辑，高度互动
7. 避免明显的道德偏见，专注于内心反应

格式：
[剧情内容]

A. [选项A]
B. [选项B] 
C. [选项C]
D. [选项D]
"""
        
        try:
            response = await self._call_gemini(system_prompt, user_prompt)
            
            # 更新故事状态
            self._extract_story_state(response)
            logging.info(f"故事状态更新 - 地点: {self.current_location}, 时间: {self.current_time}, 主题: {self.story_theme}")
            
            return response
        except Exception as e:
            logging.error(f"生成下一章节失败: {str(e)}")
            # 静默重试，不向用户显示错误
            return await self._retry_generate_next_chapter(previous_choice)
    
    async def _generate_ending(self) -> str:
        """生成故事结尾和灵魂伴侣分析"""
        system_prompt = self._build_system_prompt()
        
        user_prompt = f"""
用户的选择历史：{self.user_choices}
总章节数：{self.total_chapters}

请生成：
1. 完整的故事结尾（100-150字符，不要提供A-D选项）
2. 基于用户选择分析灵魂伴侣类型（探索/理性/情绪/命运）
3. 200字左右的灵魂伴侣分析段落

格式：
[故事结尾]

---

**灵魂伴侣类型分析**
[分析内容，200字左右]

---

再一次进入探索之旅吗？
"""
        
        try:
            response = await self._call_gemini(system_prompt, user_prompt)
            return response
        except Exception as e:
            logging.error(f"生成结尾分析失败: {str(e)}")
            # 静默重试，不向用户显示错误
            return await self._retry_generate_ending()
    
    async def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """调用Gemini API"""
        try:
            # 构建完整提示词
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # 调用Gemini
            response = self.model.generate_content(full_prompt)
            
            if response.text:
                return response.text.strip()
            else:
                raise Exception("Gemini返回空响应")
                
        except Exception as e:
            logging.error(f"Gemini API调用失败: {str(e)}")
            raise e
    
    async def _retry_generate_random_story(self, adj: str, noun: str, verb: str, max_retries: int = 3) -> str:
        """重试生成随机故事"""
        for attempt in range(max_retries):
            try:
                logging.info(f"重试生成随机故事 (第 {attempt + 1} 次)")
                return await self._generate_random_story(adj, noun, verb)
            except Exception as e:
                logging.error(f"重试生成随机故事失败 (第 {attempt + 1} 次): {str(e)}")
                if attempt == max_retries - 1:
                    # 最后一次重试失败，返回默认故事
                    return self._generate_default_story()
                await asyncio.sleep(1)  # 等待1秒后重试
    
    async def _retry_generate_custom_story(self, max_retries: int = 3) -> str:
        """重试生成自定义故事"""
        for attempt in range(max_retries):
            try:
                logging.info(f"重试生成自定义故事 (第 {attempt + 1} 次)")
                return await self._generate_custom_story()
            except Exception as e:
                logging.error(f"重试生成自定义故事失败 (第 {attempt + 1} 次): {str(e)}")
                if attempt == max_retries - 1:
                    # 最后一次重试失败，返回默认故事
                    return self._generate_default_story()
                await asyncio.sleep(1)  # 等待1秒后重试
    
    async def _retry_generate_next_chapter(self, previous_choice: str, choice_text: str = "", max_retries: int = 3) -> str:
        """重试生成下一章节"""
        for attempt in range(max_retries):
            try:
                logging.info(f"重试生成下一章节 (第 {attempt + 1} 次)")
                return await self._generate_next_chapter(previous_choice, choice_text)
            except Exception as e:
                logging.error(f"重试生成下一章节失败 (第 {attempt + 1} 次): {str(e)}")
                if attempt == max_retries - 1:
                    # 最后一次重试失败，返回默认章节
                    return self._generate_default_chapter(previous_choice)
                await asyncio.sleep(1)  # 等待1秒后重试
    
    async def _retry_generate_ending(self, max_retries: int = 3) -> str:
        """重试生成结尾分析"""
        for attempt in range(max_retries):
            try:
                logging.info(f"重试生成结尾分析 (第 {attempt + 1} 次)")
                return await self._generate_ending()
            except Exception as e:
                logging.error(f"重试生成结尾分析失败 (第 {attempt + 1} 次): {str(e)}")
                if attempt == max_retries - 1:
                    # 最后一次重试失败，返回默认结尾
                    return self._generate_default_ending()
                await asyncio.sleep(1)  # 等待1秒后重试
    
    def _generate_default_story(self) -> str:
        """生成默认故事（当API调用失败时使用）"""
        default_stories = [
            "你站在一个神秘的十字路口，四周弥漫着淡淡的雾气。前方有三条不同的道路，每条都通向未知的远方。你的内心充满了好奇和期待，想要探索这个神秘的世界。\n\nA. 选择左边的道路，那里有温暖的灯光\nB. 选择中间的道路，那里有古老的石阶\nC. 选择右边的道路，那里有清脆的鸟鸣\nD. 站在原地思考，观察周围的环境",
            
            "你发现自己置身于一个古老的图书馆中，书架高耸入云，空气中弥漫着书香。一本神秘的书从书架上掉落，发出清脆的响声。你感到一种莫名的吸引力。\n\nA. 立即捡起那本书，翻开阅读\nB. 先观察周围的环境，确保安全\nC. 询问图书管理员关于这本书的信息\nD. 将书放回原处，继续寻找其他书籍",
            
            "你来到一个美丽的花园，花朵在微风中轻轻摇曳。花园中央有一面古老的镜子，镜面闪烁着奇异的光芒。你感到镜子似乎在呼唤着你。\n\nA. 走近镜子，仔细观察镜中的自己\nB. 绕开镜子，探索花园的其他部分\nC. 触摸镜子，感受它的温度\nD. 闭上眼睛，聆听花园的声音"
        ]
        return random.choice(default_stories)
    
    def _generate_default_chapter(self, previous_choice: str) -> str:
        """生成默认章节（当API调用失败时使用）"""
        default_chapters = [
            "你继续前行，发现了一个小木屋。木屋的门半开着，里面传来温暖的火光。你感到一种家的温暖。\n\nA. 走进木屋，探索内部\nB. 在门外等待，观察情况\nC. 绕道而行，继续前进\nD. 返回原路，寻找其他方向",
            
            "你遇到了一位神秘的老人，他正在花园里修剪花朵。老人抬头看了你一眼，眼中闪烁着智慧的光芒。\n\nA. 主动上前打招呼，询问道路\nB. 保持距离，观察老人的行为\nC. 等待老人先开口说话\nD. 默默离开，不打扰老人",
            
            "你来到一个清澈的湖边，湖水倒映着天空的云彩。湖边有一艘小船，船桨静静地躺在船边。\n\nA. 登上小船，划向湖心\nB. 坐在湖边，欣赏风景\nC. 沿着湖边漫步，寻找其他路径\nD. 返回原路，选择其他方向"
        ]
        return random.choice(default_chapters)
    
    def _generate_default_ending(self) -> str:
        """生成默认结尾（当API调用失败时使用）"""
        return """经过这次灵魂探索之旅，你发现了自己内心深处的真实想法。每一个选择都反映了你的性格特点和价值观念。

---

**灵魂伴侣类型分析**
基于你在探索过程中的选择，你展现出了独特的个性特征。你倾向于在行动前深思熟虑，注重内心的感受和直觉。你的灵魂伴侣应该是一个能够理解你内心世界的人，能够与你进行深层次的交流，共同成长。

---

再一次进入探索之旅吗？"""
    
    def reset_session(self):
        """重置会话状态"""
        self.current_chapter = 1
        self.user_choices = []
        self.user_choice_texts = []
        self.story_history = []
        self.interaction_history = []
        self.is_custom_mode = False
        self.custom_scene = ""
        self.custom_character = ""
        
        # 重置故事状态
        self.current_location = ""
        self.current_time = ""
        self.current_context = ""
        self.story_theme = ""
        
        logging.info("灵魂探索机器人会话已重置")
    
    def get_session_info(self) -> Dict:
        """获取会话信息"""
        return {
            'current_chapter': self.current_chapter,
            'total_chapters': self.total_chapters,
            'user_choices': self.user_choices,
            'user_choice_texts': self.user_choice_texts,
            'interaction_history': self.interaction_history,
            'is_custom_mode': self.is_custom_mode,
            'custom_scene': self.custom_scene,
            'custom_character': self.custom_character,
            'current_location': self.current_location,
            'current_time': self.current_time,
            'current_context': self.current_context,
            'story_theme': self.story_theme,
            'story_history': self.story_history
        } 