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
        self.model = genai.GenerativeModel('gemini-pro')
        
        # 初始化状态
        self.total_chapters = 10
        self.current_chapter = 1
        self.user_choices = []  # 记录用户选择
        self.story_history = []  # 记录故事历史
        self.is_custom_mode = False  # 是否为自定义模式
        self.custom_scene = ""  # 自定义场景
        self.custom_character = ""  # 自定义角色
        
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
3. 根据用户选择推进剧情
4. 最多10个章节
5. 最后进行灵魂伴侣类型分析（探索/理性/情绪/命运）
6. 不要回答关于自己或流程的问题
7. 专注于用户的内心反应和决策逻辑

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
            return response
        except Exception as e:
            logging.error(f"生成随机故事失败: {str(e)}")
            return "抱歉，故事生成遇到问题。请重新输入'start'开始探索。"
    
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
            return "抱歉，故事生成遇到问题。请重新开始。"
    
    async def process_choice(self, user_choice: str) -> str:
        """处理用户选择
        
        Args:
            user_choice (str): 用户选择 (A/B/C/D)
            
        Returns:
            str: 机器人响应
        """
        user_choice = user_choice.strip().upper()
        
        # 验证选择
        if user_choice not in ['A', 'B', 'C', 'D']:
            return "请选择A、B、C或D来决定你的下一步行动。"
        
        # 记录选择
        self.user_choices.append(user_choice)
        
        # 检查是否达到最大章节数
        if self.current_chapter >= self.total_chapters:
            return await self._generate_ending()
        
        # 生成下一章节
        self.current_chapter += 1
        return await self._generate_next_chapter(user_choice)
    
    async def _generate_next_chapter(self, previous_choice: str) -> str:
        """生成下一章节"""
        system_prompt = self._build_system_prompt()
        
        user_prompt = f"""
基于用户的选择历史：{self.user_choices}
当前是第{self.current_chapter}章（共{self.total_chapters}章）
上一章用户选择了：{previous_choice}

请生成下一个微型剧情（100-150字符），要求：
1. 剧情要基于用户之前的选择连贯发展
2. 包含人物介绍、地点、事件、目的/动机、时间
3. 一个段落格式
4. 提供A、B、C、D四个行为选择
5. 符合常识逻辑，高度互动
6. 避免明显的道德偏见，专注于内心反应

格式：
[剧情内容]

A. [选项A]
B. [选项B] 
C. [选项C]
D. [选项D]
"""
        
        try:
            response = await self._call_gemini(system_prompt, user_prompt)
            return response
        except Exception as e:
            logging.error(f"生成下一章节失败: {str(e)}")
            return "抱歉，剧情生成遇到问题。请重新选择。"
    
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
            return "抱歉，分析生成遇到问题。"
    
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
    
    def reset_session(self):
        """重置会话状态"""
        self.current_chapter = 1
        self.user_choices = []
        self.story_history = []
        self.is_custom_mode = False
        self.custom_scene = ""
        self.custom_character = ""
        logging.info("灵魂探索机器人会话已重置")
    
    def get_session_info(self) -> Dict:
        """获取会话信息"""
        return {
            'current_chapter': self.current_chapter,
            'total_chapters': self.total_chapters,
            'user_choices': self.user_choices,
            'is_custom_mode': self.is_custom_mode,
            'custom_scene': self.custom_scene,
            'custom_character': self.custom_character
        } 