# 🌟 灵魂探索机器人 (Soul Explorer Bot)

一个基于AI的互动式灵魂探索机器人，通过苏格拉底式对话帮助用户了解自己的灵魂伴侣类型。

## 🎯 项目概述

灵魂探索机器人是一个专业的**剧本编导**和**灵魂伴侣行为分析师**，通过创造性的互动故事引导用户进行自我探索，最终分析出用户的灵魂伴侣类型。

### 核心功能
- **剧本编导**: 编写引人入胜的微型剧情（100-150字符）
- **行为分析**: 分析用户选择背后的逻辑和动机
- **灵魂伴侣类型推导**: 基于行为模式推断灵魂伴侣类型（探索/理性/情绪/命运）
- **双模式探索**: 支持随机模式和自定义模式

## 🚀 快速开始

### 环境要求
- Python 3.8+
- MongoDB
- Telegram Bot Token
- Google Gemini API Key

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置环境变量
复制 `env_template.txt` 为 `.env` 并填写以下配置：

```env
# Telegram Bot配置
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Gemini AI配置
GEMINI_API_KEY=your_gemini_api_key

# MongoDB配置
MONGO_URI=your_mongodb_connection_string
MONGO_DATABASE=your_database_name
MONGO_USERNAME=your_username
MONGO_PASSWORD=your_password

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### 运行机器人
```bash
# 运行灵魂探索机器人
python main_soul_explorer.py

# 运行测试
python test_soul_explorer.py
```

## 🎮 使用指南

### 开始探索
1. 在Telegram中搜索你的机器人
2. 发送 `/start` 开始探索
3. 选择探索模式：
   - **start**: 随机生成剧情和角色
   - **自定义**: 自定义场景和角色设定

### 探索流程
1. **入口选择**: 选择随机或自定义模式
2. **剧情体验**: 体验10个章节的微型剧情
3. **选择决策**: 每个章节提供A、B、C、D四个选项
4. **结果分析**: 获得灵魂伴侣类型分析

## 📁 项目结构

```
CupidShirin_choice_game/
├── prompt/                          # 提示词文件
│   ├── soul_explorer_role.md       # 角色定义
│   ├── soul_explorer_object.md     # 目标和要求
│   ├── soul_explorer_skill.md      # 技能定义
│   ├── soul_explorer_constraint.md # 约束条件
│   └── soul_explorer_workflow.md   # 工作流程
├── soul_explorer_bot.py            # 灵魂探索机器人类
├── main_soul_explorer.py           # 主程序
├── test_soul_explorer.py           # 测试脚本
├── config.py                       # 配置文件
├── requirements.txt                # 依赖包
└── README_soul_explorer.md         # 本文档
```

## 🧠 AI功能特性

### 提示词系统
- **角色定义**: 专业的剧本编导和灵魂伴侣行为分析师
- **目标要求**: 创造高度互动的微型剧情
- **技能系统**: 9大写作技能，包括五感描写、人物描写等
- **约束条件**: 严格的字符限制和逻辑要求
- **工作流程**: 完整的探索流程设计

### 灵魂伴侣类型
基于用户选择分析四种灵魂伴侣类型：
- **探索型**: 喜欢冒险和发现新事物
- **理性型**: 注重逻辑和理性思考
- **情绪型**: 重视情感和直觉
- **命运型**: 相信命运和缘分

## 🧪 测试

### 自动测试
```bash
python test_soul_explorer.py
# 选择 "1. 自动测试"
```

### 交互式测试
```bash
python test_soul_explorer.py
# 选择 "2. 交互式测试"
```

---

🌟 **开始你的灵魂探索之旅吧！** 🌟 