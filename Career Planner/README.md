# 职业规划助理 (Career Planning Assistant)

这是一个基于Streamlit开发的职业规划助理，通过AI分析用户的学术背景和职业意向，生成个性化的职业规划报告。

## 功能特性

- **用户信息收集**：获取用户的本科院校、专业、意向行业和职位信息
- **成绩单分析**：使用Qwen视觉模型自动识别并提取图片格式成绩单中的信息
- **知识库集成**：使用模拟数据库查询相关职业和行业信息
- **职业规划报告**：生成详细的职业规划报告，包含文字描述和可视化图表
- **灵活的助理设置**：允许自定义职业规划助理和交稿助理的角色设定、任务描述和输出格式
- **模型选择**：可为不同阶段选择不同的大语言模型
- **API状态监测**：检测所需API的连接状态和配置正确性
- **LangSmith监测**：集成LangSmith来监控和分析AI生成链

## 安装与设置

### 环境要求

- Python 3.8+
- 相关Python包（见requirements.txt）
- OpenRouter API密钥（用于访问多种LLM模型）
- Qwen API密钥（用于成绩单图像分析）
- LangSmith API密钥（用于监控和分析）

### 安装步骤

1. 克隆此仓库到本地：
```bash
git clone <repository-url>
cd career-planner
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 如果在本地运行，创建.streamlit/secrets.toml文件：
```toml
OPENROUTER_API_KEY = "your_openrouter_api_key_here"
QWEN_API_KEY = "your_qwen_api_key_here"
LANGSMITH_API_KEY = "your_langsmith_api_key_here"
LANGSMITH_PROJECT = "career-planner"  # 可选
```

4. 如果部署在Streamlit Cloud，在应用设置中配置相应的secrets。

## 使用方法

1. 启动应用：
```bash
streamlit run app.py
```

2. 在浏览器中访问应用（通常为http://localhost:8501）

3. 使用三个主要选项卡：
   - **信息收集**：输入个人信息并上传成绩单
   - **助理设置**：自定义AI助理的角色、任务和输出格式，选择使用的模型
   - **API状态**：检查API连接和配置状态

## 模型使用

本应用支持以下AI模型：
- **Qwen 3 32B** (qwen/qwen3-32b:free)
- **DeepSeek Chat v3** (deepseek/deepseek-chat-v3-0324:free)
- **Qwen Max** (qwen/qwen-max)

可以为职业规划助理和交稿助理分别选择不同的模型。成绩单分析固定使用Qwen 2.5 VL 72B模型。

## 知识库设计

应用使用模拟数据库，包含以下结构：
- 行业（Industries）
  - 职位（Positions）
    - 技能要求（Skills）
    - 学历要求（Education）
    - 薪资范围（Salary）
    - 发展前景（Prospects）
- 专业（Majors）
  - 适合行业（Suitable Industries）
  - 适合职位（Suitable Positions）
  - 核心技能（Core Skills）
  - 职业路径（Career Paths）

## 注意事项

- 成绩单只支持图片格式（PNG、JPG、JPEG）
- 本科专业、意向行业和意向岗位必须至少填写一项
- 请确保API密钥正确设置并具有足够的使用额度
- LangSmith监测可帮助追踪每次生成的完整过程 